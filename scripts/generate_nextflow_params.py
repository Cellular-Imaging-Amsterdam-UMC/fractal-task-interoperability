#!/usr/bin/env python3
"""Generate Nextflow parameter files from the Fractal task manifest.

Reads ``__FRACTAL_MANIFEST__.json`` from the installed
``fractal_cellpose_sam_task`` package and writes two files:

- ``examples/nextflow/params.yml``
    Human-readable YAML template with all task parameters, their manifest
    defaults, and description comments.  Users copy this file and edit it to
    configure their own analysis.  ``zarr_urls`` is intentionally absent —
    it is a pipeline-level parameter (passed as a Nextflow channel) rather
    than a Fractal task parameter.

- ``examples/nextflow/nextflow_schema.json``
    nf-schema compatible JSON Schema for Nextflow parameter validation.
    Derived from the manifest's ``args_schema_parallel`` schema, with
    ``$defs`` renamed to ``definitions`` (nf-schema convention) and a
    ``zarr_urls`` pipeline parameter group added.

Usage::

    python scripts/generate_nextflow_params.py
"""

from __future__ import annotations

import importlib.resources
import json
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
PARAMS_YML_OUT = REPO_ROOT / "examples" / "nextflow" / "params.yml"
NF_SCHEMA_OUT = REPO_ROOT / "examples" / "nextflow" / "nextflow_schema.json"

# Properties to skip in the output (zarr_url is passed via Nextflow channel)
SKIP_PROPERTIES = {"zarr_url"}


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_manifest() -> dict:
    """Load ``__FRACTAL_MANIFEST__.json`` from the installed package."""
    pkg = importlib.resources.files("fractal_cellpose_sam_task")
    return json.loads((pkg / "__FRACTAL_MANIFEST__.json").read_bytes())


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def get_description(name: str, prop: dict) -> str:
    """Return the human-readable description for a property."""
    return prop.get("description") or prop.get("title") or name


def get_default(prop: dict) -> tuple[bool, object]:
    """Return ``(has_default, value)`` for a top-level property."""
    if "default" in prop:
        return True, prop["default"]
    return False, None


def wrap_comment(text: str, width: int = 78, prefix: str = "# ") -> str:
    """Wrap a description string into ``# …`` comment lines."""
    wrapped = textwrap.fill(text, width=width - len(prefix))
    return "\n".join(prefix + line for line in wrapped.split("\n"))


# ---------------------------------------------------------------------------
# params.yml generation
# ---------------------------------------------------------------------------


def yaml_block(value: object, indent: int = 0) -> str:
    """Serialize *value* as an indented YAML block string (no trailing newline)."""
    raw = yaml.dump(value, default_flow_style=False, allow_unicode=True)
    # Strip trailing YAML document-end marker ("...") and newlines
    raw = raw.rstrip("\n")
    if raw.endswith("\n..."):
        raw = raw[:-4]
    raw = raw.rstrip("\n")
    if indent == 0:
        return raw
    pad = "  " * indent
    return "\n".join(pad + line for line in raw.split("\n"))


