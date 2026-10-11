"""Only create a dedicated lab directory beside this script."""
from pathlib import Path

folder = Path(__file__).resolve().parent / "lab-share"
folder.mkdir(exist_ok=True)
sample = folder / "lab-only-note.txt"
if not sample.exists():
    sample.write_text("lab-only-readable-input\n", encoding="utf-8")
print("lab-share ready")
