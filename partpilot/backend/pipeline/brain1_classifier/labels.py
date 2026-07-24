"""Category label set for the Brain 1 classifier.

TODO: Replace `CATEGORY_LABELS` with the final label list produced during
training (kept in sync with the model's output layer ordering), likely
loaded from a `labels.json` artifact alongside the model checkpoint
rather than hardcoded here.
"""

from backend.core.constants import PLACEHOLDER_CATEGORY_LABELS

CATEGORY_LABELS: list[str] = PLACEHOLDER_CATEGORY_LABELS

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
