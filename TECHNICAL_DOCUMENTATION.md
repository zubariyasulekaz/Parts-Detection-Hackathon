# PartPilot — Technical Documentation

**Version 0.1.0 · Klizer Hackathon · Submission: August 11, 2026**

A four-stage computer-vision pipeline that identifies a car part from one photograph — SKU, fitment, replacement, and accessories — and is calibrated to refuse rather than guess when it isn't sure. The **live inference pipeline** runs entirely on **open-source, self-hostable AI models** — zero dependency on any proprietary LLM API at prediction time (see Section 17 for the one offline tool used during dataset preparation).

**Headline metrics:** Top-1 accuracy 85.0% · Top-3 accuracy 96.7% · MRR 0.911 · Impostors caught 93.1%
**Catalog:** 56 SKUs across 10 categories

### Submission requirements — where to find each item

| Required item | Section |
|---|---|
| Problem Statement | 1 |
| Solution Overview | 1, 3 |
| Business Value | 13 |
| AI Models & Technologies Used | 4, 17 |
| Data Sources | 9 |
| Architecture Overview | 3 |
| Future Enhancements | 16 |

---

## 1. Overview — Problem Statement & Solution

**Problem.** Someone holding an unlabelled car part usually cannot name it — the part number is worn off, the box is gone. Today that means a photo sent to a parts counter and a wait for someone who has seen it before. That spends the counter's time, delays the customer, and does not scale past whoever happens to be on shift.

**Solution.** PartPilot answers in one upload: it names the SKU, what it fits, what supersedes it, and what to buy alongside it — using a photo alone, no part number required.

**Why AI is the right approach.** No rules-based or text-search system can match an unlabelled photo to a SKU — the input has no text, no barcode, nothing to key a lookup on. Visual similarity search is the only approach that works on pixels alone, and a classifier is needed to narrow the search space before it does. AI is not a UI layer here; it **is** the identification step. Every SKU, fitment fact, and recommendation shown afterward comes from the database, but the database is only reached because a trained vision model decided which row to look up.

The harder half of the problem is knowing when **not** to answer. A catalog that confidently names the wrong brake pad is worse than one that admits it doesn't stock the part — so refusal is a designed, calibrated feature (Section 6), not an error path.

**Design rule:** Everything before the confidence gate is a trained model. Everything after it is data. The models decide *which* part; PostgreSQL decides *what is true* about it. No language model is ever asked to invent a fact about stock or state a SKU.

---

## 2. Hackathon Rules Alignment

A direct walkthrough of how PartPilot satisfies the stated hackathon rules and bonus criteria.

| # | Rule | How PartPilot satisfies it |
|---|---|---|
| 1 | Working prototype | Full running system: FastAPI backend + React frontend. A no-setup demo mode (canned data) and a live mode (real models + database) both work end-to-end today. |
| 2 | AI must be core, not a chatbot wrapper | The identification itself — category classification + visual similarity search — **is** the AI. The optional LLM (Brain 4) only narrates a decision three other components already made; the product answer never depends on it. |
| 3 | Any tech stack | Python/FastAPI backend, React/TypeScript frontend, PyTorch + TensorFlow for models, FAISS for search, PostgreSQL for data. See Section 4. |
| 4 | ⭐ Open-source AI advantage | **Every model in the live prediction path is open-weight and self-hostable**: EfficientNetB0, DINOv2, OpenCLIP, and Qwen2.5-1.5B-Instruct via llama.cpp. (SigLIP is implemented as a supported backend in code but is not used by any of the 10 deployed category indexes — see Section 5.) No OpenAI, Anthropic, Gemini, or Azure OpenAI call exists anywhere in the inference pipeline. (Gemini was used once, offline, to help build the image dataset — see Section 9, disclosed in full in Section 17.) |
| 5 | Build for real customers | Directly applicable to auto-parts retailers, dealership service counters, repair shops, and insurance-claim triage. The architecture generalizes to any visually-identifiable SKU catalog (electronics, industrial parts, appliance parts) — a candidate Klizer accelerator, not a single-customer demo. |
| 6 | Original work, disclosed components | Built on disclosed open-source libraries and pretrained weights (Section 17), plus one disclosed proprietary tool (Gemini) used offline for a minority of catalog images (Section 9). No proprietary or third-party commercial code is embedded in the running application. Catalog data provenance is documented in full in Section 9. |
| 7 | Demonstrate business value | Answered directly in Section 13: the problem (unlabelled-part identification), who benefits (counter staff and customers), the time saved (minutes–hours → seconds), and why AI is necessary (no text/barcode exists to look up). |
| 8 | Keep it practical | Scope is deliberately a working 56-SKU catalog rather than a larger unvalidated one — every threshold in the pipeline is measured against it (Section 12), not assumed. The architecture does not change at catalog scale; only index size does. |
| 9 | Present the architecture | Covered in full in Section 3 (solution architecture), Section 4 (AI models), Section 9 (data sources), Section 10 (integration surface — REST API), Section 15 (deployment), and Section 16 (future scalability). |
| 10 | AI transparency | Full model/service disclosure in Section 17 — every model is named, sourced, and licensed as open weight. |
| 11 | Team collaboration | *[Team to fill in: contribution breakdown by member for the final presentation.]* |
| 12 | Time limits (20 min demo / 10 min Q&A) | Suggested run order in Section 15 covers the demo script; pace problem → architecture → live predictions → refusal case → business value inside the 20-minute window, leaving Q&A for the threshold/calibration methodology in Sections 6 and 12. |
| 13 | Bonus considerations | See the scorecard immediately below. |
| 14 | Realistic data | Catalog photos are primarily real manufacturer product photography, supplemented with Gemini-generated images only where a manufacturer photo was unavailable; catalog metadata is a curated synthetic dataset modeled on real retail conventions. Full documentation, generation method, and assumptions in Section 9. |

