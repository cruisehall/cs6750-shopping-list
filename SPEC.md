# SPEC: Voice Shopping-List Assistant (scripted terminal prototype)

Requirements as provided by the project owner. Section 9 lists decisions the
implementation made where the requirements were silent, so they can be checked
and changed.

## 1. Purpose and context

- Medium-fidelity "final prototype" for an individual HCI course project, shown
  in a roughly 5-minute video prototype and later evaluated by participants
  watching the video.
- Task: help a user build a grocery shopping list at the moment they check what
  they have, so items are not forgotten before a store trip.
- The prototype is **heavily scripted**. It does not need to be a fully
  functional app.

## 2. What the demo must show

1. **Remembering of ingredient lists** (for example recipes), held as "staging
   lists".
2. **The grouped-by-locale call-and-response mechanism**: the assistant walks the
   user locale by locale and reads items one at a time.

## 3. Input model

- Voice recognition is **black-boxed**. The presenter supplies user responses in
  the terminal.
- Whenever the user can give one of a few responses, the presenter **selects it
  with the arrow keys**.
- Whenever the user can give a free-text response, the presenter **types it**.
- The presenter says each response aloud while entering it. The video preface
  explains that voice recognition is black-boxed for the demonstration.
- The video shows the terminal screen.

## 4. Data model

Staging lists hold items. An item is represented like:

```yaml
name: staples
items:
- name: bread
  quantity:            # optional
    loaves: 2
  locales: ["pantry", "refrigerator"]
- name: sliced cheese
  quantity:            # optional
    count: 8
  locales: ["refrigerator"]
- name: milk
  quantity:            # optional
    gallons: 1
  locales: ["refrigerator"]
```

- Each item has a **list of locales** where it might be (one or more). Only a
  few multi-locale examples are needed.
- Locales walked: **refrigerator, pantry, spice cabinet**. Freezer is dropped.
- The **running shopping list** is separate from the staging lists and is
  **empty when the demo starts**.
- Seed data is hard-coded: two preloaded staging lists (section 5). Locales for
  seed items are inferred, not supplied.

## 5. Seed data

**Staging list 1: Recipe 4, Creamy Tuscan Sausage Soup** (12 items, no
quantities): Bay leaves, Italian sausage, Russet potatoes, Sun-dried tomatoes
(in oil), Fennel seeds, Half-and-half, Yellow onions, Baby spinach, Dried basil,
All-purpose flour, Unsalted butter, Cannellini beans (canned).

**Staging list 2: Staples** (5 items, keep exactly these five):
eggs (12), sliced cheese, sliced turkey, milk (1 gallon), bread.

**Typed-in during the demo** (becomes the "Honey Garlic Salmon Bowl" list, 12
items): Honey, Sesame Seeds, Edamame, Salmon Fillets, Garlic Powder, Jasmine
Rice, Rice Vinegar, White Pepper, Scallions, Toasted Sesame Oil, Fresh Ginger,
Soy Sauce.

## 6. Conversation flow

```yaml
- user: Help me build my shopping list
- va: Ok, would you like to add any other items to your staged lists? So far I have <N> ingredients for Creamy Tuscan Sausage Soup and your standard list of <N> staples.
- user: Yes
- va: Ok ready when you are
# for each item typed:
- user: ${item}
- va: <add ding>
- user: Done
- va: Ok, should we save this as a list for future reference?
- user: Yes
- va: What do you call this list?
- user: Honey Garlic Salmon Bowl
- va: Got it. Now I have <N> ingredients for Creamy Tuscan Sausage Soup, <N> ingredients for Honey Garlic Salmon Bowl, and your list of <N> staples. Do you want to add any other items to your staged lists?
- user: No
- va: Ok, let's begin.
# for each locale in [refrigerator, pantry, spice cabinet]:
- va: Walk to your ${locale} and say "Ready" when you're ready to begin. Then I'll read the items one at a time. Say "Yes" if you see the item, "No" if you don't see the item. If you're worried there may not be enough to last the week, you can ask "How much do I need?"
- user: Ready
# for each pending item that can be in this locale:
- va: ${item} (this one might be in the ${other locales} if it has more than one locale)
- user: Yes | No | How much do I need?
#   Yes -> <skip dong>
#   No  -> <add ding>   (see rule 7.2)
#   How much do I need? -> VA describes which lists the item is on, including
#                          quantity if available, then asks "Do you have enough?"
- va: Great work, your shopping list is ready. Would you like to send this to your phone or read it aloud?
- user: Read aloud            # or: Send to phone
- va: Alright, just say "wait" if you want me to pause, then "resume" when you're ready to resume again.
  <reads each item in the list>
# optional:
- user: wait
- va: <pauses>
- user: resume
- va: <continues>
```

