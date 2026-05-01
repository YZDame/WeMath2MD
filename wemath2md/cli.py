"""Installed CLI entrypoint for WeMath2MD."""

from importlib import import_module


def main() -> int | None:
    """Run the project CLI entrypoint."""
    root_main = import_module("main").main
    return root_main()
