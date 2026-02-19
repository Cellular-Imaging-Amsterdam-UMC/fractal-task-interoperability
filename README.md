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
Each `zarr_url` becomes a Nextflow channel item; on a multi-well dataset
the segmentation processes would run in parallel — exactly as Fractal Server
distributes tasks across its worker pool.

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
nextflow run examples/nextflow/main.nf -profile pixi
```

In both cases, `-profile pixi` tells Nextflow to use the pixi-managed conda
environment (`.pixi/envs/default`) for the task processes.

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
