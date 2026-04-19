# 🎮 Game Glitch Investigator: The Impossible Guesser

## 🚨 The Situation

You asked an AI to build a simple "Number Guessing Game" using Streamlit.
It wrote the code, ran away, and now the game is unplayable. 

- You can't win.
- The hints lie to you.
- The secret number seems to have commitment issues.

## 🛠️ Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the broken app: `python -m streamlit run app.py`

## 🕵️‍♂️ Your Mission

1. **Play the game.** Open the "Developer Debug Info" tab in the app to see the secret number. Try to win.
2. **Find the State Bug.** Why does the secret number change every time you click "Submit"? Ask ChatGPT: *"How do I keep a variable from resetting in Streamlit when I click a button?"*
3. **Fix the Logic.** The hints ("Higher/Lower") are wrong. Fix them.
4. **Refactor & Test.** - Move the logic into `logic_utils.py`.
   - Run `pytest` in your terminal.
   - Keep fixing until all tests pass!

## 📝 Document Your Experience

- [ ] Describe the game's purpose.
- [ ] Detail which bugs you found.
- [ ] Explain what fixes you applied.

## 📸 Demo

![Fixed Game UI — Normal difficulty, dynamic range, all bugs resolved](demo_screenshot.png)

### Bugs Fixed

| Bug | What was broken | Fix |
|-----|----------------|-----|
| No range validation | `parse_guess()` accepted any integer (negatives, 9999, etc.) | Added `low`/`high` params; rejects out-of-range guesses with a clear error |
| Invalid guesses consume attempts | `attempts += 1` ran before validation | Moved increment inside the valid-guess branch |
| Hardcoded range text | Info bar always said "between 1 and 100" | Now uses dynamic `{low}` and `{high}` from difficulty |
| Swapped hint messages | "Too High" said "📈 Go HIGHER!" | Corrected to "📉 Go LOWER!" (and vice versa) |
| New Game didn't reset | Only reset `attempts` and `secret` | Now resets `status`, `score`, `history` too |

### Run the fixed game

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

### Run tests

```bash
python -m pytest tests/test_game_logic.py -v
```

## 🚀 Stretch Features

- [ ] [If you choose to complete Challenge 4, insert a screenshot of your Enhanced Game UI here]
