# Phone Farm — Design Spec

## Problem

Google Play's Closed Testing track requires 20+ testers actively using an app for 14 consecutive days before production release. Additionally, thorough QA testing needs to run across multiple device configurations. Running this manually with physical phones is expensive and tedious.

## Solution

A Python CLI tool (`phone-farm`) that orchestrates Android emulators in batches on a local macOS machine, automating Google account sign-in and app interaction across 30 accounts.

## Constraints

- **Hardware:** Apple M2, 16GB RAM, 8 CPU cores, ~21GB free disk
- **Concurrency ceiling:** 5 emulators per batch (7.5GB emulators + 1GB Appium + 3GB OS overhead = ~11.5GB)
- **Disk budget:** ~6.5GB using ephemeral AVDs (5 reusable slots, not 30 persistent)
- **30 accounts** processed per cycle across 6 batches
- **~30 minutes** per full cycle

## Architecture

```
phone-farm CLI (Python, asyncio)
├── Orchestrator         — schedules batches, tracks progress
├── Emulator Pool Mgr    — create/start/stop AVDs via avdmanager + emulator CLI
├── Account Manager      — 30 Google accounts, encrypted SQLite storage
├── Automation Runner    — Appium server per emulator, runs test flows
├── Reporter             — run history, pass/fail rates per account
└── Config               — TOML-based, tunable batch size/delays/paths
```

### Flow per cycle

1. Orchestrator reads config, picks next batch of accounts (e.g., accounts 1-5)
2. Pool Manager spins up 5 headless AVDs, wipes and provisions each for its account
3. Account Manager provides credentials; emulators restore from pre-authed snapshots (skips login)
4. Automation Runner launches Appium, installs APK, runs assigned test flow
5. On completion, logs results, captures screenshots on failure, shuts down emulators
6. Repeats for next batch (accounts 6-10) until all 30 are done

### Resource budget per batch of 5

| Component | RAM |
|---|---|
| 5 emulators x 1.5GB | 7.5GB |
| 5 Appium servers x 200MB | 1.0GB |
| OS + Python + overhead | 3.0GB |
| **Total** | **~11.5GB** |

### Disk budget (ephemeral AVDs)

| Component | Size |
|---|---|
| SDK + system image + platform/build tools | 1.6GB |
| 5 AVD slots (reused across batches) | 4.0GB |
| Appium + Node.js | 300MB |
| Python + deps | 100MB |
| Logs + reports (grows over time) | 500MB |
| **Total** | **~6.5GB** |

## Account Management

### Storage schema (SQLite, encrypted at rest)

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    app_password TEXT NOT NULL,  -- encrypted with Fernet
    last_used TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',  -- active | cooldown | banned
    batch_group INTEGER NOT NULL  -- 1-6
);

CREATE TABLE run_history (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    run_date TIMESTAMP NOT NULL,
    result TEXT NOT NULL,  -- success | fail | error
    duration_seconds INTEGER,
    error_log TEXT
);
```

### Security

- Master password prompted once per cycle (or read from macOS Keychain)
- Credentials encrypted with `cryptography.fernet`, key derived via PBKDF2 from master password
- DB file excluded from git via `.gitignore`
- No credentials in plain text, logs, or config

### Snapshot strategy

Each of the 30 accounts gets a one-time manual setup:

1. `phone-farm snapshot create --account 7` boots an AVD with a GUI (non-headless)
2. User manually signs into the Google account and opts into testing
3. Tool saves an AVD snapshot named `account-7-authed`
4. During automated runs, the emulator restores this snapshot instead of logging in fresh

Snapshots are stored in `~/.android/avd/` alongside the AVD. Each snapshot is ~200-400MB. Only 5 AVD slots exist at a time, so snapshots are swapped in/out from a snapshot archive directory (`data/snapshots/`) before each batch. This adds ~500MB to the disk budget (5 active snapshots).

If a snapshot becomes stale (Google session expires), the tool detects login failure and prompts the user to re-create that account's snapshot.

### Anti-detection

- Stagger batch start times with random 30-60s delays between emulator launches
- Randomize test script execution time (+/-20%)
- Rotate batch execution order each cycle
- Each account gets a slightly different device profile (screen density, device name)

## Automation & Test Scripts

### Directory structure

```
scripts/
├── flows/
│   ├── base_flow.py          # Abstract base: install, launch, teardown
│   ├── onboarding_flow.py    # First-time: login, accept permissions, tutorial
│   ├── daily_usage_flow.py   # Open app, navigate 3-5 screens, interact
│   └── deep_test_flow.py     # Full QA: every screen, edge cases, forms
├── actions/
│   ├── tap.py                # Tap element by ID/xpath with retry
│   ├── scroll.py             # Scroll patterns
│   ├── input_text.py         # Type with random delays
│   └── wait.py               # Smart waits (element visible, app idle)
└── config/
    └── flow_config.toml      # Which flow to run per cycle type
