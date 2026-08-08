# PartPilot

Identify a car part from one photograph, then tell the user what it fits, what
replaces it, and what goes with it.

Upload a picture of a part. PartPilot predicts its category, searches a
catalog-scoped vector index for the closest stocked SKUs, resolves the winner to
full product data, and returns a ranked answer - or refuses, when nothing in the
catalog is close enough to name honestly.

## The pipeline

| Stage | Does | Built with |
|---|---|---|
| Brain 1 | Predicts the part category from the image | Fine-tuned EfficientNet |
| Brain 2 | Embeds the image and finds visually similar SKUs | DINOv2 / OpenCLIP + FAISS |
| Brain 3 | Resolves a SKU to catalog data, fitment and relationships | PostgreSQL |
| Brain 4 | Explains the match in plain language (optional) | Qwen2.5-1.5B-Instruct |

Brain 2 does not use one model for everything. DINOv2 wins overall, but three
categories benchmarked far better on OpenCLIP and are routed to it per category
(`Settings.CATEGORY_BACKENDS`). Each SKU is scored by cosine against the
L2-normalized centroid of its image vectors, which beat max-over-images on this
catalog - with a handful of photos per product, one lucky angle otherwise
promotes the wrong SKU.

## Refusing to guess

Most of the interesting work is in deciding when *not* to answer.

Every backend has its own no-match threshold, calibrated against measured
correct-match and impostor score distributions rather than picked by feel. Below
it, the pipeline returns "no catalog match" and withholds the product entirely:
no top SKU, no recommendations, and nothing selectable in the UI. If Brain 1 was
also unsure of the category, the bar rises further - two weak signals must not
add up to a confident answer.

The cost is explicit and measured: the thresholds sit at roughly 1.5% of correct
matches rejected, in exchange for catching most impostors. Recommending the
wrong part is worse than admitting the catalog does not have it.

## Repository layout

```
partpilot/          FastAPI backend, models, datasets, evaluation scripts
  backend/          API, pipeline (brains 1-4), schemas, tests
  scripts/          index building, evaluation, threshold calibration
  docs/             RUNNING.md (setup), DEMO_GUIDE.md (demo script)
frontend/           Vite + React 19 + TypeScript + Tailwind v4 client
```

## Getting started

Backend setup, configuration and troubleshooting: [`partpilot/docs/RUNNING.md`](partpilot/docs/RUNNING.md).
Frontend usage: [`frontend/README.md`](frontend/README.md).
Running the demo: [`partpilot/docs/DEMO_GUIDE.md`](partpilot/docs/DEMO_GUIDE.md).

The frontend runs standalone with `VITE_API_MODE=mock`, so the whole journey is
browsable without a backend or a database.

## Scale

The catalog is currently 56 products across 10 categories, which is enough to
calibrate against but small enough that the accuracy figures should be read as
indicative. Product metadata is kept separate from the visual index so the same
architecture extends to a customer catalog of tens of thousands of SKUs.
