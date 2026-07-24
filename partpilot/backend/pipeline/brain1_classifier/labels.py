"""Category label set for the Brain 1 classifier.

TODO: Replace `CATEGORY_LABELS` with the final label list produced during
training (kept in sync with the model's output layer ordering), likely
loaded from a `labels.json` artifact alongside the model checkpoint
rather than hardcoded here.
"""

from backend.core.constants import CATEGORY_ALIASES, PLACEHOLDER_CATEGORY_LABELS

CATEGORY_LABELS: list[str] = PLACEHOLDER_CATEGORY_LABELS


def resolve_catalog_category(label: str) -> str:
    """Map a classifier label to the catalog category name.

    Uses `CATEGORY_ALIASES` (keyed by slug) so classifier labels like
    ``"brake_pad"`` resolve to the catalog category ``"Brake Pads"``. If no
    alias is registered, the original label is returned unchanged (its slug
    is still what Brain 2 uses to locate the FAISS index).

    Args:
        label: The raw category label predicted by Brain 1.

    Returns:
        The corresponding catalog category, or `label` if none is mapped.
    """
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return CATEGORY_ALIASES.get(slug, label)

# index -> label, used to decode raw model logits/argmax output.
INDEX_TO_LABEL: dict[int, str] = dict(enumerate(CATEGORY_LABELS))
LABEL_TO_INDEX: dict[str, int] = {label: idx for idx, label in INDEX_TO_LABEL.items()}


def decode_label(index: int) -> str:
    """Map a model output index to its category label.

    Args:
        index: Argmax index of the classifier's output layer.

    Returns:
        The corresponding category label.

    Raises:
        backend.core.exceptions.CategoryNotFound: If `index` is out of range.
    """
    from backend.core.exceptions import CategoryNotFound

    try:
        return INDEX_TO_LABEL[index]
    except KeyError as exc:
        raise CategoryNotFound(f"No category registered for index {index}") from exc