### Bonus-criteria scorecard

| Bonus criterion | Status |
|---|---|
| Effective use of open-source AI models | **Yes** — the entire pipeline, not a token component |
| Runs on customer-owned / self-hosted infrastructure | **Yes** — every model runs locally; Postgres is the only external dependency and is swappable for any self-hosted instance |
| Minimizes dependency on proprietary AI services | **Yes** — zero proprietary AI API calls by default |
| Agentic AI / multi-agent orchestration | **Not applicable by design.** PartPilot is a deterministic, auditable staged pipeline, not autonomous LLM agents — a deliberate choice for a domain where an invented SKU is a real-world cost (Section 1). |
| ERP / CRM / PIM / eCommerce integration | Not yet built. The REST API and catalog schema (Sections 8, 10) are structured to make this a near-term integration, not a redesign — listed as a roadmap item (Section 16), not a current capability. |
| Measurable business impact | **Yes** — Sections 12–13 give calibrated accuracy, a priced false-answer rate, and a counter-vs-PartPilot comparison. |
| Potential to become a Klizer accelerator | **Yes** — see Section 5's generalization argument. |

---

## 3. Solution Architecture

Four independent stages — called Brains 1–4 — each with one job, wired together by an orchestrator that contains no AI logic of its own. Every stage is injected as an interface (`brain*_*/interfaces.py`), so any one can be swapped or mocked without touching the others.

**Pipeline flow:**

```
Photo upload
  -> Stage 0: Background removal (rembg)
  -> Brain 1: Classifier (EfficientNetB0) --[category + confidence]-->
  -> Brain 2: Similarity search (DINOv2 / OpenCLIP + FAISS) --[ranked SKUs + cosine scores]-->
  -> Confidence gate
       -> below threshold -> NO CATALOG MATCH (nothing named)
       -> above threshold -> Brain 3: Catalog (PostgreSQL)
            -> top candidates too close to call?
                 -> yes -> Guided chat (catalog facts only, no model) -> narrowed to one
                 -> no  -> clear winner
            -> Brain 4: Explanation (Qwen2.5-1.5B, optional)
            -> Answer: SKU, fitment, replacement, accessories
```

| Stage | Question it answers | Technology | Hands on |
|---|---|---|---|
| Stage 0 | Where is the part in this photo? | `rembg` | Part isolated on white |
| Brain 1 | What kind of part is this? | EfficientNetB0 | 1 of 10 categories + confidence |
| Brain 2 | Which exact SKU is it? | DINOv2 / OpenCLIP → FAISS | Ranked SKUs with cosine scores |
| Gate | Are we sure enough to answer at all? | Per-backend calibrated thresholds | Answer, or refusal |
| Brain 3 | What is true about it? | PostgreSQL | Product record + recommendations |
| Guided chat | Which look-alike is it? | Catalog metadata — no model | One narrowing question at a time |
| Brain 4 | How do we explain it? | Qwen2.5-1.5B via llama.cpp | Explanation + clarifying questions |

**Integrations:** a single REST API (Section 10) is the entire integration surface — any storefront, counter tool, or ERP/CRM/PIM front end talks to PartPilot the same way the bundled React frontend does.

**Deployment:** the backend is a single FastAPI process (models loaded in-process, warmed at boot); the database is any PostgreSQL instance (Supabase in this build, but not required to be). Nothing in the pipeline calls out to a third-party AI service, so the whole stack can run inside a customer's own network with no external egress.