```

### Two cycle modes

| Mode | Trigger | Flow | Purpose |
|---|---|---|---|
| `tester-gate` | Daily (cron/launchd) | `daily_usage_flow` on all 30 accounts | Satisfy Google's 14-day active testing |
| `qa` | On-demand | `deep_test_flow` on selected devices | Full app QA |

### Human-like interaction patterns

- Random delays between taps: 0.5-2.5s
- Occasional idle pauses: 5-15s (simulating reading)
- Scroll speed varies per account (stored in account config)
- Session duration varies: 45-120 seconds per account

### Error handling

- Emulator crash: log error, skip account, continue batch
- Element not found: retry 3x with increasing wait, then screenshot + fail
- Google login blocked: mark account as `cooldown`, alert user, skip

## CLI Interface

```bash
# Setup
phone-farm init                              # Create config, DB, download SDK
phone-farm accounts add                      # Add a Google account interactively
phone-farm accounts import <csv>             # Bulk import (email,app_password)
phone-farm accounts list                     # Show all accounts + status

# Running
phone-farm run tester-gate                   # Daily flow on all 30 accounts
phone-farm run qa                            # Deep test on 5 emulators
phone-farm run qa --api 34 --accounts 1,5,12 # Target specific accounts/API

# Monitoring
phone-farm status                            # Current batch progress
phone-farm logs                              # Tail orchestrator logs
phone-farm report                            # Summary: accounts x days
phone-farm report --account 7                # Detailed history for one account

# Maintenance
phone-farm doctor                            # Verify SDK, Appium, disk, ports
phone-farm cleanup                           # Remove stale AVDs, old logs
```

### Config file (`phone-farm.toml`)

```toml
[farm]
batch_size = 5
cycle_delay_seconds = 60
max_retries = 2

[emulator]
api_level = 34
ram_mb = 1536
headless = true
device_profile = "pixel_6"

[automation]
appium_base_port = 4723
default_flow = "daily_usage"
screenshot_on_failure = true
human_like_delays = true

[paths]
apk = "./app-release.apk"
scripts = "./scripts/flows/"
logs = "./logs/"
db = "./data/phone-farm.db"
```

### Run output

```
[14:03:12] Starting tester-gate cycle (30 accounts, 6 batches of 5)
[14:03:12] Batch 1/6: accounts #1-#5
[14:03:15]   emu-1 > booted (account: test01@gmail.com)
[14:03:17]   emu-2 > booted (account: test02@gmail.com)
...
[14:05:44]   emu-1 > flow complete (67s)
[14:05:51]   emu-3 > login blocked — marked cooldown
[14:06:02] Batch 1/6 complete: 4/5 passed
[14:07:05] Batch 2/6: accounts #6-#10
...
[14:32:18] Cycle complete: 28/30 passed, 2 cooldown
```

## Prerequisites

1. **Android SDK command-line tools** — `phone-farm init` downloads system images, platform tools, build tools
2. **Node.js** — `brew install node` (for Appium)
3. **Java 17+** — `brew install openjdk@17` (required by Android emulator)
4. **30 Gmail accounts** — manual creation (~2 hours). Same phone number works for up to 4 accounts
5. **Opt each account into closed testing** — share opt-in link, each account clicks Accept

## Known Constraints

- **macOS ARM emulators** use ARM system images; well-supported, no impact on testing accuracy
- **Google login automation is fragile** — mitigated by pre-seeding credentials into AVD snapshots; subsequent runs restore from snapshot, skipping login entirely
- **5 concurrent is the safe ceiling** on 16GB RAM. Tunable via `batch_size` config
- **Network bandwidth** — 5 emulators downloading/updating simultaneously; stagger installs on slow connections
- **Account bans are possible** — cooldown/rotation mitigates but doesn't eliminate risk. Recommend 35 accounts total (30 active + 5 spare)

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ (asyncio) |
| Package manager | uv |
| CLI framework | click |
| Emulator management | Android SDK CLI (avdmanager, emulator, adb) |
| UI automation | Appium 2.x + appium-python-client |
| Database | SQLite (encrypted) |
| Encryption | cryptography (Fernet + PBKDF2) |
| Config | TOML (tomllib) |
| Linting | ruff |
| Testing | pytest + pytest-asyncio |
