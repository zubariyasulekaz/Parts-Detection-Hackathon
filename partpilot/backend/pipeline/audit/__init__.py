"""Prediction audit trail.

Persists what the pipeline answered for each `/predict` run — category,
confidence, the candidate SKUs it ranked, and a thumbnail of the upload
— so past predictions can be reviewed after the fact. Nothing here is
part of the prediction itself: recording is best-effort and must never
cost a caller its answer (see `service.py`).
"""
