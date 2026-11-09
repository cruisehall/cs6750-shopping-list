#!/usr/bin/env python3
"""
Voice shopping-list assistant: scripted terminal prototype.

Speech recognition is black-boxed. Whatever the user would say is chosen with
the arrow keys (fixed responses) or typed (free text). The assistant's lines
are printed, and optionally spoken with --speak (macOS system voice).

Setup:   none (standard library only; macOS/Linux/Windows terminals)
Run:     python3 shopping_assistant.py            (normal pacing)
         python3 shopping_assistant.py --speak    (assistant lines are spoken, macOS)
         python3 shopping_assistant.py --fast     (no pauses, for rehearsing)

Staged lists live in memory only, so every run starts from the same seed data.
"""

from __future__ import annotations

import argparse
import copy
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

WALK_ORDER = ["refrigerator", "freezer", "pantry", "spice cabinet"]
MAX_QTY = 50
FULL_INSTRUCTIONS_EVERY_LOCALE = False  # True repeats the long instructions at every locale

# Read-aloud pause between items: a base time plus time per character, to
# approximate "normal writing speed".
READ_PAUSE_BASE = 1.2
READ_PAUSE_PER_CHAR = 0.12

# --------------------------------------------------------------------------
# Seed data (hard-coded staging lists)
# --------------------------------------------------------------------------

SEED_LISTS = [
    {
        "name": "Creamy Tuscan Sausage Soup",
        "kind": "recipe",
        "items": [
            {"name": "Bay leaves", "locales": ["spice cabinet"]},
            {"name": "Italian sausage", "locales": ["refrigerator"]},
            {"name": "Russet potatoes", "locales": ["pantry"]},
            {"name": "Sun-dried tomatoes (in oil)", "locales": ["pantry", "refrigerator"]},
            # {"name": "Fennel seeds", "locales": ["spice cabinet"]},
            # {"name": "Half-and-half", "locales": ["refrigerator"]},
            # {"name": "Yellow onions", "locales": ["pantry"]},
            # {"name": "Baby spinach", "locales": ["refrigerator"]},
            # {"name": "Dried basil", "locales": ["spice cabinet"]},
            # {"name": "All-purpose flour", "locales": ["pantry"]},
            # {"name": "Unsalted butter", "locales": ["refrigerator"]},
            # {"name": "Cannellini beans (canned)", "locales": ["pantry"]},
        ],
    },
    {
        "name": "Staples",
        "kind": "staples",
        "items": [
            {"name": "eggs", "quantity": {"count": 12}, "locales": ["refrigerator"]},
            # {"name": "sliced cheese", "quantity": {"count": 8}, "locales": ["refrigerator"]},
            {"name": "sliced turkey", "locales": ["refrigerator"]},
            {"name": "milk", "quantity": {"gallons": 1}, "locales": ["refrigerator"]},
            # {"name": "bread", "quantity": {"loaves": 2}, "locales": ["pantry", "freezer"]},
        ],
    },
]

# Where items the user types in are assumed to live (stand-in for a real lookup).
# Anything not listed here falls back to DEFAULT_LOCALES.
INFERRED_LOCALES = {
    "honey": ["pantry"],
    "sesame seeds": ["pantry", "spice cabinet"],
    "edamame": ["refrigerator"],
    "salmon fillets": ["refrigerator"],
    "garlic powder": ["spice cabinet"],
    "jasmine rice": ["pantry"],
    "rice vinegar": ["pantry"],
    "white pepper": ["spice cabinet"],
    "scallions": ["refrigerator"],
    "toasted sesame oil": ["pantry"],
    "fresh ginger": ["refrigerator"],
    "soy sauce": ["pantry", "refrigerator"],
    # common refrigerator items, so they don't fall back to the pantry
    "milk": ["refrigerator"],
    "eggs": ["refrigerator"],
    "cheese": ["refrigerator"],
    "butter": ["refrigerator"],
    "yogurt": ["refrigerator"],
    "orange juice": ["refrigerator"],
    "ice cream": ["freezer"],
    "chocolate syrup": ["refrigerator"]
}
DEFAULT_LOCALES = ["pantry"]

