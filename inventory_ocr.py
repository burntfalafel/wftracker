"""OCR Inventory Images and create list of detected Warframe items.

This standalone helper script scans every image inside the "inventory/" folder
located **next to** this file, performs Optical Character Recognition (OCR)
using *easyocr* and writes the names it was able to recognise to the text file
``detected_items.txt`` (one item per line).

Only names that actually exist in the tracker database are kept – this greatly
reduces false-positives and avoids polluting the list with unrelated words
that the OCR engine might have picked up (e.g. UI labels that are not item
names).

The script is intentionally simple and does **not** attempt to be super smart
about image pre-processing; feel free to tweak it for your own capture method
if you need better accuracy (e.g. by adding thresholding, cropping, etc.).

Usage:
    python3 inventory_ocr.py

Requirements:
    pip install easyocr

The very first call can take a bit because *easyocr* downloads the detection
models on demand.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
from collections import defaultdict

try:
    import easyocr  # type: ignore
except ImportError as exc:  # pragma: no cover – helpful runtime message
    print(
        "This script requires the 'easyocr' package. Install it with\n"
        "    pip install easyocr\n",
        file=sys.stderr,
    )
    raise


BASE_DIR = pathlib.Path(__file__).resolve().parent
INVENTORY_DIR = BASE_DIR / "inventory"
OUTPUT_FILE = BASE_DIR / "detected_items.txt"
DATABASE_PATH = BASE_DIR / "progress.db"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def load_known_items(db_path: pathlib.Path) -> set[str]:
    """Return the set of *all* item names present in the tracker database."""

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT name FROM items")
    names = {row[0] for row in cur.fetchall()}
    conn.close()
    return names


def ocr_images(reader: "easyocr.Reader", images_dir: pathlib.Path) -> list[str]:
    """Perform OCR on every image inside *images_dir* and return list of words."""

    recognised: list[str] = []

    for img_path in sorted(images_dir.iterdir()):
        if img_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
            continue  # skip non-images

        print(f"[*] Processing {img_path.name} …")
        results = reader.readtext(str(img_path), detail=0)
        # `results` is simply a list[str] when detail=0
        recognised.extend(results)

    return recognised


def main(argv: list[str] | None = None) -> None:  # noqa: D401 – simple CLI
    # Load set of valid names once to validate OCR output
    print("[*] Loading known items from database …")
    known_items = load_known_items(DATABASE_PATH)

    if not INVENTORY_DIR.is_dir():
        print(f"Error: expected folder {INVENTORY_DIR} with images", file=sys.stderr)
        sys.exit(1)

    print("[*] Initialising OCR engine (language='en') … this can take a while the first time")
    reader = easyocr.Reader(["en"], gpu=False)  # use CPU; GPU gives no benefit in small batches

    raw_texts = ocr_images(reader, INVENTORY_DIR)

    # Count occurrences and keep those that match known items (case-insensitive)
    counter: defaultdict[str, int] = defaultdict(int)
    lower_to_actual = {name.lower(): name for name in known_items}

    for txt in raw_texts:
        key = txt.strip().replace(" ", "_")  # normalise like resources lists
        name = lower_to_actual.get(key.lower())
        if name:
            counter[name] += 1

    if not counter:
        print("[!] No known items detected – please check the images / OCR accuracy.")

    # Sort by name, ignore duplicates
    detected_sorted = sorted(counter)

    OUTPUT_FILE.write_text("\n".join(detected_sorted) + "\n", encoding="utf-8")
    print(f"[*] Wrote {len(detected_sorted)} unique items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

