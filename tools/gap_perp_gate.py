#!/usr/bin/env python3
"""Gap/perp gate: compact JSON report for glyph-bond alignment fixture buckets.

Runs the existing SVG measurement pipeline on one or more fixture buckets
and emits a compact JSON with per-label stats and failure reason counts.
"""

# Standard Library
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys

# Ensure the tools/ directory is on sys.path so measurelib can be imported.
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
	sys.path.insert(0, _TOOLS_DIR)

from measurelib.analysis import analyze_svg_file
from measurelib.reporting import summary_stats
from measurelib.svg_parse import resolve_svg_paths

# 11 alignment target molecules -- fast representative subset of the
# full 78-file Haworth corpus.  Covers furanose/pyranose, alpha/beta,
# and the label types that historically fail gap/perp spec.
HAWORTH_GATE_TARGETS = (
	"ARDM_furanose_alpha",
	"ARRDM_furanose_beta",
	"ARRDM_pyranose_alpha",
	"ALLDM_furanose_beta",
	"ALLDM_pyranose_alpha",
	"ARRRDM_furanose_alpha",
	"ARRRDM_pyranose_alpha",
	"ARRLDM_furanose_alpha",
	"MKRDM_furanose_alpha",
	"ARRLLd_pyranose_alpha",
	"ARLLDc_pyranose_alpha",
)

# Haworth SVG directory (relative to repo root)
_HAWORTH_SVG_DIR = "output_smoke/archive_matrix_previews/generated"

# Fixture bucket definitions.
# "glob" buckets resolve a glob pattern against the repo root.
# "targets" buckets resolve explicit stems from a known directory.
FIXTURE_BUCKETS = {
	"haworth": {
		"type": "targets",
		"dir": _HAWORTH_SVG_DIR,
		"targets": HAWORTH_GATE_TARGETS,
		"description": "11 alignment-target Haworth molecules (fast)",
	},
	"haworth_full": {
		"type": "glob",
		"glob": _HAWORTH_SVG_DIR + "/*.svg",
		"description": "Full 78-file Haworth corpus (slow)",
	},
	"oasa_generic": {
		"type": "glob",
		"glob": "output_smoke/oasa_generic_renders/*.svg",
		"description": "OASA generic molecule renders (non-Haworth)",
	},
	"bkchem": {
		"type": "glob",
		"glob": "output_smoke/bkchem_render_ops/*.svg",
		"description": "BKChem render-ops corpus",
	},
}

DEFAULT_OUTPUT = "output_smoke/gap_perp_gate.json"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Run glyph-bond alignment gate on fixture buckets.",
	)
	parser.add_argument(
		"-b", "--bucket",
		dest="bucket",
		type=str,
		default=None,
		help="Fixture bucket to process (default: all with files).",
	)
	parser.add_argument(
		"-a", "--all-buckets",
		dest="all_buckets",
		action="store_true",
		help="Process all fixture buckets.",
	)
	parser.add_argument(
		"-s", "--skip-all-buckets",
		dest="all_buckets",
		action="store_false",
		help="Process only the named bucket.",
	)
	parser.add_argument(
		"-o", "--output",
		dest="output",
		type=str,
		default=DEFAULT_OUTPUT,
		help="Output path for compact JSON report.",
	)
	parser.set_defaults(all_buckets=True)
	return parser.parse_args()


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		raise RuntimeError("Could not detect repo root via git rev-parse --show-toplevel")
	return pathlib.Path(result.stdout.strip())


#============================================
def _round_or_none(value: object, decimals: int = 2) -> object:
	"""Round a float or return None."""
	if value is None:
		return None
	return round(float(value), decimals)


#============================================
def build_gate_report(file_reports: list[dict], bucket_name: str, source_desc: str) -> dict:
	"""Build compact gate JSON from per-file analysis reports."""
	summary = summary_stats(file_reports)
	# aggregate failure reason counts from per-label data
	reason_counts: dict[str, int] = {}
	for report in file_reports:
		for label in report.get("labels", []):
			if label.get("aligned", False):
				continue
			reason = label.get("reason", "unknown")
			reason_counts[reason] = reason_counts.get(reason, 0) + 1
	# per-label compact stats from summary
	per_label: dict[str, dict] = {}
	label_stats = summary.get("alignment_label_type_stats", {})
	for label_text in sorted(label_stats.keys()):
		entry = label_stats[label_text]
		gap = entry.get("gap_distance_stats", {})
		perp = entry.get("perpendicular_distance_stats", {})
		per_label[label_text] = {
			"count": entry["count"],
			"aligned_count": entry["aligned_count"],
			"alignment_rate": _round_or_none(entry["alignment_rate"], 4),
			"gap": {
				"mean": _round_or_none(gap.get("mean")),
				"stddev": _round_or_none(gap.get("stddev")),
				"median": _round_or_none(gap.get("median")),
			} if gap.get("count", 0) > 0 else {},
			"perp": {
				"mean": _round_or_none(perp.get("mean")),
				"stddev": _round_or_none(perp.get("stddev")),
				"median": _round_or_none(perp.get("median")),
			} if perp.get("count", 0) > 0 else {},
		}
	return {
		"bucket": bucket_name,
		"source": source_desc,
		"files_analyzed": summary["files_analyzed"],
		"labels_analyzed": summary["labels_analyzed"],
		"aligned_count": summary["aligned_labels"],
		"missed_count": summary["missed_labels"],
		"no_connector_count": summary["labels_without_connector"],
		"alignment_rate": _round_or_none(summary["alignment_rate"], 4),
		"per_label": per_label,
		"reason_counts": dict(sorted(reason_counts.items())),
	}


