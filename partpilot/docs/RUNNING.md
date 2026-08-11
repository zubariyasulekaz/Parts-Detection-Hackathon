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
| `.env` | contains the database connection string, so it stays out of git | **yes** |
| `partpilot_images_v3.zip` | ~50 MB of catalog photos, git-ignored | only for rebuilding indexes |

Get the `.env` file from the team and place it at `partpilot/.env` - see
[step 4](#4-configure). You can skip the images unless you intend to rebuild
the FAISS indexes - predictions embed the photo the user uploads, not the
catalog photos.

---

## 1. Clone

```bash
git clone https://github.com/zubariyasulekaz/Parts-Detection-Hackathon.git
cd Parts-Detection-Hackathon
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
It also installs `llama-cpp-python` (the Brain 4 runtime) from a prebuilt
wheel - `requirements.txt` points pip at the project's own wheel index, so
this needs no compiler and installs cleanly on Windows even without Long
Path support enabled. A plain `pip install llama-cpp-python` with no extra
index would instead try to build from source and fail there, which is why
that index is wired in rather than left as a manual step.

Brain 4 stays optional at runtime regardless - the golden path (identify a
part, including guided-chat disambiguation) works fully without it, and a
failed load just degrades to the Brain 1-3 answer with no explanation. If
`llama-cpp-python` ever fails to install on some other platform, set
`LLM_BACKEND=transformers` in `.env` to use the slower, no-extra-dependency
path instead.

## 4. Configure

Place the `.env` file the team gave you at `partpilot/.env`. Leave it as
given.

`.env` is git-ignored. Do not commit it, and do not paste its contents into
an issue or a pull request.

## 5. Run

```bash
python -m backend.main
```

Then open <http://localhost:8000/docs>.

To try a prediction: find the predict endpoint, click **Try it out**, choose a
photo of a car part, and **Execute**.

The startup log ends with either `Database reachable` or an `ERROR` naming
the problem and pointing back here - check that line before assuming the app
is ready, especially the first time you run it on a new network.

The first request takes 30-60 seconds - it downloads the background-removal
model and the embedding model, roughly 500 MB combined. After that a prediction
takes a few seconds.

---

## What is already done for you

- **Brain 1** - the trained classifier is committed (`backend/models/classifier/`)
- **Brain 2** - the FAISS indexes are committed (`backend/models/faiss/`)
- **Brain 3** - the 56 products are already in the shared database

So do **not** run `alembic upgrade head` or `scripts/import_catalog_to_db.py`.
The table exists and is populated; running the import again would simply
rewrite the same rows.

---

## Frontend

```bash
cd frontend
npm install
cp .env.example .env    # copy .env.example on Windows
npm run dev
```

This creates `frontend/.env` (no secrets in it, unlike the backend's). Run it
alongside the backend. `.env` decides what it talks to:

| | |
|---|---|
| `VITE_API_MODE` | `live` calls the backend; `mock` runs off `src/mocks` with no backend |
| `VITE_API_BASE_URL` | backend origin, must match `HOST`/`PORT` |
| `VITE_API_PREFIX` | must match `API_PREFIX` in `backend/config/settings.py` |
| `VITE_PREDICTION_EXPLAIN` | `false` skips Brain 4 (see below) |

The dev server is fixed to **<http://localhost:5555>** (`server.port` in
`vite.config.ts`, with `strictPort: true`) - it fails to start rather than
silently moving to another port if 5555 is already taken. The backend allows
all CORS origins by default, so no extra configuration is needed on that
side.

---

## If something goes wrong

**`pip install` fails on a numpy version conflict**
Make sure you are on the latest commit. TensorFlow 2.18 caps numpy below 2.1,
and an older commit pinned 2.1.3, which can never resolve.

**`rembg is not installed; cannot remove image background`**
Misleading message - it usually means `onnxruntime` is missing. It is in
`requirements.txt`, so re-run the install.

**`password authentication failed` / cannot connect**
Check `DATABASE_URL` in `.env`. It must start `postgresql+asyncpg://`, and any
`@ : / #` in the password has to be URL-encoded (`@` becomes `%40`).

**Backend seems to hang, or `could not translate host name` on the database**
The direct Supabase host (`DATABASE_URL`) resolves over IPv6 only. If
`DATABASE_URL_POOLER` is set in `.env`, `backend.core.database` detects a
missing IPv6 route at startup and switches to it automatically - check the
startup log for `Database reachable` or an `ERROR` naming the problem. If
`DATABASE_URL_POOLER` is unset, ask the team for it and add it to `.env`.

**`alembic` runs but hits the wrong project**
If you have other virtual environments around, `alembic` on PATH may not be
this one. Use `python -m alembic.config ...`, or just don't run alembic - the
table already exists.

**A script dies with `ModuleNotFoundError: No module named 'faiss'` (or
`transformers`, or `rembg`)**
The virtual environment is not active. FAISS, PyTorch, transformers and rembg
are installed into `.venv`, never system-wide, so a bare `python
scripts/...` picks up an interpreter that has none of them. Activate first, or
call the interpreter by path:

```powershell
.venv\Scripts\python.exe scripts/build_faiss_indexes.py --remove-bg
```

The failure is noisy but harmless: the script logs `rembg is not installed;
skipping background removal` for every image before it eventually crashes, and
writes nothing.

**A prediction returns a SKU but no product details**
The FAISS indexes and the database have drifted apart. Check that a SKU in
`backend/models/faiss/*.ids.json` also exists in the `products` table.

**`Could not load the 'dinov2' embedding model` / no AI explanation**
Two of the models are downloaded from Hugging Face on first use rather than
committed: `facebook/dinov2-base` (Brain 2) and `Qwen/Qwen2.5-1.5B-Instruct`
(Brain 4). Both are served from `us.aws.cdn.hf.co`, which some corporate
networks block - DNS resolves but the connection times out. Check with:

```bash
curl -so /dev/null -w "%{http_code}\n" --max-time 15 https://us.aws.cdn.hf.co/
```

`000` means it is blocked. Either get that host allowed, or download the two
models on a network that can reach it and copy `~/.cache/huggingface/hub`
across. Do not install `hf_xet` hoping to route around it - it discards any
partial download and then stalls without reporting an error.

Until then the app still runs, and degrades rather than failing:

- The three categories whose indexes were built with OpenCLIP - **Air Filter**,
  **Shock Absorber**, **Wheel Hub Assembly** - work fully, because those
  weights are already cached.
- The other seven need DINOv2 and return a 503 explaining why.
- Brain 4 explanations are skipped and `explanation` comes back `null`;
  everything else in the response is unaffected. Set
  `VITE_PREDICTION_EXPLAIN=false` in `frontend/.env` so the UI does not wait on
  the failed model load on the first request.

A failed model load is remembered for the life of the process, so only the
first request pays the download timeout. Restart the backend to retry.

---

## Rebuilding the indexes (rarely needed)

Only if the catalog images change. Needs the images zip, and is slow on a CPU -
Google Colab is easier.

```bash
python scripts/build_faiss_indexes.py --remove-bg    # rebuild
python scripts/evaluate_brain2.py --remove-bg        # measure accuracy
```

`analyze_index_vectors.py` is usually the one you want: it measures the vectors
already in the built indexes, so it reports what the running system will do and
finishes in milliseconds instead of re-embedding everything.

```bash
python scripts/analyze_index_vectors.py             # accuracy + threshold sweep
```

Current accuracy is **85.0% top-1, 96.7% top-3, MRR 0.911**, measured
leave-one-out across 56 products in 10 categories (240 queries). Leave-one-out
here means the query image is excluded from its own product's centroid, so a
photo is never matched against itself.
