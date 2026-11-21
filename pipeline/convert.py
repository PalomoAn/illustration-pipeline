
import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image


MAX_SIDE = 2000   
QUALITY = 82      

# Windows file attributes for "online-only" cloud files (iCloud, OneDrive)
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
CLOUD_ONLY = (
    FILE_ATTRIBUTE_OFFLINE
    | FILE_ATTRIBUTE_RECALL_ON_OPEN
    | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)


def is_cloud_only(path: Path) -> bool:
    # st_file_attributes only exists on Windows; elsewhere this is 0.
    attrs = getattr(path.stat(), "st_file_attributes", 0)
    return bool(attrs & CLOUD_ONLY)


def slugify(name: str) -> str:
    """'Night Bat (final)' -> 'night-bat-final'. Safe for Storage keys and URLs."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "untitled"


MONTHS = {
    # English and Spanish month names, full and short
    "january": 1, "jan": 1, "enero": 1, "ene": 1,
    "february": 2, "feb": 2, "febrero": 2,
    "march": 3, "mar": 3, "marzo": 3,
    "april": 4, "apr": 4, "abril": 4, "abr": 4,
    "may": 5, "mayo": 5,
    "june": 6, "jun": 6, "junio": 6,
    "july": 7, "jul": 7, "julio": 7,
    "august": 8, "aug": 8, "agosto": 8, "ago": 8,
    "september": 9, "sep": 9, "sept": 9, "septiembre": 9, "setiembre": 9,
    "october": 10, "oct": 10, "octubre": 10,
    "november": 11, "nov": 11, "noviembre": 11,
    "december": 12, "dec": 12, "diciembre": 12, "dic": 12,
}


def parse_month(name: str) -> int | None:
    
    name = name.lower()
    name = re.sub(r"^(19|20)\d{2}[-_. ]*", "", name)   
    num = re.match(r"\d{1,2}", name)
    if num and 1 <= int(num.group()) <= 12:
        return int(num.group())
    for word in re.findall(r"[a-z]+", name):
        if word in MONTHS:
            return MONTHS[word]
    return None


def folder_date(png: Path, src_dir: Path) -> tuple[int, int] | None:
   
    parts = png.relative_to(src_dir).parts[:-1]   # folders only, no file name
    if len(parts) < 2:
        return None
    year_part, month_part = parts[-2], parts[-1]
    year = re.search(r"(19|20)\d{2}", year_part)
    month = parse_month(month_part)
    if not year or not month:
        return None
    return int(year.group()), month


def unique_slug(base: str, used: set[str]) -> str:
    slug, n = base, 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


def convert(src: Path, dst: Path) -> tuple[int, int]:
    with Image.open(src) as im:
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")   # palette PNGs keep their transparency
        im.thumbnail((MAX_SIDE, MAX_SIDE))   # keeps aspect ratio
        im.save(dst, "WEBP", quality=QUALITY, method=6)
        return im.size


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert PNG illustrations to WebP.")
    parser.add_argument("--src", required=True, help="Folder with the PNGs")
    parser.add_argument("--out", default="out", help="Output folder (default: out)")
    parser.add_argument("--dry-run", action="store_true", help="List files, convert nothing")
    args = parser.parse_args()

    src_dir = Path(args.src)
    out_dir = Path(args.out)
    if not src_dir.is_dir():
        print(f"Source folder not found: {src_dir}")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    pngs = sorted(p for p in src_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".png")
    print(f"Found {len(pngs)} PNG(s) in {src_dir}")

    manifest, used = [], set()
    counts = {"converted": 0, "up_to_date": 0, "cloud_only": 0, "error": 0}

    for png in pngs:
        date = folder_date(png, src_dir)
        base = slugify(png.stem)
        if date:
            prefix = f"{date[0]}-{date[1]:02d}"
            if not base.startswith(prefix):   
                base = f"{prefix}-{base}"       
        slug = unique_slug(base, used)
        webp = out_dir / f"{slug}.webp"
        entry = {"source": str(png), "slug": slug, "webp": str(webp)}
        if date:
            entry["year"], entry["month"] = date
        else:
            entry["warning"] = "no YEAR/MONTH folder found"

        if is_cloud_only(png):
            entry["status"] = "cloud_only"
        elif args.dry_run:
            entry["status"] = "dry_run"
        elif webp.exists() and webp.stat().st_mtime >= png.stat().st_mtime:
            with Image.open(webp) as im:
                entry["width"], entry["height"] = im.size
            entry["status"] = "up_to_date"
        else:
            try:
                entry["width"], entry["height"] = convert(png, webp)
                entry["status"] = "converted"
            except Exception as e:   
                entry["status"] = "error"
                entry["error"] = str(e)

        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        print(f"  [{entry['status']:>10}] {png.name} -> {slug}.webp")
        manifest.append(entry)

    if not args.dry_run:
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nSummary:", ", ".join(f"{k}={v}" for k, v in counts.items() if v))
    if counts["cloud_only"]:
        print("Some files are cloud-only. In File Explorer, right-click the folder ->")
        print("'Always keep on this device', wait for the download, then run again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
