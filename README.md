# Voice Shopping-List Assistant (scripted terminal prototype)

A heavily scripted prototype of a voice assistant that walks you through your
kitchen locale by locale (refrigerator, pantry, spice cabinet), asks whether
you can see each item on your staged lists, and builds a running shopping list
from what is missing.

Voice recognition is black-boxed: choose what the user would say with the arrow
keys, or type it when it is free text.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.8 or newer (uv will find or fetch one)
- No third-party packages. The script uses only the standard library, so there
  is no install step and no virtual environment to manage.

## Run

From the folder containing `shopping_assistant.py`:

```sh
uv run shopping_assistant.py
```

To pin a specific Python version:

```sh
uv run --python 3.12 shopping_assistant.py
```

### Options

| Flag      | Effect                                                           |
|-----------|------------------------------------------------------------------|
| `--speak` | The assistant's lines are spoken aloud (macOS only, system voice) |
| `--fast`  | Removes all pauses, for rehearsing the flow                      |

```sh
uv run shopping_assistant.py --speak
uv run shopping_assistant.py --fast
```

## Using it

| Situation                              | How to respond                                     |
|----------------------------------------|----------------------------------------------------|
| A few fixed responses (Yes / No / ...) | Up and Down arrow keys, then Enter                 |
| Free text (item names, list name, quantity) | Type it, then Enter                           |
| Finish adding new items                | Type `done`                                        |
| During read-aloud, pause the assistant | Press `W` (this stands in for saying "wait")       |
| Resume after pausing                   | Select `resume`                                    |
| Quit at any time                       | Ctrl+C                                             |

## Sounds

- **ding** means an item was added to the shopping list.
- **dong** means an item was found and skipped.
- macOS plays system sounds (`Glass` and `Bottle`). Windows plays a beep.
  Linux uses the terminal bell. A `[ding]` or `[dong]` label is always printed
  on screen too.

## Customizing

Everything you are likely to edit is at the top of `shopping_assistant.py`:

- `SEED_LISTS`: the two preloaded staging lists (Recipe 4 and Staples), with
  each item's locales and optional quantity.
- `INFERRED_LOCALES`: where typed-in items are assumed to live. Items not listed
  default to the pantry.
- `WALK_ORDER`: the order in which locales are visited.
- `FULL_INSTRUCTIONS_EVERY_LOCALE`: set to `True` to repeat the long
  instructions at every locale instead of only the first.
- `READ_PAUSE_BASE` and `READ_PAUSE_PER_CHAR`: how long the assistant waits
  between items when reading the list aloud.

## Notes

- Staged lists are kept in memory only, so every run starts from the same seed
  data. This keeps repeated takes for a demo video identical.
- "Send to phone" is a mock. It plays a ding and prints a confirmation, and
  nothing is actually sent.
- Use a real terminal (Terminal, iTerm2, Windows Terminal). Some IDE output
  panels do not support arrow-key menus.