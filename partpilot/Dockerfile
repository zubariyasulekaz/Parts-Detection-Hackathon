FROM python:3.12-slim

# opencv/onnxruntime/tensorflow need these system libs even in "headless"
# mode - without them the import fails with a missing libGL.so error.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch first: the default PyPI wheel bundles CUDA and is 3-4x
# larger, which burns through HF Spaces' free-tier build time/storage.
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Docker Spaces route traffic to port 7860.
ENV HOST=0.0.0.0
ENV PORT=7860
EXPOSE 7860

CMD ["python", "-m", "backend.main"]
