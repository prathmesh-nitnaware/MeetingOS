import asyncio
import sys

from evaluation.phase10 import run_phase10

if __name__ == "__main__":
    sys.exit(asyncio.run(run_phase10()))
