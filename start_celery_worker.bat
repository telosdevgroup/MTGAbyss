@echo off
echo ========================================================
echo MTGAbyss Celery Worker Bootloader
echo ========================================================
echo.
echo Configure Ollama Target:
echo [1] Use local Ollama (http://localhost:11434)
echo [2] Use Beast Ollama (http://192.168.1.213:11434)
echo.

set /p target="Enter Ollama target (1-2, default 1): "
set OLLAMA_URL=http://127.0.0.1:11434

if "%target%"=="2" (
    set OLLAMA_URL=http://192.168.1.213:11434
    echo Configured to use Beast Ollama.
) else (
    echo Configured to use Local Ollama.
)
echo.

echo Select the worker type to start:
echo [1] GPU/Embedding Worker (queue: gpu-tasks, pool: solo)
echo [2] AI Lure/Mistral Worker (queue: ai-lures, pool: solo)
echo [3] Builder/Pi Worker (queue: builder-tasks, pool: eventlet, concurrency 2)
echo.

set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    echo Starting GPU/Embedding Worker...
    python -m celery -A celery_app worker -Q gpu-tasks -P solo --loglevel=info
) else if "%choice%"=="2" (
    echo Starting AI Lure/Mistral Worker...
    python -m celery -A celery_app worker -Q ai-lures -P solo --loglevel=info
) else if "%choice%"=="3" (
    echo Starting Builder/Pi Worker...
    python -m celery -A celery_app worker -Q builder-tasks -P eventlet -c 2 --loglevel=info
) else (
    echo Invalid choice. Exiting.
)
pause