def generate_params_yml(schema: dict, task_name: str) -> str:
    """Generate the full params.yml content."""
    props = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    lines: list[str] = [
        f"# Nextflow parameter template — {task_name}",
        "#",
        "# Generated from __FRACTAL_MANIFEST__.json. Edit as needed.",
        "#",
        "# NOTE: zarr_urls (the OME-Zarr images to segment) is a pipeline-level",
        "# parameter — it is NOT listed here because it is passed as a Nextflow",
        "# channel (one job per image).  Specify it via -params-file or on the",
        "# command line:",
        "#",
        "#   zarr_urls:",
        '#     - "/path/to/plate.zarr/B/03/0"   # one entry per image',
        '#     - "/path/to/plate.zarr/B/04/0"   # parallel jobs',
        "",
        "# ── Task parameters (from __FRACTAL_MANIFEST__.json) " + "─" * 25,
    ]

    for name, prop in props.items():
        if name in SKIP_PROPERTIES:
            continue

        desc = get_description(name, prop)
        has_default, default = get_default(prop)
        is_required = name in required_fields

        lines.append("")
        # Description comment
        lines.append(wrap_comment(desc))

        if is_required and not has_default:
            # Required with no default — emit a commented-out example
            lines.append(f"# {name} (required — uncomment and set a value):")
            if name == "channels":
                lines.extend(
                    [
                        "# channels:",
                        '#   mode: "label"       '
                        '# Options: "label" | "wavelength_id" | "index"',
                        "#   identifiers:",
                        '#     - "DAPI"          # 1-3 channel identifiers',
                    ]
                )
            else:
                lines.append(f"# {name}: ~")
        elif has_default:
            value_yaml = yaml_block(default)
            if "\n" in value_yaml or isinstance(default, (dict, list)):
                # Multi-line block value (or dict/list that needs indented block)
                lines.append(f"{name}:")
                lines.append(textwrap.indent(value_yaml, "  "))
            else:
                lines.append(f"{name}: {value_yaml}")
        else:
            # Optional with no default — emit as null (YAML ~)
            lines.append(f"{name}: ~")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# nextflow_schema.json generation
# ---------------------------------------------------------------------------


def rename_refs(obj: object) -> object:
    """Recursively rename ``$defs`` → ``definitions`` in JSON-like objects."""
    if isinstance(obj, dict):
        return {k: rename_refs(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rename_refs(item) for item in obj]
    if isinstance(obj, str):
        return obj.replace("#/$defs/", "#/definitions/")
    return obj


def generate_nf_schema(schema: dict, task_name: str) -> dict:
    """Convert the Fractal task schema to nf-schema format."""
    defs = schema.get("$defs", {})
    props = schema.get("properties", {})
    required_fields = schema.get("required", [])

    # Rename $defs → definitions throughout
    definitions: dict = {k: rename_refs(v) for k, v in defs.items()}

    # Pipeline-level group (zarr_urls)
    pipeline_group: dict = {
        "title": "Pipeline parameters",
        "type": "object",
        "description": "Parameters controlling which data to process.",
        "properties": {
            "zarr_urls": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": (
                    "Full paths to OME-Zarr images to segment. "
                    "Each entry runs as an independent parallel job."
                ),
            },
        },
        "required": ["zarr_urls"],
    }

    # Task-parameter group (all manifest params except zarr_url)
    task_props: dict = {}
    task_required: list[str] = []
    for name, prop in props.items():
        if name in SKIP_PROPERTIES:
            continue
        task_props[name] = rename_refs(prop)
        if name in required_fields:
            task_required.append(name)

    task_group: dict = {
        "title": f"Task parameters — {task_name}",
        "type": "object",
        "description": (
            f"Parameters for the Fractal task '{task_name}'. "
            "Sourced from __FRACTAL_MANIFEST__.json."
        ),
        "properties": task_props,
    }
    if task_required:
        task_group["required"] = task_required

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Nextflow pipeline — {task_name}",
        "description": (
            f"Parameter schema for running the Fractal task '{task_name}' "
            "via Nextflow. Derived from __FRACTAL_MANIFEST__.json."
        ),
        "type": "object",
        "definitions": {
            "pipeline_params": pipeline_group,
            "task_params": task_group,
            **definitions,
        },
        "allOf": [
            {"$ref": "#/definitions/pipeline_params"},
            {"$ref": "#/definitions/task_params"},
        ],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Generate params.yml and nextflow_schema.json from the manifest."""
    manifest = load_manifest()
    task = manifest["task_list"][0]
    task_name: str = task["name"]
    schema: dict = task["args_schema_parallel"]

    params_yml = generate_params_yml(schema, task_name)
    PARAMS_YML_OUT.write_text(params_yml, encoding="utf-8")
    print(f"Written: {PARAMS_YML_OUT.relative_to(REPO_ROOT)}")

    nf_schema = generate_nf_schema(schema, task_name)
    NF_SCHEMA_OUT.write_text(
        json.dumps(nf_schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Written: {NF_SCHEMA_OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
