#!/usr/bin/env python3
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Start a Celery worker for MTGAbyss with explicit host parameters.")
    parser.add_argument("--mongo-host", default="192.168.1.213", help="MongoDB host / IP (default: 192.168.1.213)")
    parser.add_argument("--mongo-port", type=int, default=27017, help="MongoDB port (default: 27017)")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Ollama base URL (default: http://127.0.0.1:11434)")
    parser.add_argument("--model", default="qwen3-vl:latest", help="VL model (default: qwen3-vl:latest)")
    parser.add_argument("--queue", default="vl", help="Celery queue to consume (default: vl)")
    parser.add_argument("--pool", default="solo", help="Celery concurrency pool (default: solo)")
    parser.add_argument("--concurrency", "-c", type=int, default=1, help="Celery concurrency count (default: 1)")
    parser.add_argument("--loglevel", default="info", help="Log level (default: info)")
    args, unknown = parser.parse_known_args()

    # Pass configuration directly into process environment before importing celery
    os.environ["MONGODB_URI"] = f"mongodb://{args.mongo_host}:{args.mongo_port}"
    os.environ["OLLAMA_URL"] = args.ollama_url.rstrip("/")
    os.environ["OLLAMA_VL_MODEL"] = args.model

    print("=" * 60)
    print("MTGAbyss Worker Bootloader")
    print("=" * 60)
    print(f"MongoDB Target : mongodb://{args.mongo_host}:{args.mongo_port}")
    print(f"Ollama Target  : {args.ollama_url} (Model: {args.model})")
    print(f"Queue          : {args.queue}")
    print(f"Pool           : {args.pool} (Concurrency: {args.concurrency})")
    print("=" * 60)

    from celery_app import app

    celery_argv = [
        "worker",
        "-Q", args.queue,
        "-P", args.pool,
        "-c", str(args.concurrency),
        f"--loglevel={args.loglevel}"
    ] + unknown

    app.worker_main(celery_argv)

if __name__ == "__main__":
    main()
