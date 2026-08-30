"""Label a folder of downloaded photos with their SKUs, quickly.

Photos saved from a browser arrive named ``61bMrcUjqKL.jpg`` - Amazon's internal
id, useless to us. The scoring script reads the expected SKU from the filename,
so an unlabelled folder measures nothing, however many photos are in it.

Renaming a hundred files by hand is miserable and error-prone, so this writes a
small page into the folder itself: every photo shown, grouped by download time,
with one box to type the SKU. Because it is a local file the browser can display
the images directly, and because it is one page the whole folder can be labelled
in a few minutes.

**Grouping by download time is what makes it fast.** Photos of one product are
saved within a minute or two of each other, so they land in one group and take
one SKU between them.

Run:
    python scripts/rigidhitch_label_photos.py --photos "C:\\path\\to\\real photos"

Then open ``label.html`` in that folder, fill in the SKUs, press the button, and
paste the generated commands into PowerShell.
"""

import argparse
import html
import json
from pathlib import Path

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
# Photos saved more than this far apart are probably different products. Two
# minutes is loose enough to survive reading a review page between saves.
GROUP_GAP_SECONDS = 150


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photos", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent / "backend" / "models" / "faiss_rigidhitch")
    args = parser.parse_args()

    if not args.photos.is_dir():
        raise SystemExit(f"not a folder: {args.photos}")

    # One entry per indexed vector, so a product with four photos appears four
    # times - dedupe or the suggestion list is mostly repeats.
    known = sorted(set(json.loads((args.index_dir / "rigidhitch.ids.json").read_text())))
    files = sorted((p for p in args.photos.iterdir() if p.suffix.lower() in IMAGE_TYPES),
                   key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"no images in {args.photos}")

    groups: list[list[Path]] = [[files[0]]]
    for previous, current in zip(files, files[1:]):
        if current.stat().st_mtime - previous.stat().st_mtime <= GROUP_GAP_SECONDS:
            groups[-1].append(current)
        else:
            groups.append([current])

    blocks = []
    for n, group in enumerate(groups, 1):
        # Each photo carries its own box as well as the group's. Time grouping
        # is a guess - a browsing session can cover several products without a
        # long enough pause to split - so the group input is a convenience that
        # fills these, never the only way to say what a photo is.
        thumbs = "".join(
            f'<figure><img src="{html.escape(p.name)}" alt="" loading="lazy">'
            f'<input class="one" data-file="{html.escape(p.name)}" list="skus" '
            f'placeholder="SKU" spellcheck="false" autocomplete="off">'
            f'<figcaption>{html.escape(p.name[:24])}</figcaption></figure>'
            for p in group
        )
        names = html.escape(json.dumps([p.name for p in group]))
        blocks.append(f'''<section class="group" data-files='{names}'>
  <div class="head">
    <span class="n">Group {n}</span>
    <span class="count">{len(group)} photo{"s" if len(group) != 1 else ""}</span>
    <input class="sku" list="skus" placeholder="Fill every photo below with this SKU"
           spellcheck="false" autocomplete="off">
  </div>
  <div class="thumbs">{thumbs}</div>
</section>''')

    options = "".join(f'<option value="{html.escape(s)}">' for s in known)
    page = f"""<!doctype html><meta charset="utf-8">
<title>Label photos</title>
<style>
:root {{ color-scheme: light dark; --ink:#161b21; --muted:#5b6570; --line:#d6dee6;
  --surface:#fff; --ground:#f5f7f9; --accent:#1f5c8b; }}
@media (prefers-color-scheme:dark) {{ :root {{ --ink:#e6ecf2; --muted:#98a4b1; --line:#2c3540;
  --surface:#1a2027; --ground:#12161b; --accent:#74b3e0; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--ground); color:var(--ink); padding:0 22px 90px;
  font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif }}
.wrap {{ max-width:1000px; margin:0 auto }}
h1 {{ font-size:26px; margin:34px 0 6px }}
p.lead {{ color:var(--muted); max-width:62ch; margin:0 0 22px }}
.group {{ background:var(--surface); border:1px solid var(--line); margin-bottom:14px }}
.head {{ display:flex; align-items:center; gap:14px; padding:12px 16px; border-bottom:1px solid var(--line);
  flex-wrap:wrap }}
.n {{ font-weight:600 }} .count {{ color:var(--muted); font-size:13px }}
input.sku {{ flex:1; min-width:230px; padding:8px 11px; border:1px solid var(--line);
  background:var(--ground); color:var(--ink); font-family:ui-monospace,Consolas,monospace; font-size:14px }}
input.sku:focus {{ outline:2px solid var(--accent); outline-offset:-2px }}
.group:has(input.sku:not(:placeholder-shown)) {{ border-color:var(--accent) }}
.thumbs {{ display:flex; flex-wrap:wrap; gap:12px; padding:14px 16px }}
figure {{ margin:0; width:132px; display:flex; flex-direction:column; gap:4px }}
img {{ width:132px; height:132px; object-fit:contain; background:#fff; border:1px solid var(--line) }}
input.one {{ width:132px; padding:5px 7px; border:1px solid var(--line); background:var(--ground);
  color:var(--ink); font-family:ui-monospace,Consolas,monospace; font-size:12px }}
input.one:focus {{ outline:2px solid var(--accent); outline-offset:-2px }}
figure:has(input.one:not(:placeholder-shown)) img {{ border-color:var(--accent) }}
figcaption {{ font-size:10.5px; color:var(--muted); word-break:break-all; margin-top:3px }}
.bar {{ position:fixed; left:0; right:0; bottom:0; background:var(--surface); border-top:1px solid var(--line);
  padding:13px 22px; display:flex; gap:14px; align-items:center; justify-content:center }}
button {{ font:600 14px system-ui; padding:10px 20px; border:1px solid var(--accent);
  background:var(--accent); color:#fff; cursor:pointer }}
textarea {{ width:100%; height:210px; margin-top:14px; font-family:ui-monospace,Consolas,monospace;
  font-size:12.5px; padding:12px; border:1px solid var(--line); background:var(--surface); color:var(--ink) }}
</style>
<div class="wrap">
<h1>Label these photos</h1>
<p class="lead">Photos are grouped by when you saved them, so one product's shots sit together.
Type a SKU into a group box to fill every photo in it, or correct any single photo
below. Start typing and it suggests from the {len(known):,} products in the index. Then press the button and paste the commands into PowerShell.</p>
<datalist id="skus">{options}</datalist>
{''.join(blocks)}
<textarea id="out" readonly placeholder="The rename commands will appear here."></textarea>
</div>
<div class="bar"><button id="go">Generate rename commands</button></div>
<script>
// The group box is a shortcut: it fills the photo boxes, which are the truth.
document.querySelectorAll('.sku').forEach((groupInput) => {{
  groupInput.addEventListener('input', () => {{
    const value = groupInput.value.trim();
    groupInput.closest('.group').querySelectorAll('.one').forEach((one) => {{
      one.value = value;
    }});
  }});
}});

document.getElementById('go').addEventListener('click', () => {{
  const lines = [];
  const used = {{}};
  document.querySelectorAll('.one').forEach((input) => {{
    const sku = input.value.trim();
    if (!sku) return;
    const file = input.dataset.file;
    const ext = file.slice(file.lastIndexOf('.'));
    // Numbered per SKU rather than per group, so two separate groups of the
    // same product cannot both produce a _1 and overwrite each other.
    used[sku] = (used[sku] || 0) + 1;
    // Single quotes: these filenames contain spaces, brackets and plus signs,
    // all of which PowerShell would otherwise interpret.
    lines.push("Rename-Item -LiteralPath '" + file + "' -NewName '" + sku + "_" + used[sku] + ext + "'");
  }});
  const out = document.getElementById('out');
  out.value = lines.length ? lines.join("\n")
    : 'No SKUs entered yet - type one into a group box or a photo box.';
  out.scrollIntoView({{behavior: 'smooth', block: 'center'}});
  out.select();
}});
</script>"""

    target = args.photos / "label.html"
    target.write_text(page, encoding="utf-8")
    print(f"{len(files)} photos in {len(groups)} time-grouped batches")
    print(f"\nOpen this in your browser:\n  {target}")
    print("\nFill in a SKU per group, press the button, then in PowerShell:")
    print(f'  cd "{args.photos}"')
    print("  ...paste the commands...")


if __name__ == "__main__":
    main()
