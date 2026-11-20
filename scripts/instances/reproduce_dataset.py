#!/usr/bin/env python3
"""Reproduce and verify benchmark graph instances from versioned metadata.json.

Reads exact generation, conversion, and selection provenance from
``dataset/processed/<dataset>/metadata.json``, invokes ``external/graph-instances``
to rebuild the requested datasets, copies the selected ``.col`` files into
``dataset/processed/<dataset>/instances/``, and verifies every file against the
recorded SHA-256 checksums.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_ROOT = PROJECT_ROOT / "dataset" / "processed"
SUBMODULE_ROOT = PROJECT_ROOT / "external" / "graph-instances"
GRAPH_INSTANCES_CLI = SUBMODULE_ROOT / "graph_instances.py"

REAL_DATASETS = ("harwell_boeing", "dimacs", "bhoslib", "snap")
SYNTHETIC_DATASETS = ("cubic", "erdos_renyi", "barabasi_albert", "watts_strogatz")
ALL_DATASETS = (*REAL_DATASETS, *SYNTHETIC_DATASETS)

DEFAULT_FRESH_GENERATION_ARGS: dict[str, list[str]] = {
    "cubic": [
        "generate",
        "cubic",
        "--doubling",
        "100",
        "1.045",
        "106",
        "--count",
        "1",
        "--remove-isolated",
    ],
    "erdos_renyi": [
        "generate",
        "erdos-renyi",
        "--doubling",
        "100",
        "1.045",
        "103",
        "--avg-degree",
        "12",
        "--count",
        "1",
        "--remove-isolated",
    ],
    "barabasi_albert": [
        "generate",
        "barabasi-albert",
        "--doubling",
        "100",
        "1.045",
        "103",
        "--m",
        "4",
        "--count",
        "1",
        "--remove-isolated",
    ],
    "watts_strogatz": [
        "generate",
        "watts-strogatz",
        "--doubling",
        "100",
        "1.045",
        "98",
        "--k",
        "6",
        "--p-rewire",
        "0.15",
        "--count",
        "1",
        "--remove-isolated",
    ],
}


def format_number(value: float | int) -> str:
    """Format numeric CLI arguments cleanly (integers without trailing .0)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:g}"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file in streaming chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_datasets(args: argparse.Namespace) -> list[str]:
    """Resolve the ordered list of dataset folder names to process."""
    if args.fresh and args.auto:
        raise ValueError("--fresh and --auto are mutually exclusive")

    existing_meta = {
        path.parent.name
        for path in PROCESSED_ROOT.glob("*/metadata.json")
    }
    if args.fresh:
        available = set(ALL_DATASETS)
    elif args.auto:
        available = set(ALL_DATASETS) | existing_meta
    else:
        available = existing_meta
        if not available:
            raise FileNotFoundError(
                f"No metadata.json files found under {PROCESSED_ROOT}. "
                "Use --fresh (or --auto) to generate a brand-new dataset from scratch."
            )

    if args.datasets:
        requested = [name.replace("-", "_") for name in args.datasets]
        missing = [name for name in requested if name not in available]
        if missing:
            raise ValueError(
                f"Unknown dataset(s): {', '.join(missing)}. "
                f"Available: {', '.join(sorted(available))}"
            )
        return list(dict.fromkeys(requested))

    if args.synthetic_only and args.real_only:
        raise ValueError("--synthetic-only and --real-only are mutually exclusive")

    if args.synthetic_only:
        ordered = [name for name in SYNTHETIC_DATASETS if name in available]
    elif args.real_only:
        ordered = [name for name in REAL_DATASETS if name in available]
    else:
        ordered = [name for name in ALL_DATASETS if name in available]
        ordered.extend(sorted(available - set(ordered)))
    return ordered


def _submodule_env() -> dict[str, str]:
    """Return a clean environment for subprocesses inside external/graph-instances."""
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["PROJECT_ROOT"] = str(SUBMODULE_ROOT)
    return env


