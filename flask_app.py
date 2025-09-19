import os
import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for


BASEDIR = Path(__file__).resolve().parent
RESOURCES_DIR = BASEDIR / "resources"
DATABASE_PATH = BASEDIR / "progress.db"


app = Flask(__name__)

def get_db() -> sqlite3.Connection:  # pragma: no cover – trivial helper
    """Return a SQLite connection bound to the current request context."""

    if "db" not in g:
        # Ensure the directory exists (should – we are in project root)
        g.db = sqlite3.connect(DATABASE_PATH)
        # Return rows as dictionaries
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: object):  # pragma: no cover – trivial teardown
    """Close the database at the end of request."""

    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create the table (if missing) and populate it from the txt files."""

    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            blueprint INTEGER DEFAULT 0,
            mastered INTEGER DEFAULT 0,
            PRIMARY KEY (category, name)
        )
        """
    )

    # Walk through every text file once at start-up and ensure each entry is present
    for txt_file in RESOURCES_DIR.glob("*.txt"):
        category = txt_file.stem  # filename without extension
        with txt_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                name = line.strip()
                if not name:
                    continue
                # Insert if missing
                db.execute(
                    "INSERT OR IGNORE INTO items (category, name) VALUES (?, ?)",
                    (category, name),
                )

    db.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    db = get_db()

    if request.method == "POST":
        # Distinguish between the *main* save form and the optional bulk-import
        # form (file upload). We look at the presence of the special hidden
        # field "_action" which is set only by the import form.

        if request.form.get("_action") == "bulk_import":
            file_storage = request.files.get("items_file")
            if file_storage and file_storage.filename:
                try:
                    # Read entire file, decode as UTF-8 and split lines
                    raw_text = file_storage.stream.read().decode("utf-8")
                    imported_items = {
                        line.strip() for line in raw_text.splitlines() if line.strip()
                    }

                    if imported_items:
                        # Update DB in bulk – set both blueprint *and* mastered
                        placeholders = ",".join(["?"] * len(imported_items))
                        # SQLite 'IN' clause cannot be empty so we ensured >0 above
                        db.execute(
                            f"UPDATE items SET blueprint = 1, mastered = 1 WHERE name IN ({placeholders})",
                            tuple(imported_items),
                        )
                        db.commit()
                except UnicodeDecodeError:
                    # Ignore invalid files silently – could add flash message later.
                    pass

            return redirect(url_for("index"))

        # Fetch all items from DB to know which ones exist
        cur = db.execute("SELECT category, name FROM items")
        all_items = cur.fetchall()

        for row in all_items:
            category = row["category"]
            name = row["name"]

            bp_key = f"bp|{category}|{name}"
            ma_key = f"ma|{category}|{name}"

            # Business rule: an item cannot be mastered without first owning its blueprint.
            # Therefore, if the user ticks “mastered” we implicitly also mark the blueprint
            # as collected even if they forgot to tick it.

            mastered = 1 if ma_key in request.form else 0
            blueprint = 1 if (bp_key in request.form or mastered) else 0

            db.execute(
                "UPDATE items SET blueprint = ?, mastered = ? WHERE category = ? AND name = ?",
                (blueprint, mastered, category, name),
            )

        db.commit()

        return redirect(url_for("index"))

    # GET request – build data structure for template
    cur = db.execute(
        "SELECT category, name, blueprint, mastered FROM items ORDER BY category, name"
    )
    items_by_category: dict[str, list[dict]] = {}
    for row in cur.fetchall():
        category = row["category"]
        items_by_category.setdefault(category, []).append(
            {
                "name": row["name"],
                "blueprint": bool(row["blueprint"]),
                "mastered": bool(row["mastered"]),
            }
        )

    return render_template("index.html", data=items_by_category)

def ensure_setup() -> None:
    """Initialise DB before the first request.

    We call this from `if __name__ == '__main__'` *and* from the `before_first_request`
    hook to support both `python flask_app.py` and `flask run`.
    """

    if not hasattr(app, "_initialised"):
        with app.app_context():
            init_db()
        app._initialised = True  # type: ignore[attr-defined]


# Initialise DB immediately on import so that any request will have it ready.
ensure_setup()


if __name__ == "__main__":
    # Use 0.0.0.0 so that Docker or remote hosts can access if needed.
    app.run(host="0.0.0.0", port=5000, debug=True)
