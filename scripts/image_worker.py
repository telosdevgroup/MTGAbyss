import os
import sys
import time
import json
import urllib.request
import urllib.parse
import argparse
import socket
import random
import threading
from concurrent.futures import ThreadPoolExecutor

class SafeCounter:
    def __init__(self, limit=None):
        self.value = 0
        self.limit = limit
        self.lock = threading.Lock()
        
    def check_and_increment(self):
        with self.lock:
            if self.limit is not None and self.value >= self.limit:
                return False
            self.value += 1
            return True

def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))

def encode_multipart_formdata(fields, files):
    boundary = b'-----Boundary' + bytes(str(time.time()).replace('.', ''), 'utf-8')
    body = []
    
    for key, value in fields.items():
        body.append(b'--' + boundary)
        body.append(bytes(f'Content-Disposition: form-data; name="{key}"', 'utf-8'))
        body.append(b'')
        body.append(bytes(str(value), 'utf-8'))
        
    for key, (filename, file_content) in files.items():
        body.append(b'--' + boundary)
        body.append(bytes(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"', 'utf-8'))
        body.append(b'Content-Type: image/jpeg')
        body.append(b'')
        body.append(file_content)
        
    body.append(b'--' + boundary + b'--')
    body.append(b'')
    
    return boundary, b'\r\n'.join(body)

def worker_thread_loop(args, thread_idx, counter):
    worker_id = f"{args.worker_id}_t{thread_idx}"
    print(f"Worker thread {thread_idx} started.")

    while True:
        # Check smoke test limit safely before claiming
        if args.smoke_test is not None:
            with counter.lock:
                if counter.value >= args.smoke_test:
                    break

        # Claim a job
        claim_url = f"{args.controller_url.rstrip('/')}/jobs/claim_image"
        try:
            claim_response = post_json(claim_url, {
                "worker_id": worker_id,
                "force": args.force
            })
        except Exception as e:
            print(f"Error connecting to controller: {e}")
            time.sleep(args.sleep_seconds)
            continue

        scryfall_id = claim_response.get("scryfall_id")
        if not scryfall_id:
            # Silent print to avoid spam
            time.sleep(args.sleep_seconds)
            continue

        card_name = claim_response.get("card_name")
        image_jobs = claim_response.get("image_jobs", [])
        remaining = claim_response.get("remaining", "?")
        print(f"({remaining} remaining) Downloading '{card_name}'...")

        files_to_upload = {}
        metadata_to_upload = {}

        success = True
        for job in image_jobs:
            size = job["size"]
            face_index = job["face_index"]
            url = job["url"]

            # Randomized delay between 100ms and 200ms
            delay = random.uniform(0.1, 0.2)
            time.sleep(delay)

            try:
                req = urllib.request.Request(url, headers={"User-Agent": args.user_agent})
                with urllib.request.urlopen(req, timeout=30) as res:
                    image_data = res.read()
                    file_key = f"{size}_{face_index}"
                    files_to_upload[file_key] = (f"{scryfall_id}_{size}_{face_index}.jpg", image_data)
                    metadata_to_upload[file_key] = {
                        "source_url": url,
                        "file_size": len(image_data)
                    }
            except Exception as ex:
                print(f"[Error] Failed to download {size} for {card_name}: {ex}")
                success = False
                break

        if not success:
            try:
                fail_url = f"{args.controller_url.rstrip('/')}/jobs/fail_image/{scryfall_id}"
                post_json(fail_url, {"worker_id": worker_id})
            except Exception as ex:
                print(f"[Error] Failed to report job failure: {ex}")
        else:
            try:
                # Check smoke limit again right before committing to avoid overshooting
                if args.smoke_test is not None:
                    if not counter.check_and_increment():
                        # Release the claim lock so another worker can take it
                        fail_url = f"{args.controller_url.rstrip('/')}/jobs/fail_image/{scryfall_id}"
                        post_json(fail_url, {"worker_id": worker_id})
                        break

                complete_url = f"{args.controller_url.rstrip('/')}/jobs/complete_image/{scryfall_id}"
                fields = {"metadata": json.dumps(metadata_to_upload)}
                boundary, multipart_body = encode_multipart_formdata(fields, files_to_upload)
                
                req = urllib.request.Request(
                    complete_url,
                    data=multipart_body,
                    headers={
                        "Content-Type": f"multipart/form-data; boundary={boundary.decode('utf-8')}"
                    },
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=60) as res:
                    res_body = json.loads(res.read().decode("utf-8"))
                    if res_body.get("status") == "completed":
                        saved_sizes = [s['size'] for s in res_body.get('saved', [])]
                        print(f"Saved: {card_name} -> {saved_sizes}")
                    else:
                        print(f"[Error] Controller response: {res_body}")
            except Exception as ex:
                print(f"[Error] Upload failed: {ex}")
                try:
                    fail_url = f"{args.controller_url.rstrip('/')}/jobs/fail_image/{scryfall_id}"
                    post_json(fail_url, {"worker_id": worker_id})
                except Exception:
                    pass

        time.sleep(args.sleep_seconds)
        
    print(f"Worker thread {thread_idx} exiting.")

def main():
    hostname = socket.gethostname()
    default_worker_id = f"image_worker_{hostname}_{os.getpid()}"
    
    parser = argparse.ArgumentParser(description="Multi-threaded Card Art Image Downloader Worker")
    parser.add_argument("--controller-url", default=os.environ.get("CONTROLLER_URL", "http://127.0.0.1:5000"), help="Controller API base URL")
    parser.add_argument("--worker-id", default=os.environ.get("WORKER_ID", default_worker_id), help="Unique ID for this worker")
    parser.add_argument("--user-agent", default="MTGAbyss/0.1 local-dev-downloader", help="User-Agent for Scryfall requests")
    parser.add_argument("--sleep-seconds", type=int, default=1, help="Sleep duration between jobs")
    parser.add_argument("--smoke-test", type=int, default=None, help="Stop after processing N cards total")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent worker threads to run")
    parser.add_argument("--force", action="store_true", help="Force claim cards even if images already downloaded")
    args = parser.parse_args()

    print("=== Starting Image Worker ===")
    print(f"Worker ID:      {args.worker_id}")
    print(f"Controller URL: {args.controller_url}")
    print(f"Worker Threads: {args.workers}")
    if args.smoke_test:
        print(f"Smoke Test Mode: will exit after {args.smoke_test} cards(s) total")
    print("=============================")

    counter = SafeCounter(args.smoke_test)

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(worker_thread_loop, args, i, counter) for i in range(args.workers)]
            for future in futures:
                try:
                    future.result()
                except KeyboardInterrupt:
                    print("Shutdown requested.")
                    break
    else:
        worker_thread_loop(args, 0, counter)

    print("Worker process complete. Exiting.")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    main()
