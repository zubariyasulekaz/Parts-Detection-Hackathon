"""Derive structured visual attributes from the catalog text already on record.

The descriptions were written to describe how each part *looks*, so the facts
that separate visually-similar SKUs are already in prose - they just are not
queryable. This lifts them into a structured bag.

Two traps this handles:

  substrings   Naive counting reports "red" 21 times because of "enginee(red)"
               and "gold" because of the brand "Duralast Gold". Everything is
               word-boundary matched.

  negation     "wheel hub assembly *without* an ABS sensor" and "*No* integrated
               reservoir" would otherwise record the exact opposite of the truth.
               A match is rejected if negated shortly before it.

Writes the derived bag back into catalog.csv's `attributes` column so the CSV
stays the single source of truth; `import_catalog_to_db.py` then carries it into
the products table.

Run:
    python scripts/extract_product_attributes.py --dry-run   # report only
    python scripts/extract_product_attributes.py
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.paths import CATALOG_CSV_PATH  # noqa: E402

CATALOG = CATALOG_CSV_PATH

NEGATION = re.compile(r"\b(?:no|not|without|lacks|lacking|absent|omits)\b[^.]{0,40}$", re.IGNORECASE)


def found(pattern: str, text: str) -> bool:
    """True if `pattern` matches somewhere it is not negated."""
    for match in re.finditer(pattern, text):
        if not NEGATION.search(text[: match.start()]):
            return True
    return False


def negated(pattern: str, text: str) -> bool:
    """True if every occurrence of `pattern` is negated (and there is one)."""
    matches = list(re.finditer(pattern, text))
    return bool(matches) and all(NEGATION.search(text[: m.start()]) for m in matches)


#: Applied to every product, first match wins.
GLOBAL_SINGLE = {
    "position": [("front", r"\bfront\b"), ("rear", r"\brear\b")],
    "sold_as": [("pair", r"\bpair\b"), ("set", r"\bset\b"), ("single", r"\bsingle\b")],
    "material": [
        ("polyurethane", r"\bpolyurethane\b"),
        ("cast-iron", r"\bcast[- ]iron\b"),
        ("stainless-steel", r"\bstainless\b"),
        ("aluminium", r"\baluminium\b|\baluminum\b"),
        ("rubber", r"\brubber\b"),
        ("steel", r"\bsteel\b"),
    ],
}

#: category -> attribute -> [(value, pattern)], first match wins.
BY_CATEGORY = {
    "Oil Filter": {
        "filter_style": [("spin-on", r"\bspin-on\b"), ("cartridge", r"\bcartridge\b")],
    },
    "Air Filter": {
        "filter_shape": [
            ("cabin", r"\bcabin\b"),
            ("conical", r"\bcone\b|\bconical\b"),
            ("panel", r"\bpanel\b|\brectangular\b"),
            ("round", r"\bround\b"),
            ("oval", r"\boval\b"),
        ],
    },
    "Brake Pads": {
        "friction_material": [
            ("ceramic", r"\bceramic\b"),
            ("semi-metallic", r"\bsemi-metallic\b"),
            ("organic", r"\borganic\b"),
        ],
    },
    "Exhaust Manifold": {
        "manifold_style": [
            ("long-tube-header", r"\blong[- ]tube\b"),
            ("shorty-header", r"\bshorty\b"),
            ("header", r"\bheader\b"),
            ("oem-manifold", r"\bmanifold\b"),
        ],
    },
    "Fuel Injector": {
        "injector_type": [
            ("common-rail", r"\bcommon[- ]rail\b"),
            ("direct-injection", r"\bdirect injection\b|\bgdi\b"),
            ("dual-fuel", r"\blpg\b|\bcng\b|\bdual-fuel\b"),
            ("unit-injector", r"\bunit injector\b|\buis\b"),
            ("port", r"\bport\b"),
        ],
    },
    "Power Steering Pump": {
        "pump_style": [
            ("electro-hydraulic", r"\belectro-hydraulic\b|\belectric motor\b"),
            ("hydraulic", r"\bhydraulic\b"),
        ],
    },
    "Shock Absorber": {
        "damper_style": [
            ("air-strut", r"\bair[- ]ride\b|\bair spring\b|\bair suspension\b"),
            ("remote-reservoir", r"\bremote[- ]reservoir\b|\bpiggyback\b"),
            ("strut-assembly", r"\bstrut\b"),
            ("shock-absorber", r"\bshock absorber\b"),
        ],
    },
    "Throttle Body": {
        "throttle_control": [
            ("cable-operated", r"\bcable[- ]operated\b|\bthrottle cable\b"),
            ("electronic", r"\belectronic\b|\bdrive[- ]by[- ]wire\b|\bmotor\b"),
        ],
    },
}

#: attribute -> (pattern, category or None). Recorded as yes/no, negation-aware,
#: so "without an ABS sensor" becomes "no" rather than being dropped.
PRESENCE = {
    "abs_sensor": (r"\babs\b", "Wheel Hub Assembly"),
    "integrated_reservoir": (r"\breservoir\b", "Power Steering Pump"),
    "catalytic_converter": (r"\bcatalytic converter\b", "Exhaust Manifold"),
    "wear_sensor": (r"\bwear[- ]sensor\b|\bwear indicator\b", "Brake Pads"),
    "pulley_fitted": (r"\bpulley\b", "Power Steering Pump"),
}

COLOURS = [
    ("black", r"\bblack\b"), ("blue", r"\bblue\b"), ("silver", r"\bsilver\b"),
    ("chrome", r"\bchrome(?:-plated)?\b"), ("red", r"\bred\b"), ("yellow", r"\byellow\b"),
    ("tan", r"\btan\b"), ("grey", r"\bgrey\b|\bgray\b|\bgraphite\b"), ("green", r"\bgreen\b"),
    ("bronze", r"\bbronze\b"), ("gold", r"\bgold(?:en)?\b"),
]


def extract(name: str, description: str, category: str) -> dict:
    # Brand names leak attribute words ("Duralast Gold", "Akebono ProACT").
    text = re.sub(r"duralast gold|duralast elite", " ", f"{name} {description}".lower())

    result: dict = {}
    for attribute, rules in {**GLOBAL_SINGLE, **BY_CATEGORY.get(category, {})}.items():
        for value, pattern in rules:
            if found(pattern, text):
                result[attribute] = value
                break

    for attribute, (pattern, only_category) in PRESENCE.items():
        if only_category and category != only_category:
            continue
        if negated(pattern, text):
            result[attribute] = "no"
        elif found(pattern, text):
            result[attribute] = "yes"

    # Primary colour only. These descriptions lead with the body colour and
    # trail off into O-rings and connectors, so the earliest mention is the one
    # a person would give if asked "what colour is it?".
    positions = [(m.start(), value) for value, pattern in COLOURS if (m := re.search(pattern, text))]
    if positions:
        result["primary_colour"] = min(positions)[1]

    lugs = re.search(r"\b(\d)-lug\b", text)
    if lugs and category == "Wheel Hub Assembly":
        result["lug_count"] = lugs.group(1)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report without writing catalog.csv.")
    args = parser.parse_args()

    with CATALOG.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    out, by_category = {}, {}
    for row in rows:
        attributes = extract(row["product_name"], row["description"], row["category"])
        out[row["sku"]] = attributes
        row["attributes"] = json.dumps(attributes, sort_keys=True)
        by_category.setdefault(row["category"], []).append((row["sku"], row["product_name"], attributes))

    for category, entries in sorted(by_category.items()):
        print(f"\n=== {category} ===")
        for sku, name, attributes in entries:
            print(f"  {sku:10} {name[:48]:48} {json.dumps(attributes)}")

    print("\n\n=== does each category get a usable splitter? ===")
    for category, entries in sorted(by_category.items()):
        if len(entries) < 2:
            continue
        best = []
        for key in sorted({k for _, _, a in entries for k in a}):
            values = [a.get(key) for _, _, a in entries]
            distinct = len({str(v) for v in values})
            complete = all(v is not None for v in values)
            if distinct > 1 and complete:
                worst = max(values.count(v) for v in values)
                best.append((worst, key, distinct))
        best.sort()
        label = (
            f"best splitter: {best[0][1]} ({best[0][2]} values, worst case {best[0][0]}/{len(entries)})"
            if best
            else "NO complete splitting attribute"
        )
        print(f"  {category:22} {len(entries)} products - {label}")

    empty = [sku for sku, attributes in out.items() if not attributes]
    if empty:
        print(f"\n  [warn] no attributes derived for: {', '.join(empty)}")

    if args.dry_run:
        print("\nDry run - catalog.csv not written.")
        return

    if "attributes" not in fieldnames:
        fieldnames.append("attributes")
    with CATALOG.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote `attributes` for {len(out)} SKUs into {CATALOG.name}")


# Guarded so `extract` can be imported and reused (the frontend mock catalog is
# populated from it) without rewriting catalog.csv as a side effect.
if __name__ == "__main__":
    main()
