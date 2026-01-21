import subprocess
import sys
from pathlib import Path

START = Path(__file__).resolve().parent

try:
    subprocess.run(
        [sys.executable, "-m", "project.main"],
        cwd=START,
        check=True,
    )
except subprocess.CalledProcessError as exc:
    print(f"Error iniciando la aplicación (código {exc.returncode}).")
