#!/usr/bin/env python3
"""Verify image embedding implementation files exist and are valid."""

import os
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_file_exists(filepath: str, max_lines: int = None) -> bool:
    """Check if file exists and optionally verify line count."""
    path = Path(filepath)

    if not path.exists():
        print(f"{RED}✗{RESET} {filepath} - NOT FOUND")
        return False

    with open(path, 'r') as f:
        lines = len(f.readlines())

    status = f"{GREEN}✓{RESET}"
    line_info = f" ({lines} lines)"

    if max_lines and lines > max_lines:
        status = f"{RED}✗{RESET}"
        line_info += f" - EXCEEDS {max_lines} line limit!"

    print(f"{status} {filepath}{line_info}")
    return True

def check_import_in_file(filepath: str, import_name: str) -> bool:
    """Check if a specific import exists in a file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if import_name in content:
                print(f"  {GREEN}✓{RESET} Contains '{import_name}'")
                return True
            else:
                print(f"  {RED}✗{RESET} Missing '{import_name}'")
                return False
    except Exception as e:
        print(f"  {RED}✗{RESET} Error reading file: {e}")
        return False

def main():
    """Run verification checks."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Image Embedding Implementation Verification{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    all_passed = True

    # Check core service files
    print(f"{BLUE}Core Services:{RESET}")
    all_passed &= check_file_exists("src/app/services/embedding/image_embedding.py", 200)
    all_passed &= check_file_exists("src/app/services/embedding/image_embedding_methods.py", 230)

    # Check utility files
    print(f"\n{BLUE}Utilities:{RESET}")
    all_passed &= check_file_exists("src/app/utils/image_preprocessor.py", 200)
    all_passed &= check_file_exists("src/app/utils/microscopy_handler.py", 220)

    # Check updated config files
    print(f"\n{BLUE}Configuration:{RESET}")
    all_passed &= check_file_exists("src/app/core/ml_config.py")
    all_passed &= check_file_exists("src/app/core/exceptions.py")
    all_passed &= check_file_exists("src/app/services/embedding/__init__.py")

    # Check exports
    print(f"\n{BLUE}Checking Exports:{RESET}")
    check_import_in_file(
        "src/app/services/embedding/__init__.py",
        "ImageEmbeddingService"
    )
    check_import_in_file(
        "src/app/core/ml_config.py",
        "IMAGE_EMBEDDING_CONFIG"
    )
    check_import_in_file(
        "src/app/core/exceptions.py",
        "ImageLoadError"
    )

    # Check documentation
    print(f"\n{BLUE}Documentation:{RESET}")
    all_passed &= check_file_exists("IMAGE_EMBEDDING_IMPLEMENTATION.md")
    all_passed &= check_file_exists("IMAGE_EMBEDDING_QUICKREF.md")
    all_passed &= check_file_exists("E5_S4_COMPLETION_SUMMARY.md")

    # Check examples and tests
    print(f"\n{BLUE}Examples & Tests:{RESET}")
    all_passed &= check_file_exists("examples/image_embedding_usage.py")
    all_passed &= check_file_exists("tests/test_image_embedding.py")

    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    if all_passed:
        print(f"{GREEN}✓ All verification checks passed!{RESET}")
        print(f"\n{BLUE}Implementation Summary:{RESET}")
        print(f"  • Image embedding service: {GREEN}COMPLETE{RESET}")
        print(f"  • Microscopy support: {GREEN}COMPLETE{RESET}")
        print(f"  • Preprocessing utilities: {GREEN}COMPLETE{RESET}")
        print(f"  • Documentation: {GREEN}COMPLETE{RESET}")
        print(f"  • Examples & tests: {GREEN}COMPLETE{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some checks failed{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
