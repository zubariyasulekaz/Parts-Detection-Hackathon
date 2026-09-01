"""Reading a part number off the photograph, when the picture alone fails.

A customer holding a part they were sent in error is usually holding its
packaging too, with a printed label facing them. The image search cannot use
that label - a bagged part inside a cardboard box is, visually, a cardboard
box - but the label carries the answer in plain text.

Measured on the 83 hand-taken photographs: 18% contain any readable text and
**2% contain a real catalogue part number**. That is far too narrow to be a
general accuracy fix, and it is not offered as one. What earns its place is
what happens on those 2%: the worst result in the whole set, a boxed part
matched to a holding-tank treatment at 0.29, carries "0020500" on its label at
1.00 OCR confidence. A confident wrong answer becomes a certain right one.

Two rules keep it safe:

* **It only runs when the picture has already failed.** Above
  ``OCR_MAX_SCORE`` the visual match is trusted and no OCR happens, so the
  common case pays none of the 0.7-2.0s this costs.
* **A token only counts if it matches a catalogue part number exactly**, after
  punctuation is stripped from both sides. No fuzzy matching, no prefixes: the
  evidence is either unambiguous or it is discarded.

Every failure path returns "nothing found" rather than raising. OCR is an
optional improvement on a result that already exists, and must never be able
to turn a working search into a 500.
"""

import re
from threading import Lock
from typing import Any

import numpy as np
from PIL import Image

from backend.core.logging import get_logger

logger = get_logger(__name__)

# Shorter than this and a token is a size, a quantity or a fragment - "2 in",
# "8 OZ", "10K" - which collide with real part numbers by accident.
MIN_TOKEN_LENGTH = 4

_engine: Any | None = None
_engine_failed = False
_lock = Lock()


def _get_engine() -> Any | None:
    """The OCR engine, loaded once on first use.

    Loading costs about a second and only happens on a request that is already
    going badly, so it is not worth warming at startup. A failed import is
    remembered so an environment without the package retries nothing.
    """
    global _engine, _engine_failed
    if _engine is not None or _engine_failed:
        return _engine
    with _lock:
        if _engine is not None or _engine_failed:
            return _engine
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415

            _engine = RapidOCR()
            logger.info("Part-number OCR engine loaded")
        except Exception as exc:  # noqa: BLE001
            _engine_failed = True
            logger.warning("Part-number OCR unavailable, falling back to the visual match: %s", exc)
    return _engine


def normalise(value: str) -> str:
    """``"021-256-10"`` -> ``"02125610"``.

    Catalogue part numbers are punctuated inconsistently between the database,
    the printed label and whatever OCR makes of it, so both sides are reduced
    to letters and digits before they are compared.
    """
    return re.sub(r"[^A-Z0-9]", "", value.upper())


# A label routinely names more than one product: its own number, and the
# number it supersedes. The real label behind this feature reads
# "Buyers / 0020500 / REPLACES 2 PW22 PRO-WNG8", and both 0020500 and PW-22 are
# real catalogue products. A line introduced by one of these words is talking
# about a *different* part, so its numbers are tried only after everything else.
CROSS_REFERENCE = re.compile(
    r"\b(REPLACE[SD]?|SUPERSED|SUBSTITUT|FORMERLY|WAS|FITS|USE\s+WITH)\b", re.I
)


def read_candidate_tokens(image: Image.Image, min_confidence: float = 0.6) -> list[str]:
    """Normalised tokens read off the photograph, best candidate first.

    Ordered so the caller can take the first that names a product:

    1. numbers from lines that are not cross-references, longest first
    2. numbers from "replaces ..." lines, longest first

    Longest first within each group because a part number is more specific than
    the quantities and sizes printed beside it. Returns an empty list on any
    failure, including a missing engine.
    """
    engine = _get_engine()
    if engine is None:
        return []
    try:
        result, _ = engine(np.asarray(image.convert("RGB")))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Part-number OCR failed on this image: %s", exc)
        return []

    primary: set[str] = set()
    secondary: set[str] = set()
    for entry in result or []:
        # RapidOCR yields (box, text, confidence).
        if len(entry) < 3:
            continue
        _, text, confidence = entry[0], entry[1], entry[2]
        try:
            if float(confidence) < min_confidence:
                continue
        except (TypeError, ValueError):
            continue
        line = str(text)
        bucket = secondary if CROSS_REFERENCE.search(line) else primary
        for piece in re.split(r"\s+", line):
            key = normalise(piece)
            if len(key) >= MIN_TOKEN_LENGTH:
                bucket.add(key)

    secondary -= primary
    order = sorted(primary, key=len, reverse=True) + sorted(secondary, key=len, reverse=True)
    return order
