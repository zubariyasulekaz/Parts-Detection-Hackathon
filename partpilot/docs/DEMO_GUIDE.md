# PartPilot - Demo Setup Guide (Google Colab)

This guide walks you through running the **PartPilot** parts-detection demo end to end
in Google Colab. Follow the steps in order. Copy each cell into a Colab notebook (or use
the provided `partpilot/notebooks/partpilot_colab_demo.ipynb`) and run them top to bottom.

**What the demo does:** you upload a photo of a car part, and the system
(1) classifies the category, (2) finds the most visually similar catalog parts, and
(3) returns the matching product plus recommended alternatives.

---

## Before you start - what you need

| Item | How you get it |
|------|----------------|
| **1. Access to the GitHub repo** | The repo is **private**. Ask the owner (`zubariyasulekaz`) to add you as a collaborator, then accept the email invite. |
| **2. A GitHub Personal Access Token** | Needed to clone a private repo in Colab. See "Step 0" below. |
| **3. The dataset images zip** | The images are **not** in the repo. The team will share `images.zip` (via Google Drive or direct download). Inside it must look like `images/<SKU>/...`. |
| **4. A Google account** | To run Google Colab (free). |

> ⚠️ Do **not** skip the images zip. The repo has the code and `catalog.csv`, but the
> actual part photos are git-ignored and must be uploaded manually.

---

## Step 0 - Create your GitHub token (one time)

1. Go to **https://github.com/settings/tokens**
2. Click **Tokens (classic) → Generate new token (classic)**
3. Name it `colab`, tick the **`repo`** checkbox (gives read access to private repos)
4. Click **Generate token** and **copy** it (looks like `ghp_xxxxxxxx`). You only see it once.

---

## Step 1 - Clone the repo

```python
import os, sys
from getpass import getpass

TOKEN = getpass('Paste your GitHub token: ')   # hidden input

%cd /content
!rm -rf Parts-Detection-Hackathon
!git clone -q https://{TOKEN}@github.com/zubariyasulekaz/Parts-Detection-Hackathon.git
%cd Parts-Detection-Hackathon
!git checkout -q demo
%cd partpilot

PARTPILOT = '/content/Parts-Detection-Hackathon/partpilot'
sys.path.insert(0, PARTPILOT)
print('Working dir:', os.getcwd())
```

✅ Expected: `Working dir: /content/Parts-Detection-Hackathon/partpilot`

---

## Step 2 - Upload the dataset images

Zip structure must be `images/<SKU>/<photo files>` (e.g. `images/DE1439/DE1439-02.avif`).
Zip the **`images`** folder itself - not the folder above it.

```python
import zipfile, os, shutil

shutil.rmtree('datasets/images', ignore_errors=True)

from google.colab import files
uploaded = files.upload()                       # choose your images zip
zip_name = list(uploaded.keys())[-1]

with zipfile.ZipFile(zip_name) as z:
    z.extractall('datasets')                    # -> datasets/images/<SKU>/...

skus = sorted(os.listdir('datasets/images'))
print(f'{len(skus)} SKU folders:', skus)
```

✅ Expected: a list of SKU folders like `['3978', 'DE1439', 'DG184', ...]`

> If you get `FileNotFoundError: datasets/images`, your zip is nested differently.
> See **Troubleshooting → Wrong zip structure**.

---

## Step 3 - Convert images to JPG

The photos are in **`.avif`** format, which TensorFlow and the FAISS builder cannot read.
This cell converts them to `.jpg` **in place**.

```python
!pip install -q pillow-avif-plugin

import pathlib
from PIL import Image
import pillow_avif   # registers .avif support in PIL

IMAGES = pathlib.Path('datasets/images')
converted = 0
for sku_dir in IMAGES.iterdir():
    if not sku_dir.is_dir():
        continue
    for img in list(sku_dir.glob('*')):
        if img.suffix.lower() in {'.avif', '.webp'}:
            try:
                Image.open(img).convert('RGB').save(
                    sku_dir / f'{img.stem}.jpg', 'JPEG', quality=95)
                img.unlink()                    # remove the original .avif
                converted += 1
            except Exception as e:
                print('[skip]', img, e)
print(f'Converted {converted} images to .jpg')
```

