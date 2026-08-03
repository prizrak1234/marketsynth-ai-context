"""Print knowledge import statistics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOTS = ["knowledge", "skills", "workflows", "standards", "knowledge_import"]


def main() -> None:
    grand_total = 0
    totals = {}
    ext_totals: Counter[str] = Counter()
    for root_name in ROOTS:
        root = REPO / root_name
        if not root.exists():
            continue
        files = [f for f in root.rglob("*") if f.is_file()]
        totals[root_name] = len(files)
        grand_total += len(files)
        for f in files:
            ext_totals[f.suffix.lower() or "(no ext)"] += 1
        print(f"== {root_name}: {len(files)} ==")
        for ext, count in Counter(f.suffix.lower() or "(no ext)" for f in files).most_common(12):
            print(f"  {ext}: {count}")

    print(f"\nGRAND TOTAL (including staging): {grand_total}")
    print("\nCombined imported (excl staging):", sum(totals.get(k, 0) for k in ROOTS if k != "knowledge_import"))
    print("\nTop extensions overall:")
    for ext, count in ext_totals.most_common(15):
        print(f"  {ext}: {count}")


if __name__ == "__main__":
    main()
