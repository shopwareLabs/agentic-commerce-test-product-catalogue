#!/usr/bin/env python3
"""Checks catalogue.json against catalogue.schema.json and against the files in the repository.

The schema covers the shape of every entry. This script adds what a schema cannot express: keys that must exist,
image files on disk, GTIN check digits, the AI marking of generated images, and that the catalogue can fill every
product role the plugin's test-data command needs.

Usage: python3 .github/bin/check-catalogue.py [repository root]
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

from jsonschema import Draft202012Validator

MAX_IMAGE_BYTES = 1024 * 1024
# IPTC digital source type for generative AI output, as written into the image's XMP packet.
AI_MARKER = b"http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
AI_WORDS = {"en": "AI", "de": "KI"}


def gtin_is_valid(gtin: str) -> bool:
    total = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(gtin[:12]))

    return (10 - total % 10) % 10 == int(gtin[12])


def is_plain(product: dict) -> bool:
    return not product.get("variants")


def option_types(product: dict) -> set[str]:
    return {option["type"] for option in (product.get("variants") or {}).get("options", [])}


# Mirrors ProductPicker in the plugin: every role needs a product of its own.
ROLES = {
    "physical product with physical and digital variants": lambda p: p["type"] == "physical" and option_types(p) == {"physical", "digital"},
    "digital product with physical and digital variants": lambda p: p["type"] == "digital" and option_types(p) == {"physical", "digital"},
    "physical product with physical variants only": lambda p: p["type"] == "physical" and option_types(p) == {"physical"},
    "product without variants with properties": lambda p: is_plain(p) and bool(p.get("properties")),
    "product without variants with custom fields": lambda p: is_plain(p) and bool(p.get("customFields")),
    "product without variants (tier prices)": is_plain,
    "product without variants (members only)": is_plain,
}


def check(root: pathlib.Path) -> list[str]:
    schema = json.loads((root / "catalogue.schema.json").read_text(encoding="utf-8"))
    catalogue = json.loads((root / "catalogue.json").read_text(encoding="utf-8"))

    errors = [
        f"catalogue.json {'/'.join(map(str, error.absolute_path)) or '(root)'}: {error.message}"
        for error in sorted(Draft202012Validator(schema).iter_errors(catalogue), key=lambda error: list(map(str, error.absolute_path)))
    ]
    if errors:
        return errors
    if "version" in catalogue:
        errors.append("catalogue.json: version is written by the release workflow; remove it")

    products = catalogue["products"]
    ids = [product["id"] for product in products]
    errors += [f"product id {product_id} is used more than once" for product_id in sorted({i for i in ids if ids.count(i) > 1})]
    gtins = [product["gtin"] for product in products] + [
        option["gtin"] for product in products for option in (product.get("variants") or {}).get("options", []) if "gtin" in option
    ]
    errors += [f"GTIN {gtin} is used more than once" for gtin in sorted({g for g in gtins if gtins.count(g) > 1})]
    errors += [f"GTIN {gtin} has a wrong check digit" for gtin in sorted(set(gtins)) if not gtin_is_valid(gtin)]

    listed_files = set()
    for product in products:
        errors += check_product(product, catalogue, set(ids), root, listed_files)

    on_disk = {path.relative_to(root).as_posix() for path in (root / "images").rglob("*") if path.is_file()}
    errors += [f"{file} is not listed in catalogue.json" for file in sorted(on_disk - listed_files)]
    for prompt_file in sorted((root / "prompts").glob("*.json")) if (root / "prompts").is_dir() else []:
        if prompt_file.stem not in ids:
            errors.append(f"{prompt_file.relative_to(root)} belongs to no product")

    for role, fits in ROLES.items():
        if not any(fits(product) for product in products):
            errors.append(f"no product can fill the role: {role}")
    plain = sum(1 for product in products if is_plain(product))
    if plain < 4:
        errors.append(f"the four roles without variants need four products without variants, the catalogue has {plain}")

    return errors


def check_product(product: dict, catalogue: dict, ids: set[str], root: pathlib.Path, listed_files: set[str]) -> list[str]:
    label = f"product {product['id']}"
    errors = []

    for key in product["categories"]:
        if key not in catalogue["categories"]:
            errors.append(f"{label}: category {key} is not in categories")
    if "manufacturer" in product and product["manufacturer"] not in catalogue["manufacturers"]:
        errors.append(f"{label}: manufacturer {product['manufacturer']} is not in manufacturers")
    for group, options in (product.get("properties") or {}).items():
        if group not in catalogue["propertyGroups"]:
            errors.append(f"{label}: property group {group} is not in propertyGroups")
            continue
        errors += [f"{label}: {option} is not an option of {group}" for option in options if option not in catalogue["propertyGroups"][group]["options"]]
    for other in product.get("crossSelling", []):
        if other not in ids or other == product["id"]:
            errors.append(f"{label}: cross-selling {other} is not another product")
    if "listPrice" in product and product["listPrice"] <= product["price"]:
        errors.append(f"{label}: listPrice must be higher than price")
    if "purchase" in product and product["purchase"]["max"] < product["purchase"]["min"]:
        errors.append(f"{label}: purchase.max must be at least purchase.min")

    covers = [image for image in product["images"] if image["role"] == "cover"]
    if len(covers) != 1:
        errors.append(f"{label}: needs exactly one image with role cover, has {len(covers)}")
    for image in product["images"]:
        errors += check_image(label, product["id"], image, root)
        listed_files.add(image["file"])

    variants = product.get("variants")
    if variants:
        if variants["group"] not in catalogue["propertyGroups"]:
            errors.append(f"{label}: variant group {variants['group']} is not in propertyGroups")
        keys = [option["key"] for option in variants["options"]]
        errors += [f"{label}: variant option {key} is used more than once" for key in sorted({k for k in keys if keys.count(k) > 1})]
        variant_images = {image["file"] for image in product["images"] if image["role"] == "variant"}
        for option in variants["options"]:
            if option.get("image") and option["image"] not in variant_images:
                errors.append(f"{label}: variant option {option['key']} names {option['image']}, which is not a variant image of the product")
            if product["price"] + option["priceDelta"] <= 0:
                errors.append(f"{label}: variant option {option['key']} makes the price zero or negative")

    return errors


def check_image(label: str, product_id: str, image: dict, root: pathlib.Path) -> list[str]:
    errors = []
    if not image["file"].startswith(f"images/{product_id}/"):
        errors.append(f"{label}: {image['file']} must be in images/{product_id}/")
    path = root / image["file"]
    if not path.is_file():
        return errors + [f"{label}: {image['file']} does not exist"]

    content = path.read_bytes()
    if content[:4] != b"RIFF" or content[8:12] != b"WEBP":
        errors.append(f"{image['file']} is not a WebP file")
    if len(content) > MAX_IMAGE_BYTES:
        errors.append(f"{image['file']} is {len(content)} bytes, more than {MAX_IMAGE_BYTES}")
    if image["aiGenerated"]:
        if AI_MARKER not in content:
            errors.append(f"{image['file']} is AI-generated but lacks the IPTC marker; prepare it with tools/label-image.py")
        for language, word in AI_WORDS.items():
            if word not in image["alt"][language]:
                errors.append(f"{label}: the {language} alt text of {image['file']} must say it is AI-generated ({word})")

    return errors


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = check(root)
    for error in errors:
        print(f"::error::{error}" if "GITHUB_ACTIONS" in os.environ else error)
    if errors:
        print(f"{len(errors)} problem(s) found")
        return 1

    catalogue = json.loads((root / "catalogue.json").read_text(encoding="utf-8"))

    images = sum(len(product["images"]) for product in catalogue["products"])
    print(f"catalogue.json valid: {len(catalogue['products'])} products, {images} images, {len(catalogue['categories'])} categories")

    return 0


if __name__ == "__main__":
    sys.exit(main())
