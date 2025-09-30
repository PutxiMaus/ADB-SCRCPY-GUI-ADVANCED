import os, subprocess
from pathlib import Path

START = Path(__file__).resolve().parent

subprocess.run(
    ['python', '-m', 'project.main'], 
    cwd=START,
    check=True
)