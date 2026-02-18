"""Offline/test calibration harness for glyph primitive attachment contracts."""

# Standard Library
import argparse
import json

# local repo modules
from oasa import render_geometry

try:
	import cairo
except ImportError:
	cairo = None


CALIBRATION_FONTS = ("sans-serif", "Arial")
CALIBRATION_GLYPHS = ("C", "O", "S", "N", "H", "P")
CALIBRATION_SITES = ("core_center", "stem_centerline", "closed_center")
CALIBRATION_FONT_SIZE = 72.0

CENTERLINE_ERROR_THRESHOLD = 0.20
BOUNDARY_HIT_ERROR_THRESHOLD = 0.36


#============================================
def _glyph_outline_metrics(symbol: str, font_name: str, font_size: float) -> dict:
	"""Return normalized center/boundary metrics from one rendered glyph outline."""
	if cairo is None:
		raise RuntimeError("cairo is required for glyph calibration")
	padding = 36
	surface = cairo.ImageSurface(cairo.FORMAT_A8, 320, 320)
	context = cairo.Context(surface)
	context.set_source_rgba(0.0, 0.0, 0.0, 0.0)
	context.paint()
	context.select_font_face(font_name, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
	context.set_font_size(float(font_size))
	extents = context.text_extents(symbol)
	origin_x = padding - extents.x_bearing
	origin_y = padding - extents.y_bearing
	context.move_to(origin_x, origin_y)
	context.text_path(symbol)
	context.set_source_rgba(1.0, 1.0, 1.0, 1.0)
	context.fill()
	width = surface.get_width()
	height = surface.get_height()
	stride = surface.get_stride()
	data = memoryview(surface.get_data())
	pixels = []
	for row in range(height):
		row_offset = row * stride
		for col in range(width):
			alpha = int(data[row_offset + col])
			if alpha > 0:
				pixels.append((col, row, alpha))
	if not pixels:
		raise RuntimeError(f"No rendered pixels for glyph {symbol!r} font={font_name!r}")
	min_x = min(col for col, _row, _alpha in pixels)
	max_x = max(col for col, _row, _alpha in pixels)
	min_y = min(row for _col, row, _alpha in pixels)
	max_y = max(row for _col, row, _alpha in pixels)
	total_alpha = sum(alpha for _col, _row, alpha in pixels)
	centroid_x = sum((col + 0.5) * alpha for col, _row, alpha in pixels) / float(total_alpha)
	centroid_y = sum((row + 0.5) * alpha for _col, row, alpha in pixels) / float(total_alpha)
	def _runs_for_row(row_index: int) -> list[tuple[int, int]]:
		row_offset = row_index * stride
		runs = []
		run_start = None
		for col in range(min_x, max_x + 1):
			alpha = int(data[row_offset + col])
			if alpha > 0:
				if run_start is None:
					run_start = col
				continue
			if run_start is not None:
				runs.append((run_start, col - 1))
				run_start = None
		if run_start is not None:
			runs.append((run_start, max_x))
		return runs
	stem_samples = []
	for row_index in range(min_y, max_y + 1):
		runs = _runs_for_row(row_index)
		if not runs:
			continue
		run_start, run_end = runs[0]
		if run_start > (min_x + 2):
			continue
		run_width = run_end - run_start + 1.0
		if run_width <= 0.0:
			continue
		stem_samples.append((run_width, run_start + (run_width * 0.5)))
	row_candidates = [int(round(centroid_y))]
	for delta in range(1, 12):
		row_candidates.append(int(round(centroid_y)) - delta)
		row_candidates.append(int(round(centroid_y)) + delta)
	selected_row = None
	selected_runs = []
	for row_index in row_candidates:
		if row_index < min_y or row_index > max_y:
			continue
		runs = _runs_for_row(row_index)
		if runs:
			selected_row = row_index
			selected_runs = runs
			break
	if selected_row is None:
		raise RuntimeError(f"No sample row runs for glyph {symbol!r} font={font_name!r}")
	left_run_start, left_run_end = selected_runs[0]
	left_outer_boundary_x = left_run_start + 0.5
	left_inner_boundary_x = left_run_end + 0.5
	right_boundary_x = selected_runs[-1][1] + 0.5
	left_run_center_x = ((left_run_start + left_run_end + 1.0) * 0.5)
	bbox_width = max(1.0, (max_x - min_x + 1.0))
	if stem_samples:
		stem_samples.sort(key=lambda item: item[0])
		use_count = max(1, len(stem_samples) // 3)
		selected_stem = stem_samples[:use_count]
		stem_center_x = sum(center for _width, center in selected_stem) / float(use_count)
	else:
		stem_center_x = left_run_center_x
	def _factor(x_value: float) -> float:
		return (x_value - min_x) / bbox_width
	return {
		"symbol": symbol,
		"font_name": font_name,
		"font_size": float(font_size),
		"bbox": (min_x, min_y, max_x, max_y),
		"sample_row": int(selected_row),
		"centroid_factor": _factor(centroid_x),
		"stem_center_factor": _factor(stem_center_x),
		"left_run_center_factor": _factor(left_run_center_x),
		"outer_left_boundary_factor": _factor(left_outer_boundary_x),
		"inner_left_boundary_factor": _factor(left_inner_boundary_x),
		"right_boundary_factor": _factor(right_boundary_x),
	}


#============================================
def _primitive_metrics(symbol: str, font_name: str, font_size: float) -> dict:
	"""Return normalized primitive centerline/boundary metrics for one glyph."""
	advances = render_geometry._text_char_advances(symbol, float(font_size), font_name)
	span_width = float(advances[0]) if advances else float(font_size * 0.60)
	span_width = max(1e-6, span_width)
	primitive = render_geometry.glyph_attach_primitive(
		symbol=symbol,
		span_x1=0.0,
		span_x2=span_width,
		y1=0.0,
		y2=1.0,
		font_size=float(font_size),
		font_name=font_name,
	)
	metrics = {
		"symbol": symbol,
		"font_name": font_name,
		"glyph_class": primitive.glyph_class,
	}
	for site in CALIBRATION_SITES:
		metrics[f"{site}_center_factor"] = primitive.center_x(site) / span_width
		metrics[f"{site}_left_boundary_factor"] = primitive.left_boundary_x(site) / span_width
		metrics[f"{site}_right_boundary_factor"] = primitive.right_boundary_x(site) / span_width
	return metrics


#============================================
def _closed_center_truth_factor(
		symbol: str,
		outline_metrics: dict,
		closed_surrogate_metrics: dict) -> float:
	"""Return closed-center truth factor for one symbol."""
	if symbol == "C":
		return float(closed_surrogate_metrics["centroid_factor"])
	return float(outline_metrics["centroid_factor"])


#============================================
def build_calibration_report(
		font_names: tuple[str, ...] = CALIBRATION_FONTS,
		glyphs: tuple[str, ...] = CALIBRATION_GLYPHS,
		font_size: float = CALIBRATION_FONT_SIZE) -> dict:
	"""Build full per-font glyph primitive calibration report."""
	rows = []
	calibration_table = {}
	for font_name in font_names:
		closed_surrogate = _glyph_outline_metrics("O", font_name, font_size)
		calibration_table[font_name] = {}
		for symbol in glyphs:
			outline = _glyph_outline_metrics(symbol, font_name, font_size)
			primitive = _primitive_metrics(symbol, font_name, font_size)
			center_truth = {
				"core_center": float(outline["centroid_factor"]),
				"stem_centerline": float(outline["stem_center_factor"]),
				"closed_center": _closed_center_truth_factor(symbol, outline, closed_surrogate),
			}
			if symbol in ("C", "O", "P"):
				core_left_boundary = float(outline["inner_left_boundary_factor"])
			else:
				core_left_boundary = float(outline["outer_left_boundary_factor"])
			boundary_truth = {
				"core_center": core_left_boundary,
				"stem_centerline": float(outline["outer_left_boundary_factor"]),
				"closed_center": core_left_boundary,
			}
			center_errors = {}
			boundary_errors = {}
			for site in CALIBRATION_SITES:
				pred_center = float(primitive[f"{site}_center_factor"])
				pred_boundary = float(primitive[f"{site}_left_boundary_factor"])
				center_errors[site] = abs(pred_center - center_truth[site])
				boundary_errors[site] = abs(pred_boundary - boundary_truth[site])
			row = {
				"font_name": font_name,
				"symbol": symbol,
				"glyph_class": primitive["glyph_class"],
				"center_truth": center_truth,
				"boundary_truth": boundary_truth,
				"primitive_predicted": {
					site: {
						"center_factor": float(primitive[f"{site}_center_factor"]),
						"left_boundary_factor": float(primitive[f"{site}_left_boundary_factor"]),
					}
					for site in CALIBRATION_SITES
				},
				"centerline_errors": center_errors,
				"boundary_hit_errors": boundary_errors,
				"max_centerline_error": max(center_errors.values()),
				"max_boundary_hit_error": max(boundary_errors.values()),
			}
			rows.append(row)
			calibration_table[font_name][symbol] = {
				"glyph_class": primitive["glyph_class"],
				"core_center": float(primitive["core_center_center_factor"]),
				"stem_centerline": float(primitive["stem_centerline_center_factor"]),
				"closed_center": float(primitive["closed_center_center_factor"]),
			}
	return {
		"font_names": list(font_names),
		"glyphs": list(glyphs),
		"font_size": float(font_size),
		"sites": list(CALIBRATION_SITES),
		"thresholds": {
			"centerline_error_max": CENTERLINE_ERROR_THRESHOLD,
			"boundary_hit_error_max": BOUNDARY_HIT_ERROR_THRESHOLD,
		},
		"rows": rows,
		"calibration_table": calibration_table,
	}


#============================================
def format_calibration_report(report: dict) -> str:
	"""Format one ASCII calibration table report."""
	lines = []
	lines.append("font\tsymbol\tclass\tmax_center_err\tmax_boundary_err")
	for row in report["rows"]:
		lines.append(
			f"{row['font_name']}\t{row['symbol']}\t{row['glyph_class']}\t"
			f"{row['max_centerline_error']:.4f}\t{row['max_boundary_hit_error']:.4f}"
		)
	lines.append("")
	lines.append("per_font_calibration_table:")
	lines.append(json.dumps(report["calibration_table"], indent=2, sort_keys=True))
	return "\n".join(lines)


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments for calibration harness."""
	parser = argparse.ArgumentParser(
		description="Build glyph primitive calibration report for attach contracts."
	)
	parser.add_argument(
		"--output-json",
		dest="output_json",
		default="",
		help="Optional JSON output path for full report payload.",
	)
	return parser.parse_args()


#============================================
def main() -> None:
	"""Run calibration harness and print report table."""
	args = parse_args()
	report = build_calibration_report()
	print(format_calibration_report(report))
	if args.output_json:
		with open(args.output_json, "w", encoding="utf-8") as file_handle:
			json.dump(report, file_handle, indent=2, sort_keys=True)


if __name__ == "__main__":
	main()
