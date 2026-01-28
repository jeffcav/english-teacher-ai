"""
Quick start script to initialize PhonicFlow.
Handles first-time setup and validation.
"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a shell command and report results."""
    print(f"  • {description}...", end=" ", flush=True)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓")
            return True
        else:
            print("✗")
            print(f"    Error: {result.stderr}")
            return False
    except Exception as e:
        print("✗")
        print(f"    Error: {str(e)}")
        return False


def check_prerequisites():
    """Check if all prerequisites are met."""
    print("\n🔍 Checking Prerequisites...")
    print("=" * 50)
    
    checks = {
        "Python 3.10+": "python3 --version",
        "Pip": "pip3 --version",
        "FFmpeg": "ffmpeg -version",
    }
    
    passed = True
    for check_name, command in checks.items():
        if run_command(command, f"Checking {check_name}"):
            continue
        else:
            passed = False
            print(f"    ⚠️  {check_name} not found or outdated")
    
    # Check for Ollama
    print(f"  • Checking for Ollama...", end=" ", flush=True)
    try:
        result = subprocess.run(
            "curl -s http://localhost:11434/tags",
            shell=True,
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ (running locally)")
        else:
            print("⚠️  (not running locally)")
            print("    Note: Ollama must be running separately")
    except:
        print("⚠️  (not accessible)")
        print("    Note: Start Ollama with: ollama serve")
    
    return passed


def setup_directories():
    """Create necessary project directories."""
    print("\n📁 Setting Up Directories...")
    print("=" * 50)
    
    dirs = [
        "app/feedback_storage",
        "logs",
        ".git"  # If not already a git repo
    ]
    
    for dir_path in dirs:
        if not Path(dir_path).exists():
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {dir_path}")
        else:
            print(f"  ✓ Already exists: {dir_path}")


def create_env_file():
    """Create .env file from template if not exists."""
    print("\n⚙️  Setting Up Configuration...")
    print("=" * 50)
    
    if Path(".env").exists():
        print("  ✓ .env file already exists")
        return
    
    if Path(".env.example").exists():
        subprocess.run("cp .env.example .env", shell=True)
        print("  ✓ Created .env from .env.example")
        print("  ⚠️  Please review and update .env as needed")
    else:
        print("  ⚠️  .env.example not found")


def display_next_steps():
    """Display next steps for the user."""
    print("\n" + "=" * 50)
    print("✅ Setup Complete!")
    print("=" * 50)
    print("\n🚀 Next Steps:")
    print("\n1. Ensure Ollama is running:")
    print("   $ ollama serve")
    print("\n2. Download required model:")
    print("   $ ollama pull llama3")
    print("\n3. In a new terminal, start the backend:")
    print("   $ source venv/bin/activate")
    print("   $ python -m uvicorn app.backend.main:app --reload")
    print("\n4. In another terminal, start the frontend:")
    print("   $ source venv/bin/activate")
    print("   $ streamlit run app/frontend/streamlit_app.py")
    print("\n5. Open your browser:")
    print("   http://localhost:8501")
    print("\n" + "=" * 50)


def main():
    """Main setup flow."""
    print("\n")
    print("╔" + "═" * 48 + "╗")
    print("║" + " PhonicFlow - AI English Tutor Setup ".center(48) + "║")
    print("╚" + "═" * 48 + "╝")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n⚠️  Some prerequisites are missing!")
        print("Please install them before continuing.")
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Create environment file
    create_env_file()
    
    # Display next steps
    display_next_steps()


if __name__ == "__main__":
    main()
