# Phone Farm Roadmap

## What's Live Now (v0.1.0)

Everything below works today, for free, on your machine:

- **Deterministic QA explorer** — boots emulator, installs APK, taps every clickable element, detects crashes and ANRs
- **CLI emulator control** — `phone-farm emu boot/screen/tap/type/scroll/back/crashes/teardown`
- **MCP server** — 11 tools for AI agent integration (any MCP client)
- **Web dashboard** — dark theme, APK upload, real-time test monitoring
- **Demo mode** — `phone-farm demo` downloads Wikipedia app and runs a full test
- **Accessibility audit** — WCAG checks for missing labels, small touch targets
- **Crash reporter** — enhanced crash reports with reproduction steps
- **One-click install** — `curl | bash` for macOS and Linux

---

## Coming Soon: Phone Farm Pro

AI-powered exploration that thinks like a real QA engineer.

### AI Vision Testing
The AI agent sees your app's actual screen — not just the accessibility tree — and reasons about what to test next. It finds bugs that scripts and click-bots never will:
- **Visual bugs** — overlapping elements, truncated text, broken layouts, contrast issues
- **Functional bugs** — forms that don't submit, buttons that do nothing, broken navigation
- **Edge case discovery** — the AI tries empty inputs, special characters, rapid taps, back navigation in unexpected places
- **Intelligent exploration** — prioritizes unexplored screens, avoids repeating actions, adapts strategy when stuck

### Smart Test Data
The AI fills forms with realistic data — valid emails, phone numbers, addresses, credit card test numbers — then tries invalid data to see how the app handles it.

### Multi-Device Testing
Run the same AI exploration across multiple device profiles simultaneously:
- Different screen sizes (phone, tablet, foldable)
- Different API levels (Android 12-15)
- Different locales (RTL, CJK, emoji-heavy)

### CI/CD Integration
```yaml
# GitHub Actions
- uses: avinashchby/phone-farm-action@v1
  with:
    apk: app-release.apk
    fail-on: critical,high
```

### Regression Detection
Upload two APK versions. Phone Farm compares them screen-by-screen and reports:
- New crashes introduced
- UI elements that moved or disappeared
- Screens that changed unexpectedly
- Performance regressions

### Team Dashboard (Cloud)
Hosted version for teams who don't want to manage emulators:
- Shared bug reports across the team
- Test history and trend charts
- Slack/Discord notifications on new bugs
- Role-based access control

### Export to Test Scripts
Found a critical bug? Export the AI's exact navigation path as a repeatable test:
- Maestro YAML
- Appium script (Python/Java)
- ADB shell commands

---

## Pricing (Planned)

| | Community | Pro | Team |
|---|---|---|---|
| Deterministic explorer | Yes | Yes | Yes |
| CLI + MCP server | Yes | Yes | Yes |
| Web dashboard | Yes | Yes | Yes |
| AI vision testing | - | Yes | Yes |
| Multi-device | - | Yes | Yes |
| CI/CD action | - | Yes | Yes |
| Regression detection | - | - | Yes |
| Cloud dashboard | - | - | Yes |
| Export to scripts | - | Yes | Yes |
| Price | Free forever | $29/mo or BYOK | $99/mo per seat |

BYOK = Bring Your Own Key (use your Anthropic API key, pay only API costs)

---

## How to Get Early Access

Star the repo and watch for releases. Pro features will ship incrementally — each one usable standalone.

Want to be a design partner? Open an issue or email avinash@remotelama.com.