def _has_required_packages(python_cmd: list[str]) -> bool:
    """Return True if the submodule Python can import all runtime dependencies."""
    probe = subprocess.run(
        [
            *python_cmd,
            "-c",
            "import networkx, numpy, requests, scipy, sklearn",
        ],
        cwd=SUBMODULE_ROOT,
        env=_submodule_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return probe.returncode == 0


def resolve_submodule_python(bootstrap: bool, dry_run: bool) -> list[str]:
    """Locate (and optionally bootstrap) the Python interpreter for external/graph-instances."""
    venv_python = SUBMODULE_ROOT / ".venv" / "bin" / "python"
    if dry_run:
        return [str(venv_python)]

    if venv_python.is_file():
        cmd = [str(venv_python)]
        if _has_required_packages(cmd):
            return cmd
        if bootstrap:
            print("Installing missing dependencies in external/graph-instances/.venv...")
            subprocess.run(
                [*cmd, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=SUBMODULE_ROOT,
                env=_submodule_env(),
                check=True,
            )
            return cmd

    if bootstrap:
        mise_bin = shutil.which("mise")
        if mise_bin:
            print("Submodule .venv not found; bootstrapping via mise + pip...")
            subprocess.run(
                [mise_bin, "trust", str(SUBMODULE_ROOT / "mise.toml")],
                cwd=SUBMODULE_ROOT,
                env=_submodule_env(),
                check=True,
            )
            subprocess.run(
                [mise_bin, "install"],
                cwd=SUBMODULE_ROOT,
                env=_submodule_env(),
                check=True,
            )
            subprocess.run(
                [
                    mise_bin,
                    "exec",
                    "--",
                    "python",
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                ],
                cwd=SUBMODULE_ROOT,
                env=_submodule_env(),
                check=True,
            )
            if venv_python.is_file():
                return [str(venv_python)]
            return [mise_bin, "exec", "--", "python"]

    raise RuntimeError(
        f"Submodule virtual environment not found or incomplete at {venv_python}.\n"
        "Initialize it first (with mise or standard Python venv):\n"
        "  # With mise:\n"
        "  cd external/graph-instances && mise trust && mise install && "
        "source .venv/bin/activate && pip install -r requirements.txt\n"
        "  # Without mise:\n"
        "  cd external/graph-instances && python3 -m venv .venv && "
        "source .venv/bin/activate && pip install -r requirements.txt"
    )


def run_cli(
    python_cmd: list[str],
    cli_args: list[str],
    dry_run: bool,
) -> None:
    """Invoke external/graph-instances/graph_instances.py."""
    cmd = [*python_cmd, str(GRAPH_INSTANCES_CLI), *cli_args]
    rendered = " ".join(shlex.quote(part) for part in cmd)
    print(f"  $ {rendered}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=SUBMODULE_ROOT, env=_submodule_env(), check=True)


def build_generate_args(dataset: str, generation: dict) -> list[str]:
    """Reconstruct exact graph_instances.py generate CLI arguments from metadata."""
    model = generation.get("model") or dataset.replace("_", "-")
    params = generation["parameters"]
    args: list[str] = ["generate", model]

    doubling = params.get("doubling")
    if doubling is not None:
        args.extend(["--doubling", *(format_number(v) for v in doubling)])
    elif params.get("vertex_counts"):
        args.extend(["--vertices", *(str(int(n)) for n in params["vertex_counts"])])

    if model == "erdos-renyi":
        if params.get("p") is not None:
            args.extend(["--p", *(format_number(v) for v in params["p"])])
        elif params.get("avg_degree") is not None:
            args.extend(
                ["--avg-degree", *(format_number(v) for v in params["avg_degree"])]
            )
    elif model == "barabasi-albert":
        if params.get("m") is not None:
            args.extend(["--m", *(str(int(v)) for v in params["m"])])
    elif model == "watts-strogatz":
        if params.get("k") is not None:
            args.extend(["--k", *(str(int(v)) for v in params["k"])])
        if params.get("p_rewire") is not None:
            args.extend(
                ["--p-rewire", *(format_number(v) for v in params["p_rewire"])]
            )

    if params.get("reps") is not None:
        args.extend(["--count", str(int(params["reps"]))])

    if generation.get("initial_seed") is not None:
        args.extend(["--seed", str(int(generation["initial_seed"]))])

    if params.get("remove_isolated"):
        args.append("--remove-isolated")

    return args


def build_select_args(dataset: str, selection: dict) -> list[str]:
    """Reconstruct exact graph_instances.py select CLI arguments from metadata."""
    target = dataset.replace("_", "-")
    params = selection["parameters"]
    args: list[str] = [
        "select",
        target,
        "--count",
        str(int(params["requested_count"])),
        "--seed",
        str(int(params["seed"])),
        "--bfs-samples",
        str(int(params["bfs_samples"])),
        "--exact-triangle-edges",
        str(int(params["exact_triangle_edges"])),
        "--triangle-samples",
        str(int(params["triangle_samples"])),
        "--max-vertices",
        str(int(params["max_vertices"])),
        "--memory-limit-mb",
        str(int(params["memory_limit_mb"])),
        "--timeout-s",
        format_number(params["timeout_s"]),
        "--max-per-series",
        str(int(params["max_per_series"])),
    ]
    if params.get("skip_edgeless"):
        args.append("--skip-edgeless")
    if not params.get("log_scale", True):
        args.append("--no-log-scale")
    return args


def clean_col_files(directory: Path, dry_run: bool) -> None:
    """Remove existing top-level .col files in directory."""
    if not directory.is_dir():
        return
    col_files = list(directory.glob("*.col"))
    if not col_files:
        return
    print(f"  Cleaning {len(col_files)} existing .col file(s) in {directory}")
    if dry_run:
        return
    for path in col_files:
        path.unlink()


def sync_selected_to_root(
    dataset: str,
    update_metadata: bool,
    dry_run: bool,
) -> None:
    """Copy selected .col instances (and optionally metadata/CSV) to dataset/processed."""
    sub_base = SUBMODULE_ROOT / "datasets" / dataset
    src_selected = sub_base / "selected"
    dst_base = PROCESSED_ROOT / dataset
    dst_instances = dst_base / "instances"

    print(f"  Syncing {src_selected}/*.col -> {dst_instances}/")
    if dry_run:
        return

    if not src_selected.is_dir():
        raise FileNotFoundError(f"Selected directory not found: {src_selected}")

    dst_instances.mkdir(parents=True, exist_ok=True)
    src_files = sorted(src_selected.glob("*.col"))
    src_names = {path.name for path in src_files}

    for existing in dst_instances.glob("*.col"):
        if existing.name not in src_names:
            existing.unlink()

    for path in src_files:
        shutil.copy2(path, dst_instances / path.name)

    if update_metadata:
        print(f"  Updating {dst_base}/metadata.json and selection.csv")
        for extra in ("metadata.json", "selection.csv"):
            src_extra = sub_base / extra
            if src_extra.is_file():
                shutil.copy2(src_extra, dst_base / extra)

    print(f"  Copied {len(src_files)} .col file(s) to {dst_instances}")


def verify_dataset(dataset: str) -> tuple[int, int, int]:
    """Verify selected .col files against SHA-256 hashes in metadata.json.

    Returns:
        Tuple ``(checked, missing, mismatched)``.
    """
    meta_path = PROCESSED_ROOT / dataset / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    inst_dir = meta_path.parent / "instances"
    expected_items = meta["selection"]["selected_graphs"]

    checked = 0
    missing = 0
    mismatched = 0
    for item in expected_items:
        fpath = inst_dir / item["file"]
        if not fpath.is_file():
            print(f"  [MISSING]  {dataset}/{item['file']}")
            missing += 1
            continue
        actual_hash = sha256_file(fpath)
        if actual_hash != item["sha256"]:
            print(
                f"  [MISMATCH] {dataset}/{item['file']} "
                f"(expected {item['sha256'][:12]}..., got {actual_hash[:12]}...)"
            )
            mismatched += 1
        checked += 1

    expected_names = {item["file"] for item in expected_items}
    extra = (
        sorted(p.name for p in inst_dir.glob("*.col") if p.name not in expected_names)
        if inst_dir.is_dir()
        else []
    )
    for name in extra:
        print(f"  [EXTRA]    {dataset}/{name} (not listed in metadata.json)")

    status = "OK" if (missing == 0 and mismatched == 0 and not extra) else "FAIL"
    print(
        f"  [{status}] {dataset}: {checked - mismatched}/{len(expected_items)} "
        f"verified (missing={missing}, mismatched={mismatched}, extra={len(extra)})"
    )
    return checked, missing, mismatched + len(extra)


def generate_fresh_dataset(
    dataset: str,
    python_cmd: list[str],
    args: argparse.Namespace,
) -> None:
    """Build a brand-new dataset from scratch (fresh random seeds) and update metadata."""
    target = dataset.replace("_", "-")
    sub_base = SUBMODULE_ROOT / "datasets" / dataset

    print(f"\n=== [{dataset}] (fresh) ===")
    if dataset in DEFAULT_FRESH_GENERATION_ARGS:
        if not args.no_clean:
            clean_col_files(sub_base / "processed", args.dry_run)
            clean_col_files(sub_base / "selected", args.dry_run)
            sub_meta = sub_base / "metadata.json"
            if sub_meta.is_file():
                print(f"  Removing previous {sub_meta}")
                if not args.dry_run:
                    sub_meta.unlink()
        run_cli(python_cmd, DEFAULT_FRESH_GENERATION_ARGS[dataset], args.dry_run)
    else:
        if not args.skip_download:
            run_cli(python_cmd, ["download", target], args.dry_run)
        run_cli(python_cmd, ["convert", target, "--remove-isolated"], args.dry_run)

    run_cli(python_cmd, ["filter", target, "--remove-isolated"], args.dry_run)
    select_seed = (
        args.select_seed
        if args.select_seed is not None
        else secrets.randbelow(2**31)
    )
    if args.select_seed is None:
        print(f"  Using random selection seed: {select_seed}")
    run_cli(
        python_cmd,
        [
            "select",
            target,
            "--count",
            str(args.count),
            "--seed",
            str(select_seed),
        ],
        args.dry_run,
    )

    sync_selected_to_root(
        dataset,
        update_metadata=True,
        dry_run=args.dry_run,
    )


def reproduce_dataset(
    dataset: str,
    python_cmd: list[str],
    args: argparse.Namespace,
) -> None:
    """Reproduce a single dataset from its versioned metadata.json."""
    meta_path = PROCESSED_ROOT / dataset / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    target = dataset.replace("_", "-")
    sub_base = SUBMODULE_ROOT / "datasets" / dataset

    print(f"\n=== [{dataset}] ===")
    remove_isolated = False

    if "generation" in meta:
        generation = meta["generation"]
        remove_isolated = bool(generation.get("parameters", {}).get("remove_isolated"))
        if not args.no_clean:
            clean_col_files(sub_base / "processed", args.dry_run)
        gen_args = build_generate_args(dataset, generation)
        run_cli(python_cmd, gen_args, args.dry_run)
    else:
        if "download" in meta and not args.skip_download:
            download_args = ["download", target]
            download_cmd = meta["download"].get("command") or []
            if "--include-friendster" in download_cmd:
                download_args.append("--include-friendster")
            run_cli(python_cmd, download_args, args.dry_run)
        if "conversion" in meta:
            conversion = meta["conversion"]
            remove_isolated = bool(
                conversion.get("parameters", {}).get("remove_isolated")
            )
            convert_args = ["convert", target]
            if remove_isolated:
                convert_args.append("--remove-isolated")
            run_cli(python_cmd, convert_args, args.dry_run)

    if remove_isolated:
        run_cli(python_cmd, ["filter", target, "--remove-isolated"], args.dry_run)

    if "selection" not in meta:
        raise ValueError(f"Missing 'selection' section in {meta_path}")
    select_args = build_select_args(dataset, meta["selection"])
    run_cli(python_cmd, select_args, args.dry_run)

    sync_selected_to_root(
        dataset,
        update_metadata=args.update_metadata,
        dry_run=args.dry_run,
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce benchmark .col instances into dataset/processed/ "
            "using the exact parameters and seeds in metadata.json."
        )
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Automatically reproduce any dataset that already has "
            "dataset/processed/<ds>/metadata.json, or generate it fresh from "
            "scratch when metadata.json does not exist."
        ),
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help=(
            "Generate a brand-new dataset from scratch with fresh random seeds "
            "for synthetic models (does not require existing metadata.json) and "
            "updates dataset/processed/<ds>/{instances,metadata.json,selection.csv}."
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Representative instances to select per dataset in --fresh mode (default: 30).",
    )
    parser.add_argument(
        "--select-seed",
        type=int,
        default=None,
        help=(
            "K-Means selection seed used in --fresh mode "
            "(default: random seed per dataset, saved to metadata.json)."
        ),
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        help=(
            "Specific dataset(s) to process (hyphen or underscore names, e.g. "
            "cubic erdos-renyi snap). Defaults to all datasets with metadata.json."
        ),
    )
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Process only the 4 synthetic datasets (cubic, erdos_renyi, barabasi_albert, watts_strogatz).",
    )
    parser.add_argument(
        "--real-only",
        action="store_true",
        help="Process only the 4 real/benchmark datasets (harwell_boeing, dimacs, bhoslib, snap).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading real datasets (reuse existing external/graph-instances/datasets/<ds>/raw/).",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete existing .col files in submodule processed/ before synthetic generation.",
    )
    parser.add_argument(
        "--update-metadata",
        action="store_true",
        help="Also overwrite dataset/processed/<ds>/{metadata.json,selection.csv} with newly generated files.",
    )
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Do not attempt to auto-install external/graph-instances/.venv when missing.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip SHA-256 verification after copying instances.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify SHA-256 checksums of existing dataset/processed/<ds>/instances/*.col.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print all commands that would be executed without modifying any files.",
    )
    return parser.parse_args()


def main() -> None:
    """Run dataset reproduction and/or SHA-256 verification."""
    args = parse_args()
    datasets = discover_datasets(args)

    if args.verify_only:
        print(f"Verifying {len(datasets)} dataset(s) against metadata.json SHA-256 hashes...")
        total_checked = 0
        total_missing = 0
        total_errors = 0
        for dataset in datasets:
            checked, missing, errors = verify_dataset(dataset)
            total_checked += checked
            total_missing += missing
            total_errors += errors
        print(
            f"\nSummary: checked={total_checked}, missing={total_missing}, "
            f"mismatched_or_extra={total_errors}"
        )
        if total_missing or total_errors:
            raise SystemExit(1)
        return

    if not GRAPH_INSTANCES_CLI.is_file():
        git_bin = shutil.which("git")
        if git_bin and not args.no_bootstrap:
            print("Submodule external/graph-instances not initialized; running git submodule update...")
            if not args.dry_run:
                subprocess.run(
                    [git_bin, "submodule", "update", "--init", "--recursive"],
                    cwd=PROJECT_ROOT,
                    check=True,
                )
        if not args.dry_run and not GRAPH_INSTANCES_CLI.is_file():
            raise FileNotFoundError(
                f"Submodule CLI not found at {GRAPH_INSTANCES_CLI}.\n"
                "Run: git submodule update --init --recursive"
            )

    python_cmd = resolve_submodule_python(
        bootstrap=not args.no_bootstrap,
        dry_run=args.dry_run,
    )

    for dataset in datasets:
        has_metadata = (PROCESSED_ROOT / dataset / "metadata.json").is_file()
        if args.fresh or (args.auto and not has_metadata):
            if args.auto:
                print(f"[auto] {dataset}: metadata.json not found -> running fresh generation")
            generate_fresh_dataset(dataset, python_cmd, args)
        else:
            if args.auto:
                print(f"[auto] {dataset}: metadata.json found -> reproducing from metadata")
            reproduce_dataset(dataset, python_cmd, args)

    if not args.dry_run and not args.skip_verify:
        print("\n=== SHA-256 Verification ===")
        total_missing = 0
        total_errors = 0
        for dataset in datasets:
            _, missing, errors = verify_dataset(dataset)
            total_missing += missing
            total_errors += errors
        if total_missing or total_errors:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