✅ Expected: `Converted N images to .jpg`

---

## Step 4 - Install dependencies

```python
!pip install -q pydantic-settings==2.7.1 python-dotenv==1.0.1 \
    open_clip_torch==2.29.0 faiss-cpu==1.9.0.post1 rembg==2.0.60
```

> Colab already has TensorFlow, torch, NumPy, Pillow and OpenCV, so only the
> remaining packages are installed here.

---

## Step 5 - Train Brain 1 (category classifier)

Trains an EfficientNetB0 transfer-learning model to tell part categories apart, and
saves it where the backend expects.

```python
import csv, json, shutil, pathlib
import tensorflow as tf
from tensorflow import keras
from PIL import Image
import pillow_avif

ROOT = pathlib.Path.cwd()  # .../partpilot

# --- group SKU images into category folders using catalog.csv ---
sku_category = {}
with open('datasets/catalog.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        sku_category[row['sku']] = row['category'].strip()

TRAIN_DIR = pathlib.Path('/content/brain1_dataset')
shutil.rmtree(TRAIN_DIR, ignore_errors=True)
for sku, category in sku_category.items():
    src = ROOT / 'datasets' / 'images' / sku
    if not src.is_dir():
        continue
    dst = TRAIN_DIR / category
    dst.mkdir(parents=True, exist_ok=True)
    for img in src.glob('*'):
        if img.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            shutil.copy(img, dst / f'{sku}_{img.name}')
print('Images per category:',
      {p.name: len(list(p.glob('*'))) for p in TRAIN_DIR.iterdir()})

# --- datasets ---
IMG_SIZE = (224, 224)
BATCH = 8
train_ds = tf.keras.utils.image_dataset_from_directory(
    TRAIN_DIR, validation_split=0.2, subset='training', seed=42,
    image_size=IMG_SIZE, batch_size=BATCH)
val_ds = tf.keras.utils.image_dataset_from_directory(
    TRAIN_DIR, validation_split=0.2, subset='validation', seed=42,
    image_size=IMG_SIZE, batch_size=BATCH)
class_names = train_ds.class_names
print('Classes (output order):', class_names)

# --- model (EfficientNetB0 transfer learning) ---
aug = keras.Sequential([
    keras.layers.RandomFlip('horizontal'),
    keras.layers.RandomRotation(0.1),
    keras.layers.RandomZoom(0.1),
])
base = tf.keras.applications.EfficientNetB0(
    include_top=False, weights='imagenet', input_shape=(224, 224, 3))
base.trainable = False

inp = keras.Input((224, 224, 3))
x = aug(inp)
x = tf.keras.applications.efficientnet.preprocess_input(x)
x = base(x, training=False)
x = keras.layers.GlobalAveragePooling2D()(x)
x = keras.layers.Dropout(0.2)(x)
out = keras.layers.Dense(len(class_names), activation='softmax')(x)
model = keras.Model(inp, out)
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])
model.fit(train_ds, validation_data=val_ds, epochs=15)

# --- save model + labels where the backend expects them ---
out_dir = ROOT / 'backend' / 'models' / 'classifier'
out_dir.mkdir(parents=True, exist_ok=True)
model.save(out_dir / 'brain1_classifier.keras')
(out_dir / 'labels.json').write_text(json.dumps(class_names))
print('Saved brain1_classifier.keras + labels.json ->', out_dir)
```

✅ Expected: training runs for 15 epochs and prints
`Saved brain1_classifier.keras + labels.json -> .../classifier`

---

## Step 6 - Build Brain 2 (similarity search indexes)

Embeds each catalog image with OpenCLIP and builds one FAISS index per category.

