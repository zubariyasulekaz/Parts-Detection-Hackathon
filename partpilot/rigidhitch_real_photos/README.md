# Real photographs

83 photographs of 20 products, taken by hand over three days in August 2026.
One folder per SKU, files suffixed `-u1-`.

The suffix is the only thing that marks these as hand-taken, and it is worth
checking rather than globbing for: five catalogue images for `EPUMP-BLU1-21`
were filed here by mistake because the SKU itself contains the letters `u1`.
They have been removed. Match on `-u1-`, with the hyphens.

**These are the only irreplaceable files in this repository.** Everything else
here is code, or is rebuildable from the catalogue: the index takes two minutes,
the model takes an afternoon on a GPU. These took someone standing in front of
a part with a camera, and if they are lost they are lost.

They live in git for that reason alone — 9.4 MB, small enough that the usual
"build artifacts stay out of history" rule does not apply.

## Why they matter

Every accuracy figure measured on catalogue photographs compares a studio shot
against studio shots: white background, even light, canonical angle. A customer's
photograph is none of those. These are the only measurement of what the system
actually does in the hands of the people it is for.

They are also the fix. Adding a product's real photographs to the index moves it
sharply:

| | before | after |
|---|---|---|
| `02411`, wire spool | rank 3 | **rank 1**, 0.598 with a 0.335 gap |
| `TLL73FB`, LED light | 0.55 | **0.73** |

That is the mechanism, and it is the strongest argument for collecting more:
one photograph per product, and that product becomes findable.

## Running set

The application does not read this folder. It serves images from
`RIGIDHITCH_IMAGE_DIR`, where these files sit alongside the catalogue
photographs in the same per-SKU folders. This copy is the source of truth; that
one is the working set.

To add these to a fresh checkout's image directory, copy each `<SKU>/` folder's
contents into the matching folder under `RIGIDHITCH_IMAGE_DIR/images/`.

## Adding more

Photograph the part as a customer would — in hand, on a bench, on the vehicle —
not on white. Name the file `<SKU>-u1-<n>.png` and drop it in `<SKU>/`.

Then embed and append it to the index. Background removal must be applied first,
or the table behind the part becomes part of its fingerprint.

Score a folder of new photographs before adding them:

```
python scripts/rigidhitch_score_real_photos.py --photos <folder>
```

A photograph that already finds its own product without being indexed is a good
one. One that finds something else is worth looking at before it goes in.
