# Contributing

Contributions come from Shopware colleagues with write access to this repository, such as the shopwareLabs team `shopware-devs`, as pull requests. How you create a product doesn't matter: with your own generator, a photo of something you built, or by hand in `catalogue.json`. What matters is that the result passes the check and the rules below.

## What a product needs

`catalogue.schema.json` is the definition of `catalogue.json`. Every field, what it means and which values it takes are described there. The first key of `catalogue.json`, `"$schema": "./catalogue.schema.json"`, lets VS Code and PhpStorm complete and validate fields as you type.

The minimum for a product:

- a unique `id` in lower case with hyphens, used as its folder name in `images/`;
- `name` and `description` in English (`en`) and German (`de`); names have at most 245 characters;
- `price` (gross, euros), `tax`, `stock`, `type` (`physical` or `digital`);
- a unique `gtin` in the range 200–299 with a valid check digit (any EAN-13 calculator works);
- at least one category from `categories`; the first is the main category;
- exactly one image with the role `cover`, and for every image `alt` texts in both languages and `aiGenerated`.

The easiest start is to copy an existing product of the same kind and change it. Every key you reference (category, manufacturer, property group, option, cross-selling product) must exist; add new ones in the same pull request.

## Variants

A product with `variants` names a property group and at least two options. The first option is the look the cover shows. An option that looks different gets an image with the role `variant` and names its file in `image`; that image becomes the variant's cover. Options without an image show the parent's images. `priceDelta` is added to the parent's price, and an option's `type` may differ from the parent's, for example a PDF edition of a physical product.

## Images

- WebP, at most 1200 px on the longer side and 1 MB, stored as `images/<product id>/<shot>.webp`.
- Every file in `images/` must be listed in `catalogue.json`, and every listed file must exist.
- **AI-generated images** need the visible "AI-generated" label, the IPTC marker `trainedAlgorithmicMedia` and `"aiGenerated": true`, and both alt texts must say so ("AI" and "KI"). `tools/label-image.py` does the first two:

  ```sh
  python3 -m pip install "pillow>=10.1"
  python3 tools/label-image.py my-render.png images/my-product/cover.webp --description "Blue ceramic mug"
  ```

- **Other images** (your own photos, drawings) use `--not-ai` and `"aiGenerated": false`.
- Publishing prompts is optional: `prompts/<product id>.json` holds `id` and, per image file name, the `prompt` and `model`.

Only contribute images you have the rights to. Everything in this repository is published under CC0 1.0, so by opening a pull request you release your contribution under CC0.

## Rules

- Everything is fictional: products, manufacturers, brands. No real people or faces, no logos, no trademarks, no characters from films or games.
- English uses en-GB spelling. German shop texts address the customer formally ("Sie") or, better, impersonally.
- Food needs `unit`, and the `ingredients` and `allergens` custom fields; food, books and e-books take the `reduced` tax.
- New property groups and categories are fine; the test-data command creates and removes them.
- The catalogue must keep enough kinds of products for the test-data command: the check fails when a product type it needs is missing.

## Pull requests

- Work on a branch and open a pull request against `main`; nobody pushes to `main` directly.
- **Every commit must be signed and verified.** GitHub accepts GPG, SSH and S/MIME signatures; a GPG or SSH key must be added to your GitHub account as a signing key. See GitHub's [Signing commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits). An unsigned commit on the branch blocks the merge, so sign before you push, or rebase and re-sign.
- The check `catalogue` must pass, and a code owner must approve.
- Pull requests are squash-merged, so the title becomes the commit on `main`. Use a conventional title such as `feat: add a scented candle` or `fix: correct the honey allergens`.

## Check locally

With Python 3.12 to 3.14:

```sh
python3 -m pip install --no-deps --require-hashes -r .github/requirements-check.txt
python3 .github/bin/check-catalogue.py
```

The same check runs on every pull request. Maintainers cut releases from `main`.
