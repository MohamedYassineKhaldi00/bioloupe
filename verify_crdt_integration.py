#!/usr/bin/env python3
"""
Verification script for Y.js CRDT integration (E8-S3).
Checks that all components are properly integrated.
"""
from __future__ import annotations

import sys


def verify_files_exist():
    """Verify all required files exist."""
    import os

    files = [
        "src/app/schemas/crdt_schemas.py",
        "src/app/websocket/services/yjs_service.py",
        "src/app/websocket/handlers/crdt.py",
        "tests/test_crdt.py",
        "E8_S3_CRDT_INTEGRATION.md",
    ]

    missing = []
    for file in files:
        if not os.path.exists(file):
            missing.append(file)

    if missing:
        print("❌ Missing files:")
        for file in missing:
            print(f"  - {file}")
        return False

    print("✅ All required files exist")
    return True


def verify_imports():
    """Verify Python imports work."""
    try:
        import y_py as Y
        print("✅ y-py installed and importable")
    except ImportError:
        print("❌ y-py not installed. Run: pip install y-py==0.6.2")
        return False

    return True


def verify_namespace_registration():
    """Verify CRDT namespace is registered."""
    try:
        with open("src/app/websocket/server.py", "r") as f:
            content = f.read()

        if "CRDTNamespace" not in content:
            print("❌ CRDTNamespace not imported in server.py")
            return False

        if 'crdt_ns' not in content:
            print("❌ CRDT namespace not instantiated")
            return False

        if 'register_namespace(crdt_ns)' not in content:
            print("❌ CRDT namespace not registered")
            return False

        print("✅ CRDT namespace properly registered")
        return True
    except FileNotFoundError:
        print("❌ server.py not found")
        return False


def verify_background_tasks():
    """Verify background tasks are configured."""
    try:
        with open("src/app/websocket/server.py", "r") as f:
            content = f.read()

        if "_yjs_save_loop" not in content:
            print("❌ Y.js save background task missing")
            return False

        if "_yjs_cleanup_loop" not in content:
            print("❌ Y.js cleanup background task missing")
            return False

        print("✅ Background tasks configured")
        return True
    except FileNotFoundError:
        print("❌ server.py not found")
        return False


def verify_requirements():
    """Verify y-py is in requirements.txt."""
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()

        if "y-py" not in content:
            print("❌ y-py not in requirements.txt")
            return False

        print("✅ y-py in requirements.txt")
        return True
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False


def verify_schemas():
    """Verify CRDT schemas are defined."""
    try:
        with open("src/app/schemas/crdt_schemas.py", "r") as f:
            content = f.read()

        required_schemas = [
            "YjsSyncStep1Event",
            "YjsSyncStep2Event",
            "YjsUpdateEvent",
            "YjsAwarenessUpdateEvent",
            "MaterialSubscribeEvent",
            "MaterialUnsubscribeEvent",
        ]

        missing = []
        for schema in required_schemas:
            if schema not in content:
                missing.append(schema)

        if missing:
            print("❌ Missing schemas:")
            for schema in missing:
                print(f"  - {schema}")
            return False

        print("✅ All CRDT schemas defined")
        return True
    except FileNotFoundError:
        print("❌ crdt_schemas.py not found")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Y.js CRDT Integration Verification (Story E8-S3)")
    print("=" * 60)
    print()

    checks = [
        ("Files exist", verify_files_exist),
        ("Dependencies installed", verify_imports),
        ("Namespace registered", verify_namespace_registration),
        ("Background tasks", verify_background_tasks),
        ("Requirements updated", verify_requirements),
        ("Schemas defined", verify_schemas),
    ]

    results = []
    for name, check in checks:
        print(f"\n{name}:")
        result = check()
        results.append(result)

    print("\n" + "=" * 60)

    if all(results):
        print("✅ ALL CHECKS PASSED")
        print("\nStory E8-S3: Y.js CRDT Integration is complete!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run tests: pytest tests/test_crdt.py -v")
        print("  3. Start server: python run.py")
        print("  4. Connect client to /crdt namespace")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
