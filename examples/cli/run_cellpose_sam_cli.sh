#!/usr/bin/env bash
# Run fractal-cellpose-sam-task (v0.1.9) via the Fractal CLI interface.
#
# The Fractal task spec defines a standard CLI contract: tasks accept
#   --args-json <path>   JSON file with all task parameters
#   --out-json  <path>   path where the task writes its JSON return value
#
# This script:
#   1. Downloads the example dataset (if not already present)
#   2. Writes a task args JSON file
#   3. Invokes the task via `python -m <module> --args-json ... --out-json ...`
#   4. Prints the task output JSON
#
# Typical use (from the repo root, inside the pixi environment):
#   bash examples/cli/run_cellpose_sam_cli.sh
#   pixi run ci-cli

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DATA_DIR="${REPO_ROOT}/data_cli"
ZARR_URL="${DATA_DIR}/20200812-CardiomyocyteDifferentiation14-Cycle1_mip.zarr/B/03/0"
LABEL_NAME="nuclei_cli"

# ---------------------------------------------------------------------------
# 1. Download dataset
# ---------------------------------------------------------------------------
echo "==> Downloading dataset to ${DATA_DIR} (skipped if already present)..."
python "${REPO_ROOT}/scripts/download_zenodo_dataset.py" --outdir "${DATA_DIR}"

# ---------------------------------------------------------------------------
# 2. Write args JSON to a temp file (cleaned up on exit)
# ---------------------------------------------------------------------------
ARGS_JSON="$(mktemp /tmp/cellpose_sam_args.XXXXXX.json)"
OUT_JSON="$(mktemp /tmp/cellpose_sam_out.XXXXXX.json)"
rm "${OUT_JSON}"   # run_fractal_task fails if the output file already exists

trap 'rm -f "${ARGS_JSON}" "${OUT_JSON}"' EXIT

cat > "${ARGS_JSON}" <<EOF
{
    "zarr_url": "${ZARR_URL}",
    "channels": {
        "mode": "label",
        "identifiers": ["DAPI"]
    },
    "label_name": "${LABEL_NAME}",
    "overwrite": true
}
EOF

echo "==> Args JSON written to ${ARGS_JSON}:"
cat "${ARGS_JSON}"
echo ""

# ---------------------------------------------------------------------------
# 3. Invoke the task via the Fractal CLI interface
# ---------------------------------------------------------------------------
echo "==> Running task via CLI..."
python -m fractal_cellpose_sam_task.cellpose_sam_segmentation_task \
    --args-json "${ARGS_JSON}" \
    --out-json  "${OUT_JSON}"

# ---------------------------------------------------------------------------
# 4. Print output
# ---------------------------------------------------------------------------
echo ""
echo "==> Task output JSON (${OUT_JSON}):"
cat "${OUT_JSON}"
echo ""
echo "==> Done. Label '${LABEL_NAME}' written to:"
echo "    ${ZARR_URL}/labels/${LABEL_NAME}"
