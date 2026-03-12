#!/usr/bin/env python3
"""Run fractal-cellpose-sam-task with configurable parameters"""

import argparse
from pathlib import Path
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

def main():
    parser = argparse.ArgumentParser(description="Run fractal-cellpose-sam segmentation")
    parser.add_argument("--zarr_url", required=True, help="Path to ZARR file")
    parser.add_argument("--nuc_channel", type=int, default=0, help="Channel index for segmentation")
    parser.add_argument("--label_name", default="nuclei_segmentation", help="Output label name")
    parser.add_argument("--diameter", type=int, default=30, help="Cell diameter")
    parser.add_argument("--cellprob_threshold", type=float, default=0.0, help="Cell probability threshold")
    parser.add_argument("--flow_threshold", type=float, default=0.4, help="Flow threshold")
    parser.add_argument("--min_size", type=int, default=15, help="Minimum size")
    parser.add_argument("--use_gpu", action="store_true", help="Use GPU")
    parser.add_argument("--cp_model", default="cpsam", help="Cellpose model")
    parser.add_argument("--do_3D", action="store_true", help="3D processing")
    parser.add_argument("--anisotropy", type=float, default=1.0, help="Anisotropy for 3D")
    parser.add_argument("--exclude_on_edges", action="store_true", help="Exclude edge cells")
    parser.add_argument("--normalize", action="store_true", default=True, help="Normalize intensities")
    
    args = parser.parse_args()
    
    # Set up channel configuration
    if args.nuc_channel >= 0:
        channels = CellposeChannels(mode="index", identifiers=[str(args.nuc_channel)])
    else:
        channels = CellposeChannels(mode="index", identifiers=["0"])
    
    # Set up advanced parameters
    advanced = AdvancedCellposeParameters(
        diameter=args.diameter,
        cellprob_threshold=args.cellprob_threshold,
        flow_threshold=args.flow_threshold,
        min_size=args.min_size,
        use_gpu=args.use_gpu,
        do_3D=args.do_3D,
        anisotropy=args.anisotropy,
        exclude_on_edges=args.exclude_on_edges,
        normalize=args.normalize,
        verbose=True
    )
    
    # Determine custom model
    custom_model = None if args.cp_model == "cpsam" else args.cp_model
    
    print(f"Running Cellpose on {args.zarr_url}, channel {args.nuc_channel}")
    
    try:
        cellpose_sam_segmentation_task(
            zarr_url=args.zarr_url,
            channels=channels,
            label_name=args.label_name,
            iterator_configuration=None,
            custom_model=custom_model,
            advanced_parameters=advanced,
            pre_post_process=PrePostProcessConfiguration(),
            create_masking_roi_table=SkipCreateMaskingRoiTable(),
            overwrite=True,
        )
        print(f"Done! Output saved as label: {args.label_name}")
    except Exception as e:
        print(f"Error in fractal segmentation: {e}")
        raise

if __name__ == "__main__":
    main()