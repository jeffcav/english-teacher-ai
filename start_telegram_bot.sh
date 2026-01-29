#!/bin/bash
# Quick start script for Telegram bot

set -e

echo "🚀 PhonicFlow Telegram Bot - Quick Start"
echo "========================================"
echo ""

# Check for TELEGRAM_BOT_TOKEN
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not set"
    echo ""
    echo "Please set your Telegram bot token:"
    echo "  export TELEGRAM_BOT_TOKEN='your_token_here'"
    echo ""
    echo "Get a token from @BotFather on Telegram"
    exit 1
fi

echo "✅ TELEGRAM_BOT_TOKEN is set"
echo "   Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo ""

# Check backend
echo "🔍 Checking backend connectivity..."
if curl -s http://localhost:8000/docs > /dev/null; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "⚠️  Backend not responding on http://localhost:8000"
    echo "   Make sure the backend is running:"
    echo "   python -m uvicorn app.backend.main:app --reload"
    echo ""
fi

# Check ffmpeg
echo "🔍 Checking ffmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg is installed"
else
    echo "❌ ffmpeg is not installed"
    echo "   Install with: sudo apt-get install ffmpeg (Linux)"
    echo "                 brew install ffmpeg (macOS)"
    exit 1
fi

# Check Python dependencies
echo "🔍 Checking Python dependencies..."
python -c "import telegram" 2>/dev/null && echo "✅ python-telegram-bot is installed" || \
    { echo "❌ python-telegram-bot not installed. Run: pip install python-telegram-bot==20.0"; exit 1; }
python -c "import pydub" 2>/dev/null && echo "✅ pydub is installed" || \
    { echo "❌ pydub not installed. Run: pip install pydub==0.25.1"; exit 1; }

echo ""
echo "✅ All checks passed!"
echo ""
echo "🤖 Starting Telegram bot..."
echo "========================================"
echo ""

python -m app.telegram_bot.main
