# PartPilot

**PartPilot** is an AI-powered automobile parts identification platform. A
user uploads a photo of a vehicle part; the system identifies its category,
finds visually similar catalog products, resolves the exact SKU, and
recommends alternatives and accessories — with catalogs of 100,000+ products
in mind.

> **Status:** This repository currently contains the **architecture
> skeleton only**. All AI logic (model loading, inference, embeddings,
> FAISS search, LLM reasoning) is stubbed with `NotImplementedError` and
> `TODO` markers, ready for incremental implementation. See
> [Development Roadmap](#development-roadmap) below.

---

## Project Overview

Given an image of a vehicle part, PartPilot is designed to:

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
│   │   │   ├── repository.py     # `ProductRepository` — the only DB access point
│   │   │   ├── product_service.py# `ProductService` — business-facing catalog API
│   │   │   └── recommendation_service.py
│   │   ├── brain4_reasoning/     # (future) LLM explanation — interfaces only
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

- **Brain 1 — Image Classification** (`pipeline/brain1_classifier/`)
  Receives a raw part image and predicts its category using an
  EfficientNet model. Training, evaluation, and inference are split into
  `train.py`, `evaluate.py`, and `predict.py` respectively.

- **Brain 2 — Similarity Search** (`pipeline/brain2_similarity/`)
  Given the predicted category and the source image, generates an
  OpenCLIP embedding (`embedding_generator.py`) and searches a
  category-scoped FAISS index (`faiss_index.py`, managed by
  `index_manager.py`) for the top-K most visually similar SKUs.

- **Brain 3 — Catalog Intelligence** (`pipeline/brain3_catalog/`)
  Resolves a SKU to full catalog metadata (brand, description,
  compatible vehicles, replacement/alternative/accessory SKUs), backed
  by PostgreSQL. `models.py` defines the `products` table (SQLAlchemy
  ORM); `repository.py` (`ProductRepository`) is the only module that
  talks to the database; `product_service.py` (`ProductService`) is the
  business-facing API everything else — including future AI modules —
  should call. Exposed over HTTP via `GET/POST/PUT/DELETE /products`.
  Alternative/accessory recommendation resolution
  (`recommendation_service.py`) is still a `TODO` stub.

- **Brain 4 — Reasoning** (`pipeline/brain4_reasoning/`) *(future)*
  Will use a Hugging Face LLM to turn the structured pipeline output into
  a natural-language explanation. Only `ReasoningInterface` exists today
  — no implementation, by design.

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
DB connection — both the app (async, via `asyncpg`) and Alembic
(sync, via `psycopg2`) read it from `Settings`, so nothing needs to be
duplicated in `alembic.ini`.

```bash
alembic upgrade head              # apply all migrations
alembic revision --autogenerate -m "describe change"   # after editing models.py
alembic downgrade -1              # roll back the last migration
```

---

## Development Roadmap

This skeleton compiles and runs end-to-end with **dummy data**. Endpoint
handlers currently return placeholder responses rather than invoking the
(unimplemented) pipeline, so the API contract can be validated and
consumed by a frontend before any model exists.

Suggested implementation order:

1. **Brain 1 — Classifier**: implement `preprocess.py`, `model_loader.py`,
   `predict.py`, then `train.py`/`evaluate.py` once a labeled dataset is
   available in `datasets/`.
2. **Brain 3 — Catalog**: done — `ProductRepository`/`ProductService` are
   fully implemented against PostgreSQL, with full CRUD exposed at
   `/products`. Remaining work: implement
   `RecommendationService.recommend` (resolve `replacement_sku`/
   `alternative_skus`/`accessory_skus` to full product records).
3. **Brain 2 — Similarity Search**: implement `clip_model.py`,
   `embedding_generator.py`, `faiss_index.py`, and `index_manager.py`;
   build per-category indexes from the catalog.
4. **Wire the orchestrator**: replace the dummy response in
   `api/routers/prediction.py` with a real call to
   `PipelineOrchestrator.run()` once Brain 1/2 exist (Brain 3 is already
   wired in).
5. **Brain 4 — Reasoning** *(future)*: implement `llm_service.py` and
   `prompt_builder.py` against a chosen Hugging Face model/endpoint.
6. **Hardening**: replace the permissive `verify_api_key` no-op with real
   auth, add request-id middleware, add structured metrics/tracing, and
   add real `ProductRepository`/`ProductService` integration tests against
   a (containerized) PostgreSQL instance.

## Future Improvements

- Batch/async inference for high-throughput scenarios.
- A background job (or `admin` endpoint) to incrementally update FAISS
  indexes as new catalog products are onboarded, instead of full rebuilds.
- Caching layer (e.g. Redis) for hot SKUs/categories.
- Observability: structured logging correlation IDs, request tracing,
  and per-stage latency metrics (Brain 1/2/3/4 timing breakdown).
- CI pipeline running `pytest` + linting on every PR.