**Future scalability:** see Section 16 — the index structure, threshold calibration, and session storage are each called out as the specific things that need to change at 10x–1000x catalog size, and none of them require an architecture change.

Orchestration code: `partpilot/backend/pipeline/orchestrator.py`

---

## 4. Technology & AI Models Used

| Layer | Technology | Role | Open source? |
|---|---|---|---|
| API | FastAPI 0.115, Uvicorn, Pydantic v2 | REST service, validation, OpenAPI docs at `/docs` | Yes |
| Classifier (Brain 1) | TensorFlow 2.18 · EfficientNetB0 | ImageNet-pretrained backbone, frozen, fresh 10-way softmax head, fine-tuned on the catalog using Kaggle Notebooks' free GPU tier | Yes |
| Embeddings (Brain 2) | PyTorch · HF Transformers · DINOv2 / OpenCLIP (SigLIP supported in code, not deployed) | Image → vector, one backend per category | Yes |
| Vector search | FAISS `IndexFlatIP` | Exact cosine search, one index per category (pgvector supported as an alternate store) | Yes |
| Background removal | rembg (ONNX Runtime) | Segments the part from its background before both models see it | Yes |
| Reasoning (Brain 4) | llama.cpp · Qwen2.5-1.5B-Instruct (Q4_K_M GGUF) | Explanation text; HF `transformers` as fallback runtime | Yes |
| Catalog (Brain 3) | PostgreSQL (Supabase) · SQLAlchemy async + asyncpg · Alembic | Product records, fitment, recommendations, audit trail | Yes (Postgres) |
| Config | pydantic-settings | Typed, validated configuration from `.env` | Yes |
| Frontend | Vite · React 19 · TypeScript · Tailwind v4 | Upload flow, results, guided chat UI, architecture page | Yes |

**No proprietary AI service is called by the live inference pipeline** — every model a prediction actually runs through (Sections 5–7) is open weight and self-hostable. The one exception in the whole project is Google Gemini, used offline during dataset preparation to generate a minority of catalog images (Section 9); it plays no role at prediction time. Full model-by-model disclosure is in Section 17.

---

## 5. Pipeline Reference

### Stage 0 — Background removal (rembg / ONNX)

- **In:** uploaded photo, decoded pixels
- **Out:** same part on a plain white background

Catalog photos are shot on white; user photos are shot on a workbench or garage floor. Left uncorrected, both models partially match on background texture rather than the part. Running removal once, upstream of Brain 1 and Brain 2, guarantees they can never disagree about what they're looking at. The original photo travels alongside the cleaned one so a query always matches how its target index was built.

### Brain 1 — Classifier (EfficientNetB0, TensorFlow)

- **In:** background-removed image, resized to 224×224
- **Out:** category + confidence, plus a full ranking of all 10 categories
- **Code:** `backend/pipeline/brain1_classifier/`

Brain 2 searches inside one category's index rather than the whole catalog — Brain 1 picks that index, so a wrong category is unrecoverable downstream however good Brain 2 is.

**Decision:** When softmax confidence falls below `CLASSIFIER_CONFIDENCE_THRESHOLD` (0.5), the orchestrator also searches the runner-up category. Both searches run; the winner is whichever category's top match clears *its own* threshold by the larger margin — margins are comparable across backends, raw cosine scores are not.

**Training infrastructure.** The classifier head was fine-tuned on Kaggle Notebooks specifically to get free GPU acceleration — training EfficientNetB0's head on the catalog is fast on a GPU and impractically slow on CPU-only hardware, and Kaggle's free GPU tier removed the need for paid compute for a component that only needs to be trained once. The trained checkpoint is committed to the repo (`backend/models/classifier/`), so this GPU dependency exists only at training time, never at inference.

### Brain 2 — Similarity search (DINOv2 / OpenCLIP → FAISS)

- **In:** background-removed image + category from Brain 1
- **Out:** ranked SKUs with cosine similarity, plus which model produced them
- **Code:** `backend/pipeline/brain2_similarity/`

The embedding layer (`embedding_backends.py`) supports three open-weight model families behind one interface — DINOv2, OpenCLIP, and SigLIP — plus `+`-joined combinations of them. Only DINOv2 and OpenCLIP were actually used to build the 10 deployed category indexes; SigLIP is implemented and available via `EMBEDDING_BACKEND`/`CATEGORY_BACKENDS`, but no category currently routes to it.

