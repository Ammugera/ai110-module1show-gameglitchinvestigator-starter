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

The secret number kept changing because Streamlit **reruns the entire script from top to bottom** every time the user interacts with a widget — clicking a button, typing in a text box, or changing a dropdown. In the original code, `random.randint(1, 100)` was called at the top of the script without any guard, so every rerun generated a brand-new secret. The number wasn't "resetting" in the traditional sense; it was being *recreated* from scratch on every single interaction because the script had no memory between runs.

If I were explaining Streamlit reruns to a friend, I'd say: "Imagine a whiteboard where every time you tap it, someone erases everything and redraws the whole board from the top. If you wrote `pick a random number` at the top of the whiteboard, you'd get a different number every tap. `st.session_state` is like a sticky note on the side of the whiteboard that *doesn't* get erased — it survives the redraw. So you write `if there's no sticky note yet, pick a random number and write it on the sticky note`, and from then on you always read from the sticky note instead of picking again."

The fix was wrapping the secret generation in a session-state guard: `if "secret" not in st.session_state: st.session_state.secret = random.randint(low, high)`. This ensures the secret is only generated once — on the very first run — and then persists across all subsequent reruns. The `New Game` button explicitly overwrites `st.session_state.secret` with a new random value and calls `st.rerun()`, which is the only time the secret should ever change. Understanding this pattern — "initialize once, read always, reset explicitly" — was the single biggest takeaway for working with Streamlit.

---

## 5. Looking ahead: your developer habits

**One habit I want to reuse: "play it, then test it."** The most valuable thing I did in this project was actually *playing the game* with the debug panel open before and after every fix. That's how I caught the swapped hints — a bug the AI completely missed during code review. Reading code and writing tests are important, but there's no substitute for using your own product. In future projects, I want to always start debugging by manually exercising the feature as a real user, noting what feels wrong, and *then* writing the automated tests to lock in those expectations. The two-layer approach (manual first, pytest second) gave me much more confidence that fixes were actually working.

**One thing I'd do differently: verify AI suggestions against the actual runtime, not just the code.** When the AI told me `check_guess()` was "working correctly," I initially accepted that and moved on to other bugs. It was only later, while playing the game, that I realized the hints were backwards. The AI was reading the code structurally — "the function returns a tuple, handles the comparison, has an except branch" — but it never simulated what the player would actually *see*. Next time, for every AI suggestion I receive, I'll run the specific scenario in the app (or write a quick test) before accepting the suggestion as correct. Trust, but verify — especially when the AI says "this part looks fine."

**How this project changed the way I think about AI-generated code:** I went in assuming the AI would either be right or obviously wrong, but the reality was more subtle. The AI was *confidently* wrong about the swapped hints, *accidentally* right about the TypeError fallback in `check_guess()` (the int-vs-str coercion on even attempts technically works, but only because of a fragile exception handler), and *genuinely* helpful for scaffolding tests and refactoring code into `logic_utils.py`. The lesson is that AI is a powerful first-draft tool, but it doesn't *understand* what the code is supposed to do for a human user — it only knows what the code *structurally* does. I'm the one who has to bridge that gap by testing, questioning, and sometimes rejecting what it gives me.

