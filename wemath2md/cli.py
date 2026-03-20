"""Installed CLI entrypoint for WeMath2MD."""

from pathlib import Path
import sys


def main() -> int | None:
    # Editable installs execute from the environment bin directory, not the repo
    # root. Insert the repo root so the existing flat modules remain importable.
    repo_root = Path(__file__).resolve().parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    from main import main as root_main

    return root_main()

