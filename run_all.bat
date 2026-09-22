@echo off
REM ==============================================================================
REM MeetingOS - Unified Startup Script for Windows
REM Launches Docker infra, migrations, FastAPI backend, React web, and Celery.
REM ==============================================================================

where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    uv run python run_all.py %*
) else (
    python run_all.py %*
)
