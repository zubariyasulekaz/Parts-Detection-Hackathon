import os
import shutil
from imagededup.methods import CNN

# Root dataset folder
DATASET_ROOT = "dataset"

# Output folder
OUTPUT_ROOT = "duplicate_review"

# Similarity threshold
THRESHOLD = 0.90

cnn = CNN()

os.makedirs(OUTPUT_ROOT, exist_ok=True)

for category in os.listdir(DATASET_ROOT):

    category_path = os.path.join(DATASET_ROOT, category)

    if not os.path.isdir(category_path):
        continue

    print(f"\nProcessing {category}...")

    encodings = cnn.encode_images(image_dir=category_path)

    duplicates = cnn.find_duplicates(
        encoding_map=encodings,
        min_similarity_threshold=THRESHOLD,
    )

    output_category = os.path.join(OUTPUT_ROOT, category)
    os.makedirs(output_category, exist_ok=True)

    processed = set()
    group_number = 1

    for img, similar_list in duplicates.items():

        # Skip if already part of another group
        if str(img) in processed:
            continue

        if not similar_list:
            continue

        # Create one group containing the reference image + all similar images
        group = [str(img)] + [str(x) for x in similar_list]

        # Remove duplicates while preserving order
        group = list(dict.fromkeys(group))

        group_folder = os.path.join(
            output_category,
            f"group_{group_number:03d}"
        )
        os.makedirs(group_folder, exist_ok=True)

        for filename in group:
            src = os.path.join(category_path, filename)

            if os.path.exists(src):
                shutil.copy2(src, os.path.join(group_folder, filename))
                processed.add(filename)

        print(f"Created group_{group_number:03d} ({len(group)} images)")

        group_number += 1

