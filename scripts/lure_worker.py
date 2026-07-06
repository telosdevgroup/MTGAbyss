import os
import sys
import time
import json
import urllib.request
import urllib.parse
import argparse
import socket

# Add current directory and parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from lure_shared import clean_lure_text, validate_lure_text
except ImportError:
    from scripts.lure_shared import clean_lure_text, validate_lure_text

def run_ollama(ollama_url, model, prompt):
    url = f"{ollama_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.4
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=120) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data.get("response", "").strip()

def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))

def get_json(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))

def main():
    # Setup default values
    hostname = socket.gethostname()
    default_worker_id = f"worker_{hostname}_{os.getpid()}"
    
    parser = argparse.ArgumentParser(description="Lure Generation Worker")
    parser.add_argument("--controller-url", default=os.environ.get("CONTROLLER_URL", "http://127.0.0.1:5000"), help="Controller API base URL")
    parser.add_argument("--worker-id", default=os.environ.get("WORKER_ID", default_worker_id), help="Unique ID for this worker")
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"), help="Ollama API base URL")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "mistral-small3.2:24b"), help="Ollama model to use")
    parser.add_argument("--sleep-seconds", type=int, default=int(os.environ.get("SLEEP_SECONDS", "5")), help="Sleep duration between jobs")
    parser.add_argument("--smoke-test", type=int, nargs="?", const=3, default=None, help="Process N jobs then exit (default 3 if flag passed without number)")
    parser.add_argument("--dry-run", action="store_true", help="Polled jobs are simulated and not sent to Ollama")
    parser.add_argument("--force", action="store_true", help="Force claim cards even if they already have a generated Lure")
    args = parser.parse_args()

    print("=== Starting Lure Worker ===")
    print(f"Worker ID:      {args.worker_id}")
    print(f"Controller URL: {args.controller_url}")
    print(f"Ollama URL:     {args.ollama_url}")
    print(f"Model:          {args.model}")
    print(f"Sleep Seconds:  {args.sleep_seconds}")
    if args.smoke_test:
        print(f"Smoke Test Mode: will exit after {args.smoke_test} job(s)")
    if args.dry_run:
        print("Dry Run: Lure generation is mocked!")
    print("============================")

    jobs_processed = 0

    while True:
        # Check smoke test limit
        if args.smoke_test is not None and jobs_processed >= args.smoke_test:
            print(f"Smoke test limit of {args.smoke_test} jobs reached. Exiting worker.")
            break

        # Poll for a job
        claim_url = f"{args.controller_url.rstrip('/')}/jobs/claim"
        try:
            claim_response = post_json(claim_url, {
                "worker_id": args.worker_id,
                "force": args.force
            })
        except Exception as e:
            print(f"Error connecting to controller at {claim_url}: {e}")
            print(f"Retrying in {args.sleep_seconds} seconds...")
            time.sleep(args.sleep_seconds)
            continue

        job_id = claim_response.get("job_id")
        if not job_id:
            print("No jobs available. Sleeping...")
            time.sleep(args.sleep_seconds)
            continue

        card_name = claim_response.get("card_name")
        prompt = claim_response.get("prompt")
        remaining = claim_response.get("remaining", "?")
        print(f"\n[Claimed Job] Card Name: '{card_name}' (ID: {job_id}, {remaining} remaining)")

        # Generate Lure
        start_time = time.time()
        try:
            if args.dry_run:
                raw_lure = f"Beneath the quiet boughs of the ancient forest, {card_name} watches. A myth told in whispers, it commands the respect of the land, drawing those who wander too deep into its timeless grasp. A silent witness to the passage of ages, it remains waiting."
            else:
                raw_lure = run_ollama(args.ollama_url, args.model, prompt)

            elapsed = time.time() - start_time
            print(f"Ollama generation completed in {elapsed:.2f} seconds.")

            cleaned_lure = clean_lure_text(raw_lure)
            is_valid, validation_error = validate_lure_text(cleaned_lure, card_name)
            
            if is_valid:
                print("Lure text validation passed!")
                print(f"Generated Lure:\n----------------------------------------\n{cleaned_lure}\n----------------------------------------")
                # Complete the job
                complete_url = f"{args.controller_url.rstrip('/')}/jobs/{job_id}/complete"
                complete_response = post_json(complete_url, {
                    "text": cleaned_lure,
                    "model": args.model,
                    "worker_id": args.worker_id
                })
                print(f"Submitted success: {complete_response}")
            else:
                print(f"Validation failed: {validation_error}")
                print(f"Failed Lure text was:\n----------------------------------------\n{cleaned_lure}\n----------------------------------------")
                # Fail the job
                fail_url = f"{args.controller_url.rstrip('/')}/jobs/{job_id}/fail"
                fail_response = post_json(fail_url, {
                    "error": f"Validation failed: {validation_error}",
                    "worker_id": args.worker_id
                })
                print(f"Submitted failure: {fail_response}")

        except Exception as e:
            print(f"Error processing job for {card_name}: {e}")
            try:
                fail_url = f"{args.controller_url.rstrip('/')}/jobs/{job_id}/fail"
                fail_response = post_json(fail_url, {
                    "error": str(e),
                    "worker_id": args.worker_id
                })
                print(f"Submitted failure report: {fail_response}")
            except Exception:
                pass

        jobs_processed += 1
        time.sleep(args.sleep_seconds)

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    main()
