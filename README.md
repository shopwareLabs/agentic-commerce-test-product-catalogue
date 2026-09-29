# Agentic Commerce test product catalogue

A dataset of **fictional** products for test shops, with English and German shop texts and product images. The first release holds 60 products with three **AI-generated** photos each (a cover, a lifestyle scene and a size comparison) and 20 more images for variants. Its products sit in these shop categories, many of them in more than one; contributors may add categories:

| Category | German |
|---|---|
| Home & Living | Wohnen & Deko |
| Kitchen & Table | Küche & Tisch |
| Food & Drink | Lebensmittel & Getränke |
| Toys & Games | Spielwaren |
| Desk & Stationery | Schreibwaren & Büro |
| Fashion & Accessories | Mode & Accessoires |
| Curiosities & Gifts | Kuriositäten & Geschenke |

Twelve of them have variants: colours, flavours, materials, or physical and digital editions, and eleven show some options in images of their own. The data also includes prices, list prices, tax classes, units, weights, properties, custom fields, manufacturers and cross-selling.

The Shopware plugin Agentic Commerce (`shopware/agentic-commerce`) uses it for `bin/console swag-agentic-commerce:test-data`. The command downloads the latest release, verifies it, and builds test products from randomly chosen catalogue entries in a category tree of its own.

## AI disclosure

Most images in this repository are AI-generated, and each image entry in `catalogue.json` says whether it is (`aiGenerated`). No image shows a real product, brand or person. An AI-generated image is disclosed in three ways:

- **Visible label:** "AI-generated" is drawn into the pixels, bottom left. It survives downloads, re-shares and thumbnails.
- **Metadata:** each WebP carries an XMP packet with the IPTC digital source type [`trainedAlgorithmicMedia`](https://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia).
- **Alt texts:** its alt texts in `catalogue.json` state that the image is AI-generated.

The images of the first release were created with these models, both licensed under Apache-2.0:

- [Qwen-Image-2512](https://huggingface.co/Qwen/Qwen-Image-2512) for the covers;
- [Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) for the scenes and variants.

`prompts/<id>.json` records the prompt and model of each generated image where the contributor published them. The product names, manufacturers and texts are invented.

## Licence

[CC0 1.0 Universal](LICENSE): no rights reserved. You may copy, change and use everything, including commercially, without asking or giving credit. Contributors release their texts and images under CC0 when they contribute them. Purely AI-generated images are probably not protected by copyright in most jurisdictions, so for them CC0 states what applies anyway.

The GTINs are in the GS1 prefix range 200–299, which is reserved for internal use and never assigned to a real product.

## Contents

```
catalogue.json            products, categories, property groups and manufacturers
catalogue.schema.json     JSON Schema of catalogue.json, schema 1: the definition of every field
images/<id>/<shot>.webp   cover and further images (lifestyle, scale, detail, variant-<key>), WebP, at most 1200 px and 1 MB
prompts/<id>.json         prompt and model of generated images, optional
tools/label-image.py      prepares an image: size, WebP, and for AI-generated images label and marker
```

In each release, `catalogue.json` also carries the release `version`.

## Releases and verification

Each release has three assets:

| File | Content |
|---|---|
| `test-product-catalogue-<version>.zip` | Everything above: images stored, JSON deflated |
| `index.json` | `schema`, `version`, `archive` file name, `size`, `sha256`, `created` |
| `index.json.sig` | Base64 Ed25519 signature over the exact bytes of `index.json` |

The plugin pins the public keys. It fetches `index.json` and its signature from `releases/latest/download/` and checks the signature. It downloads the archive only if the cached copy's SHA-256 differs. Before reading the archive, it checks the size and SHA-256. It reads the archive in place and never extracts it.

To verify a release by hand, put the base64 public key from the plugin into `key.b64`:

```sh
# Wrap the raw 32-byte key in the Ed25519 SubjectPublicKeyInfo prefix to get a PEM key.
{ printf '\x30\x2a\x30\x05\x06\x03\x2b\x65\x70\x03\x21\x00'; base64 -d key.b64; } | openssl pkey -pubin -inform DER -out key.pem
base64 -d index.json.sig > index.json.raw-sig
openssl pkeyutl -verify -rawin -pubin -inkey key.pem -in index.json -sigfile index.json.raw-sig
jq -r '"\(.sha256)  \(.archive)"' index.json | sha256sum -c
```

## Maintenance

Shopware colleagues with write access, such as the shopwareLabs team `shopware-devs`, contribute through pull requests; see [CONTRIBUTING.md](CONTRIBUTING.md). Every pull request needs signed commits, a passing catalogue check against `catalogue.schema.json` and a code owner's review, and is squash-merged into `main`. Issues, the wiki, discussions and projects are switched off.

Only maintainers can push a release tag `v<major>.<minor>.<patch>`, which runs `.github/workflows/release.yml`. A read-only job first checks that the tag is on `main` and runs the catalogue check. The release job then waits for approval in the protected `release` environment, builds the archive, signs the index with the environment secret `CATALOGUE_SIGNING_KEY` (an Ed25519 private key in PEM) and publishes the release.

A new major version means an incompatible `catalogue.json` schema. The plugin rejects schemas it does not know.
