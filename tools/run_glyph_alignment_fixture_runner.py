#!/usr/bin/env python3
"""Run scaffold glyph-alignment fixtures and write per-fixture diagnostics."""

# Standard Library
import json
import argparse
import pathlib
import datetime
import importlib.util


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse runner CLI args."""
	parser = argparse.ArgumentParser(
		description="Run glyph-alignment fixture scaffold through measurement tool."
	)
	parser.add_argument(
		"--fixtures-dir",
		dest="fixtures_dir",
		default="tests/fixtures/glyph_alignment",
		help="Directory containing fixture SVG+JSON pairs.",
	)
	parser.add_argument(
		"--output-dir",
		dest="output_dir",
		default="output_smoke/glyph_alignment_fixture_runner",
		help="Output directory for per-fixture reports.",
	)
	parser.add_argument(
		"--alignment-center-mode",
		dest="alignment_center_mode",
		default="optical",
		choices=("primitive", "optical"),
		help="Alignment center mode forwarded to measurement tool.",
	)
	parser.add_argument(
		"--include-haworth-base-ring",
		action="store_true",
		default=False,
		help="Include Haworth base ring checks (default excludes base ring).",
	)
	parser.add_argument(
		"--render-png",
		action="store_true",
		help="Convert diagnostic SVG overlays to PNG with cairosvg (default: on).",
	)
	parser.add_argument(
		"--no-render-png",
		dest="render_png",
		action="store_false",
		help="Disable diagnostic PNG conversion.",
	)
	parser.add_argument(
		"--png-scale",
		dest="png_scale",
		type=float,
		default=4.0,
		help="CairoSVG scale factor for diagnostic PNG conversion (default: 4.0).",
	)
	parser.add_argument(
		"--fail-on-expectation",
		action="store_true",
		default=False,
		help="Exit non-zero when any required expectation check fails.",
	)
	parser.set_defaults(render_png=True)
	return parser.parse_args()


#============================================
def _repo_root() -> pathlib.Path:
	"""Return repo root from this script location."""
	return pathlib.Path(__file__).resolve().parents[1]


#============================================
def _load_measure_tool(repo_root: pathlib.Path) -> object:
	"""Load tools/measure_glyph_bond_alignment.py as a module."""
	tool_path = repo_root / "tools" / "measure_glyph_bond_alignment.py"
	spec = importlib.util.spec_from_file_location("measure_glyph_bond_alignment", tool_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Could not load tool module from {tool_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


#============================================
def _load_sidecar(svg_path: pathlib.Path) -> dict:
	"""Load fixture sidecar JSON, or empty dict when missing."""
	sidecar_path = svg_path.with_suffix(".json")
	if not sidecar_path.is_file():
		return {}
	return json.loads(sidecar_path.read_text(encoding="utf-8"))


#============================================
def _evaluate_expectations(report: dict, sidecar: dict) -> tuple[list[dict], list[dict]]:
	"""Return (checks, failures) from sidecar expectations against one report."""
	expectations = sidecar.get("expectations", {})
	checks = []
	failures = []

	min_labels = expectations.get("min_labels_analyzed")
	if min_labels is not None:
		passed = int(report.get("labels_analyzed", 0)) >= int(min_labels)
		check = {
			"type": "min_labels_analyzed",
			"expected": int(min_labels),
			"actual": int(report.get("labels_analyzed", 0)),
			"pass": bool(passed),
		}
		checks.append(check)
		if not passed:
			failures.append(check)

	max_outside = expectations.get("max_outside_tolerance")
	if max_outside is not None:
		actual_outside = int(report.get("alignment_outside_tolerance_count", 0))
		passed = actual_outside <= int(max_outside)
		check = {
			"type": "max_outside_tolerance",
			"expected": int(max_outside),
			"actual": actual_outside,
			"pass": bool(passed),
		}
		checks.append(check)
		if not passed:
			failures.append(check)

	labels_by_index = {}
	for label in report.get("labels", []):
		label_index = label.get("label_index")
		if label_index is None:
			continue
		labels_by_index[int(label_index)] = label

	for target in expectations.get("target_centerlines", []):
		label_index = target.get("label_index")
		required = bool(target.get("required", True))
		if label_index is None:
			continue
		label = labels_by_index.get(int(label_index))
		if label is None:
			check = {
				"type": "target_centerline",
				"label_index": int(label_index),
				"required": required,
				"pass": False,
				"reason": "label_index_not_found",
			}
			checks.append(check)
			if required:
				failures.append(check)
			continue
		point = label.get("alignment_center_point")
		expected_center_x = target.get("expected_center_x")
		if expected_center_x is None or point is None or len(point) != 2:
			check = {
				"type": "target_centerline",
				"label_index": int(label_index),
				"required": required,
				"pass": False,
				"reason": "missing_expected_or_point",
			}
			checks.append(check)
			if required:
				failures.append(check)
			continue
		font_size = float(target.get("font_size", label.get("font_size", 12.0)))
		tolerance_factor = float(target.get("tolerance_factor", 0.15))
		tolerance = tolerance_factor * font_size
		delta = abs(float(point[0]) - float(expected_center_x))
		passed = delta <= tolerance
		check = {
			"type": "target_centerline",
			"label_index": int(label_index),
			"required": required,
			"expected_center_x": float(expected_center_x),
			"actual_center_x": float(point[0]),
			"delta": float(delta),
			"tolerance": float(tolerance),
			"pass": bool(passed),
		}
		checks.append(check)
		if required and (not passed):
			failures.append(check)

	c_retention = expectations.get("c_stripe_min_retention_ratio")
	if c_retention is not None:
		candidates = []
		for label in report.get("labels", []):
			if str(label.get("alignment_center_char", "")).upper() != "C":
				continue
			gate = label.get("optical_gate_debug") or {}
			component_count = gate.get("component_point_count")
			stripe_count = gate.get("stripe_point_count")
			stripe_applied = bool(gate.get("stripe_applied", False))
			if not isinstance(component_count, int) or component_count <= 0:
				continue
			if stripe_applied:
				if not isinstance(stripe_count, int):
					continue
				retention_count = int(stripe_count)
			else:
				# When stripe gate is intentionally skipped, do not treat that as amputation.
				retention_count = int(component_count)
			retention = float(retention_count) / float(component_count)
			candidates.append(
				{
					"label_index": int(label.get("label_index", -1)),
					"stripe_applied": stripe_applied,
					"retention_ratio": retention,
					"component_point_count": int(component_count),
					"stripe_point_count": int(stripe_count) if isinstance(stripe_count, int) else None,
				}
			)
		required = bool(expectations.get("c_stripe_min_retention_required", True))
		if not candidates:
			check = {
				"type": "c_stripe_min_retention_ratio",
				"required": required,
				"pass": False,
				"reason": "no_c_alignment_labels_found",
				"expected_min_ratio": float(c_retention),
			}
			checks.append(check)
			if required:
				failures.append(check)
		else:
			min_observed = min(item["retention_ratio"] for item in candidates)
			passed = min_observed >= float(c_retention)
			check = {
				"type": "c_stripe_min_retention_ratio",
				"required": required,
				"pass": bool(passed),
				"expected_min_ratio": float(c_retention),
				"observed_min_ratio": float(min_observed),
				"candidates": candidates,
			}
			checks.append(check)
			if required and (not passed):
				failures.append(check)

	for requirement in expectations.get("min_final_point_count_by_char", []):
		target_char = str(requirement.get("target_char", "")).upper().strip()
		if not target_char:
			continue
		min_count = requirement.get("min_count")
		if min_count is None:
			continue
		required = bool(requirement.get("required", True))
		candidates = []
		for label in report.get("labels", []):
			label_char = str(label.get("alignment_center_char", "")).upper().strip()
			if label_char != target_char:
				continue
			gate = label.get("optical_gate_debug") or {}
			final_count = gate.get("final_point_count")
			if not isinstance(final_count, int):
				continue
			candidates.append(
				{
					"label_index": int(label.get("label_index", -1)),
					"final_point_count": int(final_count),
				}
			)
		if not candidates:
			check = {
				"type": "min_final_point_count_by_char",
				"target_char": target_char,
				"required": required,
				"pass": False,
				"reason": "no_matching_labels_found",
				"expected_min_count": int(min_count),
			}
			checks.append(check)
			if required:
				failures.append(check)
			continue
		min_observed = min(item["final_point_count"] for item in candidates)
		passed = min_observed >= int(min_count)
		check = {
			"type": "min_final_point_count_by_char",
			"target_char": target_char,
			"required": required,
			"pass": bool(passed),
			"expected_min_count": int(min_count),
			"observed_min_count": int(min_observed),
			"candidates": candidates,
		}
		checks.append(check)
		if required and (not passed):
			failures.append(check)

	return checks, failures


#============================================
def _try_render_png(svg_path: pathlib.Path, png_path: pathlib.Path, scale: float) -> bool:
	"""Best-effort SVG->PNG conversion with cairosvg."""
	try:
		import cairosvg
	except ImportError:
		return False
	cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), scale=max(0.1, float(scale)))
	return True


#============================================
def _run_fixture(
		module: object, svg_path: pathlib.Path, sidecar: dict,
		args: argparse.Namespace, output_dir: pathlib.Path) -> dict:
	"""Run one fixture through measure tool and write outputs."""
	fixture_dir = output_dir / svg_path.stem
	diagnostic_dir = fixture_dir / "diagnostics"
	diagnostic_dir.mkdir(parents=True, exist_ok=True)

	report = module.analyze_svg_file(
		svg_path=svg_path,
		exclude_haworth_base_ring=(not args.include_haworth_base_ring),
		bond_glyph_gap_tolerance=module.BOND_GLYPH_GAP_TOLERANCE,
		alignment_center_mode=str(args.alignment_center_mode),
		write_diagnostic_svg=True,
		diagnostic_svg_dir=diagnostic_dir,
	)
	summary = module._summary_stats([report])
	top_misses = module._top_misses([report])
	text_report = module._text_report(
		summary=summary,
		top_misses=top_misses,
		input_glob=str(svg_path),
		exclude_haworth_base_ring=(not args.include_haworth_base_ring),
		alignment_center_mode=str(args.alignment_center_mode),
	)
	checks, failures = _evaluate_expectations(report=report, sidecar=sidecar)

	report_payload = {
		"fixture": str(svg_path),
		"sidecar": sidecar,
		"checks": checks,
		"required_failures": failures,
		"report": report,
		"summary": summary,
		"top_misses": top_misses,
	}
	json_path = fixture_dir / "fixture_report.json"
	text_path = fixture_dir / "fixture_report.txt"
	json_path.write_text(json.dumps(report_payload, indent=2, sort_keys=True), encoding="utf-8")
	text_path.write_text(text_report, encoding="utf-8")

	diagnostic_svg = report.get("diagnostic_svg")
	diagnostic_png = None
	if args.render_png and diagnostic_svg:
		diag_svg_path = pathlib.Path(diagnostic_svg)
		scale_suffix = f".{float(args.png_scale):g}x"
		diag_png_path = diag_svg_path.with_suffix(f"{scale_suffix}.png")
		if _try_render_png(diag_svg_path, diag_png_path, scale=float(args.png_scale)):
			diagnostic_png = str(diag_png_path)

	return {
		"fixture": str(svg_path),
		"name": svg_path.stem,
		"labels_analyzed": int(report.get("labels_analyzed", 0)),
		"alignment_outside_tolerance_count": int(report.get("alignment_outside_tolerance_count", 0)),
		"required_failure_count": len(failures),
		"required_failures": failures,
		"diagnostic_svg": diagnostic_svg,
		"diagnostic_png": diagnostic_png,
		"json_report": str(json_path),
		"text_report": str(text_path),
	}


#============================================
def _write_runner_summary(output_dir: pathlib.Path, items: list[dict]) -> tuple[pathlib.Path, pathlib.Path]:
	"""Write runner summary files and return their paths."""
	now_text = datetime.datetime.now().isoformat(timespec="seconds")
	total = len(items)
	total_required_failures = sum(int(item.get("required_failure_count", 0)) for item in items)
	fixtures_with_required_failures = sum(
		1 for item in items if int(item.get("required_failure_count", 0)) > 0
	)
	payload = {
		"generated_at": now_text,
		"fixtures_total": total,
		"fixtures_with_required_failures": fixtures_with_required_failures,
		"total_required_failures": total_required_failures,
		"items": items,
	}
	json_path = output_dir / "fixture_runner_summary.json"
	text_path = output_dir / "fixture_runner_summary.txt"
	json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

	lines = []
	lines.append("Glyph Alignment Fixture Runner Summary")
	lines.append(f"Generated at: {now_text}")
	lines.append(f"Fixtures total: {total}")
	lines.append(f"Fixtures with required failures: {fixtures_with_required_failures}")
	lines.append(f"Total required failures: {total_required_failures}")
	lines.append("")
	for item in items:
		lines.append(f"- fixture: {item.get('fixture')}")
		lines.append(f"  labels analyzed: {item.get('labels_analyzed')}")
		lines.append(
			f"  alignment outside tolerance: {item.get('alignment_outside_tolerance_count')}"
		)
		lines.append(f"  required failures: {item.get('required_failure_count')}")
		lines.append(f"  diagnostic svg: {item.get('diagnostic_svg')}")
		lines.append(f"  diagnostic png: {item.get('diagnostic_png')}")
		lines.append(f"  json report: {item.get('json_report')}")
	text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
	return json_path, text_path


#============================================
def main() -> None:
	"""Run all glyph-alignment fixture scaffolds."""
	args = parse_args()
	repo_root = _repo_root()
	fixtures_dir = (repo_root / args.fixtures_dir).resolve()
	output_dir = (repo_root / args.output_dir).resolve()
	output_dir.mkdir(parents=True, exist_ok=True)
	module = _load_measure_tool(repo_root)

	svg_paths = sorted(fixtures_dir.glob("*.svg"))
	if not svg_paths:
		raise RuntimeError(f"No fixture SVG files found in {fixtures_dir}")

	items = []
	for svg_path in svg_paths:
		sidecar = _load_sidecar(svg_path)
		item = _run_fixture(
			module=module,
			svg_path=svg_path,
			sidecar=sidecar,
			args=args,
			output_dir=output_dir,
		)
		items.append(item)

	summary_json, summary_text = _write_runner_summary(output_dir=output_dir, items=items)
	fixtures_with_required_failures = sum(
		1 for item in items if int(item.get("required_failure_count", 0)) > 0
	)
	total_required_failures = sum(int(item.get("required_failure_count", 0)) for item in items)
	print(f"Wrote fixture runner JSON summary: {summary_json}")
	print(f"Wrote fixture runner text summary: {summary_text}")
	print(f"Fixtures analyzed: {len(items)}")
	print(f"Fixtures with required failures: {fixtures_with_required_failures}")
	print(f"Total required failures: {total_required_failures}")
	print(f"Output directory: {output_dir}")
	if args.fail_on_expectation and total_required_failures > 0:
		raise SystemExit(2)


if __name__ == "__main__":
	main()
