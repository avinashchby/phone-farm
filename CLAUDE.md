# Phone Farm

Android emulator orchestration + AI-powered QA testing.

## Quick Reference

```bash
phone-farm doctor          # Check prerequisites
phone-farm emu boot <apk>  # Boot emulator with APK
phone-farm emu screen      # Get accessibility tree XML
phone-farm emu screenshot ./ss.png  # Take screenshot
phone-farm emu tap --text "Login"   # Tap element
phone-farm emu type --id "com.app:id/email" --value "test@example.com"
phone-farm emu scroll down
phone-farm emu back
phone-farm emu crashes     # Check for crashes (JSON)
phone-farm emu teardown    # Stop everything
```

## QA Testing Workflow

When asked to test an APK, follow this loop:

### 1. Setup
```bash
phone-farm emu boot ./path-to-app.apk
```

### 2. Explore Loop
Repeat until you've covered the app:

```bash
# See what's on screen
phone-farm emu screen
# Take a screenshot to visually inspect
phone-farm emu screenshot ./screenshots/step-N.png
```

Read the screenshot to understand the UI. Then interact:
```bash
phone-farm emu tap --text "Button Text"
phone-farm emu type --id "com.app:id/input_field" --value "test data"
phone-farm emu scroll down
phone-farm emu back
```

Periodically check for crashes:
```bash
phone-farm emu crashes
```

### 3. What to Look For
- **Crashes**: Run `phone-farm emu crashes` after each action sequence
- **Visual bugs**: Read screenshots for overlapping elements, truncated text, broken layouts
- **Functional bugs**: Does the app do what it should? Do forms submit? Do buttons work?
- **Accessibility**: Are elements labeled? Is text readable?
- **Edge cases**: Empty inputs, special characters, rapid taps, back navigation

### 4. Teardown
```bash
phone-farm emu teardown
```

### 5. Report
Summarize findings with severity (critical/high/medium/low), category, steps to reproduce, and screenshots.

## Project Structure

- `phone_farm/` — Core modules (emulator, appium, config, db, crypto, logging)
- `phone_farm/qa_agent/` — AI QA agent modules (state parsing, memory, bug reports, logcat)
- `scripts/actions/` — Reusable UI actions (tap, scroll, type, wait)
- `scripts/flows/` — Pre-scripted test flows
- `tests/` — 110+ pytest tests

## Commands

| Command | Purpose |
|---------|---------|
| `phone-farm run tester-gate` | Run batch tester-gate cycle |
| `phone-farm run qa` | Run batch QA cycle |
| `phone-farm accounts add/list/import` | Manage test accounts |
| `phone-farm report` | View run history |
| `phone-farm doctor` | Check prerequisites |
| `phone-farm qa-test <apk>` | AI-powered QA (needs API key) |
| `phone-farm emu *` | Manual emulator control (for Claude Code) |

## Dev

```bash
uv sync                    # Install deps
uv run pytest -v           # Run tests
uv run ruff check --fix    # Lint
```
