# RigidHitch — a second, separate catalog

RigidHitch is a towing/trailer-hitch parts retailer (receiver hitches, tow bars,
trailer jacks, fifth-wheel hitches, RV parts, electrical) — a completely
different product domain from PartPilot's original 56-SKU car-parts catalog.
This doc covers what's specific to RigidHitch: its own database, its own data
pipeline, and the architectural differences from the original app.

**Scale:** 10,813 SKUs, 27,297 photos, 35 categories.

---

## 1. How this differs from the original PartPilot app

| | Original PartPilot | RigidHitch |
|---|---|---|
| Database | Supabase (Postgres + pooler, IPv6 handling) | **Plain local Postgres** - no Supabase involved |
| Category classifier (Brain 1) | Yes - EfficientNet trained on 10 categories | **None** - decided against training one (see below) |
| Product relationships (replacement/alternative/accessory SKUs) | Populated | **0% populated** - not in RigidHitch's source data |
| Fitment | `{make, model, year}` vehicle strings | Free-text hitch-class tags (`"2 Inch Receivers"`, `"Fisher Compatible"`) stored in `attributes.fitment` |
| Catalog size | 56 SKUs | 10,813 SKUs |

**Why no Brain 1 for RigidHitch:** category classification only works well when
categories are visually distinct and there's enough clean labeled data to
train on. RigidHitch has deep category → subcategory nesting (35 leaf
categories) and no clean per-category training set, so a classifier here
would need a lot of work for uncertain payoff. Instead, an uploaded photo is
matched directly against the whole catalog by visual similarity - category
becomes a **result label** (read off whichever SKU wins the match), not
something predicted from the photo. See the "Search architecture" phase in
the project roadmap for what that means for accuracy trade-offs.

---

## 2. The database

A separate database (`PartPilot_RigidHitch`), separate from PartPilot's own
`DATABASE_URL` - kept apart deliberately since this is a different client's
data, not a variation on the existing catalog. Uses **plain Postgres**
(currently a local instance), not Supabase.

Schema is managed by a **second, parallel Alembic environment** -
`alembic_rigidhitch/` - independent of the main app's `alembic/`:

```
partpilot/
  alembic_rigidhitch.ini          # points Alembic at alembic_rigidhitch/
  alembic_rigidhitch/
    env.py                        # reads RIGIDHITCH_DATABASE_URL, never touches the main app's settings
    schema.py                     # single source of truth for the products table columns
    versions/
      0001_create_products_table.py
```

### One-time setup on any machine

```bash
# 1. Point at your own Postgres database for RigidHitch
#    (add to partpilot/.env - loaded automatically via python-dotenv)
RIGIDHITCH_DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@localhost:5432/PartPilot_RigidHitch

# 2. Create the database itself (Alembic only creates the table, not the database)
createdb PartPilot_RigidHitch

# 3. Create the table structure (safe to re-run - does nothing if already applied)
cd partpilot
alembic -c alembic_rigidhitch.ini upgrade head
```

✅ Expected: `Running upgrade  -> 0001, create products table (RigidHitch)`

---

## 3. The data pipeline

Three scripts, run in this order, against a copy of RigidHitch's
`rigidhitch_dataset` folder (shared separately - not in the repo, same
git-ignore convention as the original catalog's images):

### Step 1 - Clean the catalog CSV

A full audit found the raw `catalog.csv` mostly clean (no duplicate SKUs,
no missing required fields, category values not mixed with brand names -
an earlier naive check using `cut -d','` wrongly suggested otherwise; a
proper CSV-quoting-aware parse showed the category column is fine). Two real
issues found and fixed:

- 24 rows had raw HTML/entities left in `description` from a scrape
- 586 rows (5.4%) had a blank `brand`

```bash
python scripts/clean_rigidhitch_catalog.py --dataset-dir "path/to/rigidhitch_dataset"
```
Writes `catalog.clean.csv` alongside the original - **never overwrites the
source file**.

⚠️ One bug was caught and fixed during this work: the first version of the
HTML-stripping regex was too greedy and deleted a genuine spec value (`Low
(<120v) / High (>132v) voltage` was misread as one HTML tag). The regex now
requires a letter right after `<` to count as a real tag. Verified afterward
with a full before/after diff across all 10,813 rows - no other real content
loss found.

### Step 2 - Normalize images (Vinith)

An evidence-based scan (corner-pixel background-whiteness check, not a
guess) found **4,203 of 27,297 photos (19.9%) across 2,153 SKUs** have
inconsistent backgrounds - scattered across multiple brands, not just one.

```bash
python scripts/normalize_rigidhitch_images.py
```
Flagged images go through `rembg` and get re-composited onto white; every
image (flagged or not) gets squashed to a consistent square size, matching
the convention the existing Brain 1 checkpoint was trained on. Output goes to
a separate `images_clean/` tree - originals untouched.

**Status: not yet run against the full corpus as of this doc.**

### Step 3 - Import into the database

```bash
python scripts/import_rigidhitch_catalog.py \
    --database-url "$RIGIDHITCH_DATABASE_URL" \
    --dataset-dir "path/to/rigidhitch_dataset" \
    --catalog-file catalog.clean.csv
```
Safe to re-run - upserts on `sku`. `replacement_sku` / `alternative_sku` /
`accessory_skus` / `compatible_vehicles` are deliberately **not** carried
into the table as-is (see the differences table above); fitment tags land in
`attributes.fitment` instead.

✅ Verified in the live database after import: 10,813 rows, 586 with
`brand = 'Unknown'`, matching the cleaning script's own counts exactly.

---

## 4. Known data limitations (tell the client, don't let these surface as surprises)

- **No replacement/alternative/accessory relationships exist at all** - 0%
  populated in the source data. The recommendation-engine feature (a core
  part of the original PartPilot pitch) currently has nothing to work with
  for RigidHitch.
- **43% of SKUs (4,668) have only 1 photo.** The multi-photo averaging
  technique that measurably helped the original catalog's accuracy gets no
  benefit on these.
- **Fitment coverage is ~19%** (2,039 of 10,813 rows) - most SKUs have no
  fitment/compatibility data at all.
- **Brand is unknown for 5.4% of SKUs** (filled with the literal string
  `"Unknown"`, not blank, so it doesn't look like a bug in the UI).

---

## 5. Photo count per SKU (measured, from the live database)

| Photos | SKUs |
|---:|---:|
| 1 | 4,668 |
| 2 | 1,617 |
| 3 | 1,962 |
| 4 | 808 |
| 5 | 661 |
| 6 | 891 |
| 7 | 90 |
| 8 | 66 |
| 9 | 35 |
| 10 | 12 |
| 11 | 3 |

---

## 6. What's left (roadmap)

1. ✅ Catalog cleaned, imported into `PartPilot_RigidHitch`
2. ⬜ Run `normalize_rigidhitch_images.py` against the full 27,297-photo corpus
3. ⬜ Build DINOv2 embeddings + a FAISS index across the catalog (flat index
   recommended as the starting point, given there's no category classifier
   to route by - see Section 1)
4. ⬜ Calibrate refusal thresholds on RigidHitch's own correct-vs-impostor
   score distribution - the original 0.48/0.86 thresholds don't transfer
5. ⬜ Decide how to handle recommendations given the 0%-populated
   relationship columns
6. ⬜ Frontend: drop the "category detected" step, handle catalog-browsing
   UI at 10,813 SKUs instead of 56, RigidHitch branding
7. ⬜ Move `PartPilot_RigidHitch` off a local laptop onto a real shared host
   before anyone besides the person who set it up can use it
