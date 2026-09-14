"""Create mobile-sized WebP derivatives for product cards.

Run after adding product PNGs: python optimize_images.py
The source PNGs are retained for editing and as a fallback.
"""
import glob
import os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
for source in glob.glob(os.path.join(ROOT, "posts", "*", "img", "*.png")):
    output = os.path.splitext(source)[0] + ".webp"
    with Image.open(source) as image:
        image.thumbnail((240, 240), Image.Resampling.LANCZOS)
        image.save(output, "WEBP", quality=84, method=6)
    print(os.path.relpath(output, ROOT))
