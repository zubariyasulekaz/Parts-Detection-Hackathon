import os
import random
import shutil

# -----------------------------
# SETTINGS
# -----------------------------

SOURCE_DIR = "dataset"
OUTPUT_DIR = "split_dataset"

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Makes the random split reproducible
RANDOM_SEED = 42

# Image extensions to include
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp"
)

# -----------------------------
# CHECK RATIOS
# -----------------------------

assert TRAIN_RATIO + VAL_RATIO + TEST_RATIO == 1.0, \
    "Train, validation, and test ratios must add up to 1.0"

random.seed(RANDOM_SEED)

# -----------------------------
# CREATE OUTPUT FOLDERS
# -----------------------------

for split in ["train", "val", "test"]:
    os.makedirs(
        os.path.join(OUTPUT_DIR, split),
        exist_ok=True
    )

# -----------------------------
# SPLIT EACH CATEGORY
# -----------------------------

categories = sorted(
    folder
    for folder in os.listdir(SOURCE_DIR)
    if os.path.isdir(os.path.join(SOURCE_DIR, folder))
)

print("\nStarting dataset split...\n")

total_train = 0
total_val = 0
total_test = 0

for category in categories:

    category_path = os.path.join(
        SOURCE_DIR,
        category
    )

    # Get only image files
    images = [
        file
        for file in os.listdir(category_path)
        if file.lower().endswith(IMAGE_EXTENSIONS)
    ]

    # Randomly shuffle images
    random.shuffle(images)

    total_images = len(images)

    # Calculate split positions
    train_count = int(
        total_images * TRAIN_RATIO
    )

    val_count = int(
        total_images * VAL_RATIO
    )

    # Remaining images go to test
    test_count = (
        total_images
        - train_count
        - val_count
    )

    # Split the list
    train_images = images[:train_count]

    val_images = images[
        train_count:
        train_count + val_count
    ]

    test_images = images[
        train_count + val_count:
    ]

    # Create category folders
    for split in ["train", "val", "test"]:

        os.makedirs(
            os.path.join(
                OUTPUT_DIR,
                split,
                category
            ),
            exist_ok=True
        )

    # Copy training images
    for image in train_images:

        source = os.path.join(
            category_path,
            image
        )

        destination = os.path.join(
            OUTPUT_DIR,
            "train",
            category,
            image
        )

        shutil.copy2(
            source,
            destination
        )

    # Copy validation images
    for image in val_images:

        source = os.path.join(
            category_path,
            image
        )

        destination = os.path.join(
            OUTPUT_DIR,
            "val",
            category,
            image
        )

        shutil.copy2(
            source,
            destination
        )

    # Copy test images
    for image in test_images:

        source = os.path.join(
            category_path,
            image
        )

        destination = os.path.join(
            OUTPUT_DIR,
            "test",
            category,
            image
        )

        shutil.copy2(
            source,
            destination
        )

    # Update totals
    total_train += len(train_images)
    total_val += len(val_images)
    total_test += len(test_images)

    # Print category summary
    print(
        f"{category:<30}"
        f"Total: {total_images:>4} | "
        f"Train: {len(train_images):>4} | "
        f"Val: {len(val_images):>4} | "
        f"Test: {len(test_images):>4}"
    )

# -----------------------------
# FINAL SUMMARY
# -----------------------------

print("\n" + "=" * 75)

print(
    f"{'TOTAL':<30}"
    f"Train: {total_train:>5} | "
    f"Val: {total_val:>5} | "
    f"Test: {total_test:>5}"
)

print("=" * 75)

print(
    f"\nDataset successfully split into:"
    f"\n{OUTPUT_DIR}/"
)