#!/usr/bin/env python3
import os
import sys

# Ensure the plasmoid contents directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
contents_dir = os.path.dirname(script_dir)
if contents_dir not in sys.path:
    sys.path.insert(0, contents_dir)

try:
    from backend.collector import update_local, DEFAULT_CACHE_PATH
except Exception as e:
    sys.stderr.write(f"[WidgetTokens] Import error: {e}\n")
    update_local = None
    DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/plasma-tokens/history.json")


def main():
    # Only skip update if --read-only flag is explicitly passed
    read_only = "--read-only" in sys.argv

    if not read_only and update_local is not None:
        try:
            update_local()
        except Exception as e:
            sys.stderr.write(f"[WidgetTokens] Collection error: {e}\n")

    # Output JSON directly to stdout for Plasma5Support.DataSource
    if os.path.exists(DEFAULT_CACHE_PATH):
        try:
            with open(DEFAULT_CACHE_PATH, "r", encoding="utf-8") as f:
                sys.stdout.write(f.read())
                return
        except Exception as e:
            sys.stderr.write(f"[WidgetTokens] Read error: {e}\n")

    sys.stdout.write('{"summary":{},"days":[]}')


if __name__ == "__main__":
    main()