```python
!python scripts/build_faiss_indexes.py --remove-bg
import os
print('Indexes:', os.listdir('backend/models/faiss'))
```

✅ Expected: `Indexes:` lists `brake_pads.faiss`, `oil_filter.faiss` and their
`.ids.json` files.

> First run downloads the CLIP weights (~600 MB) and the rembg model (~176 MB).
> This is normal and only happens once per session.

---

## Step 7 - Run the demo (upload a photo, get the match)

```python
import os, sys, io, importlib
from PIL import Image
from google.colab import files

# make this cell self-contained (works even after a runtime restart)
os.chdir('/content/Parts-Detection-Hackathon/partpilot')
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())
importlib.invalidate_caches()          # clears stale import cache

from backend.api.dependencies import get_orchestrator

uploaded = files.upload()              # choose a test part photo
name = list(uploaded.keys())[0]
img = Image.open(io.BytesIO(uploaded[name])).convert('RGB')

orchestrator = get_orchestrator()
result = orchestrator.run(img, top_k=5)
pred = result.prediction

print(f'Predicted category : {pred.predicted_category}  (confidence {pred.confidence:.1%})')
print(f'Search time        : {pred.search_time_ms:.0f} ms')
print('Top matches:')
for r in pred.results:
    print(f'   {r.sku:10}  similarity {r.similarity_score:.3f}')
if result.product:
    print(f'\nBest match product : {result.product.product_name}  (SKU {result.product.sku})')
if result.recommendation and result.recommendation.alternatives:
    print('Alternatives       :', [p.sku for p in result.recommendation.alternatives])
```

✅ Expected (example):
```
Predicted category : Oil Filter  (confidence 98.3%)
Top matches:
   3978        similarity 0.848
   S45011      similarity 0.832
   S45023      similarity 0.784
Best match product : Engine Oil Filter  (SKU 3978)
Alternatives       : ['S45011']
```

> The **first** prediction is slow (~20 s) because it loads the CLIP + rembg models.
> Run the cell again with another photo and it will be much faster.

---

## Troubleshooting

**`fatal: could not read Username for 'https://github.com'`**
The repo is private and your token is missing/wrong. Redo Step 0 and Step 1 with a
valid token that has the `repo` scope.

**`FileNotFoundError: datasets/images` (wrong zip structure)**
Your zip is nested differently. Inspect it and normalize:
```python
import os
for root, dirs, files in os.walk('datasets'):
    if root.count(os.sep) <= 3:
        print(root, '->', dirs[:8], f'({len(files)} files)')
```
The `<SKU>` folders (with image files inside) must end up at `datasets/images/<SKU>/`.
Move/rename folders until that's true, then continue from Step 3.

**`ValueError: No images found` / `Images per category: {..: 0}`**
The images are still `.avif`. Run **Step 3** (convert to JPG) before Step 5.

**`InvalidImage: rembg is not installed` or `cannot import name '_center' from numpy`**
A NumPy-in-memory vs on-disk mismatch after installing packages. Fix:
1. `!pip install -q "numpy==2.1.3"`
2. Colab menu → **Runtime → Restart runtime**
3. Re-run from **Step 1** (files on disk survive a restart; only re-establish the path).

**`ModuleNotFoundError: No module named 'backend'`**
The `sys.path` / import cache is stale (common after a restart). Make sure the cell
starts with:
```python
import os, sys, importlib
os.chdir('/content/Parts-Detection-Hackathon/partpilot')
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())
importlib.invalidate_caches()
```
Step 7's cell already includes this.

---

## Notes

- **Small dataset:** with only a few dozen images the accuracy numbers are indicative,
  not production-grade. The goal is a working end-to-end demo.
- **Models are rebuilt each session.** Colab wipes everything on a full disconnect, so
  Steps 5–6 must be re-run when you start a fresh session (unless the team shares the
  pre-built `backend/models/` folder - then you can skip straight to Step 7).
- **Brain 4 (LLM reasoning)** is optional and not required for this demo.
```
