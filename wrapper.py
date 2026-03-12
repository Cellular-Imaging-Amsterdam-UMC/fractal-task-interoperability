#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BIAFLOWS wrapper for fractal-cellpose-sam segmentation

This wrapper integrates the fractal-cellpose-sam library with the BIAFLOWS framework
to process ZARR files with Cellpose-SAM segmentation.
"""

import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path

from biaflows import CLASS_OBJSEG
from biaflows.helpers import BiaflowsJob, prepare_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fractal_biaflows_wrapper")


def find_zarr_files(input_path):
    """Find all ZARR files in the input directory"""
    zarr_files = []
    input_path = Path(input_path)
    
    # Look for .zarr directories
    for item in input_path.rglob("*"):
        if item.is_dir() and item.name.endswith('.zarr'):
            zarr_files.append(item)
    
    logger.info(f"Found {len(zarr_files)} ZARR files: {[str(z) for z in zarr_files]}")
    return zarr_files


def copy_zarr_to_output(zarr_path, output_dir):
    """Copy ZARR file to output directory"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    zarr_name = zarr_path.name
    output_zarr = output_dir / zarr_name
    
    # Copy the entire ZARR directory structure
    if output_zarr.exists():
        shutil.rmtree(output_zarr)
    
    shutil.copytree(zarr_path, output_zarr)
    logger.info(f"Copied {zarr_path} to {output_zarr}")
    return output_zarr


