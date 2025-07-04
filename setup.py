#!/usr/bin/env python3
"""
Setup script for Conway's Game of Life Spaceship Trading Cards
Automates the installation and configuration process
"""

import os
import sys
import subprocess
import platform


def run_command(command, description, cwd=None):
    """Run a shell command with error handling"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            cwd=cwd,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def check_git():
    """Check if git is available"""
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_make():
    """Check if make is available"""
    try:
        subprocess.run(["make", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def setup_submodules():
    """Initialize and update git submodules"""
    if not check_git():
        print("❌ Git is not available. Please install Git first.")
        return False
    
    print("\n📥 Setting up submodules...")
    
    # Initialize submodules
    if not run_command("git submodule update --init --recursive", "Initializing submodules"):
        return False
    
    return True


def compile_ntzfind():
    """Compile the ntzfind tool"""
    ntzfind_dir = os.path.join("submodules", "ntzfind")
    
    if not os.path.exists(ntzfind_dir):
        print("❌ ntzfind submodule not found. Please run submodule setup first.")
        return False
    
    if not check_make():
        print("❌ Make is not available. Please install build tools.")
        print("   On Ubuntu/Debian: sudo apt install build-essential")
        print("   On macOS: xcode-select --install")
        print("   On Windows: Install Visual Studio Build Tools or use WSL")
        return False
    
    print("\n🔨 Compiling ntzfind...")
    
    # Check if already compiled
    ntzfind_exe = os.path.join(ntzfind_dir, "ntzfind")
    if os.path.exists(ntzfind_exe):
        print("✅ ntzfind already compiled")
        return True
    
    return run_command("make", "Compiling ntzfind", cwd=ntzfind_dir)


def install_python_deps():
    """Install Python dependencies"""
    print("\n🐍 Installing Python dependencies...")
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found")
        return False
    
    return run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python packages"
    )


def create_directories():
    """Create necessary output directories"""
    print("\n📁 Creating output directories...")
    
    directories = [
        "gifs",
        "qrs", 
        "card_fronts",
        "card_backs",
        "card_backgrounds",
        "fonts"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created {directory}/ directory")
    
    return True


def main():
    """Main setup function"""
    print("=" * 60)
    print("  Conway's Game of Life Spaceship Trading Cards Setup")
    print("=" * 60)
    print()
    
    print(f"🖥️  Platform: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    success = True
    
    # Step 1: Setup submodules
    if not setup_submodules():
        success = False
    
    # Step 2: Install Python dependencies
    if not install_python_deps():
        success = False
        print("⚠️  You can install dependencies manually with: pip install -r requirements.txt")
    
    # Step 3: Compile ntzfind
    if not compile_ntzfind():
        success = False
        print("⚠️  You can compile ntzfind manually with: cd submodules/ntzfind && make")
    
    # Step 4: Create directories
    if not create_directories():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Setup completed successfully!")
        print("\n🚀 You can now run: python main.py")
    else:
        print("⚠️  Setup completed with some issues.")
        print("   Please check the errors above and resolve them manually.")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        sys.exit(1)