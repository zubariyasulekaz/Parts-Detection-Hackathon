# Running PartPilot

Setup for a teammate getting the app working on their own machine.

The trained models and the built search indexes are committed, and the product
catalog lives in a shared database, so there is nothing to train or rebuild -
install, point at the database, run.

---

## What you need from the team

Two things are not in the repo:

| | Why | Needed to run? |
|---|---|---|
| `DATABASE_URL` | contains a password, so it stays out of git | **yes** |
| `partpilot_images_v3.zip` | ~50 MB of catalog photos, git-ignored | only for rebuilding indexes |

Ask for the `DATABASE_URL`. You can skip the images unless you intend to
rebuild the FAISS indexes - predictions embed the photo the user uploads, not
the catalog photos.

---

## 1. Clone

```bash
git clone https://github.com/zubariyasulekaz/Parts-Detection-Hackathon.git
cd Parts-Detection-Hackathon
git checkout solai
cd partpilot
```

The repo is private, so you need to be added as a collaborator first. On the
command line use a personal access token with the `repo` scope rather than a
password.

## 2. Create a virtual environment

```bash
python -m venv .venv
```

```powershell
# Windows
.venv\Scripts\Activate.ps1
```
```bash
# macOS / Linux
source .venv/bin/activate
```

## 3. Install

```bash
pip install -r requirements.txt
```

This pulls TensorFlow, PyTorch and FAISS, so it is a few GB and takes a while.

## 4. Configure

```powershell
copy .env.example .env      # Windows
```
```bash
cp .env.example .env        # macOS / Linux
```

Open `.env` and set `DATABASE_URL` to the connection string the team gave you.
Leave everything else as it is.

`.env` is git-ignored. Do not commit it, and do not paste the connection string
into an issue or a pull request.

## 5. Run

```bash
python -m backend.main
```

Then open <http://localhost:8000/docs>.

To try a prediction: find the predict endpoint, click **Try it out**, choose a
photo of a car part, and **Execute**.

The first request takes 30-60 seconds - it downloads the background-removal
model and the embedding model, roughly 500 MB combined. After that a prediction
takes a few seconds.

---

## What is already done for you

- **Brain 1** - the trained classifier is committed (`backend/models/classifier/`)
- **Brain 2** - the FAISS indexes are committed (`backend/models/faiss/`)
- **Brain 3** - the 55 products are already in the shared database

So do **not** run `alembic upgrade head` or `scripts/import_catalog_to_db.py`.
The table exists and is populated; running the import again would simply
rewrite the same rows.

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Run it alongside the backend.

---

## If something goes wrong

**`pip install` fails on a numpy version conflict**
Make sure you are on the latest `solai`. TensorFlow 2.18 caps numpy below 2.1,
and an older commit pinned 2.1.3, which can never resolve.

**`rembg is not installed; cannot remove image background`**
Misleading message - it usually means `onnxruntime` is missing. It is in
`requirements.txt`, so re-run the install.

**`password authentication failed` / cannot connect**
Check `DATABASE_URL` in `.env`. It must start `postgresql+asyncpg://`, and any
`@ : / #` in the password has to be URL-encoded (`@` becomes `%40`).

**`could not translate host name` on the database**
The direct Supabase host resolves over IPv6 only. If your network has no IPv6,
ask the team for the session-pooler URL instead.

**`alembic` runs but hits the wrong project**
If you have other virtual environments around, `alembic` on PATH may not be
this one. Use `python -m alembic.config ...`, or just don't run alembic - the
table already exists.

**A prediction returns a SKU but no product details**
The FAISS indexes and the database have drifted apart. Check that a SKU in
`backend/models/faiss/*.ids.json` also exists in the `products` table.

---

## Rebuilding the indexes (rarely needed)

Only if the catalog images change. Needs the images zip, and is slow on a CPU -
Google Colab is easier.

```bash
python scripts/build_faiss_indexes.py --remove-bg    # rebuild
python scripts/evaluate_brain2.py --remove-bg        # measure accuracy
```

Current accuracy is 77.5% top-1 and 94.7% top-3, measured leave-one-out across
55 products in 10 categories.
