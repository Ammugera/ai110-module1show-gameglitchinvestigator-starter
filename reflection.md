# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

The game first appears with as a basic website with a settings menu to the side of the main game. There are 2 buttons to allow you to submit guesses and reset the game, as well as a hint toggle. Above these buttons is a input field for you to put in your guess, and if you have hints enabled your hint will appear in a dialogue box below this. Overall the game is rather simple but has a lot of bugs.
Bugs:
- Can go into negatives and above 1000 though it asks to guess a number between 1 and 1000
  - **Expected:** The game should only accept guesses within the valid range for the difficulty (e.g. 1–100 for Normal). Guesses outside that range should be rejected with an error.
  - **Actual:** There is no range validation at all. Any integer, including negatives and numbers far above 1000, is accepted as a valid guess.
- Lets users input values over 1000 and under 1 which eats into guesses
  - **Expected:** Invalid or out-of-range guesses should not count against the player's remaining attempts.
  - **Actual:** The attempt counter increments before the guess is even validated, so bad inputs still use up a turn.
- No indication that an answer has been accepted when show hint is turned off
  - **Expected:** The player should still receive some feedback that their guess was submitted, even without the directional hint.
  - **Actual:** The hint message is the only feedback for a normal guess. With "Show hint" unchecked, nothing appears on screen at all — the guess is silently consumed.
- New game button doesn't reset game, had to refresh page to reset
  - **Expected:** Clicking "New Game" should fully reset all game state (attempts, score, history, and game status) so a fresh round can begin.
  - **Actual:** The button only resets attempts and the secret number. It does not reset the score, history, or the win/loss status, so if the game has already ended, it stays stuck on the game-over screen.
- Score is a nonsensical metric what is it measuring
  - **Expected:** The score should be a clear, intuitive measure of performance — rewarding fewer guesses and penalizing more.
  - **Actual:** The scoring formula is inconsistent: guessing too high sometimes adds points and sometimes subtracts them depending on the attempt number, while guessing too low always subtracts points. The score can go deeply negative and doesn't clearly reflect how well the player is doing.
- Difficulty settings are weird. Less of a bug but should be more adjustable.
  - **Expected:** Higher difficulty should mean a larger number range and/or fewer guesses, scaling logically from Easy to Hard.
  - **Actual:** Hard mode has a range of 1–50, which is actually smaller than Normal's 1–100, making it arguably easier to guess the number. The UI also always displays "Guess a number between 1 and 100" regardless of the selected difficulty.

---

## 2. How did you use AI as a teammate?

I used **Gemini Agent mode** (in VS Code) as my primary AI teammate throughout this project. I described each bug, reviewed the suggestions it gave me, and then applied or rejected them based on my own testing.

### ✅ Correct AI suggestion — Moving the attempt increment after validation

When I told the AI that invalid guesses were eating into the player's remaining attempts, it correctly identified that `st.session_state.attempts += 1` was running *before* `parse_guess()` validated the input. It suggested moving the increment inside the `else` branch (the valid-guess path) so that only successfully parsed, in-range guesses would count. I verified this by running the game in the browser: I typed `"abc"` and `-5` into the input field and confirmed that the "Attempts left" counter no longer decreased for those invalid inputs. I also wrote pytest cases (`test_invalid_guess_does_not_increment_attempts`, `test_out_of_range_guess_does_not_increment_attempts`) that simulate the submit flow and assert the attempt counter stays at 1 after bad input — all passed.

### ✅ Correct AI suggestion — Adding range validation to `parse_guess()`

I pointed out that the game accepted any integer (negatives, numbers above 1000, etc.) even though each difficulty has a specific range. The AI suggested adding `low` and `high` parameters to `parse_guess()` and returning an error message like `"Guess must be between {low} and {high}."` when the value falls outside the bounds. I verified this by selecting Easy mode (range 1–20), typing `21` and `-3`, and confirming both were rejected with the correct error message. The boundary values `1` and `20` were still accepted. I also confirmed this with pytest cases like `test_parse_guess_rejects_above_max` and `test_parse_guess_accepts_low_boundary`.

### ❌ Misleading AI suggestion — Claiming `check_guess()` hint messages were correct

When the AI originally generated the `check_guess()` function, it did not flag a significant UX bug: the hint emoji and text are **swapped**. When the player's guess is *too high*, the code returns `"📈 Go HIGHER!"` — which tells the player to go *higher* when they actually need to go *lower*. Similarly, guessing too low shows `"📉 Go LOWER!"`. When I asked the AI to review the game logic for issues, it described `check_guess()` as working correctly and moved on to other bugs. I caught this myself by playing the game with the debug panel open: the secret was 42, I guessed 60, and the hint said "📈 Go HIGHER!" even though I clearly needed to go lower. This taught me that AI can miss logic errors that are obvious to a human actually *playing* the game — reading code is not the same as testing it.

---

## 3. Debugging and testing your fixes

I used a two-layer approach to decide whether a bug was really fixed: **manual testing in the browser** first, then **automated pytest cases** to make sure the fix holds over time. A bug wasn't "done" until both layers agreed. Manual testing caught things that are hard to assert in code (like whether the UI *felt* right), while pytest caught edge cases I wouldn't think to try by hand every time.

### Manual testing — playing the game with the debug panel open

The app has a built-in "Developer Debug Info" expander that shows the secret number, attempt count, score, and history. After each fix, I opened this panel and played through several rounds. For the range-validation fix, I selected Easy mode (range 1–20), then deliberately entered `-3`, `0`, `21`, and `999`. Each one was rejected with the message "Guess must be between 1 and 20." and the "Attempts left" counter stayed the same — confirming both Bug 1 (no range check) and Bug 2 (invalid guesses eating attempts) were resolved. I then entered `1`, `20`, and `10` to confirm valid boundary and mid-range values were still accepted. For the swapped-hints fix, I set the secret to a known value via the debug panel, guessed higher, and verified the hint now correctly said "📉 Go LOWER!" instead of the old "📈 Go HIGHER!".

### Pytest — automated regression tests

I wrote 13 pytest cases in `tests/test_game_logic.py` targeting the two bugs. For Bug 1, the tests call `parse_guess()` directly with out-of-range inputs (negatives, zero, above-max) and assert that `ok` is `False` and the error message contains the correct range. They also verify that boundary values (`1` and the difficulty ceiling) return `ok = True`. For Bug 2, I created a `_simulate_submit()` helper that mirrors the fixed `if submit:` block from `app.py` — it calls `parse_guess()`, and only increments `state.attempts` in the `else` (valid) branch. The test `test_multiple_invalid_then_valid` sends three bad inputs followed by one good one and asserts that `attempts` only increased by 1. Running `python -m pytest tests/test_game_logic.py -v` shows all 19 tests passing.

### How AI helped with tests

The AI (Gemini Agent mode) wrote the initial test scaffolding — the `_FakeSessionState` helper class, the `_simulate_submit()` function, and the parametrized test cases. I reviewed each test to make sure it was actually testing what I intended and not just passing trivially. For example, I confirmed that `test_out_of_range_guess_does_not_increment_attempts` uses `"999"` (a value above the range) rather than a non-numeric string, so it specifically targets the *range check* rather than the *type check*. The AI also suggested boundary tests for the low and high ends of the range, which I wouldn't have thought to add on my own.

---

## 4. What did you learn about Streamlit and state?

- In your own words, explain why the secret number kept changing in the original app.
- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?
- What change did you make that finally gave the game a stable secret number?

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.
