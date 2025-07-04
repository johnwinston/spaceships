#!/usr/bin/env python3
"""
Conway's Game of Life Spaceship Trading Cards
Interactive tool for discovering spaceships and creating trading cards
"""

import os
import sys
from src.auto_ntzfind import AUTO_NTZFIND
from src.rle2apgcode import RLE2APGCODE
from src.cleanup import CLEANUP
from src.combine import COMBINE
from submodules import lifelib


def print_banner():
    """Print welcome banner"""
    print("=" * 60)
    print("  Conway's Game of Life Spaceship Trading Cards")
    print("=" * 60)
    print("  Discover spaceships and create beautiful trading cards!")
    print("=" * 60)
    print()


def get_yes_no(prompt):
    """Get yes/no input from user"""
    while True:
        response = input(f"{prompt} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def get_positive_int(prompt):
    """Get a positive integer from user"""
    while True:
        try:
            value = int(input(f"{prompt}: "))
            if value > 0:
                return value
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")


def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    
    # Check if ntzfind is compiled
    ntzfind_path = os.path.join("submodules", "ntzfind", "ntzfind")
    if not os.path.exists(ntzfind_path):
        missing.append("ntzfind executable (run 'make' in submodules/ntzfind/)")
    
    # Check if lifelib is available
    if not os.path.exists(os.path.join("submodules", "lifelib")):
        missing.append("lifelib submodule")
    
    return missing


def main():
    """Main interactive interface"""
    print_banner()
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print("⚠️  Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\nPlease see README.md for installation instructions.")
        print("Continuing anyway...\n")
    
    period = 0
    
    # Step 1: Auto-ntzfind
    print("🔍 STEP 1: Spaceship Discovery")
    print("Use ntzfind to search for new spaceships with a given period.")
    
    if get_yes_no("Run spaceship discovery"):
        period = get_positive_int("Enter period (e.g., 2, 3, 4)")
        iterations = get_positive_int("Number of spaceships to find")
        
        print(f"\n🧹 Clearing previous results for period {period}...")
        try:
            CLEANUP(period).clear_files()
            print("✅ Files cleared")
        except Exception as e:
            print(f"❌ Error clearing files: {e}")
            return
        
        print(f"🚀 Searching for {iterations} spaceships with period {period}...")
        try:
            AUTO_NTZFIND(iterations, period).run()
            print("✅ Spaceship search completed")
            
            # Automatically run RLE2APGCODE after successful search
            print("🔄 Converting patterns to APG codes...")
            RLE2APGCODE(lifelib, period).run()
            print("✅ Pattern conversion completed")
        except Exception as e:
            print(f"❌ Error during spaceship search: {e}")
    
    print()
    
    # Step 2: RLE to APG (if not already done)
    print("🔄 STEP 2: Pattern Processing")
    print("Convert RLE files to APG codes and generate QR codes.")
    
    if get_yes_no("Run pattern processing"):
        if period == 0:
            period = get_positive_int("Enter period")
        
        print(f"📝 Processing patterns for period {period}...")
        try:
            RLE2APGCODE(lifelib, period).run()
            print("✅ Pattern processing completed")
        except Exception as e:
            print(f"❌ Error processing patterns: {e}")
    
    print()
    
    # Step 3: Cleanup
    print("🧹 STEP 3: Pattern Review")
    print("Review discovered patterns and select the best ones.")
    
    if get_yes_no("Review and select patterns"):
        if period == 0:
            period = get_positive_int("Enter period")
        
        print(f"👀 Opening pattern review interface for period {period}...")
        try:
            CLEANUP(period).select_patterns()
            print("✅ Pattern review completed")
        except Exception as e:
            print(f"❌ Error during pattern review: {e}")
    
    print()
    
    # Step 4: Combine
    print("🎨 STEP 4: Trading Card Creation")
    print("Generate beautiful trading cards from selected patterns.")
    
    if get_yes_no("Create trading cards"):
        if period == 0:
            period = get_positive_int("Enter period")
        
        print(f"🎴 Creating trading cards for period {period}...")
        try:
            COMBINE(period).run()
            print("✅ Trading cards created successfully!")
            print("📁 Check the following directories for output:")
            print("   - card_fronts/ : Front side of cards")
            print("   - card_backs/  : Back side of cards")
            print("   - Sheets will be created for printing")
        except Exception as e:
            print(f"❌ Error creating trading cards: {e}")
    
    print()
    print("🎉 All done! Thanks for using the Spaceship Trading Card generator!")
    print("🌟 Share your discoveries with the Conway's Game of Life community!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error and try again.")
        sys.exit(1)
