import os
import subprocess
import sys
import venv
import shutil

# -----------------------
# CONFIGURABLE VARIABLES
# -----------------------
VENV_DIR = ".venv"
REQUIREMENTS_FILE = "requirements.txt"
ENTRY_FILE = "app.py"

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def run_command(command, shell=False):
    """Run a system command and show output live."""
    print(f"[CMD] {command}")
    result = subprocess.run(command, shell=shell)
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {command}")
        sys.exit(result.returncode)

def python_exists():
    """Check if Python is available."""
    try:
        subprocess.run([sys.executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def create_venv():
    """Create a virtual environment."""
    print(f"[INFO] Creating virtual environment in '{VENV_DIR}'...")
    venv.create(VENV_DIR, with_pip=True)

def install_requirements():
    """Install dependencies."""
    if os.path.exists(REQUIREMENTS_FILE):
        print(f"[INFO] Installing packages from {REQUIREMENTS_FILE}...")
        run_command([venv_python(), "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
    else:
        print("[WARN] No requirements.txt found — skipping.")

def venv_python():
    """Return the path to the venv's Python executable."""
    if os.name == "nt":  # Windows
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:  # Mac/Linux
        return os.path.join(VENV_DIR, "bin", "python")

def main():
    # 1️⃣ Check if Python exists
    if not python_exists():
        print("[ERROR] Python is not installed. Please install it first.")
        sys.exit(1)

    # 2️⃣ Create venv if missing
    if not os.path.exists(VENV_DIR):
        create_venv()
        install_requirements()
    else:
        print(f"[INFO] Using existing virtual environment '{VENV_DIR}'...")

    # 3️⃣ Run the app
    print(f"[INFO] Launching {ENTRY_FILE}...")
    run_command([venv_python(), ENTRY_FILE])

if __name__ == "__main__":
    main()
