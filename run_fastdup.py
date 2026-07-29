import fastdup

# Analyze your dataset
fd = fastdup.create(
    input_dir="dataset",
    work_dir="fastdup_output"
)

fd.run()