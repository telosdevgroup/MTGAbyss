#!/usr/bin/env python3
"""
minecraft_run_all_embeddings.py — Orchestrator to chain run all Minecraft embedding pipelines.

Sequentially executes:
1. Functional & Semantic Intent Embeddings (`minecraft_generate_functional_embeddings.py`)
2. Visual & Architectural Palette Embeddings (`minecraft_generate_palette_embeddings.py`)
3. Graph & Crafting Progression Embeddings (`minecraft_generate_graph_embeddings.py`)

Usage:
    python scripts/minecraft_run_all_embeddings.py
    python scripts/minecraft_run_all_embeddings.py --limit 100
"""

import os
import sys
import time
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def run_stage(title: str, script_name: str, extra_args: list):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"\n=======================================================")
    print(f" [*] STARTING STAGE: {title}")
    print(f"=======================================================")
    start_time = time.time()
    cmd = [sys.executable, script_path] + extra_args
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    elapsed = time.time() - start_time
    if proc.returncode != 0:
        print(f" [!] Error: Stage '{title}' exited with code {proc.returncode}")
        return False
    print(f" [OK] COMPLETED: {title} in {elapsed:.2f}s")
    return True


def main():
    parser = argparse.ArgumentParser(description="Chain run all Minecraft embedding generators")
    parser.add_argument("--limit", type=int, default=0, help="Limit items/blocks per stage (0 = all)")
    args = parser.parse_args()

    extra = []
    if args.limit > 0:
        extra = ["--limit", str(args.limit)]

    total_start = time.time()
    stages = [
        ("Functional & Semantic Embeddings", "minecraft_generate_functional_embeddings.py"),
        ("Visual & Architectural Palette Embeddings", "minecraft_generate_palette_embeddings.py"),
        ("Graph & Crafting Progression Embeddings", "minecraft_generate_graph_embeddings.py"),
    ]

    for title, script in stages:
        success = run_stage(title, script, extra)
        if not success:
            sys.exit(1)

    total_elapsed = time.time() - total_start
    print(f"\n=======================================================")
    print(f" [OK] ALL EMBEDDING PIPELINES FINISHED SUCCESSFULLY ({total_elapsed:.2f}s)")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