Counts (`<N>`) come from the data, not hard-coded text.

## 7. Behavior rules

1. **Vocabulary** is Yes / No / "How much do I need?". ("Add" / "skip" wording
   is not used.)
2. **"No" adds an item only after the item's final locale.** At an earlier
   locale it means "not here, keep looking".
3. **"Yes" skips the item at all later locales** as soon as the user confirms
   it is at one locale.
4. **Duplicate items across staging lists are asked once.**
5. **Quantities are not combined.** Quantity handling is for future iterations.
6. **"How much do I need?"**: the assistant describes which lists the item is on
   (with quantity if available), then asks "Do you have enough?".
   - "Yes" leaves the item off the list.
   - "No" asks "How many would you like to add?" and the user answers with a
     number from **1 to 50**. The item is added with that quantity and the walk
     for that item ends.
7. **Error handling** is simple: "Sorry, I didn't get that, can you say again?"
   and **move on after 2 tries**.
8. **Read aloud** pauses between items at about normal writing speed. The user
   can say "wait" and "resume".
9. **Send to phone** is a **mock**: the assistant plays an audible ding to
   simulate success and nothing is sent. The presenter says in the video that
   it is a stand-in.
10. The final prompt (read aloud or send to phone) **ends the demo**.

## 8. Out of scope

- Generating the ingredient list from speech or a recipe (lists are pre-loaded
  or typed).
- A "try the <locale>" command.
- Handling items that already exist on the running shopping list.
- Freezer as a locale.
- Combining or totaling quantities across lists.
- Real speech recognition, wake words, and Vosk or Whisper integration.
- Demonstrating the error path in the video (happy path only).

## 9. Implementation decisions (not specified by the owner)

- Arrow-key menus use only the standard library (no third-party packages).
- Locales for seed and typed-in items were inferred. Multi-locale examples:
  sun-dried tomatoes, sesame seeds, soy sauce, bread. A typed-in item that matches
  an existing staged item by name reuses its locales. Other typed-in items not in the
  lookup default to the pantry.
- Seed quantities for staples follow the YAML example: bread 2 loaves, sliced
  cheese 8, milk 1 gallon, eggs 12. Sliced turkey has none.
- A plain "No" with no quantity question adds the item with its listed
  quantity, if any.
- Extra assistant lines: "Ok, I'll ask again at the <locale>." after a deferred
  "No", "Sent to your phone." after the send-to-phone ding, and "That's your
  whole list." after reading aloud.
- The long walk instructions play at the first locale only. Later locales get
  the short "Walk to your <locale> and say Ready" line.
- The "might also be in" hint lists only locales still to come.
- Presenter key "W" stands in for saying "wait" during read-aloud.
- Staged lists are in memory only, so each run starts from the same seed data.
- Optional `--speak` (macOS system voice) and `--fast` (no pauses) flags. Speech
  runs through one long-lived `osascript` engine that is warmed up at launch,
  because starting `say` for each line added about a second of delay. If the
  engine fails, it falls back to `say`.

## 10. Open items

- The script's original counts ("10 ingredients", "15 staples") differ from the
  data (12 and 5). The data was treated as correct.
- An end-of-session summary of skipped items was discussed and is not in the
  final flow, so it is not implemented.
- Voice quality (default macOS `say` versus a more realistic voice) is
  undecided.