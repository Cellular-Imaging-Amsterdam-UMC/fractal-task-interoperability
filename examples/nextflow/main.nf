#!/usr/bin/env nextflow
/*
 * Fractal Cellpose-SAM task — Nextflow example
 *
 * Demonstrates that a Fractal-spec-compliant task can be orchestrated by
 * Nextflow using the standard Fractal CLI interface:
 *
 *   python -m <task_module> --args-json <path> --out-json <path>
 *
 * The Fractal task spec defines parallel tasks as processing one OME-Zarr
 * image (zarr_url) at a time.  Nextflow naturally models this: each item in
 * the `zarr_urls` channel becomes an independent process execution.  On a
 * real dataset with multiple wells/positions the processes run in parallel —
 * exactly as Fractal server would distribute them across workers.
 *
 * Usage (from the repo root, after `pixi install`):
 *   nextflow run examples/nextflow/main.nf -profile pixi
 */

nextflow.enable.dsl = 2

// ---------------------------------------------------------------------------
// Process: run the Fractal Cellpose-SAM task via its CLI entry point
// ---------------------------------------------------------------------------
process CELLPOSE_SAM_SEGMENTATION {
    tag "${zarr_url}"

    input:
    val zarr_url

    output:
    path "out.json"

    script:
    def overwrite_flag = params.overwrite ? "true" : "false"
    """
    # Write the Fractal-spec args JSON for this image
    cat > args.json <<'ARGS_EOF'
    {
        "zarr_url": "${zarr_url}",
        "channels": {
            "mode": "label",
            "identifiers": ["DAPI"]
        },
        "label_name": "${params.label_name}",
        "overwrite": ${overwrite_flag}
    }
ARGS_EOF

    # Invoke the task via the Fractal CLI interface
    python -m fractal_cellpose_sam_task.cellpose_sam_segmentation_task \
        --args-json args.json \
        --out-json  out.json
    """
}

// ---------------------------------------------------------------------------
// Workflow
// ---------------------------------------------------------------------------
workflow {
    // Build a channel of zarr_url strings.
    // For this demo dataset there is one image: well B / field 03, image 0.
    // On a real multi-well plate this list would contain one entry per image,
    // and Nextflow would run CELLPOSE_SAM_SEGMENTATION in parallel for each.
    def zarr_root = file(params.dataset_dir).toAbsolutePath().toString() +
                    "/20200812-CardiomyocyteDifferentiation14-Cycle1_mip.zarr"

    zarr_urls = channel.of("${zarr_root}/B/03/0")

    CELLPOSE_SAM_SEGMENTATION(zarr_urls)

    CELLPOSE_SAM_SEGMENTATION.out.view { out_json ->
        "Task output written to: ${out_json}"
    }
}