def run_fractal_segmentation(zarr_path, params, bj):
    """Run fractal-cellpose-sam via pixi calling the proper script"""
    
    # Get parameters
    nuc_channel = getattr(params, 'nuc_channel', 0)
    diameter = getattr(params, 'diameter', 30)
    cellprob_threshold = getattr(params, 'cellprob_threshold', 0.0)
    flow_threshold = getattr(params, 'flow_threshold', 0.4)
    min_size = getattr(params, 'min_size', 15)
    use_gpu = getattr(params, 'use_gpu', True)
    model_type = getattr(params, 'cp_model', 'cpsam')
    label_name = getattr(params, 'label_name', 'nuclei_segmentation')
    do_3D = getattr(params, 'do_3D', False)
    anisotropy = getattr(params, 'anisotropy', 1.0)
    exclude_on_edges = getattr(params, 'exclude_on_edges', False)
    normalize = getattr(params, 'normalize', True)
    
    # Build command to run the fractal script with parameters
    cmd = [
        "bash", "-c",
        f"cd /app && pixi run python examples/python/run_channel3_nuclei.py "
        f"--zarr_url '{str(zarr_path)}' "
        f"--nuc_channel {nuc_channel} "
        f"--label_name '{label_name}' "
        f"--diameter {diameter} "
        f"--cellprob_threshold {cellprob_threshold} "
        f"--flow_threshold {flow_threshold} "
        f"--min_size {min_size} "
        f"--cp_model '{model_type}' "
        f"--anisotropy {anisotropy} "
        f"{'--use_gpu' if use_gpu else ''} "
        f"{'--do_3D' if do_3D else ''} "
        f"{'--exclude_on_edges' if exclude_on_edges else ''} "
        f"{'--normalize' if normalize else ''}"
    ]
    
    bj.job.update(
        progress=50,
        statusComment=f"Running fractal segmentation on {zarr_path.name}"
    )
    
    logger.info(f"Running command: {cmd[2]}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode != 0:
            error_msg = f"Fractal segmentation failed with exit code {result.returncode}"
            error_msg += f"\nSTDOUT: {result.stdout}"
            error_msg += f"\nSTDERR: {result.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("Fractal segmentation completed successfully")
        logger.info(f"STDOUT: {result.stdout}")
        
        return True
        
    except subprocess.TimeoutExpired:
        error_msg = "Fractal segmentation timed out after 1 hour"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Error running fractal segmentation: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def main(argv):
    """Main BIAFLOWS wrapper function"""
    # Base path is mandatory for Singularity containers
    os.getenv("HOME")  # Ensure HOME is defined
    problem_cls = CLASS_OBJSEG
    logger.info(f"argv={argv}")
    with BiaflowsJob.from_cli(argv) as bj:
        try:
            # Get parameters from BIAFLOWS job
            nuc_channel = getattr(bj.parameters, 'nuc_channel', 0)
            diameter = getattr(bj.parameters, 'diameter', 30)
            cellprob_threshold = getattr(bj.parameters, 'cellprob_threshold', 0.0)
            flow_threshold = getattr(bj.parameters, 'flow_threshold', 0.4)
            min_size = getattr(bj.parameters, 'min_size', 15)
            use_gpu = getattr(bj.parameters, 'use_gpu', True)
            model_type = getattr(bj.parameters, 'cp_model', 'cpsam')
            label_name = getattr(bj.parameters, 'label_name', 'nuclei_segmentation')
            exclude_on_edges = getattr(bj.parameters, 'exclude_on_edges', False)
            do_3D = getattr(bj.parameters, 'do_3D', False)
            anisotropy = getattr(bj.parameters, 'anisotropy', 1.0)
            batch_size = getattr(bj.parameters, 'batch_size', 8)
            tile_overlap = getattr(bj.parameters, 'tile_overlap', 0.1)
            normalize = getattr(bj.parameters, 'normalize', True)
            
            logger.info(f"Parameters: channel={nuc_channel}, diameter={diameter}, "
                       f"cellprob_threshold={cellprob_threshold}, flow_threshold={flow_threshold}, "
                       f"min_size={min_size}, use_gpu={use_gpu}, model={model_type}, "
                       f"exclude_on_edges={exclude_on_edges}, do_3D={do_3D}, anisotropy={anisotropy}, "
                       f"batch_size={batch_size}, normalize={normalize}")
            
            # Prepare data
            bj.job.update(status=10, statusComment="Preparing data...")
            # Pass the folder arguments explicitly from the job to prepare_data
            in_imgs, gt_imgs, in_path, gt_path, out_path, tmp_path = prepare_data(
                problem_cls, bj, is_2d=not do_3D,
                infolder=bj.flags.get('infolder'),
                outfolder=bj.flags.get('outfolder'), 
                gtfolder=bj.flags.get('gtfolder')
            )
            
            logger.info(f"Paths from prepare_data: in_path={in_path}, out_path={out_path}")
            
            # Find all ZARR files in input directory
            bj.job.update(status=20, statusComment="Searching for ZARR files...")
            zarr_files = find_zarr_files(in_path)
            
            if not zarr_files:
                bj.job.update(status=100, statusComment="No ZARR files found in input directory")
                logger.warning("No ZARR files found in input directory")
                return
            
            bj.job.update(status=25, statusComment=f"Found {len(zarr_files)} ZARR files to process")
            
            # Process each ZARR file
            total_files = len(zarr_files)
            processed_count = 0
            
            for i, zarr_file in enumerate(zarr_files):
                base_progress = 30 + int((i / total_files) * 50)  # Progress from 30% to 80%
                
                try:
                    bj.job.update(
                        status=base_progress,
                        statusComment=f"Processing {zarr_file.name} ({i+1}/{total_files})"
                    )
                    
                    # Copy ZARR file to output directory first
                    output_zarr = copy_zarr_to_output(zarr_file, out_path)
                    
                    # Run fractal cellpose segmentation on the output copy via subprocess
                    bj.job.update(
                        status=base_progress + 5,
                        statusComment=f"Running fractal segmentation on {zarr_file.name}"
                    )
                    
                    # Use subprocess approach like W_Segmentation-Cellpose4
                    run_fractal_segmentation(output_zarr, bj.parameters, bj)
                    
                    processed_count += 1
                    logger.info(f"Successfully processed {zarr_file.name}")
                    
                except Exception as e:
                    logger.error(f"Error processing {zarr_file.name}: {str(e)}")
                    bj.job.update(
                        status=base_progress,
                        statusComment=f"Error processing {zarr_file.name}: {str(e)}"
                    )
                    # Continue with next file instead of failing completely
                    continue
            
            # Final status
            if processed_count == total_files:
                bj.job.update(
                    status=100, 
                    statusComment=f"Segmentation completed successfully. Processed {processed_count}/{total_files} files."
                )
            else:
                bj.job.update(
                    status=100, 
                    statusComment=f"Segmentation completed with warnings. Processed {processed_count}/{total_files} files."
                )
                
        except Exception as e:
            logger.error(f"Fatal error in main: {str(e)}")
            bj.job.update(status=100, statusComment=f"Job failed: {str(e)}")
            raise


if __name__ == "__main__":
    main(sys.argv[1:])