# --------------------------------------------------------------------------
# Quantity helpers
# --------------------------------------------------------------------------

_SINGULAR = {"loaves": "loaf"}


def fmt_qty(q: dict) -> str:
    parts = []
    for unit, amount in q.items():
        if unit == "count":
            parts.append(str(amount))
        else:
            word = unit
            if amount == 1:
                word = _SINGULAR.get(unit, unit[:-1] if unit.endswith("s") else unit)
            parts.append(f"{amount} {word}")
    return " ".join(parts)


def upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


# --------------------------------------------------------------------------
# Session model
# --------------------------------------------------------------------------


@dataclass
class Entry:
    """One distinct item across all selected staging lists."""

    name: str
    locales: list
    sources: list = field(default_factory=list)  # (list name, quantity dict or None)
    status: str = "pending"  # pending | found | added

    def final_locale(self) -> str:
        return [l for l in WALK_ORDER if l in self.locales][-1]

    def remaining_locales_after(self, locale: str) -> list:
        order = [l for l in WALK_ORDER if l in self.locales]
        return order[order.index(locale) + 1:]


def build_entries(staged_lists: list) -> list:
    """Merge staged lists into distinct entries (a duplicated item is asked once)."""
    entries: dict = {}
    for lst in staged_lists:
        for it in lst["items"]:
            key = it["name"].strip().lower()
            if key not in entries:
                entries[key] = Entry(name=it["name"], locales=list(it["locales"]))
            e = entries[key]
            for loc in it["locales"]:
                if loc not in e.locales:
                    e.locales.append(loc)
            e.sources.append((lst["name"], it.get("quantity")))
    return list(entries.values())


def join_oxford(parts: list) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def summarize_lists(staged_lists: list, staples_phrase: str) -> str:
    parts = []
    for lst in staged_lists:
        n = len(lst["items"])
        if lst["kind"] == "staples":
            parts.append(f"{staples_phrase} of {n} staples")
        else:
            parts.append(f"{n} ingredients for {lst['name']}")
    return join_oxford(parts)


# --------------------------------------------------------------------------
# I/O layer (terminal). Tests swap this for a scripted version.
# --------------------------------------------------------------------------

DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
RESET = "\033[0m"


class _KeyMode:
    """Hold the terminal in single-key mode for a whole menu (so fast key presses aren't lost)."""

    def __enter__(self):
        if os.name != "nt":
            import termios
            import tty

            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *exc):
        if os.name != "nt":
            import termios

            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        return False


def _read_key() -> str:
    """Return 'up', 'down', 'enter', or another key. Call inside _KeyMode."""
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            return "enter"
        if ch in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        return ch
    import select

    fd = sys.stdin.fileno()
    ch = os.read(fd, 1).decode(errors="ignore")
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x1b":
        seq = ""
        while len(seq) < 2 and select.select([fd], [], [], 0.05)[0]:
            seq += os.read(fd, 1).decode(errors="ignore")
        return {"[A": "up", "[B": "down", "OA": "up", "OB": "down"}.get(seq, "")
    return ch


# A long-running speech engine (macOS JavaScript for Automation, run by the
# built-in osascript). Starting `say` for every line costs about a second of
# process and voice startup. This engine starts once, warms up the voice
# silently, then speaks each line it reads on stdin and answers "done".
_SPEAKER_JS = r"""
ObjC.import('AppKit');
ObjC.import('Foundation');
const synth = $.NSSpeechSynthesizer.alloc.init;
function waitUntilQuiet() {
  while (synth.isSpeaking)
    $.NSRunLoop.currentRunLoop.runUntilDate($.NSDate.dateWithTimeIntervalSinceNow(0.02));
}
synth.volume = 0; synth.startSpeakingString('warm up'); waitUntilQuiet(); synth.volume = 1;
const stdin = $.NSFileHandle.fileHandleWithStandardInput;
const stdout = $.NSFileHandle.fileHandleWithStandardOutput;
const done = $.NSString.alloc.initWithString('done\n').dataUsingEncoding($.NSUTF8StringEncoding);
let buf = '';
while (true) {
  const data = stdin.availableData;
  if (data.length == 0) break;
  buf += $.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding).js;
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i);
    buf = buf.slice(i + 1);
    synth.startSpeakingString(line);
    waitUntilQuiet();
    stdout.writeData(done);
  }
}
"""


