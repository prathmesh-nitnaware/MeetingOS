#!/usr/bin/env python3
"""
MeetingOS - Unified Service Runner (run_all.py)

Orchestrates and launches all MeetingOS services with a single command:
  1. Infrastructure (Docker Postgres + Redis, if Docker is available)
  2. Database migrations (Alembic)
  3. FastAPI Backend API (uvicorn)
  4. React Web Frontend (Vite)
  5. Celery Background Workers (if Redis is available)

Usage:
  python run_all.py
  uv run python run_all.py
  ./run_all.ps1       (PowerShell)
  run_all.bat         (Command Prompt)

Options:
  --no-docker    Skip starting Docker containers
  --no-worker    Skip starting Celery background workers
  --no-migrate   Skip running database migrations
  --no-web       Start backend only, skip web frontend
  --open         Open the web UI in default browser once ready
"""

import argparse
import atexit
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Configure utf-8 encoding safely on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Enable VT100 colors on Windows console
if sys.platform == "win32":
    os.system("")

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "apps" / "web"

running_processes: list[tuple[str, subprocess.Popen]] = []
shutdown_initiated = False


def log(tag: str, msg: str, color: str = CYAN) -> None:
    print(f"{color}{BOLD}[{tag}]{RESET} {msg}", flush=True)


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is currently open and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def stream_output(prefix: str, color: str, pipe) -> None:
    """Stream stdout/stderr of a child process with a colored prefix."""
    try:
        for line in iter(pipe.readline, ""):
            if shutdown_initiated:
                break
            stripped = line.rstrip()
            if stripped:
                print(f"{color}[{prefix}]{RESET} {stripped}", flush=True)
    except (ValueError, OSError):
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def kill_process_tree(proc: subprocess.Popen) -> None:
    """Force-terminate process and all its children across Windows/Linux."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def cleanup_all() -> None:
    global shutdown_initiated
    if shutdown_initiated:
        return
    shutdown_initiated = True
    print("\n")
    log("SHUTDOWN", "Stopping all MeetingOS services...", YELLOW)
    for name, proc in reversed(running_processes):
        log("SHUTDOWN", f"Stopping {name} (PID: {proc.pid})...", YELLOW)
        kill_process_tree(proc)
    log("SHUTDOWN", "All services stopped cleanly.", GREEN)


def signal_handler(_signum, _frame) -> None:
    cleanup_all()
    sys.exit(0)


atexit.register(cleanup_all)


def start_docker_infra() -> bool:
    """Attempt to start Docker Postgres and Redis containers."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        log("DOCKER", "Docker CLI not found in PATH. Skipping docker compose.", YELLOW)
        return False

    try:
        res = subprocess.run(
            [docker_bin, "compose", "up", "-d"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            log("DOCKER", "PostgreSQL and Redis containers are ready.", GREEN)
            return True
        else:
            log("DOCKER", f"Docker notice: {res.stderr.strip() or res.stdout.strip()}", YELLOW)
            return False
    except Exception as e:
        log("DOCKER", f"Could not start Docker containers: {e}", YELLOW)
        return False


def run_migrations() -> bool:
    """Run Alembic database migrations to ensure schema is at head."""
    uv_bin = shutil.which("uv")
    cmd = (
        [uv_bin, "run", "alembic", "upgrade", "head"]
        if uv_bin
        else [sys.executable, "-m", "alembic", "upgrade", "head"]
    )

    log("DB", "Verifying database migrations (alembic upgrade head)...", CYAN)
    try:
        res = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, check=False)
        if res.returncode == 0:
            log("DB", "Database schema is up to date.", GREEN)
            return True
        else:
            log("DB", f"Migration warning: {res.stderr.strip() or res.stdout.strip()}", YELLOW)
            return False
    except Exception as e:
        log("DB", f"Migration execution skipped: {e}", YELLOW)
        return False


def spawn_process(name: str, cmd: list[str], cwd: Path, color: str) -> subprocess.Popen:
    """Spawn a supervised background subprocess with streamed output."""
    log(name, f"Starting: {' '.join(cmd)}", color)
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    running_processes.append((name, proc))

    threading.Thread(target=stream_output, args=(name, color, proc.stdout), daemon=True).start()
    threading.Thread(target=stream_output, args=(name, color, proc.stderr), daemon=True).start()
    return proc


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="MeetingOS - Run all services")
    parser.add_argument("--no-docker", action="store_true", help="Skip docker compose up -d")
    parser.add_argument("--no-worker", action="store_true", help="Skip starting Celery workers")
    parser.add_argument("--no-migrate", action="store_true", help="Skip running Alembic migrations")
    parser.add_argument("--no-web", action="store_true", help="Skip starting Web Frontend")
    parser.add_argument("--open", action="store_true", help="Automatically open browser once ready")
    args = parser.parse_args()

    print(f"{CYAN}{BOLD}")
    print("==============================================================================")
    print("  MeetingOS - Unified Service Runner")
    print("==============================================================================")
    print(f"{RESET}")

    # 1. Start Docker Infrastructure (if enabled)
    if not args.no_docker:
        start_docker_infra()

    # 2. Database Migrations (if enabled)
    if not args.no_migrate:
        run_migrations()

    # Determine execution tools
    uv_bin = shutil.which("uv")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    npm_bin = shutil.which(npm_cmd) or shutil.which("npm")

    # 3. Start Backend API Server (FastAPI on port 8000)
    api_cmd = (
        [
            uv_bin,
            "run",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ]
        if uv_bin
        else [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ]
    )
    spawn_process("API", api_cmd, ROOT_DIR, BLUE)

    # 4. Start Celery Worker (if requested and Redis is open)
    if not args.no_worker:
        redis_available = check_port_open("localhost", 6379, timeout=0.5)
        if redis_available:
            celery_cmd = (
                [
                    uv_bin,
                    "run",
                    "celery",
                    "-A",
                    "workers.celery_app",
                    "worker",
                    "--loglevel=info",
                    "-Q",
                    "meetingos.asr,meetingos.nlp,meetingos.embedding,meetingos.sync",
                ]
                if uv_bin
                else [
                    sys.executable,
                    "-m",
                    "celery",
                    "-A",
                    "workers.celery_app",
                    "worker",
                    "--loglevel=info",
                    "-Q",
                    "meetingos.asr,meetingos.nlp,meetingos.embedding,meetingos.sync",
                ]
            )
            spawn_process("CELERY", celery_cmd, ROOT_DIR, MAGENTA)
        else:
            log("CELERY", "Redis is not active on localhost:6379. Celery worker skipped.", YELLOW)

    # 5. Start Frontend Web Server (Vite on port 5173)
    if not args.no_web:
        if WEB_DIR.exists() and npm_bin:
            spawn_process("WEB", [npm_bin, "run", "dev"], WEB_DIR, GREEN)
        else:
            log("WEB", "npm not found or apps/web directory missing. Web frontend skipped.", YELLOW)

    # Print summary banner (using standard ASCII markers for safe cross-codepage printing)
    print(f"\n{BOLD}MeetingOS services are running:{RESET}")
    print(f"  {GREEN}-> Web Frontend:  {BOLD}http://localhost:5173{RESET}")
    print(f"  {BLUE}-> API Server:    {BOLD}http://localhost:8000{RESET}")
    print(f"  {CYAN}-> Swagger Docs:  {BOLD}http://localhost:8000/api/v1/docs{RESET}")
    print(f"  {CYAN}-> Health Check:  {BOLD}http://localhost:8000/api/v1/health{RESET}")
    print(f"\n{YELLOW}Press Ctrl+C at any time to cleanly stop all services.{RESET}\n")

    if args.open:
        time.sleep(2)
        try:
            import webbrowser

            webbrowser.open("http://localhost:5173")
        except Exception:
            pass

    # Monitor running processes
    try:
        while True:
            time.sleep(1)
            for name, proc in running_processes:
                ret = proc.poll()
                if ret is not None and not shutdown_initiated:
                    log(name, f"Process exited unexpectedly with code {ret}", RED)
    except KeyboardInterrupt:
        cleanup_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
