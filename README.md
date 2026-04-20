# Fractal task interoperability — BIAFLOWS wrapper

This repo provides a [BIAFLOWS](https://biaflows.neubias.org/)-compatible wrapper
around [`fractal-cellpose-sam-task`](https://github.com/fractal-analytics-platform/fractal-cellpose-sam-task)
for cell/nuclei segmentation on OME-ZARR files.

The wrapper follows the standard BIAFLOWS interface (`--infolder` / `--outfolder` / `--gtfolder`)
and discovers algorithm parameters automatically from [`descriptor.json`](descriptor.json),
making it easy to deploy on SLURM clusters via [BIOMERO](https://github.com/NL-BioImaging/biomero).

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
| `label_name` | `nuclei_segmentation` | Name for the output label array |
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

