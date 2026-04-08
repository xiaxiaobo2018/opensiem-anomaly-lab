# /// script
# dependencies = []
# ///

import zipfile
from pathlib import Path

# --- CONFIG ---
# This is where your file is currently sitting
SOURCE_ZIP = Path("data/anomod/AnoMod.zip") 
# This is where the lab expects the data to live
EXTRACT_TO = Path("data/raw/anomod") 

def main():
    if not SOURCE_ZIP.exists():
        print(f"❌ Error: Could not find {SOURCE_ZIP}")
        return

    print(f"📦 Extracting {SOURCE_ZIP.name} to {EXTRACT_TO}...")
    EXTRACT_TO.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(SOURCE_ZIP, 'r') as zip_ref:
        # We extract it so your code can read the individual CSV/Log files
        zip_ref.extractall(EXTRACT_TO)
    
    print("✨ Extraction complete!")
    print(f"📂 Your data is now ready in: {EXTRACT_TO}")

if __name__ == "__main__":
    main()