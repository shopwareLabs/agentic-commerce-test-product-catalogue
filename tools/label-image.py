#!/usr/bin/env python3
"""Prepares an image for the catalogue: at most 1200 px, WebP, and for AI-generated images the visible label and the
IPTC marker the check requires.

Needs Pillow 10.1 or newer (`python3 -m pip install "pillow>=10.1"`).

Usage:
  python3 tools/label-image.py photo.png images/my-product/cover.webp --description "Blue ceramic mug"
  python3 tools/label-image.py photo.jpg images/my-product/detail.webp --not-ai
"""

from __future__ import annotations

import argparse
import html
import io
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

MAX_SIZE = 1200
QUALITY = 82
MAX_BYTES = 1024 * 1024
LABEL = "AI-generated"
# IPTC's marking for generative AI output: https://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia
DIGITAL_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"


def xmp_packet(description: str) -> bytes:
    return f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
    xmlns:dc="http://purl.org/dc/elements/1.1/">
   <Iptc4xmpExt:DigitalSourceType>{DIGITAL_SOURCE_TYPE}</Iptc4xmpExt:DigitalSourceType>
   <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{html.escape(description)}</rdf:li></rdf:Alt></dc:description>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""".encode()


def add_label(image: Image.Image) -> Image.Image:
    """Draws the label bottom left, where shop overlays such as badges and the wishlist heart do not cover it."""
    width, height = image.size
    font = ImageFont.load_default(size=max(12, round(width * 0.026)))
    margin = round(width * 0.02)
    padding = round(font.size * 0.45)

    left, top, right, bottom = font.getbbox(LABEL)
    box_width = right - left + 2 * padding
    box_height = bottom - top + 2 * padding
    x, y = margin, height - margin - box_height

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((x, y, x + box_width, y + box_height), radius=round(box_height * 0.3), fill=(0, 0, 0, 153))
    draw.text((x + padding - left, y + padding - top), LABEL, font=font, fill=(255, 255, 255, 255))

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("target", type=pathlib.Path, help="images/<product id>/<shot>.webp")
    parser.add_argument("--description", default="", help="what the image shows, written into the metadata")
    parser.add_argument("--not-ai", action="store_true", help="the image is not AI-generated: no label, no marker")
    arguments = parser.parse_args()

    image = Image.open(arguments.source).convert("RGB")
    image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
    options = {"quality": QUALITY, "method": 6}
    if not arguments.not_ai:
        image = add_label(image)
        options["xmp"] = xmp_packet(f"AI-generated image of a fictional product. {arguments.description}".strip())

    buffer = io.BytesIO()
    image.save(buffer, "WEBP", **options)
    if buffer.tell() > MAX_BYTES:
        print(f"{arguments.target}: {buffer.tell()} bytes is more than {MAX_BYTES}; use a smaller or simpler image", file=sys.stderr)
        return 1

    arguments.target.parent.mkdir(parents=True, exist_ok=True)
    arguments.target.write_bytes(buffer.getvalue())
    print(f"{arguments.target}: {image.width} x {image.height}, {buffer.tell()} bytes{'' if arguments.not_ai else ', labelled'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
