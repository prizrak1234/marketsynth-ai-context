"""Derive compact Marketsynth brand assets from the approved master logo.

Does NOT modify the master file.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "web/public/brand/marketsynth-logo-master.png"
OUT = ROOT / "web/public/brand"
MASTER_SHA256 = "233FC4CCC844A700D4944FC6FA30BBA3017C39A6B5343D4122FD18DEA568DF37"


def save_resized(img: Image.Image, path: Path, size: int, bg=None) -> None:
    canvas = Image.new("RGBA", (size, size), bg if bg else (0, 0, 0, 0))
    fitted = img.copy()
    fitted.thumbnail((size, size), Image.Resampling.LANCZOS)
    ox = (size - fitted.width) // 2
    oy = (size - fitted.height) // 2
    canvas.paste(fitted, (ox, oy), fitted)
    canvas.save(path, optimize=True)


def main() -> None:
    raw = MASTER.read_bytes()
    digest = sha256(raw).hexdigest().upper()
    if digest != MASTER_SHA256:
        raise SystemExit(f"Master hash mismatch: {digest}")

    master = Image.open(MASTER).convert("RGBA")
    w, h = master.size
    left, right = int(w * 0.28), int(w * 0.72)
    top, bottom = int(h * 0.02), int(h * 0.58)
    emblem = master.crop((left, top, right, bottom))
    ew, eh = emblem.size
    side = max(ew, eh)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(emblem, ((side - ew) // 2, (side - eh) // 2), emblem)

    OUT.mkdir(parents=True, exist_ok=True)
    sym = OUT / "marketsynth-symbol.png"
    dark = OUT / "marketsynth-symbol-dark.png"
    fav32 = OUT / "marketsynth-favicon-32.png"
    fav16 = OUT / "marketsynth-favicon-16.png"
    apple = OUT / "marketsynth-apple-touch-icon.png"
    public_ico = OUT / "marketsynth-favicon.ico"
    app_ico = ROOT / "web/src/app/favicon.ico"

    save_resized(square, sym, 256)
    save_resized(square, dark, 128)
    save_resized(square, fav32, 32)
    save_resized(square, fav16, 16)
    save_resized(square, apple, 180, bg=(18, 18, 20, 255))

    i32 = Image.open(fav32).convert("RGBA")
    i32.save(public_ico, format="ICO", sizes=[(32, 32), (16, 16)])
    i32.save(app_ico, format="ICO", sizes=[(32, 32), (16, 16)])

    # Master still unchanged
    assert sha256(MASTER.read_bytes()).hexdigest().upper() == MASTER_SHA256
    print("ok derived assets written; master unchanged")
    for p in [MASTER, sym, dark, fav32, fav16, apple, public_ico, app_ico]:
        b = p.read_bytes()
        print(f"{p.relative_to(ROOT)} size={len(b)} sha256={sha256(b).hexdigest().upper()}")


if __name__ == "__main__":
    main()
