#!/usr/bin/env python3
"""Download and extract the Zenodo MIP OME-Zarr dataset used for interoperability tests.

Specifically downloads:
20200812-CardiomyocyteDifferentiation14-Cycle1_mip.zarr.zip

Uses pooch for:
- caching
- checksum verification
- retry robustness

Result:
<outdir>/20200812-CardiomyocyteDifferentiation14-Cycle1_mip.zarr
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pooch

DOI = "10.5281/zenodo.13305156"
DOI_SLUG = DOI.replace("/", "_").replace(".", "_")

RECORD_ID = "13305156"

FILENAME = "20200812-CardiomyocyteDifferentiation14-Cycle1_mip.zarr.zip"
ZARR_NAME = "20200812-CardiomyocyteDifferentiation14-Cycle1_mip.zarr"

# Pin checksum for reproducibility and to avoid extra Zenodo API calls
REGISTRY = {
    FILENAME: "md5:51809479777cafbe9ac0f9fa5636aa95",
}

BASE_URL = f"https://zenodo.org/records/{RECORD_ID}/files/"

DEFAULT_CACHE_DIR = pooch.os_cache("fractal-cellpose-sam-orchestrators") / DOI_SLUG


def download_and_extract(outdir: Path, cache_dir: Path | None = None) -> Path:
    """Download and extract the MIP OME-Zarr dataset.

    Parameters
    ----------
    outdir : Path
        Target directory where the .zarr folder will be placed.

    cache_dir : Path, optional
        Cache directory used by pooch. Defaults to platform cache.

    Returns:
    -------
    Path
        Path to extracted .zarr directory.
    """
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    pooch_obj = pooch.create(
        path=cache_dir,
        base_url=BASE_URL,
        registry=REGISTRY,
        retry_if_failed=5,
        allow_updates=False,
    )

    print(f"Downloading {FILENAME} to cache: {cache_dir}")

    extracted_paths = pooch_obj.fetch(
        FILENAME,
        processor=pooch.Unzip(extract_dir=ZARR_NAME),
    )

    # Derive extracted .zarr root
    # pooch returns list of extracted files
    first_path = Path(extracted_paths[0])
    extracted_zarr = first_path.parent

    if extracted_zarr.name != ZARR_NAME:
        extracted_zarr = extracted_zarr / ZARR_NAME

    if not extracted_zarr.exists():
        raise RuntimeError(f"Expected extracted zarr not found: {extracted_zarr}")

    target_zarr = outdir / ZARR_NAME

    # Replace existing output to guarantee clean run
    if target_zarr.exists():
        print(f"Removing existing output: {target_zarr}")
        shutil.rmtree(target_zarr)

    print(f"Copying dataset to: {target_zarr}")
    shutil.copytree(extracted_zarr, target_zarr)

    print(f"Dataset ready at: {target_zarr}")

    return target_zarr


def main():
    parser = argparse.ArgumentParser(
        description="Download Zenodo MIP OME-Zarr dataset."
    )

    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: ./data)",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Optional pooch cache directory",
    )

    args = parser.parse_args()

    zarr_path = download_and_extract(
        outdir=args.outdir,
        cache_dir=args.cache_dir,
    )

    print(zarr_path)


if __name__ == "__main__":
    main()
