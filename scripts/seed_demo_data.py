"""
Life OS Root Script Runner: Seed Demo Data
Delegates execution to backend/scripts/seed_demo_data.py
"""
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_SCRIPT = ROOT_DIR / "backend" / "scripts" / "seed_demo_data.py"

if __name__ == "__main__":
    cmd = [sys.executable, str(BACKEND_SCRIPT)] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
