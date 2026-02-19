# Fractal task interoperability

This repo demonstrates that a [Fractal-spec](https://fractal-analytics-platform.github.io/tasks_spec/)
compliant task can be invoked interoperably across different execution contexts,
using [`fractal-cellpose-sam-task`](https://github.com/fractal-analytics-platform/fractal-cellpose-sam-task)
as a concrete example.

The Fractal task spec defines a standard CLI interface: tasks accept
`--args-json <path>` and `--out-json <path>` arguments, making them portable
across any orchestrator that can run a shell command.

## Examples

All three examples run the same segmentation task on the same public dataset
([Zenodo 10.5281/zenodo.13305156](https://zenodo.org/records/13305156)),
each writing its output label into a separate data directory.

| Example | Entry point | Output label | Data directory |
|---------|-------------|--------------|----------------|
| Python import | `examples/python/run_cellpose_sam_python_script.py` | `nuclei_python_script` | `data_python/` |
| CLI | `examples/cli/run_cellpose_sam_cli.sh` | `nuclei_cli` | `data_cli/` |
| Nextflow | `examples/nextflow/main.nf` | `nuclei_nextflow` | `data_nextflow/` |
| Snakemake | `examples/snakemake/Snakefile` | `nuclei_snakemake` | `data_snakemake/` |

### Python import example

Calls the task as a regular Python function — no CLI involved.

```bash
pixi run cpsam-python
# or
python examples/python/run_cellpose_sam_python_script.py
```

### CLI example

Invokes the task through its Fractal CLI entry point
(`python -m <module> --args-json ... --out-json ...`).
This is the same interface that Fractal Server uses when it dispatches tasks
to workers.

```bash
pixi run cpsam-cli
# or
bash examples/cli/run_cellpose_sam_cli.sh
```

See [examples/cli/args_template.json](examples/cli/args_template.json) for the
task parameter schema.

### Nextflow example

Orchestrates the task via Nextflow, using the same CLI interface.
Each entry in `zarr_urls` becomes a Nextflow channel item and runs as an
independent parallel job — exactly as Fractal Server distributes parallel
tasks across its worker pool.

Task parameters are supplied via a YAML params file:

| File | Purpose |
|------|---------|
| [`examples/nextflow/params.yml`](examples/nextflow/params.yml) | Template with all manifest defaults (auto-generated from `__FRACTAL_MANIFEST__.json` via `pixi run generate-nextflow-params`) |
| [`examples/nextflow/params_example.yml`](examples/nextflow/params_example.yml) | Demo configuration used by `pixi run cpsam-nextflow` |

**Option A — via pixi** (no separate Nextflow install needed):
```bash
pixi run cpsam-nextflow
```
The pixi task automatically downloads the dataset to `data_nextflow/` before
launching Nextflow.

**Option B — standalone Nextflow** (for users who already have Nextflow installed):
```bash
# Stage the dataset first
pixi run download-nextflow-data
# Then run the pipeline
nextflow run examples/nextflow/main.nf -profile pixi \
    -params-file examples/nextflow/params_example.yml
```

In both cases, `-profile pixi` tells Nextflow to use the pixi-managed conda
environment (`.pixi/envs/default`) for the task processes.

### Snakemake example

Orchestrates the task via Snakemake, using the same CLI interface.
Each entry in `zarr_urls` becomes an independent Snakemake job via an integer
index wildcard.

Task parameters are supplied via a YAML config file:
[`examples/snakemake/config_example.yaml`](examples/snakemake/config_example.yaml)

```bash
pixi run cpsam-snakemake
```
The pixi task automatically downloads the dataset to `data_snakemake/` before
launching Snakemake.

Standalone (with Snakemake already installed):
```bash
pixi run download-snakemake-data
snakemake --snakefile examples/snakemake/Snakefile --cores 1
```

To run on custom data, pass your own config:
```bash
snakemake --snakefile examples/snakemake/Snakefile --cores 4 \
    --configfile my_config.yaml
```

## Installation

This project uses [pixi](https://pixi.sh) for environment management.

```bash
# Install pixi (if not already installed)
curl -fsSL https://pixi.sh/install.sh | sh

# Install all dependencies (including fractal-cellpose-sam-task from GitHub)
# This also installs Nextflow in an isolated pixi environment.
pixi install
```

Pixi manages two isolated environments:
- `default` — Python + the Cellpose-SAM task (used by the Python and CLI examples)
- `nextflow` — Nextflow only (used by `pixi run cpsam-nextflow`)

If you prefer to use a standalone Nextflow installation instead, see the
[Nextflow installation docs](https://www.nextflow.io/docs/latest/install.html).
