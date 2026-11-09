## Demo: Kitchen Sweep Voice Assistant

```sh
uv run --python 3.12 shopping_assistant.py --speak
```

- [ ] Create new "Movie Night" list with 3 items:
  - ice cream
  - chocolate syrup
  - popcorn
- [ ] Respond with:

  | Item | Response | To demo... |
  |---|---|---|
  | Italian Sausage | NO | audible `ding` feedback after adding an item |
  | Sun-dried tomatoes (in oil) | NO | fallback to second locale |
  | Eggs | How much do I need? | adding specific quantity to list (6) |
  | Sliced Turkey | YES | audible `dong` feedback after skipping an item |

- [ ] Read list aloud at the end
  - Say "WAIT" at "Sun-dried tomatoes in oil"
   
## Design Decisions
### Features Demonstrated in Prototype 2

_NOTE: Not all of the features are fully implemented in the "backend" (see **Limitations**), so in that sense this is a *horizontal prototype* - the interactions across a variety of features are demonstrable, the implementation details ("vertical") are mocked_

1. Discoverable controls

    ✅ Voice assistant explains the available commands at each step

1. Multi-list management
  
    i.e. build a new list on the fly, save for future use, import multiple lists

    ✅ Offloads cognitive effort to remember "staples" I buy every week, allows user to short-circuit repeating ingredients for common recipes each week.

2. Locale-by-locale grouping
  
    ✅ Offloads cognitive effort to figure out where to look *for each item*, improves efficiency

3. Call-response format
  
    ✅ Puts user in control of the tempo, allows them to keep eyes on the inventory (lower cognitive load compared to looking back and forth at list)

4. Audible feedback given when an item is added ("ding") or skipped ("dong")
  
    ✅ Helps user cross bridge of evaluation
    
    ⚠️ More important when actual voice interface is implemented, see **Limitation 1**

5. Locale fall-back ("Might also be in the <locale>")
  
    ✅ Accounts for common mistake observed during initial evaluation, where users checked only one locale when item could have been in another locale 

### Prototype Limitations

1. Mock the user voice interaction
  
 
    Voice detection is complex, good candidate for future improvement.

2. Hard-code Locales

    Eventually this tool could be integrated with a basic LLM which could automatically "match" a grocery item to the fridge, pantry, etc.

3. Over-simplified representation of quantities
