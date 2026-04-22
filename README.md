# Cellpose-SAM Cell Segmentation — BIAFLOWS-style BIOMERO wrapper using Fractal Task

Automate cell and nuclei segmentation on OME-ZARR images using
[Cellpose-SAM](https://github.com/fractal-analytics-platform/fractal-cellpose-sam-task) —
a combination of Cellpose's flow-based detection and Meta's Segment Anything Model (SAM).

**Why use this?**
Cellpose-SAM generalises well across cell types and imaging conditions without manual
threshold tuning, making it a strong default choice for high-content screening (HCS)
datasets. This wrapper packages it for fully automated, scalable batch processing on
SLURM clusters via [BIOMERO](https://github.com/NL-BioImaging/biomero) — no GPU required.

**How segmentation works under the hood:**
The actual segmentation is delegated to the
[Fractal Analytics Platform](https://fractal-analytics-platform.github.io/) task library
(`fractal-cellpose-sam-task`). Fractal handles all OME-ZARR I/O and writes the segmentation
result as a label array at `<image>.zarr/labels/<label_name>/` inside the output ZARR file.
This wrapper's job is simply to expose that Fractal task through a BIAFLOWS-compatible
interface so it integrates with BIOMERO.

## Departure from the standard BIAFLOWS spec

Standard BIAFLOWS workflows use a Cytomine descriptor and Cytomine-specific connection
arguments to fetch images from a Cytomine server. **This wrapper does not follow that convention:**

- The descriptor uses the **Boutiques schema** (`boutiques-0.5`) instead of the Cytomine schema,
  because the inputs and outputs are plain file-system paths, not Cytomine objects.
- There are **no Cytomine connection arguments** (`--cytomine_host`, `--cytomine_public_key`, …).
- As a result, **this workflow cannot be run inside Cytomine**.

It *can* be run:
- via **BIOMERO** on a SLURM cluster (primary use case),
- with **Docker or Singularity** directly on any machine,
- or **locally** without any container runner (see [Local development](#installation-for-local-development)).

The interface still uses the familiar BIAFLOWS folder arguments
(`--infolder` / `--outfolder` / `--gtfolder`) for compatibility with BIOMERO's job dispatch,
but the key difference from standard BIAFLOWS is that **input images must be OME-ZARR
directories, not TIFF files**. Each `.zarr` directory in `--infolder` is treated as one image.
The `--gtfolder` argument is accepted but ignored — there is no ground-truth comparison step.

All segmentation parameters are defined in [`descriptor.json`](descriptor.json) and
automatically wired to the CLI at runtime.

## How it works

1. Discovers all `.zarr` files in the input directory
2. Copies each file to the output directory
3. Runs `fractal-cellpose-sam` segmentation on the output copy, writing labels in-place
4. Parameters are parsed directly from `descriptor.json` at runtime — no hardcoded argument lists

## Files

| File | Purpose |
|------|---------|
| [`wrapper.py`](wrapper.py) | BIAFLOWS wrapper — entry point |
| [`descriptor.json`](descriptor.json) | Parameter definitions (Boutiques schema) |
| [`Dockerfile`](Dockerfile) | Container definition (CPU-only, Ubuntu + pixi) |
| [`examples/python/run_fractal_cellpose.py`](examples/python/run_fractal_cellpose.py) | Thin script called by the wrapper to invoke the fractal task |

## Parameters

All parameters are defined in `descriptor.json` and automatically wired to the CLI.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `nuc_channel` | `0` | Channel index to segment (−1 = default channel) |
| `diameter` | `200` | Expected cell diameter in pixels |
| `prob_threshold` | `0.5` | Cell probability threshold (centred at 0.0) |
| `flow_threshold` | `0.4` | Flow error threshold (0 = disabled) |
| `min_size` | `15` | Minimum pixels per mask (−1 = disabled) |
| `use_gpu` | `false` | GPU flag (see note below — CPU-only in this container) |
| `cp_model` | `cpsam` | Cellpose model name or path |
| `label_name` | `fractal_cellpose_sam_segmentation` | Name for the output label array in the ZARR file |
| `exclude_on_edges` | `false` | Discard masks touching image edges |
| `do_3d` | `false` | Run 3D segmentation |
| `anisotropy` | `1.0` | Z/XY voxel size ratio for 3D mode |
| `normalize` | `true` | Normalise intensity before segmentation |

## Usage

### With Singularity (BIOMERO / SLURM)

```bash
singularity run "$IMAGE_PATH/$SINGULARITY_IMAGE" \
    --infolder "$DATA_PATH/data/in" \
    --outfolder "$DATA_PATH/data/out" \
    --gtfolder "$DATA_PATH/data/gt" \
    --local -nmc \
    --nuc_channel 0 --diameter 200 --cp_model cpsam
```

### With Docker

```bash
docker run --rm \
    -v /path/to/input:/data/in \
    -v /path/to/output:/data/out \
    cellularimagingcf/fractal-cellpose-sam-biaflows \
    --infolder /data/in --outfolder /data/out \
    --nuc_channel 0 --diameter 200
```

## Building the container

```bash
docker build -t cellularimagingcf/fractal-cellpose-sam-biaflows .
# Convert for Singularity/Apptainer:
singularity build fractal-cellpose-sam-biaflows.sif docker-daemon://cellularimagingcf/fractal-cellpose-sam-biaflows:latest
```

## CPU-only design

The container is intentionally **CPU-only** to keep the image small and broadly
compatible. The `use_gpu` parameter is accepted (for descriptor compatibility with
BIOMERO's parameter passing) but GPU support is not installed — Cellpose-SAM will
run on CPU regardless of how the flag is set.

To add GPU support, replace the base image with a CUDA image and install
`torch` with CUDA extras in `pixi.toml`.

## Installation (for local development)

This project uses [pixi](https://pixi.sh) for environment management.

```bash
# Install pixi if not already present
curl -fsSL https://pixi.sh/install.sh | bash

# Install all dependencies
pixi install

# Run wrapper locally
pixi run python wrapper.py \
    --infolder ./test_data/in \
    --outfolder ./test_data/out \
    --nuc_channel 0 --diameter 200
```

