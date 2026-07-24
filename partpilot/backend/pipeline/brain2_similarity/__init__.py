"""Brain 2: Similarity Search.

Given a category and an image, generates an OpenCLIP embedding and
searches a category-specific FAISS index for the top-K matching SKUs.
See `interfaces.py` for the contract other pipeline stages depend on.
"""
