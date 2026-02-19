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
 * image (zarr_url) at a time.  Nextflow naturally models this: each entry in
 * params.zarr_urls becomes an independent process execution.  On a dataset
 * with multiple wells/positions the processes run in parallel — exactly as
 * Fractal Server distributes them across its worker pool.
 *
 * Usage (from the repo root, after `pixi install`):
 *   nextflow run examples/nextflow/main.nf -profile pixi \
 *       -params-file examples/nextflow/params_example.yml
 */

nextflow.enable.dsl = 2

// ---------------------------------------------------------------------------
// Helper: build the Fractal-spec args JSON for one image
// ---------------------------------------------------------------------------
def fractal_args(String zarr_url) {
    // zarr_url and channels are required; all other parameters are included
    // only when explicitly provided in the params file (falling back to the
    // task's own manifest defaults otherwise).
    def args = [
        zarr_url : zarr_url,
        channels : params.channels,
    ]
    ["label_name", "overwrite", "level_path", "iterator_configuration",
     "custom_model", "advanced_parameters", "pre_post_process",
     "create_masking_roi_table"].each { key ->
        if (params[key] != null) args[key] = params[key]
    }
    return groovy.json.JsonOutput.toJson(args)
}

// ---------------------------------------------------------------------------
// Process: run the Fractal Cellpose-SAM task via its CLI entry point
// ---------------------------------------------------------------------------
process CELLPOSE_SAM_SEGMENTATION {
    tag "${zarr_url}"

    input:
    tuple val(zarr_url), val(args_json)

    output:
    path "out.json"

    script:
    """
    # Write the Fractal-spec args JSON for this image
    cat > args.json <<'ARGS_EOF'
${args_json}
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
    // Each entry in params.zarr_urls becomes one parallel job —
    // mirroring how Fractal Server dispatches parallel tasks across workers.
    zarr_url_and_args = channel
        .from(params.zarr_urls)
        .map { url ->
            def abs_url = file(url).toAbsolutePath().toString()
            tuple(abs_url, fractal_args(abs_url))
        }

    CELLPOSE_SAM_SEGMENTATION(zarr_url_and_args)

    CELLPOSE_SAM_SEGMENTATION.out.view { out_json ->
        "Task output written to: ${out_json}"
    }
}
