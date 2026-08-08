---
title: PartPilot
emoji: 🔧
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# PartPilot

**PartPilot** is an AI-powered automobile parts identification platform. A
user uploads a photo of a vehicle part; the system identifies its category,
finds visually similar catalog products, resolves the exact SKU, and
recommends alternatives and accessories - with catalogs of 100,000+ products
in mind.

> **Status:** All four brains are implemented and `POST /predict` runs the
> real pipeline end-to-end. Trained classifier weights and the per-category
> FAISS indexes are committed, so there is nothing to train before running.
> See [Status](#status) below for what is done and what is still open.

---

## Project Overview

Given an image of a vehicle part, PartPilot:

1. **Predict the product category** (e.g. oil filter, brake pad, air filter).
2. **Search visually similar products** within that category.
3. **Identify the SKU** of the closest match.
4. **Return catalog information** (brand, description, compatible vehicles).
5. **Recommend alternatives** (replacement/equivalent SKUs).
6. **Recommend accessories** commonly paired with that SKU.
7. **Optionally generate a natural-language explanation** via an LLM.

---

## Tech Stack

| Concern              | Choice                         |
|-----------------------|---------------------------------|
| Language               | Python 3.12                    |
| API framework          | FastAPI + Uvicorn               |
| Validation             | Pydantic v2 (+ pydantic-settings) |
| Classification (Brain 1) | TensorFlow (EfficientNet)    |
| Embeddings (Brain 2)   | OpenCLIP                        |
| Vector search (Brain 2)| FAISS                           |
| Catalog persistence (Brain 3) | PostgreSQL, SQLAlchemy 2.x (async) + asyncpg, Alembic |
| Image processing       | Pillow, OpenCV, rembg           |
| Reasoning (Brain 4, future) | Hugging Face `transformers` |
| Testing                | Pytest                          |

---

## Folder Structure

```text
partpilot/
├── backend/
│   ├── app.py                    # FastAPI application factory
│   ├── main.py                   # Uvicorn entrypoint
│   ├── api/                      # HTTP layer: routers + dependency injection
│   │   ├── router.py
│   │   ├── dependencies.py
│   │   └── routers/
│   │       ├── health.py
│   │       ├── prediction.py
│   │       ├── catalog.py
│   │       └── admin.py
│   ├── pipeline/                 # The four AI "Brains" + orchestrator
│   │   ├── brain1_classifier/    # Image -> category (EfficientNet)
│   │   ├── brain2_similarity/    # Category + image -> similar SKUs (OpenCLIP + FAISS)
│   │   ├── brain3_catalog/       # SKU -> catalog metadata + recommendations (PostgreSQL)
│   │   │   ├── models.py         # SQLAlchemy `Product` ORM model
│   │   │   ├── repository.py     # `ProductRepository` - the only DB access point
│   │   │   ├── product_service.py# `ProductService` - business-facing catalog API
│   │   │   └── recommendation_service.py
│   │   ├── brain4_reasoning/     # (future) LLM explanation - interfaces only
│   │   └── orchestrator.py       # Chains Brain 1 -> 2 -> 3 -> 4
│   ├── schemas/                  # Pydantic v2 request/response models
│   ├── core/                     # Logging, exceptions, constants, security, startup, database
│   ├── config/                   # Settings, paths, environment helpers
│   ├── utils/                    # Generic helpers (images, files, validation, timing)
│   ├── data/                     # Runtime data: catalog, embeddings, indexes, uploads
│   ├── models/                   # Runtime model artifacts: classifier, clip, faiss
│   └── tests/                    # Pytest suite
├── alembic/                      # DB migrations (Alembic)
│   ├── env.py
│   └── versions/
├── datasets/                     # Training/eval datasets (not committed)
├── notebooks/                    # Exploratory notebooks
├── scripts/                      # One-off / operational scripts
├── docs/                         # Additional documentation
├── requirements.txt
├── alembic.ini
├── .env.example
└── .gitignore
```

---

## AI Pipeline & Data Flow

```text
                ┌──────────────┐
   Image  ───▶  │   Brain 1    │  ───▶  category
                │ Classifier   │
                └──────────────┘
                       │
                       ▼
                ┌──────────────┐
category+image ─▶│   Brain 2    │  ───▶  top-K similar SKUs
                │ Similarity   │
                │   Search     │
                └──────────────┘
                       │
                       ▼
                ┌──────────────┐
     SKU   ───▶ │   Brain 3    │  ───▶  Product + Recommendation
                │   Catalog    │
                │ Intelligence │
                └──────────────┘
                       │
                       ▼ (optional)
                ┌──────────────┐
   result  ───▶ │   Brain 4    │  ───▶  natural-language explanation
                │  Reasoning   │
                │   (future)   │
                └──────────────┘
```

This flow is codified in `backend/pipeline/orchestrator.py`'s
`PipelineOrchestrator.run()`. Each stage is consumed through an abstract
interface (`ClassifierInterface`, `SimilaritySearchInterface`,
`CatalogInterface`, `RecommendationInterface`, `ReasoningInterface`) so
concrete implementations can be developed, tested, and swapped
independently (dependency inversion).

### How each Brain works

- **Brain 1 - Image Classification** (`pipeline/brain1_classifier/`)
  Receives a raw part image and predicts its category using an
  EfficientNet model. Training, evaluation, and inference are split into
  `train.py`, `evaluate.py`, and `predict.py` respectively.

- **Brain 2 - Similarity Search** (`pipeline/brain2_similarity/`)
  Given the predicted category and the source image, generates an
  OpenCLIP embedding (`embedding_generator.py`) and searches a
  category-scoped FAISS index (`faiss_index.py`, managed by
  `index_manager.py`) for the top-K most visually similar SKUs.

- **Brain 3 - Catalog Intelligence** (`pipeline/brain3_catalog/`)
  Resolves a SKU to full catalog metadata (brand, description,
  compatible vehicles, replacement/alternative/accessory SKUs), backed
  by PostgreSQL. `models.py` defines the `products` table (SQLAlchemy
  ORM); `repository.py` (`ProductRepository`) is the only module that
  talks to the database; `product_service.py` (`ProductService`) is the
  business-facing API everything else - including future AI modules -
  should call. Exposed over HTTP via `GET/POST/PUT/DELETE /products`.
  `recommendation_service.py` resolves `replacement_sku`,
  `alternative_skus` and `accessory_skus` to full product records, which is
  what the results page renders.

- **Brain 4 - Reasoning** (`pipeline/brain4_reasoning/`) *(optional)*
  Uses Qwen2.5-1.5B-Instruct to turn the structured pipeline output into a
  natural-language explanation, and to ask clarifying questions when the match
  is ambiguous. Controlled per request by the `explain` query parameter. It is
  deliberately the only stage allowed to fail quietly: if the weights cannot be
  loaded, the request still returns the Brain 1-3 answer with
  `explanation: null`.

---

## Getting Started

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # then edit as needed, esp. DATABASE_URL

# create the products table (requires a running PostgreSQL instance)
alembic upgrade head

# run the API (auto-reload in DEBUG mode)
python -m backend.main
# or
uvicorn backend.app:app --reload

# run tests
pytest backend/tests
```

The API is served under `Settings.API_PREFIX` (default `/api/v1`), e.g.
`GET http://localhost:8000/api/v1/health`. Interactive docs are available
at `/docs` (Swagger UI) and `/redoc`.

### Database migrations (Alembic)

`DATABASE_URL` (see `.env.example`) is the single source of truth for the
DB connection - both the app (async, via `asyncpg`) and Alembic
(sync, via `psycopg2`) read it from `Settings`, so nothing needs to be
duplicated in `alembic.ini`.

```bash
alembic upgrade head              # apply all migrations
alembic revision --autogenerate -m "describe change"   # after editing models.py
alembic downgrade -1              # roll back the last migration
```

---

## Status

All four brains are implemented and wired. `POST /predict` runs the real
pipeline end-to-end: background removal, classification, per-category vector
search, catalog resolution, and an optional LLM explanation. Nothing in the
request path returns placeholder data.

| | State |
|---|---|
| **Brain 1** - Classifier | Fine-tuned EfficientNet, checkpoint committed under `backend/models/classifier/` |
| **Brain 2** - Similarity search | DINOv2 by default, OpenCLIP for the three categories that benchmark better on it; per-category FAISS indexes committed |
| **Brain 3** - Catalog | `ProductRepository`/`ProductService` against PostgreSQL, CRUD at `/products`, recommendations resolved to full product records |
| **Brain 4** - Reasoning | Qwen2.5-1.5B-Instruct, optional; degrades to no explanation when the weights are unreachable |
| Orchestrator | `PipelineOrchestrator.run()` drives all four stages and the no-match decision |
| Audit trail | Every run recorded and readable back via `/history` |

Known gaps, roughly in priority order:

1. **Latency.** A steady-state prediction is around 7s, of which roughly half
   is database round trips rather than model time - the audit write is awaited
   inline on the response path, and a remote Postgres costs about 1.1s per
   round trip. A local database and a backgrounded audit write are the two
   levers.
2. **Catalog size.** 56 products across 10 categories is enough to calibrate
   against, not enough to prove the retrieval story at scale.
3. **Domain gap.** Every indexed image is a studio shot on white; real uploads
   are phone photos. Thresholds calibrated leave-one-out on studio images run
   optimistic against what users actually send.
4. **Hardening.** `verify_api_key` is still a permissive no-op; no request-id
   middleware, structured metrics or tracing; no integration tests against a
   containerized PostgreSQL.

## Future Improvements

- Batch/async inference for high-throughput scenarios.
- A background job (or `admin` endpoint) to incrementally update FAISS
  indexes as new catalog products are onboarded, instead of full rebuilds.
- Caching layer (e.g. Redis) for hot SKUs/categories.
- Observability: structured logging correlation IDs, request tracing,
  and per-stage latency metrics (Brain 1/2/3/4 timing breakdown).
- CI pipeline running `pytest` + linting on every PR.
