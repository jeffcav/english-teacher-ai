#!/usr/bin/env python3
"""
Telegram Bot Implementation Verification Script
Validates all components are in place and working
"""

import sys
import os
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_file(path, required=True):
    """Check if file exists"""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {path}")
    return exists if required else True

def check_directory(path):
    """Check if directory exists"""
    exists = Path(path).is_dir()
    status = "✅" if exists else "❌"
    print(f"{status} {path}/")
    return exists

def check_import(module_name):
    """Check if Python module can be imported"""
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {module_name}: {str(e)}")
        return False

def main():
    """Run verification checks"""
    print_header("PhonicFlow Telegram Bot - Implementation Verification")
    
    all_checks_passed = True
    
    # 1. Directory Structure
    print_header("1. Directory Structure")
    dirs_to_check = [
        "app/telegram_bot",
        "app/telegram_bot/handlers",
        "app/telegram_bot/utils",
        "logs"
    ]
    for dir_path in dirs_to_check:
        if not check_directory(dir_path):
            all_checks_passed = False
    
    # 2. Core Files
    print_header("2. Core Files")
    core_files = [
        "app/telegram_bot/__init__.py",
        "app/telegram_bot/config.py",
        "app/telegram_bot/bot.py",
        "app/telegram_bot/main.py",
    ]
    for file_path in core_files:
        if not check_file(file_path):
            all_checks_passed = False
    
    # 3. Handler Files
    print_header("3. Handler Files")
    handler_files = [
        "app/telegram_bot/handlers/__init__.py",
        "app/telegram_bot/handlers/message_handler.py",
        "app/telegram_bot/handlers/audio_handler.py",
    ]
    for file_path in handler_files:
        if not check_file(file_path):
            all_checks_passed = False
    
    # 4. Utility Files
    print_header("4. Utility Files")
    util_files = [
        "app/telegram_bot/utils/__init__.py",
        "app/telegram_bot/utils/api_client.py",
        "app/telegram_bot/utils/session_manager.py",
        "app/telegram_bot/utils/audio_converter.py",
    ]
    for file_path in util_files:
        if not check_file(file_path):
            all_checks_passed = False
    
    # 5. Docker & Config Files
    print_header("5. Docker & Configuration Files")
    docker_files = [
        "Dockerfile.telegram_bot",
        ".env.telegram.example",
        "docker-compose.yml",
    ]
    for file_path in docker_files:
        if not check_file(file_path):
            all_checks_passed = False
    
    # 6. Documentation
    print_header("6. Documentation Files")
    doc_files = [
        "plan_telegram.md",
        "TELEGRAM_SETUP_GUIDE.md",
        "TELEGRAM_IMPLEMENTATION_SUMMARY.md",
    ]
    for file_path in doc_files:
        if not check_file(file_path):
            all_checks_passed = False
    
    # 7. Scripts
    print_header("7. Helper Scripts")
    script_files = [
        "start_telegram_bot.sh",
    ]
    for file_path in script_files:
        if not check_file(file_path, required=False):
            pass  # Optional
    
    # 8. Python Imports (Core)
    print_header("8. Python Module Imports")
    modules_to_check = [
        "app.telegram_bot.config",
        "app.telegram_bot.bot",
        "app.telegram_bot.main",
        "app.telegram_bot.handlers.message_handler",
        "app.telegram_bot.handlers.audio_handler",
        "app.telegram_bot.utils.api_client",
        "app.telegram_bot.utils.session_manager",
        "app.telegram_bot.utils.audio_converter",
    ]
    
    imports_ok = True
    for module in modules_to_check:
        if not check_import(module):
            imports_ok = False
    
    all_checks_passed = all_checks_passed and imports_ok
    
    # 9. External Dependencies
    print_header("9. External Dependencies")
    dependencies = [
        "telegram",
        "pydub",
        "requests",
    ]
    
    deps_ok = True
    for dep in dependencies:
        if not check_import(dep):
            deps_ok = False
    
    all_checks_passed = all_checks_passed and deps_ok
    
    # 10. Requirements.txt
    print_header("10. Dependencies in requirements.txt")
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
            telegram_bot_ok = "python-telegram-bot" in content
            pydub_ok = "pydub" in content
            
            status = "✅" if telegram_bot_ok else "❌"
            print(f"{status} python-telegram-bot==20.0")
            
            status = "✅" if pydub_ok else "❌"
            print(f"{status} pydub==0.25.1")
            
            all_checks_passed = all_checks_passed and telegram_bot_ok and pydub_ok
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        all_checks_passed = False
    
    # 11. Environment Variables
    print_header("11. Environment Variables (for runtime)")
    env_vars = [
        "TELEGRAM_BOT_TOKEN",
        "BACKEND_URL",
    ]
    
    print("Note: These are required at runtime, not during installation\n")
    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        if value == "NOT SET":
            print(f"⚠️  {var}: NOT SET (will be needed to run)")
        else:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {masked}")
    
    # 12. File Count Summary
    print_header("12. File Summary")
    python_files = list(Path("app/telegram_bot").glob("**/*.py"))
    print(f"📊 Python files in app/telegram_bot: {len(python_files)}")
    for pf in sorted(python_files):
        print(f"   - {pf}")
    
    # Final Result
    print_header("VERIFICATION RESULT")
    
    if all_checks_passed and imports_ok and deps_ok:
        print("✅ ALL CHECKS PASSED!\n")
        print("The Telegram bot implementation is complete and ready for testing.")
        print("\nNext steps:")
        print("1. Set environment variables:")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("   export BACKEND_URL='http://localhost:8000'")
        print("\n2. Start the backend:")
        print("   python -m uvicorn app.backend.main:app --reload")
        print("\n3. Start the bot:")
        print("   python -m app.telegram_bot.main")
        print("\n4. Or use Docker:")
        print("   docker-compose up telegram_bot")
        print("\nFor detailed setup, see: TELEGRAM_SETUP_GUIDE.md")
        return 0
    else:
        print("❌ SOME CHECKS FAILED!\n")
        print("Please ensure all files are created and dependencies are installed.")
        print("\nQuick fixes:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Install ffmpeg: sudo apt-get install ffmpeg (Linux)")
        print("3. Check files exist: ls -la app/telegram_bot/")
        return 1

if __name__ == "__main__":
    sys.exit(main())
