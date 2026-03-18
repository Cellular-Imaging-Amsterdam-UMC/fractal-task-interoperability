#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minimal wrapper for fractal-cellpose-sam segmentation

This wrapper runs the fractal-cellpose-sam library on ZARR files,
without biaflows dependencies - parsing parameters directly from command line.
"""

import os
import sys
import shutil
import logging
import subprocess
import argparse
import json
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fractal_wrapper")


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


def run_algorithm(zarr_path, params, script_path="examples/python/run_fractal_cellpose.py"):
    """Generic function to run algorithm script via pixi with parsed parameters"""
    
    # Build base command - use direct Python path for Singularity compatibility
    cmd = ["/app/.pixi/envs/default/bin/python", script_path, "--zarr_url", str(zarr_path)]
    
    # Add all algorithm-specific parameters (skip standard workflow params)
    standard_params = {"infolder", "outfolder", "gtfolder", "local", "nmc"}
    
    for param_name, param_value in vars(params).items():
        if param_name in standard_params:
            continue
            
        # Convert parameter name to command line flag
        flag = f"--{param_name}"
        
        # Handle different parameter types
        if isinstance(param_value, bool):
            if param_value:  # Only add flag if True
                cmd.append(flag)
        else:
            cmd.extend([flag, str(param_value)])
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"Algorithm failed with exit code {result.returncode}"
            error_msg += f"\nSTDOUT: {result.stdout}"
            error_msg += f"\nSTDERR: {result.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("Algorithm completed successfully")
        logger.info(f"STDOUT: {result.stdout}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error running algorithm: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def load_descriptor():
    """Load descriptor.json to automatically configure argument parser"""
    script_dir = Path(__file__).parent
    descriptor_path = script_dir / "descriptor.json"
    
    if not descriptor_path.exists():
        raise FileNotFoundError(f"descriptor.json not found at {descriptor_path}")
    
    with open(descriptor_path, 'r') as f:
        return json.load(f)


def create_parser_from_descriptor():
    """Create argument parser: standard workflow params + algorithm-specific from descriptor.json"""
    descriptor = load_descriptor()
    parser = argparse.ArgumentParser(description=descriptor.get("description", "Fractal wrapper"))
    
    # Standard workflow parameters (always present for backward compatibility)
    parser.add_argument("--infolder", required=True, help="Input folder containing data")
    parser.add_argument("--outfolder", required=True, help="Output folder for results")
    parser.add_argument("--gtfolder", help="Ground truth folder (optional)")
    parser.add_argument("--local", action="store_true", help="Local mode (compatibility)")
    parser.add_argument("-nmc", action="store_true", help="No model cache (compatibility)")
    
    # Standard workflow param IDs to skip when processing descriptor
    standard_params = {"infolder", "outfolder", "gtfolder", "local", "nmc"}
    
    # Algorithm-specific parameters from descriptor.json
    for input_spec in descriptor.get("inputs", []):
        arg_id = input_spec["id"]
        
        # Skip standard workflow parameters
        if arg_id in standard_params:
            continue
            
        flag = input_spec.get("command-line-flag", f"--{arg_id}")
        name = input_spec.get("name", arg_id)
        description = input_spec.get("description", "")
        input_type = input_spec.get("type", "String")
        default_value = input_spec.get("default-value")
        optional = input_spec.get("optional", True)
        
        # Convert boutiques type to Python type based on default value
        if input_type == "Number":
            # Smart type detection: look at default value type from JSON
            if isinstance(default_value, int):
                arg_type = int  # e.g., nuc_channel: 0, diameter: 200, min_size: 15
            elif isinstance(default_value, float):
                arg_type = float  # e.g., prob_threshold: 0.5, anisotropy: 1.0  
            else:
                arg_type = float  # fallback for numbers without defaults
        elif input_type == "Boolean":
            arg_type = None  # Will use action="store_true"
        else:
            arg_type = str
        
        # Add argument to parser
        if input_type == "Boolean":
            # Handle Boolean arguments that can accept explicit True/False values
            def str_to_bool(v):
                if isinstance(v, bool):
                    return v
                if v.lower() in ('yes', 'true', 't', 'y', '1'):
                    return True
                elif v.lower() in ('no', 'false', 'f', 'n', '0'):
                    return False
                else:
                    raise argparse.ArgumentTypeError('Boolean value expected.')
            
            parser.add_argument(
                flag,
                type=str_to_bool,
                nargs='?',
                const=True,  # Value when flag is present without argument
                default=bool(default_value) if default_value is not None else False,
                help=f"{name}: {description}"
            )
        else:
            parser.add_argument(
                flag,
                type=arg_type,
                required=not optional,
                default=default_value,
                help=f"{name}: {description}"
            )
    
    return parser


def parse_args():
    """Parse command line arguments from descriptor.json"""
    parser = create_parser_from_descriptor()
    return parser.parse_args()


def main():
    """Main wrapper function"""
    logger.info(f"Starting fractal-cellpose-sam wrapper")
    
    # Parse command line arguments
    args = parse_args()
    logger.info(f"Arguments: {args}")
    
    try:
        # Set up paths
        in_path = Path(args.infolder)
        out_path = Path(args.outfolder)
        out_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Input path: {in_path}")
        logger.info(f"Output path: {out_path}")
            
        # Find all ZARR files in input directory
        logger.info("Searching for ZARR files...")
        zarr_files = find_zarr_files(in_path)
        
        if not zarr_files:
            logger.warning("No ZARR files found in input directory")
            return
        
        logger.info(f"Found {len(zarr_files)} ZARR files to process")
            
        # Process each ZARR file
        total_files = len(zarr_files)
        processed_count = 0
        
        for i, zarr_file in enumerate(zarr_files):
            try:
                logger.info(f"Processing {zarr_file.name} ({i+1}/{total_files})")
                
                # Copy ZARR file to output directory first
                output_zarr = copy_zarr_to_output(zarr_file, out_path)
                
                # Run algorithm on the output copy
                logger.info(f"Running algorithm on {zarr_file.name}")
                run_algorithm(output_zarr, args)
                
                processed_count += 1
                logger.info(f"Successfully processed {zarr_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing {zarr_file.name}: {str(e)}")
                # Continue with next file instead of failing completely
                continue
        
        # Final status
        if processed_count == total_files:
            logger.info(f"Segmentation completed successfully. Processed {processed_count}/{total_files} files.")
        else:
            logger.warning(f"Segmentation completed with warnings. Processed {processed_count}/{total_files} files.")
            
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()