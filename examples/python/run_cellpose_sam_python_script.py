#!/usr/bin/env python3
"""
Run fractal-cellpose-sam-task via Python

Typical use (from the repo root):
  pixi run python examples/python/run_cellpose_sam_python_script.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow importing the shared download utility from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from ngio import open_ome_zarr_container

from fractal_cellpose_sam_task.cellpose_sam_segmentation_task import (
    cellpose_sam_segmentation_task,
)

from fractal_cellpose_sam_task.pre_post_process import (
    PrePostProcessConfiguration,
)

from fractal_cellpose_sam_task.utils import (
    AdvancedCellposeParameters,
    CellposeChannels,
    SkipCreateMaskingRoiTable,
)

from download_zenodo_dataset import download_and_extract

logger = logging.getLogger("run_cellpose_sam_python")

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    zarr = download_and_extract(Path("data_python"))
    zarr_url = str(Path(zarr) / "B" / "03" / "0")
    logger.info("Using zarr_url=%s", zarr_url)

    channels = CellposeChannels(mode="label", identifiers=["DAPI"])
    output_label_name = "nuclei_python_script"

    # Minimal “advanced” settings, staying close to task defaults
    advanced = AdvancedCellposeParameters(verbose=False)

    pre_post = PrePostProcessConfiguration()

    logger.info("Running task…")
    cellpose_sam_segmentation_task(
        zarr_url=zarr_url,
        channels=channels,
        label_name=output_label_name,
        iterator_configuration=None,
        custom_model=None,
        advanced_parameters=advanced,
        pre_post_process=pre_post,
        create_masking_roi_table=SkipCreateMaskingRoiTable(),
        overwrite=True,
    )

    # Quick sanity check: does label now exist?
    ome_zarr = open_ome_zarr_container(zarr_url)
    try:
        _ = ome_zarr.get_label(name=output_label_name)
        logger.info("Found output label: %s", output_label_name)
    except Exception:
        logger.warning(
            "Task completed but output label was not found under name="
            f"{output_label_name}"
        )
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())