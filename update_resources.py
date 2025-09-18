"""Update Warframe items lists.

This script downloads the official community maintained data set that contains
all Warframe equipment (https://github.com/WFCD/warframe-items) and updates the
plain-text lists in the resources/ directory (warframes.txt, primaries.txt,
secondaries.txt and melees.txt).
"""

from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

# Remote location of the canonical data set (single big JSON file)
DATASET_URL = (
    "https://raw.githubusercontent.com/WFCD/warframe-items/master/data/json/All.json"
)

# Mapping from the `category` field in the data set to the text file that has
# to be produced in resources/.
CATEGORY_TO_FILE = {
    "Warframes": "warframes.txt",
    "Primary": "primaries.txt",
    "Secondary": "secondaries.txt",
    "Melee": "melees.txt",
}



def normalise_name(name: str) -> str:
    """Convert an in-game item name to the representation used in the text files.

    Currently we only replace whitespace with underscores so that the names can
    be used directly in URLs such as
    https://warframe.fandom.com/wiki/<NAME> which is what the main program does
    when opening the browser.
    """

    return name.replace(" ", "_")


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def download_dataset(url: str = DATASET_URL):
    """Download and return the JSON data from *url* as Python objects."""

    with urllib.request.urlopen(url) as response:
        if response.status != 200:
            raise RuntimeError(f"Failed to download data set – HTTP {response.status}")
        return json.load(response)


def build_lists(data):
    """Return a mapping *category* -> *sorted list of names* (normalised)."""

    lists: dict[str, list[str]] = {cat: [] for cat in CATEGORY_TO_FILE}

    for item in data:
        category = item.get("category")
        if category not in CATEGORY_TO_FILE:
            continue  # not one of the categories we care about

        name = item.get("name", "").strip()
        if not name:
            continue

        lists[category].append(normalise_name(name))

    # Remove duplicates and sort
    for cat, names in lists.items():
        unique_sorted = sorted(set(names), key=str.lower)
        lists[cat] = unique_sorted

    return lists


def write_lists(lists: dict[str, list[str]]):
    """Write the *lists* mapping to the appropriate files inside resources/."""

    resources_dir = pathlib.Path(__file__).parent / "resources"
    if not resources_dir.is_dir():
        resources_dir.mkdir(parents=True, exist_ok=True)

    for category, names in lists.items():
        file_path = resources_dir / CATEGORY_TO_FILE[category]
        # Write with Unix line endings and a trailing newline (like the current files)
        file_path.write_text("\n".join(names) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None):
    try:
        data = download_dataset()
    except Exception as exc:
        print(f"Error while downloading dataset: {exc}", file=sys.stderr)
        sys.exit(1)

    lists = build_lists(data)
    write_lists(lists)

    print("resources/ directory updated successfully.")


if __name__ == "__main__":
    main()

