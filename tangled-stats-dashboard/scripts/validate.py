#!/usr/bin/env python3
"""
Validate workspace configuration.

Checks that submodules are properly initialized and on correct branches.
"""

import subprocess
import sys
from pathlib import Path


def get_workspace_root() -> Path:
    """Get workspace root (parent of this repo)."""
    return Path(__file__).parent.parent.parent.resolve()


def check_submodule_exists() -> tuple[bool, str]:
    """Check that main repo submodule exists."""
    workspace = get_workspace_root()
    main_repo = workspace / "snowdrop-tangled-agents"

    if not main_repo.exists():
        return False, f"""
Main repo submodule not found: {main_repo}

To fix, initialize submodules:
    cd {workspace}
    git submodule update --init --recursive
"""
    return True, f"Submodule exists: {main_repo}"


def check_stats_module() -> tuple[bool, str]:
    """Check that stats module exists in main repo."""
    workspace = get_workspace_root()
    stats = workspace / "snowdrop-tangled-agents" / "snowdrop_tangled_agents" / "stats"

    if not stats.exists():
        main_repo = workspace / "snowdrop-tangled-agents"
        return False, f"""
Stats module not found. Main repo may be on wrong branch.

To fix:
    cd {main_repo}
    git checkout feature/dynamic-learning
    git pull
"""
    return True, "Stats module found"


def check_imports() -> tuple[bool, str]:
    """Check that Python imports work."""
    workspace = get_workspace_root()
    main_repo = workspace / "snowdrop-tangled-agents"

    sys.path.insert(0, str(main_repo))
    try:
        from snowdrop_tangled_agents.stats.collector import StatsCollector
        return True, "Imports OK"
    except ImportError as e:
        return False, f"Import failed: {e}"
    finally:
        sys.path.pop(0)


def main():
    print("=" * 50)
    print("Workspace Validation")
    print("=" * 50)
    print()

    checks = [
        ("Submodule exists", check_submodule_exists),
        ("Stats module", check_stats_module),
        ("Python imports", check_imports),
    ]

    all_passed = True
    for name, fn in checks:
        passed, msg = fn()
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        if not passed:
            print(msg)
            all_passed = False
        print()

    print("=" * 50)
    if all_passed:
        print("All checks passed!")
    else:
        print("Some checks failed. See above for fixes.")
    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
