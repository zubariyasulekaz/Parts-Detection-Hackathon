"""Geometric verification: does a candidate actually match the query, structurally?

The embedding search ranks well but cannot tell a right answer from a wrong one
by score. Measured on RigidHitch's own data, correct matches score 0.955 and
wrong ones 0.877 - overlapping badly enough that no cutoff separates them, which
is why a similarity threshold rejecting 9% of correct answers still catches only
57% of impostors.

Keypoint matching answers a different question: not "do these look alike" but
"do the same physical features appear in the same spatial arrangement". On the
same data that separates cleanly - a median of 86 inliers when correct against
11 when wrong.

SIFT finds distinctive points, descriptors are matched with Lowe's ratio test,
and RANSAC then keeps only the matches consistent with a single homography. That
last step is what makes this structural rather than another appearance score: a
wrong part can produce plenty of individually plausible matches, but they will
not agree on one transform.

Uses OpenCV, already present as a rembg dependency - no new model, no download,
no network at query time.

Run:
    python scripts/rigidhitch_geometric_verify.py query.jpg candidate.jpg
    python scripts/rigidhitch_geometric_verify.py --measure    # against the audit data
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Below this many RANSAC inliers a candidate is not structurally supported.
# From the measured trade-off: 20 keeps 70% of correct matches while rejecting
# 82% of wrong ones; 30 keeps 65% and rejects 95%.
INLIER_THRESHOLD = 20
# Lowe's ratio test. A descriptor whose best match is barely better than its
# second-best is ambiguous, and on a catalogue full of near-identical parts that
# ambiguity is the norm - so this does a lot of work here.
RATIO = 0.75
MAX_KEYPOINTS = 2000
# RANSAC needs 4 correspondences to fit a homography at all.
MIN_FOR_HOMOGRAPHY = 4


@dataclass
class Verification:
    inliers: int
    matches: int
    keypoints_query: int
    keypoints_candidate: int

    @property
    def supported(self) -> bool:
        return self.inliers >= INLIER_THRESHOLD

    @property
    def inlier_ratio(self) -> float:
        return self.inliers / self.matches if self.matches else 0.0


def _load_gray(path: Path, max_side: int = 640) -> np.ndarray:
    """Grayscale, downscaled - SIFT is scale-invariant, so full resolution only costs time."""
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise SystemExit(f"could not read image: {path}")
    scale = max_side / max(image.shape[:2])
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image


def verify(query: np.ndarray, candidate: np.ndarray) -> Verification:
    """Count RANSAC-consistent keypoint matches between two grayscale images."""
    sift = cv2.SIFT_create(nfeatures=MAX_KEYPOINTS)
    kp_q, des_q = sift.detectAndCompute(query, None)
    kp_c, des_c = sift.detectAndCompute(candidate, None)

    # A featureless image (a plain painted surface, a silhouette) yields nothing
    # to match. That is a real outcome, not an error: it means this pair cannot
    # be structurally verified either way.
    if des_q is None or des_c is None or len(kp_q) < 2 or len(kp_c) < 2:
        return Verification(0, 0, len(kp_q or []), len(kp_c or []))

    matcher = cv2.BFMatcher()
    good = [
        m for m, n in matcher.knnMatch(des_q, des_c, k=2)
        if m.distance < RATIO * n.distance
    ]
    if len(good) < MIN_FOR_HOMOGRAPHY:
        return Verification(0, len(good), len(kp_q), len(kp_c))

    src = np.float32([kp_q[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_c[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)

    inliers = int(mask.sum()) if mask is not None else 0
    return Verification(inliers, len(good), len(kp_q), len(kp_c))


def verify_paths(query_path: Path, candidate_path: Path) -> Verification:
    return verify(_load_gray(query_path), _load_gray(candidate_path))


def measure_against_audit(audit_csv: Path) -> None:
    """Reproduce the separation from the existing audit rows.

    Confirms this implementation lands in the same place as the prototype that
    produced those numbers, before it is trusted anywhere else.
    """
    rows = list(csv.DictReader(audit_csv.open()))
    correct = np.array([float(r["inliers"]) for r in rows if r["is_correct"] == "1"])
    wrong = np.array([float(r["inliers"]) for r in rows if r["is_correct"] == "0"])

    print(f"audit rows: {len(rows):,}  ({len(correct):,} correct, {len(wrong):,} wrong)")
    print(f"  inliers, correct : median {np.median(correct):.0f}  p25 {np.percentile(correct, 25):.0f}")
    print(f"  inliers, wrong   : median {np.median(wrong):.0f}  p25 {np.percentile(wrong, 25):.0f}")
    print()
    print(f"{'cutoff':>8}{'correct kept':>15}{'wrong rejected':>17}")
    for cut in (10, 15, 20, 25, 30, 40):
        print(f"{cut:>8}{(correct >= cut).mean() * 100:>14.1f}%{(wrong < cut).mean() * 100:>16.1f}%")
    print(f"\nShipping cutoff: {INLIER_THRESHOLD}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("query", type=Path, nargs="?")
    parser.add_argument("candidate", type=Path, nargs="?")
    parser.add_argument("--measure", type=Path, nargs="?", const=Path(
        r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset"
        r"\work\receiver-hitches\rerank_rows.csv"
    ), help="Report the separation in an existing audit CSV instead of comparing two images.")
    args = parser.parse_args()

    if args.measure:
        measure_against_audit(args.measure)
        return

    if not args.query or not args.candidate:
        raise SystemExit("give two image paths, or --measure")

    result = verify_paths(args.query, args.candidate)
    print(f"keypoints : {result.keypoints_query} query / {result.keypoints_candidate} candidate")
    print(f"matches   : {result.matches} passing the ratio test")
    print(f"inliers   : {result.inliers} consistent with one homography "
          f"({result.inlier_ratio:.0%} of matches)")
    print(f"verdict   : {'SUPPORTED' if result.supported else 'NOT SUPPORTED'} "
          f"(cutoff {INLIER_THRESHOLD})")


if __name__ == "__main__":
    main()
