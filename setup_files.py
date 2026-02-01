"""
Setup script to create all missing ESASS prototype files.
"""

from pathlib import Path

# Create all __init__.py files
init_files = [
    "esass_prototype/__init__.py",
    "esass_prototype/storage/__init__.py",
]

for init_file in init_files:
    path = Path(init_file)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('"""Package initialization"""\n')
        print(f"Created: {init_file}")
    else:
        print(f"Exists: {init_file}")

# Check for models.py and storage modules
check_files = [
    "esass_prototype/models.py",
    "esass_prototype/storage/log_store.py",
    "esass_prototype/storage/pattern_store.py",
    "esass_prototype/storage/skill_store.py",
]

print("\nChecking critical files:")
for file in check_files:
    exists = Path(file).exists()
    print(f"{file}: {'✓' if exists else '✗ MISSING'}")

print("\nSetup complete!")
