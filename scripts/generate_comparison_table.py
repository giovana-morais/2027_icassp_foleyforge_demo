#!/usr/bin/env python3
"""Regenerate the Model Comparison table in index.html from manifest.csv.

Reads assets/listening-test-v4/manifest.csv plus the per-example audio
folders, and rewrites the <table class="comparison-table"> markup found
between the GENERATED:comparison-table markers in index.html. Nothing
outside those markers is touched.

Usage:
    python3 scripts/generate_comparison_table.py [--check]

    --check   don't write anything; exit 1 if index.html would change
              (useful as a CI/pre-commit guard against a stale table)

Run this any time examples are added/removed/renamed under
assets/listening-test-v4/, then commit the resulting index.html diff.
"""

import argparse
import csv
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTENING_TEST_DIR = os.path.join(ROOT, "assets", "audio", "model_comparison")
MANIFEST_PATH = os.path.join(LISTENING_TEST_DIR, "manifest-clean.csv")
INDEX_HTML_PATH = os.path.join(ROOT, "index.html")

MARKER_START = "<!-- GENERATED:comparison-table START (do not hand-edit; run scripts/generate_comparison_table.py) -->"
MARKER_END = "<!-- GENERATED:comparison-table END -->"

# (column label, filename in each example folder). Edit this to add/rename/
# reorder columns; everything else derives from it automatically.
COLUMNS = [
    ("Input", "input.wav"),
    ("SAO", "sao_instruct.wav"),
    # ("SDEdit", "sdedit.wav"),
    ("EchoEdit+", "echoedit_plus.wav"),
    ("SDEdit+Sketch", "sdedit_rms.wav"),
    ("FoleyForge (ours)", "our_tf_nit09_rg05.wav"),
]
OURS_LABEL = "FoleyForge (ours)"


def load_manifest():
    with open(MANIFEST_PATH, newline="") as f:
        return list(csv.DictReader(f))


def example_folder(row):
    # Folder naming convention: "{rank:02d}_{example_id}"
    return f"{int(row['rank']):02d}_{row['example_id']}"


def build_table(rows):
    missing = []
    out = []
    A = out.append

    A('            <table class="comparison-table">')
    A("                <thead>")
    A("                    <tr>")
    for label, _ in COLUMNS:
        cls = ' class="ours"' if label == OURS_LABEL else ""
        A(f"                        <th{cls}>{html.escape(label)}</th>")
    A("                    </tr>")
    A("                </thead>")
    A("                <tbody>")

    for row in rows:
        folder = example_folder(row)
        folder_path = os.path.join(LISTENING_TEST_DIR, folder)
        if not os.path.isdir(folder_path):
            missing.append(folder_path)
            continue

        instruction = html.escape(row["instruction"].strip())
        A('                    <tr class="instruction-row">')
        A(
            f'                        <th colspan="{len(COLUMNS)}" scope="colgroup">'
            f'Instruction: {instruction}</th>'
        )
        A("                    </tr>")
        A('                    <tr class="audio-row">')
        for label, fname in COLUMNS:
            rel_path = f"assets/listening-test-v4/{folder}/{fname}"
            if not os.path.exists(os.path.join(ROOT, rel_path)):
                missing.append(rel_path)
            cls = ' class="ours"' if label == OURS_LABEL else ""
            A(
                f'                        <td{cls} data-label="{html.escape(label)}">'
                f'<audio controls preload="none" src="{rel_path}"></audio></td>'
            )
        A("                    </tr>")

    A("                </tbody>")
    A("            </table>")
    return "\n".join(out), missing


def splice_into_index_html(table_markup):
    with open(INDEX_HTML_PATH) as f:
        src = f.read()

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), re.DOTALL
    )
    if not pattern.search(src):
        sys.exit(
            "Could not find comparison-table markers in index.html. "
            f"Expected to see:\n{MARKER_START}\n...\n{MARKER_END}"
        )

    replacement = f"{MARKER_START}\n{table_markup}\n{MARKER_END}"
    return pattern.sub(replacement, src, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if index.html is not already up to date, without writing",
    )
    args = parser.parse_args()

    rows = load_manifest()
    table_markup, missing = build_table(rows)
    new_src = splice_into_index_html(table_markup)

    if missing:
        print("Missing audio files/folders referenced by manifest.csv:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    with open(INDEX_HTML_PATH) as f:
        old_src = f.read()

    if new_src == old_src:
        print(f"index.html already up to date ({len(rows)} examples).")
        sys.exit(1 if missing else 0)

    if args.check:
        print("index.html is stale; run without --check to regenerate.", file=sys.stderr)
        sys.exit(1)

    with open(INDEX_HTML_PATH, "w") as f:
        f.write(new_src)
    print(f"Wrote comparison table for {len(rows)} examples to index.html.")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