#============================================
def _resolve_bucket_paths(repo_root: pathlib.Path, bucket_name: str) -> tuple:
	"""Resolve SVG paths for a bucket.  Returns (svg_paths, source_desc)."""
	config = FIXTURE_BUCKETS[bucket_name]
	bucket_type = config.get("type", "glob")
	if bucket_type == "targets":
		# explicit target stems from a known directory
		svg_dir = repo_root / config["dir"]
		targets = config["targets"]
		svg_paths = []
		for stem in targets:
			path = svg_dir / f"{stem}.svg"
			if path.exists():
				svg_paths.append(path)
		source_desc = f"{config['dir']}/ ({len(targets)} targets)"
		return sorted(svg_paths), source_desc
	# default: glob pattern
	glob_pattern = config["glob"]
	svg_paths = resolve_svg_paths(repo_root, glob_pattern)
	return svg_paths, glob_pattern


#============================================
def _empty_report(bucket_name: str, source_desc: str) -> dict:
	"""Return a skipped/empty gate report."""
	return {
		"bucket": bucket_name,
		"source": source_desc,
		"files_analyzed": 0,
		"labels_analyzed": 0,
		"aligned_count": 0,
		"missed_count": 0,
		"no_connector_count": 0,
		"alignment_rate": 0.0,
		"per_label": {},
		"reason_counts": {},
		"skipped": True,
	}


#============================================
def run_bucket(repo_root: pathlib.Path, bucket_name: str) -> dict:
	"""Analyze one fixture bucket and return its gate report."""
	svg_paths, source_desc = _resolve_bucket_paths(repo_root, bucket_name)
	if not svg_paths:
		return _empty_report(bucket_name, source_desc)
	# run analysis without diagnostic output for speed
	file_reports = [
		analyze_svg_file(
			path,
			exclude_haworth_base_ring=True,
			write_diagnostic_svg=False,
		)
		for path in svg_paths
	]
	return build_gate_report(file_reports, bucket_name, source_desc)


#============================================
def print_bucket_summary(report: dict) -> None:
	"""Print concise console summary for one bucket."""
	bucket = report["bucket"]
	files = report["files_analyzed"]
	labels = report["labels_analyzed"]
	aligned = report["aligned_count"]
	if report.get("skipped"):
		print(f"  {bucket}: (no files)")
		return
	rate_pct = report["alignment_rate"] * 100.0
	print(f"  {bucket}: {files} files, {labels} labels, {aligned} aligned ({rate_pct:.1f}%)")
	# reason breakdown
	reasons = report.get("reason_counts", {})
	if reasons:
		reason_parts = ", ".join(f"{k}={v}" for k, v in sorted(reasons.items()))
		print(f"    reasons: {reason_parts}")


#============================================
def main() -> None:
	"""Run gap/perp gate on fixture buckets and write compact JSON."""
	args = parse_args()
	repo_root = get_repo_root()
	# decide which buckets to process
	if args.bucket is not None:
		if args.bucket not in FIXTURE_BUCKETS:
			available = ", ".join(sorted(FIXTURE_BUCKETS.keys()))
			raise SystemExit(f"Unknown bucket: {args.bucket!r}. Available: {available}")
		bucket_names = [args.bucket]
	else:
		bucket_names = sorted(FIXTURE_BUCKETS.keys())
	# run each bucket
	buckets: dict[str, dict] = {}
	for name in bucket_names:
		print(f"Processing bucket: {name}")
		buckets[name] = run_bucket(repo_root, name)
	# build output JSON
	output = {
		"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"buckets": buckets,
	}
	# write output
	output_path = pathlib.Path(args.output)
	if not output_path.is_absolute():
		output_path = (repo_root / output_path).resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
	# console summary
	print()
	print("Gap/perp gate results:")
	for name in bucket_names:
		print_bucket_summary(buckets[name])
	print()
	print(f"Wrote: {output_path}")


if __name__ == "__main__":
	main()