**Per-category model routing.** No single embedding model wins everywhere. Per-category benchmarking routes three categories to OpenCLIP and leaves the rest on DINOv2 (the self-supervised default, which optimises for "is this the same object" rather than "what is this called"):

| Category | DINOv2 | OpenCLIP | Routed to |
|---|---:|---:|---|
| Air Filter | 66.7% | 95.2% | OpenCLIP |
| Wheel Hub Assembly | 16.7% | 33.3% | OpenCLIP |
| Shock Absorber | 95.8% | 100% | OpenCLIP |
| All other categories | best | — | DINOv2 |

**Measured:** A DINOv2 + OpenCLIP ensemble scored 72.8% top-1 — behind DINOv2 alone at 73.2%. Averaging two models pulls the strong one toward the weak one; that single measurement is what pointed to per-category routing instead of blending, which went on to deliver the largest single accuracy gain in the project (see Section 12).

**Scoring: centroid vs. best photo.** Each product has 2–7 photos, each stored as its own vector row. Scoring against the mean vector of a product's photos beats scoring against its single best-matching photo:

| Scoring strategy | Correct SKU ranked first |
|---|---:|
| Centroid (mean of product's vectors) — used | 79% |
| Max over images (best single photo) | 72% |

Per-image vectors are still stored individually rather than pre-collapsed, which keeps every photo inspectable and lets leave-one-out evaluation exclude a held-out image exactly.

**Other measured settings:**
- **Test-time augmentation** — the image and its mirror are both embedded and averaged (`EMBEDDING_TTA=True`), so a part photographed from the "wrong" side still lands near its catalog shots.
- **Index sidecars** — each `.faiss` file ships with `.ids.json` (row → SKU) and `.meta.json` (which model built it, whether backgrounds were removed) so a query is always embedded the way its index expects.

---

## 6. Confidence Gate — Refusing to Guess

The two embedding models compress cosine similarity very differently: an out-of-catalog image tops out around 0.83 on DINOv2 but 0.92 on OpenCLIP, so one global threshold cannot serve both. Thresholds are keyed per backend and calibrated against the measured score distributions of correct matches vs. impostors.

| Backend | Threshold | Correct matches rejected | Impostors caught |
|---|---:|---:|---:|
| DINOv2 | 0.45 | 0.0% | 90.0% |
| DINOv2 — chosen | 0.48 | 1.3% | 93.1% |
| OpenCLIP | 0.84 | 0.0% | 43.9% |
| OpenCLIP — chosen | 0.86 | 1.5% | 62.1% |

**Priced trade-off:** Roughly 1.5% of correct matches are given up to catch the large majority of impostors — recommending the wrong part is judged worse than admitting the catalog doesn't have it. OpenCLIP's distributions overlap more; that's an accepted cost of keeping it for the three categories where it ranks far better.

If Brain 1 itself was unsure of the category (confidence below 0.5), the threshold rises by `NO_MATCH_UNCERTAIN_MARGIN` (+0.04) — two weak signals should not combine into a confident answer. On refusal the pipeline skips Brain 3 entirely: no product lookup, nothing selectable in the UI, near-misses recorded only as audit context.

---

## 7. Guided Disambiguation Chat

Some parts cannot be told apart by photograph alone — two brake pad sets for different vehicles are the same object shot twice. When rank 1 and rank 2 land within `CONFIRMATION_SIMILARITY_GAP` of each other, the pipeline stops guessing and asks the catalog's own facts, one narrowing question at a time. There is no free-text input and no language model in this loop — every option is a button generated from a real catalog row, so nothing can be invented and every answer provably narrows the candidate set.

| Facet | Example | Asked |
|---|---|---|
| Visual attributes | "How many wheel studs?" | First — answerable by looking at the part |
| Vehicle make / model / year | "Which vehicle is this for?" | Next — the user knows their own car |
| Part number | "Is one of these numbers stamped on it?" | Decisive, but requires hunting for text |
| Brand | "Do you know the brand?" | Last — often unknown to whoever is asking at all |

Sessions live server-side (`backend/pipeline/chat/engine.py`, `backend/api/routers/chat.py`) — only SKUs and similarity scores travel from the client; every fact the chat asks about is fetched from the catalog on the server, so the conversation cannot be fed invented product data.

---

## 8. Data Model

Brain 3's catalog is a single `products` table (PostgreSQL, accessed only through `ProductRepository`), keyed by SKU. `attributes` is an open JSONB bag rather than a fixed column set, because what visually separates two air filters is not what separates two brake pads.

| Column | Type | Meaning |
|---|---|---|
| `sku` | text, PK | Primary key |
| `product_name` | text | Display name |
| `brand` | text, indexed | Manufacturer |
| `category` | text, indexed | One of 10 catalog categories |
| `description` | text, nullable | Free text |
| `manufacturer_part_number` | text, indexed | Number stamped on the part, e.g. `DE1439` |
| `attributes` | jsonb | Open key/value bag — `filter_style`, `position`, `primary_colour`, etc.; keys vary by category |
| `image_paths` | text[] | Catalog photo paths |
| `replacement_sku` | text, nullable | Superseding part, offered first in recommendations |
| `alternative_skus` | text[] | Cross-brand equivalents |
| `accessory_skus` | text[] | Recommended companion purchases |
| `compatible_vehicles` | jsonb[] | Make / model / year fitment rows |
| `created_at` / `updated_at` | timestamptz | Server-set |

Recommendation logic (`brain3_catalog/recommendation_service.py`) is pure catalog lookup, no model: alternatives are `replacement_sku` first, then de-duplicated `alternative_skus`; a referenced SKU missing from the catalog is skipped with a warning rather than crashing the response.

---

## 9. Data Sources & Data Realism

Three distinct data assets feed the pipeline, sourced and built differently — one for Brain 1's category classifier, two for Brain 2/3's product catalog:

**Brain 1 training images — broad, category-level, web-sourced.** The classifier is trained to tell 10 part *categories* apart, not specific SKUs, so it needs volume and visual variety rather than per-product precision. That training set was built with `ddgs` (the DuckDuckGo image search library) querying broad, descriptive terms per category (e.g. "car suspension bushing", "OEM suspension bushing", "control arm bushing"), targeting roughly 400 candidate images per category. The raw scrape was then cleaned before training — near-duplicates and collages removed (`image_dedup.py`, `run_fastdup.py`), off-topic results filtered with a CLIP-similarity pass (`filter_dataset_clip.py`), and the result split into train/validation folders per category (`split_dataset.py`). This dataset is intentionally separate from, and much larger and noisier than, the curated 56-SKU catalog below — it only needs to teach "what does an air filter look like in general," not "which exact SKU is this."

**Brain 2/3 catalog photography — real images, supplemented where needed.** The primary source is real product photography collected from manufacturer and retailer product pages (open, publicly available listings) across all 10 part categories. Where a SKU or a needed angle had no usable manufacturer photo, the gap was filled with AI-generated product images created with Google Gemini, so every SKU still reaches a usable photo count. All photos — sourced and generated alike — went through the same cleaning pipeline: near-duplicate and collage/composite images were removed with a perceptual-duplicate pass (`fastdup`), and each kept photo was background-normalized (Stage 0) so the classifier and embedding models see the part the same way regardless of where the source photo came from. Each of the 56 SKUs carries 2–7 verified photos after cleaning.

**Catalog metadata — curated, realistic synthetic data.** Product names, brands, manufacturer part numbers, fitment ranges, cross-references (`replacement_sku`, `alternative_skus`, `accessory_skus`), and category-specific attributes are a curated dataset modeled closely on real automotive aftermarket retail conventions — real brand-naming patterns (e.g. Duralast, Wagner ThermoQuiet, Febi Bilstein, MOOG, TRW), realistic part-number formats, and plausible make/model/year fitment windows. This was a deliberate choice over arbitrary placeholder labels: it lets the recommendation engine (Section 8) and the guided-chat disambiguation logic (Section 7) exercise real business relationships — a brake pad set that has actually been superseded, an accessory that actually belongs with a given filter — rather than meaningless linkage.

**Documented assumptions:**
- SKUs and manufacturer part numbers are illustrative, not real retailer inventory identifiers.
- No proprietary retailer data, pricing, or customer data was used or is required by the architecture.
- The Brain 1 training images were scraped from public web search results via `ddgs` — sufficient volume and variety to train a general category classifier.
- Manufacturer-sourced photos were collected from public product listings; Gemini-generated photos are clearly a fill-in for coverage where a manufacturer photo wasn't available, not a substitute for real photography where it was. The pipeline itself is agnostic to where photos come from, so the image sources are a swappable input, not an architectural constraint (see Section 16).
- Gemini was used only as an **offline, one-time data-preparation tool** to generate a minority of catalog images. It is not part of the live prediction pipeline and nothing about the runtime system's zero-proprietary-API claim (Sections 4, 17) depends on it.
- Data quality was treated as a first-class variable, not an afterthought: the accuracy figures in Section 12 are only meaningful because the underlying catalog data was built to be internally consistent (fitment, cross-references, and attribute keys per category all validated against each other).

---

## 10. API Reference

Base path `/api/v1` (configurable via `API_PREFIX`). Interactive docs are auto-generated at `/docs`. Every response is wrapped in a `StandardResponse<T>` envelope. This is also the full integration surface for connecting PartPilot to an external storefront, counter tool, or ERP/CRM/PIM system (Section 2, bonus criteria).

**Prediction**

| Method | Path | Description |
|---|---|---|
| POST | `/predict` | Upload a photo → full pipeline run → category, ranked candidates, matched product, recommendations, explanation, audit id |
| POST | `/predict/{audit_id}/confirm` | Record which SKU the user actually settled on — validates or corrects the audit entry |

**Chat**

| Method | Path | Description |
|---|---|---|
| POST | `/chat/start` | Open a disambiguation session from a prediction's candidates |
| GET | `/chat/{session_id}` | Current session state (e.g. after a page reload) |
| POST | `/chat/{session_id}/answer` | Submit one turn — an option, or "not sure" |
| POST | `/chat/{session_id}/undo` | Rewind the transcript to an earlier turn |

**Catalog**

| Method | Path | Description |
|---|---|---|
| GET | `/products` | List products |
| GET | `/products/{sku}` | Get one product |
| POST | `/products` | Create a product |
| PUT | `/products/{sku}` | Update a product |
| DELETE | `/products/{sku}` | Delete a product |
| GET | `/products/{sku}/recommendations` | Alternatives + accessories for one SKU |

**History & admin**

| Method | Path | Description |
|---|---|---|
| GET | `/history` | List audit entries |
| DELETE | `/history/{entry_id}` | Delete an audit entry |
| GET | `/health` | Service health check |
| POST | `/admin/reload-model` | Hot-reload Brain 1/2 weights (API key required) |
| POST | `/admin/rebuild-index` | Rebuild FAISS indexes (API key required) |
| GET | `/admin/catalog-stats` | Catalog summary counts (API key required) |

---

## 11. Configuration Reference

All tuning lives in one typed, validated file — `backend/config/settings.py` — sourced from environment variables / `.env` via `pydantic-settings`. Selected keys:

| Setting | Default | Meaning |
|---|---|---|
| `CLASSIFIER_CONFIDENCE_THRESHOLD` | 0.5 | Below this, Brain 1 also searches the runner-up category |
| `CATEGORY_TRUST_THRESHOLD` | 0.75 | Below this, a no-match result states no category at all |
| `EMBEDDING_BACKEND` | dinov2 | Default Brain 2 embedding model |
| `CATEGORY_BACKENDS` | 3 overrides | Per-category backend routing (Section 5) |
| `EMBEDDING_TTA` | true | Average image + mirror embeddings |
| `NO_MATCH_THRESHOLDS` | dinov2: 0.48 · openclip: 0.86 | Per-backend refusal thresholds (Section 6) |
| `NO_MATCH_UNCERTAIN_MARGIN` | 0.04 | Added to the threshold when Brain 1 was unsure |
| `VECTOR_STORE` | faiss | `faiss` reads index files from disk; `pgvector` queries the products table directly |
| `LLM_BACKEND` | llamacpp | Brain 4 runtime — `llamacpp` (fast, quantised) or `transformers` (fallback) |
| `LLM_GGUF_FILE` | qwen2.5-1.5b-instruct-q4_k_m.gguf | ~1.1 GB, 4-bit quantised |
| `WARM_MODELS_ON_STARTUP` | true | Pay model load at boot (~50s), not on the first request |
| `MAX_UPLOAD_SIZE_MB` | 10 | Upload size limit |

---

## 12. Evaluation

Measured **leave-one-out** over the stored index vectors — each image is excluded from its own product's centroid before scoring, so nothing is ever matched against itself. 240 queries across 56 products in 10 categories.

| Category | Backend | Top-1 | Top-3 |
|---|---|---:|---:|
| Power Steering Pump | DINOv2 | 100.0% | 100.0% |
| Shock Absorber | OpenCLIP | 95.8% | 95.8% |
| Fuel Injector | DINOv2 | 93.1% | 100.0% |
| Air Filter | OpenCLIP | 90.9% | 100.0% |
| Oil Filter | DINOv2 | 85.0% | 100.0% |
| Suspension Bushing | DINOv2 | 83.3% | 95.8% |
| Throttle Body | DINOv2 | 82.8% | 93.1% |
| Brake Pads | DINOv2 | 77.4% | 96.8% |
| Wheel Hub Assembly | OpenCLIP | 76.2% | 100.0% |
| Exhaust Manifold | DINOv2 | 70.8% | 87.5% |

Where top-1 is weak but top-3 is near-perfect, the correct SKU was *found* and merely mis-ordered — several exhaust manifolds are the same assembly photographed from a different side. No embedding separates what a photograph doesn't distinguish; that gap is what the guided chat is for.

**How the number got here**

| # | Approach | Top-1 |
|---|---|---:|
| 1 | OpenCLIP baseline | 69.6% |
| 2 | DINOv2 | 73.2% |
| 3 | DINOv2 + OpenCLIP ensemble | 72.8% |
| 4 | Per-category routing | 77.5% |
| 5 | + centroid scoring, image cleaning | **85.0%** |

Reproduce: `cd partpilot && python scripts/analyze_index_vectors.py` (reads the built indexes, reproduces the table above in seconds)

---

## 13. Business Value

**What business problem does this solve?** Identifying an unlabelled car part today requires a human who has seen that exact part before — a scarce, shift-bound resource. PartPilot turns that lookup into a self-service, always-available step.

**Who benefits?** Parts-counter staff (fewer manual lookups), customers and DIY repairers (an instant answer instead of a trip), and the business itself (every identification also surfaces the accessory attach and the correct replacement, which a busy counter would otherwise have to remember to mention).

**How much time, cost, or effort does it save?** Minutes-to-hours of manual lookup collapses to seconds, with no dependency on a specific staff member's tenure or memory.

**Why is AI the right solution?** The only input is a photograph with no text or barcode — there is nothing for a rules engine or keyword search to key on. Visual similarity is the only mechanism that works on pixels alone.

| | Parts counter today | PartPilot |
|---|---|---|
| Who identifies it | Someone experienced | Anyone with a phone |
| Time to an answer | Minutes to hours | Seconds |
| Available | Opening hours | Always |
| Wrong-part risk | A judgement call | Priced: ~1.5% of correct matches given up to catch most impostors |

- **It refuses.** The false-answer rate is a calibrated number, not an accident.
- **It sells the rest of the basket.** Every identification also returns the superseding part and accessories — attach-rate a counter would otherwise have to remember.
- **It improves by being used.** Each confirmation records which SKU the customer settled on — labelled training data at zero labelling cost.

The catalog here is 56 products, so the figures above are indicative — the architecture doesn't change at tens of thousands of SKUs, only the index sizes.

---

## 14. Repository Layout

```
partpilot/
  backend/
    api/                # FastAPI routers — predict, chat, catalog, history, admin, health
    pipeline/
      brain1_classifier/    # EfficientNet category classifier
      brain2_similarity/    # embeddings, FAISS, per-category routing
      brain3_catalog/       # products, recommendations (PostgreSQL)
      brain4_reasoning/     # Qwen explanation (llama.cpp / transformers)
      chat/                 # guided-chat question engine + sessions
      audit/                # prediction trail + confirmations
      orchestrator.py       # wires the four stages together
    config/settings.py      # every threshold and model choice, in one file
    models/faiss/           # built indexes, one set per category
  scripts/            # index building, evaluation, threshold calibration
  datasets/           # catalog.csv (images git-ignored)
  docs/               # RUNNING.md, DEMO_GUIDE.md
frontend/             # Vite + React 19 + TypeScript + Tailwind v4
```

**Design rule:** Interfaces, not implementations — the orchestrator depends only on `*Interface` ABCs, so any brain can be swapped or mocked in isolation. Every tuning decision lives in `settings.py`, with the measurement that justified it written next to the number.

---

## 15. Setup & Run

### Demo mode — no backend, no database, no model download

The frontend ships with canned data, so the whole user journey runs on any machine with Node installed:

```
git clone https://github.com/zubariyasulekaz/Parts-Detection-Hackathon.git
cd Parts-Detection-Hackathon/frontend
npm install
cp .env.example .env        # VITE_API_MODE=mock is already the default
npm run dev                 # open http://localhost:5173
```

### Live pipeline — real models + database

Everything heavy already ships with the repo — the trained classifier, the built FAISS indexes, and all 56 products live in the shared database — so install → configure → run is the whole path. Only `DATABASE_URL` is needed and it is git-ignored by design.

```
cd partpilot
python -m venv .venv && .venv\Scripts\Activate.ps1     # Windows
pip install -r requirements.txt
cp .env.example .env        # set DATABASE_URL; leave the rest alone
python -m backend.main      # open http://localhost:8000/docs
```

Then point the frontend at it: set `VITE_API_MODE=live` and `VITE_CHAT_API=true` in `frontend/.env`. Startup takes ~50s while all four brains warm up (`WARM_MODELS_ON_STARTUP`) — deliberate, so the first uploader doesn't pay that cost.

Full setup, troubleshooting and index rebuilding: `partpilot/docs/RUNNING.md`.

### Suggested demo run order (fits the 20-minute demo window)

1. Problem statement + why AI (Section 1) — ~2 min
2. Architecture walkthrough using the pipeline diagram (Section 3) — ~4 min
3. Live prediction: a clear-winner photo → straight to the answer, no questions asked — ~3 min
4. Live prediction: a close-call photo → the guided chat opens and narrows it to one SKU — ~4 min
5. Live prediction: an out-of-catalog photo → the refusal case, and why it matters more than the two wins above — ~3 min
6. Business value + open-source model disclosure (Sections 13, 17) — ~4 min

Leaves 10 minutes for Q&A on threshold calibration (Section 6) and the accuracy methodology (Section 12) — the two areas most likely to draw technical follow-up questions.

---

## 16. Future Enhancements

Ordered by what the measurements say is actually limiting the system, not by what is interesting to build.

| # | Next step | Why it's next |
|---|---|---|
| 1 | Fine-tune the embedding on the catalog | Exhaust manifolds sit at 70.8% top-1 but 87.5% top-3 — the right SKU is found and mis-ordered; metric learning on the catalog can separate what a general encoder can't. |
| 2 | Ask for a second photo instead of guessing | Cheaper and more honest than a re-ranker when one angle can't distinguish two SKUs; the disambiguation flow already exists to hang it on. |
| 3 | Feed confirmations back into ranking | The audit trail already captures which SKU the user settled on — the highest-value signal in the system, currently unused for ranking. |
| 4 | Approximate search at catalog scale | `IndexFlatIP` is exact and free at 56 products; past ~10⁵ vectors per category it becomes IVF/HNSW behind the same index interface. |
| 5 | Re-calibrate thresholds on real traffic | Thresholds were tuned on catalog photos; phone photos in a garage will shift both distributions. |
| 6 | Persist chat sessions outside the process | Sessions currently live in process memory; Redis lets a conversation survive a restart and scale across workers. |
| 7 | ERP / CRM / PIM connector | The REST API (Section 10) is already the right shape for this; next step is an adapter, not a redesign. |

---

## 17. AI Transparency & Model Disclosure

Every AI component in PartPilot, in full:

| Component | Model | Publisher | License class | Runs where |
|---|---|---|---|---|
| Category classifier | EfficientNetB0 (ImageNet-pretrained backbone, fine-tuned head) | Google (backbone) | Open weight | Inference: locally, CPU. Head was fine-tuned on Kaggle Notebooks to use their free GPU tier — training-time only, not a runtime dependency. |
| Visual similarity (7 categories) | DINOv2 (`facebook/dinov2-base`) | Meta AI | Open weight | Locally |
| Visual similarity (3 categories) | OpenCLIP (`ViT-B-32`, openai weights) | LAION / OpenAI-weights via open_clip | Open weight | Locally |
| Visual similarity (implemented, not deployed) | SigLIP (`google/siglip-base-patch16-224`) | Google | Open weight | Supported by the embedding-backend interface; none of the 10 built category indexes currently use it |
| Background segmentation | rembg | Open-source project (ONNX) | Open source | Locally |
| Vector search | FAISS `IndexFlatIP` | Meta AI | Open source | Locally |
| Explanation / reasoning (optional) | Qwen2.5-1.5B-Instruct, Q4_K_M GGUF, served via llama.cpp | Alibaba Cloud (Qwen team) | Open weight | Locally |
| Catalog image generation (offline, data prep only — not in the prediction path) | Google Gemini (image generation) | Google | Proprietary, hosted API | Google's cloud, one-time, at dataset-build time only |

**Every model actually exercised by the live prediction path is open weight and self-hostable, with zero proprietary AI API calls at inference time**: the classifier, DINOv2, OpenCLIP, rembg, FAISS, and Qwen2.5 — six components, running in-process on commodity CPU hardware, deployable entirely inside a customer's own network with no external AI-service egress. `LLM_BACKEND` also supports a `transformers` fallback runtime for Brain 4, itself running the same open-weight Qwen checkpoint.

The one proprietary AI service used anywhere in this project is **Google Gemini**, and it was used exactly once, offline, to generate a minority of catalog product images where a manufacturer photo wasn't available (Section 9). It has no code path into the running application and could be removed from the dataset-build tooling with no change to the pipeline.

PostgreSQL (Section 8) is the one external *runtime* dependency in this build, and it is not an AI service — a plain relational store, swappable for any self-hosted Postgres instance.

---

*The models decide which part. The database decides what is true about it.*
