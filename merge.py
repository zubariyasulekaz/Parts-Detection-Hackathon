import os
import shutil
import re

# Paths
dataset1 = r"C:\Users\Zubariya Suleka\Documents\parts_pilot_hackaton\dataset_2"
dataset2 = r"C:\Users\Zubariya Suleka\Documents\parts_pilot_hackaton\merged_dataset"
output = r"C:\Users\Zubariya Suleka\Documents\parts_pilot_hackaton\full_dataset"

os.makedirs(output, exist_ok=True)

# Regex to match names like oil_filter_12.jpg
pattern = re.compile(r"(.+?)_(\d+)(\.[^.]+)$")

for dataset in [dataset1, dataset2]:
    for category in os.listdir(dataset):
        src_folder = os.path.join(dataset, category)

        if not os.path.isdir(src_folder):
            continue

        dst_folder = os.path.join(output, category)
        os.makedirs(dst_folder, exist_ok=True)

        for file in os.listdir(src_folder):
            src_file = os.path.join(src_folder, file)

            if not os.path.isfile(src_file):
                continue

            match = pattern.match(file)

            if match:
                prefix, num, ext = match.groups()

                # Find the next available number
                existing_nums = []
                for existing in os.listdir(dst_folder):
                    m = pattern.match(existing)
                    if m and m.group(1) == prefix:
                        existing_nums.append(int(m.group(2)))

                next_num = max(existing_nums, default=0) + 1
                new_name = f"{prefix}_{next_num}{ext}"

            else:
                # If filename doesn't follow prefix_number.ext
                base, ext = os.path.splitext(file)
                new_name = file
                counter = 1
                while os.path.exists(os.path.join(dst_folder, new_name)):
                    new_name = f"{base}_{counter}{ext}"
                    counter += 1

            shutil.copy2(src_file, os.path.join(dst_folder, new_name))

print("Datasets merged successfully!")