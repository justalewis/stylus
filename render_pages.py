"""Rasterize a PDF's pages to PNG using pypdfium2 (pure-Python wheel)."""
from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium


def main(pdf_path: str, out_dir: str, page_indices: list[int], scale: float = 2.0):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(pdf_path)
    print(f"  pages in document: {len(doc)}")
    for idx in page_indices:
        if idx < 1 or idx > len(doc):
            print(f"  ! page {idx} out of range, skipping")
            continue
        page = doc[idx - 1]
        image = page.render(scale=scale).to_pil()
        target = out / f"page-{idx:03d}.png"
        image.save(target)
        print(f"  wrote {target}  ({image.size[0]}x{image.size[1]})")


if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else r"content/journals/lics/_unfiled/fernandes-sanofranchini-mcintyre-2026/article.pdf"
    out = sys.argv[2] if len(sys.argv) > 2 else r"content/journals/lics/_unfiled/fernandes-sanofranchini-mcintyre-2026/preview"
    pages = [int(p) for p in sys.argv[3:]] if len(sys.argv) > 3 else [1, 2, 3, 4, 32]
    main(pdf, out, pages)
