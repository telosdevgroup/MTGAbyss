#!/usr/bin/env python3
"""
Convenience entrypoint for scripts/network_blaster.py.
Allows running `python network_blaster.py --deep` directly from repository root.
"""
import os
import sys

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "network_blaster.py")

if __name__ == "__main__":
    with open(SCRIPT_PATH, "rb") as f:
        code = compile(f.read(), SCRIPT_PATH, "exec")
        exec(code, {"__name__": "__main__", "__file__": SCRIPT_PATH})
