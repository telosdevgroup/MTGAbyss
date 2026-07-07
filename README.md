# MTGAbyss

A static site compiler and AI generation pipeline for Magic: The Gathering card profiles.

## Lure Generation System (Controller + Worker)

We use a modularized, networked controller-worker architecture to generate Lures for commanders.

### 1. Start the Controller Server
Run the controller on the host machine. By default, it binds to `127.0.0.1:5000` (localhost).
```bash
python scripts/job_controller.py --host 127.0.0.1 --port 5000
```
To allow workers from other laptops on the local network (LAN) to connect, bind the controller to `0.0.0.0`:
```bash
python scripts/job_controller.py --host 0.0.0.0 --port 5000
```


### 2. Start a Local Worker
Run the worker on the host machine (Beast), pointing to the local controller and local Ollama instance:
```bash
python scripts/lure_worker.py --controller-url http://127.0.0.1:5000 --ollama-url http://localhost:11434 --model mistral-small3.2:24b
```

### 3. Start a Laptop Worker (Remote over LAN)
From a laptop, point the worker to Beast's LAN IP address (e.g., `192.168.1.100`):
```bash
python scripts/lure_worker.py --controller-url http://192.168.1.100:5000 --ollama-url http://localhost:11434 --model llama3.1:8b
```

### Smoke Test / Dry Run Option
To test the pipeline without calling the real Ollama API and generate mock responses for 3 cards:
```bash
python scripts/lure_worker.py --dry-run --smoke-test 3
```
