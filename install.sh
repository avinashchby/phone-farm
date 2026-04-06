#!/bin/bash
# Phone Farm — One-click installer
# Usage: curl -sSL https://raw.githubusercontent.com/AvinashChaubey/phone-farm/main/install.sh | bash

set -e

echo "==============================="
echo "  Phone Farm Installer"
echo "==============================="
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" != "Darwin" ] && [ "$OS" != "Linux" ]; then
    echo "ERROR: Only macOS and Linux are supported."
    exit 1
fi

echo "[1/6] Checking Python 3.12+..."
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "  Found Python $PY_VERSION"
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]); then
        echo "  WARNING: Python 3.12+ recommended. You have $PY_VERSION."
    fi
else
    echo "  ERROR: Python 3 not found. Install Python 3.12+."
    exit 1
fi

echo "[2/6] Checking Java 17+..."
if command -v java &>/dev/null; then
    echo "  Found: $(java -version 2>&1 | head -1)"
else
    echo "  Installing Java 17..."
    if [ "$OS" = "Darwin" ]; then
        brew install openjdk@17
    else
        sudo apt-get install -y openjdk-17-jdk
    fi
fi

echo "[3/6] Checking Node.js..."
if command -v node &>/dev/null; then
    echo "  Found: Node $(node --version)"
else
    echo "  Installing Node.js..."
    if [ "$OS" = "Darwin" ]; then
        brew install node
    else
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
fi

echo "[4/6] Checking Android SDK..."
if command -v adb &>/dev/null; then
    echo "  Found: $(adb version 2>&1 | head -1)"
else
    echo "  Installing Android command-line tools..."
    if [ "$OS" = "Darwin" ]; then
        brew install --cask android-commandlinetools
        export ANDROID_HOME="/opt/homebrew/share/android-commandlinetools"
    else
        mkdir -p "$HOME/android-sdk/cmdline-tools"
        cd "$HOME/android-sdk/cmdline-tools"
        curl -sSL "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" -o tools.zip
        unzip -q tools.zip && mv cmdline-tools latest && rm tools.zip
        export ANDROID_HOME="$HOME/android-sdk"
        export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
    fi
    echo "  Accepting licenses..."
    yes | sdkmanager --licenses >/dev/null 2>&1
    echo "  Installing emulator + platform tools..."
    sdkmanager "emulator" "platform-tools" "platforms;android-34" "system-images;android-34;google_apis;arm64-v8a"
fi

echo "[5/6] Checking Appium..."
if command -v appium &>/dev/null; then
    echo "  Found: Appium $(appium --version)"
else
    echo "  Installing Appium..."
    npm install -g appium
    appium driver install uiautomator2
fi

echo "[6/6] Installing Phone Farm..."
pip install phone-farm 2>/dev/null || pip3 install phone-farm

echo ""
echo "==============================="
echo "  Installation complete!"
echo "==============================="
echo ""
echo "  Start the dashboard:  phone-farm serve"
echo "  Check prerequisites:  phone-farm doctor"
echo "  Run MCP server:       phone-farm-mcp"
echo ""
echo "  Open http://localhost:8000 after starting the dashboard."
echo ""