class Speaker:
    """Speaks a line and blocks until it finishes. Falls back to `say` if the engine fails."""

    def __init__(self):
        try:
            self.proc = subprocess.Popen(
                ["osascript", "-l", "JavaScript", "-e", _SPEAKER_JS],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except OSError:
            self.proc = None

    def say(self, text: str) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.stdin.write(" ".join(text.split()) + "\n")
                self.proc.stdin.flush()
                if self.proc.stdout.readline():
                    return
            except (OSError, ValueError):
                pass
            self.proc = None
        subprocess.run(["say", text], check=False)

    def close(self) -> None:
        if self.proc is not None:
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()


class TerminalIO:
    def __init__(self, speak: bool = False, fast: bool = False):
        self.speak = speak and platform.system() == "Darwin"
        self.fast = fast
        self.speaker = Speaker() if self.speak else None
        if speak and not self.speak:
            print(f"{DIM}(--speak only works on macOS; printing text only){RESET}")

    def close(self) -> None:
        if self.speaker is not None:
            self.speaker.close()

    # Assistant output ------------------------------------------------------
    def va(self, text: str) -> None:
        print(f"\n{CYAN}{BOLD}Assistant:{RESET} {text}")
        if self.speaker is not None:
            self.speaker.say(text)
        self.pause(0.5)

    def note(self, text: str) -> None:
        print(f"{DIM}{text}{RESET}")

    def sound(self, kind: str) -> None:
        """kind is 'ding' (item added) or 'dong' (item skipped)."""
        print(f"{DIM}   [{kind}]{RESET}")
        system = platform.system()
        try:
            if system == "Darwin":
                name = "Glass" if kind == "ding" else "Bottle"
                subprocess.Popen(["afplay", f"/System/Library/Sounds/{name}.aiff"])
            elif system == "Windows":
                import winsound
                winsound.Beep(1300 if kind == "ding" else 500, 180 if kind == "ding" else 280)
            else:
                sys.stdout.write("\a")
                sys.stdout.flush()
        except Exception:
            pass
        self.pause(0.4)

    def pause(self, seconds: float) -> None:
        if not self.fast and seconds > 0:
            time.sleep(seconds)

    # User input -----------------------------------------------------------
    def choose(self, options: list) -> str:
        """Arrow-key menu (up/down, Enter)."""
        if not sys.stdin.isatty():  # piped input fallback: type the option text
            try:
                line = input("› You say: ").strip().lower()
            except EOFError:
                raise KeyboardInterrupt
            for o in options:
                if o.lower() == line:
                    return o
            return options[0]
        idx = 0
        n = len(options)

        def draw(first: bool) -> None:
            if not first:
                sys.stdout.write(f"\033[{n}A")
            for i, o in enumerate(options):
                marker = f"{CYAN}{BOLD}❯ {o}{RESET}" if i == idx else f"  {o}"
                sys.stdout.write(f"\r\033[K{marker}\n")
            sys.stdout.flush()

        print(f"{DIM}› You say:  (↑/↓ then Enter){RESET}")
        draw(True)
        with _KeyMode():
            while True:
                key = _read_key()
                if key == "up":
                    idx = (idx - 1) % n
                elif key == "down":
                    idx = (idx + 1) % n
                elif key == "enter":
                    break
                else:
                    continue
                draw(False)
        # collapse the menu to a single line showing the choice
        sys.stdout.write(f"\033[{n + 1}A")
        for _ in range(n + 1):
            sys.stdout.write("\r\033[K\n")
        sys.stdout.write(f"\033[{n + 1}A")
        print(f"› You say: {BOLD}{options[idx]}{RESET}")
        return options[idx]

    def text(self) -> str:
        """Free-text response typed on the keyboard."""
        try:
            return input("› You say: ").strip()
        except EOFError:
            raise KeyboardInterrupt

    # Read-aloud "wait" control -------------------------------------------
    def interrupted_during(self, seconds: float) -> bool:
        """Wait up to `seconds`; return True if the presenter pressed W ("wait")."""
        if self.fast or seconds <= 0 or not sys.stdin.isatty():
            return False
        end = time.time() + seconds
        if os.name == "nt":
            import msvcrt

            while time.time() < end:
                if msvcrt.kbhit() and msvcrt.getwch().lower() == "w":
                    return True
                time.sleep(0.02)
            return False
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                remaining = end - time.time()
                if remaining <= 0:
                    return False
                ready, _, _ = select.select([sys.stdin], [], [], remaining)
                if ready and sys.stdin.read(1).lower() == "w":
                    return True
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# --------------------------------------------------------------------------
# The conversation
# --------------------------------------------------------------------------


class Assistant:
    def __init__(self, io):
        self.io = io
        self.staged = copy.deepcopy(SEED_LISTS)
        self.shopping: list = []  # (name, quantity text or None)

    # -- helpers -----------------------------------------------------------
    def yes_no(self) -> bool:
        return self.io.choose(["Yes", "No"]) == "Yes"

    def ask_free_text(self, fallback: str, apology_hint: str = "") -> str:
        """Free text with simple error handling: re-ask once, then move on."""
        for attempt in range(2):
            raw = self.io.text()
            if raw:
                return raw
            if attempt == 0:
                self.io.va("Sorry, I didn't get that, can you say again?")
        return fallback

    def ask_quantity(self) -> int:
        for attempt in range(2):
            raw = self.io.text()
            try:
                n = int(raw)
                if 1 <= n <= MAX_QTY:
                    return n
            except ValueError:
                pass
            if attempt == 0:
                self.io.va("Sorry, I didn't get that, can you say again?")
        self.io.va("Ok, I'll add one.")
        return 1

    def infer_locales(self, name: str) -> list:
        """Where a typed-in item lives: reuse a staged item with the same name, else the lookup."""
        key = name.strip().lower()
        for lst in self.staged:
            for it in lst["items"]:
                if it["name"].strip().lower() == key:
                    return list(it["locales"])
        return list(INFERRED_LOCALES.get(key, DEFAULT_LOCALES))

    def add_staged(self, lst: dict) -> None:
        """New lists go before the staples list, so staples are always read last."""
        idx = next((i for i, l in enumerate(self.staged) if l["kind"] == "staples"), len(self.staged))
        self.staged.insert(idx, lst)

    # -- phases ------------------------------------------------------------
    def run(self) -> None:
        self.io.choose(["Help me build my shopping list"])
        self.add_items_phase()
        self.walk_phase()
        self.finish_phase()

    def add_items_phase(self) -> None:
        io = self.io
        summary = summarize_lists(self.staged, "your standard list")
        io.va(
            f"Ok, would you like to add any other items to your staged lists? "
            f"So far I have {summary}."
        )
        while self.yes_no():
            self.collect_new_items()
            summary = summarize_lists(self.staged, "your list")
            io.va(f"Now I have {summary}. Do you want to add any other items to your staged lists?")
        io.va("Ok, let's begin.")

    def collect_new_items(self) -> None:
        io = self.io
        io.va("Ok ready when you are; just say 'Done' when your list is complete")
        new_items = []
        while True:
            said = io.text()
            if not said:
                continue
            if said.lower() == "done":
                break
            new_items.append({"name": said, "locales": self.infer_locales(said)})
            io.sound("ding")
        if not new_items:
            io.va("Ok, no new items.")
            return
        io.va("Ok, should we save this as a list for future reference?")
        if self.yes_no():
            io.va("What do you call this list?")
            name = self.ask_free_text(fallback="My list")
            self.add_staged({"name": name, "kind": "recipe", "items": new_items})
            io.va("Got it.")
        else:
            self.add_staged({"name": "Extra items", "kind": "recipe", "items": new_items})
            io.va("Ok, I'll use them for this trip only.")

    def walk_phase(self) -> None:
        io = self.io
        entries = build_entries(self.staged)
        first_locale = True
        for locale in WALK_ORDER:
            todo = [e for e in entries if e.status == "pending" and locale in e.locales]
            if not todo:
                continue
            if first_locale or FULL_INSTRUCTIONS_EVERY_LOCALE:
                io.va(
                    f'Walk to your {locale} and say "Ready" when you\'re ready to begin. '
                    f"Then I'll read the items one at a time. Say \"Yes\" if you see the item, "
                    f'"No" if you don\'t see the item. If you\'re worried there may not be '
                    f'enough to last the week, you can ask "How much do I need?"'
                )
            else:
                io.va(f'Walk to your {locale} and say "Ready" when you\'re ready to begin.')
            first_locale = False
            io.choose(["Ready"])
            for e in todo:
                self.check_item(e, locale)

    def check_item(self, e: Entry, locale: str) -> None:
        io = self.io
        later = e.remaining_locales_after(locale)
        prompt = upper_first(e.name)
        if later:
            prompt += f" (this one might also be in the {' or '.join(later)})"
        io.va(prompt)
        while True:
            response = io.choose(["Yes", "No", "How much do I need?"])
            if response == "Yes":
                e.status = "found"
                io.sound("dong")
                return
            if response == "No":
                if later:
                    io.va(f"Ok, I'll ask again at the {later[0]}.")
                else:
                    e.status = "added"
                    self.shopping.append((e.name, self.default_qty_text(e)))
                    io.sound("ding")
                return
            # "How much do I need?"
            io.va(self.describe_need(e))
            io.va("Do you have enough?")
            if self.yes_no():
                e.status = "found"
                io.sound("dong")
            else:
                io.va("How many would you like to add?")
                n = self.ask_quantity()
                e.status = "added"
                self.shopping.append((e.name, str(n)))
                io.sound("ding")
            return

    @staticmethod
    def default_qty_text(e: Entry):
        quantities = [q for _, q in e.sources if q]
        if len(e.sources) == 1 and quantities:
            return fmt_qty(quantities[0])
        return None

    @staticmethod
    def describe_need(e: Entry) -> str:
        parts = []
        for list_name, q in e.sources:
            if q:
                parts.append(f"{list_name} calls for {fmt_qty(q)}.")
            else:
                parts.append(f"{list_name} doesn't list an amount.")
        quantities = [q for _, q in e.sources if q]
        if len(e.sources) > 1 and len(quantities) == len(e.sources):
            keys = {tuple(q.keys()) for q in quantities}
            if len(keys) == 1:
                (key,) = keys
                total = {k: sum(q[k] for q in quantities) for k in key}
                parts.append(f"That's {fmt_qty(total)} total.")
        return " ".join(parts)

    def finish_phase(self) -> None:
        io = self.io
        io.va("Great work, your shopping list is ready. Would you like to send this to your phone or read it aloud?")
        choice = io.choose(["Send to phone", "Read aloud"])
        if choice == "Send to phone":
            io.sound("ding")
            io.va("Sent to your phone.")
            return
        io.va('Alright, just say "wait" if you want me to pause, then "resume" when you\'re ready to resume again.')
        io.note('[demo control: press W while the assistant is reading to say "wait"]')
        for name, qty in self.shopping:
            line = upper_first(name) + (f", {qty}" if qty else "")
            io.va(line)
            if io.interrupted_during(READ_PAUSE_BASE + READ_PAUSE_PER_CHAR * len(line)):
                io.note("[paused]")
                io.choose(["resume"])
        io.va("That's your whole list.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scripted voice shopping-list assistant")
    parser.add_argument("--speak", action="store_true", help="speak assistant lines (macOS)")
    parser.add_argument("--fast", action="store_true", help="skip all pauses (rehearsal)")
    args = parser.parse_args()
    io = TerminalIO(speak=args.speak, fast=args.fast)
    io.note("Prototype: voice recognition is simulated. Select or type what the user would say.")
    try:
        Assistant(io).run()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        io.close()


if __name__ == "__main__":
    main()