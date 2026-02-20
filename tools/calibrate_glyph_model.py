#!/usr/bin/env python3
"""Empirical glyph calibration: render reference text with rsvg-convert, measure
actual glyph positions from pixels, and compare with renderer and measurement
tool models.

This script generates minimal calibration SVGs with isolated text labels,
renders them with rsvg-convert at high resolution, and uses pixel analysis to
find actual glyph boundaries. It then compares measured positions against the
renderer's Cairo-based model and the measurement tool's hardcoded model.
"""

# Standard Library
import os
import subprocess
import sys
import tempfile

# PIP3 modules
import numpy
import PIL.Image

# Ensure tools/ is importable for measurelib
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
	sys.path.insert(0, _TOOLS_DIR)

# Ensure packages are importable
_REPO_ROOT = subprocess.run(
	["git", "rev-parse", "--show-toplevel"],
	capture_output=True, text=True, check=True,
).stdout.strip()
_OASA_DIR = os.path.join(_REPO_ROOT, "packages", "oasa")
if _OASA_DIR not in sys.path:
	sys.path.insert(0, _OASA_DIR)

# local repo modules - renderer model
from oasa.render_lib.label_geometry import _text_char_advances
from oasa.render_lib.label_geometry import _visible_label_text
from oasa import render_ops as _ro

# local repo modules - measurement model
from measurelib.glyph_model import (
	label_svg_estimated_primitives,
)


# Calibration parameters
FONT_SIZE = 12.0
FONT_NAME = "sans-serif"
# Scale factor for rsvg rendering (higher = more precise pixel measurement)
RENDER_SCALE = 10
# SVG canvas size (in SVG units)
CANVAS_W = 200
CANVAS_H = 80
# Text placement origin in SVG units
TEXT_X = 100.0
TEXT_Y = 40.0
# Pixel intensity threshold for detecting rendered glyphs
INTENSITY_THRESHOLD = 128


# Labels to calibrate -- plain text and formatted (with subscript markup)
CALIBRATION_LABELS = [
	# (display_text, renderer_markup, anchor)
	("OH", "OH", "start"),
	("HO", "HO", "end"),
	("OH", "OH", "middle"),
	("CH3", "CH<sub>3</sub>", "start"),
	("CH3", "CH<sub>3</sub>", "middle"),
	("CH2OH", "CH<sub>2</sub>OH", "start"),
	("CH2OH", "CH<sub>2</sub>OH", "middle"),
	("CH2OH", "CH<sub>2</sub>OH", "end"),
	("COOH", "COOH", "start"),
	("NH2", "NH<sub>2</sub>", "start"),
	# Single characters for advance calibration
	("O", "O", "start"),
	("H", "H", "start"),
	("C", "C", "start"),
	("N", "N", "start"),
]


#============================================
def _generate_calibration_svg(display_text: str, anchor: str) -> str:
	"""Generate minimal SVG with one text label at known coordinates."""
	# Build SVG with text at (TEXT_X, TEXT_Y) using the specified anchor
	svg_lines = [
		'<?xml version="1.0" encoding="UTF-8"?>',
		f'<svg xmlns="http://www.w3.org/2000/svg" '
		f'width="{CANVAS_W}" height="{CANVAS_H}" '
		f'viewBox="0 0 {CANVAS_W} {CANVAS_H}">',
		'  <rect width="100%" height="100%" fill="white"/>',
		f'  <text x="{TEXT_X}" y="{TEXT_Y}" '
		f'font-family="{FONT_NAME}" font-size="{FONT_SIZE}" '
		f'text-anchor="{anchor}" fill="black">{display_text}</text>',
		'</svg>',
	]
	return "\n".join(svg_lines)


#============================================
def _generate_subscript_svg(display_text: str, renderer_markup: str, anchor: str) -> str:
	"""Generate SVG with tspan subscript structure matching renderer output.

	Converts renderer <sub> markup into SVG <tspan> elements with dy offsets
	and scaled font-size, matching the actual SVG the renderer produces.
	"""
	# If no sub/sup tags, just use plain SVG
	if "<sub>" not in renderer_markup and "<sup>" not in renderer_markup:
		return _generate_calibration_svg(display_text, anchor)
	# Parse renderer markup segments using the same logic as render_ops
	segments = _ro._text_segments(renderer_markup)
	# Build SVG tspan structure matching renderer output
	sub_font_size = FONT_SIZE * _ro.SCRIPT_FONT_SCALE
	inner_parts = []
	baseline_state = "base"
	for chunk, tags in segments:
		segment_state = _ro._segment_baseline_state(tags)
		# Compute dy for baseline transition
		dy_px = _ro._baseline_transition_dy_px(FONT_SIZE, baseline_state, segment_state)
		if segment_state == "sub":
			# Subscript: smaller font, shifted down
			attrs = f' font-size="{sub_font_size:.1f}"'
			if abs(dy_px) > 1e-9:
				attrs += f' dy="{dy_px:.2f}"'
			inner_parts.append(f'<tspan{attrs}>{chunk}</tspan>')
		elif segment_state == "sup":
			# Superscript: smaller font, shifted up
			attrs = f' font-size="{sub_font_size:.1f}"'
			if abs(dy_px) > 1e-9:
				attrs += f' dy="{dy_px:.2f}"'
			inner_parts.append(f'<tspan{attrs}>{chunk}</tspan>')
		else:
			# Base text after a subscript/superscript needs dy reset
			if abs(dy_px) > 1e-9:
				inner_parts.append(f'<tspan dy="{dy_px:.2f}">{chunk}</tspan>')
			else:
				inner_parts.append(chunk)
		baseline_state = segment_state
	text_content = "".join(inner_parts)
	svg_lines = [
		'<?xml version="1.0" encoding="UTF-8"?>',
		f'<svg xmlns="http://www.w3.org/2000/svg" '
		f'width="{CANVAS_W}" height="{CANVAS_H}" '
		f'viewBox="0 0 {CANVAS_W} {CANVAS_H}">',
		'  <rect width="100%" height="100%" fill="white"/>',
		f'  <text x="{TEXT_X}" y="{TEXT_Y}" '
		f'font-family="{FONT_NAME}" font-size="{FONT_SIZE}" '
		f'text-anchor="{anchor}" fill="black">{text_content}</text>',
		'</svg>',
	]
	return "\n".join(svg_lines)


#============================================
def _render_svg_to_array(svg_content: str) -> numpy.ndarray:
	"""Render SVG content via rsvg-convert and return grayscale pixel array."""
	with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as svg_f:
		svg_f.write(svg_content)
		svg_path = svg_f.name
	png_path = svg_path.replace(".svg", ".png")
	try:
		# render at RENDER_SCALE zoom
		subprocess.run(
			["rsvg-convert", "-z", str(RENDER_SCALE), "-o", png_path, svg_path],
			check=True, capture_output=True,
		)
		img = PIL.Image.open(png_path).convert("L")
		pixels = numpy.array(img)
		return pixels
	finally:
		# clean up temp files
		for path in (svg_path, png_path):
			if os.path.exists(path):
				os.unlink(path)


#============================================
def _measure_glyph_columns(
		pixels: numpy.ndarray,
		threshold: int = INTENSITY_THRESHOLD) -> list[tuple[int, int]]:
	"""Find contiguous dark-pixel column ranges in the rendered image.

	Returns list of (col_start, col_end) pairs for each glyph cluster,
	where columns are in pixel coordinates.
	"""
	# Invert: dark text on white background -> high values = text
	inverted = 255 - pixels
	# Threshold to binary
	binary = (inverted > threshold).astype(numpy.uint8)
	# Sum along rows to get per-column density
	col_sums = binary.sum(axis=0)
	# Find columns with any text pixels
	has_text = col_sums > 0
	# Find contiguous runs
	runs = []
	in_run = False
	run_start = 0
	for col_idx in range(len(has_text)):
		if has_text[col_idx] and not in_run:
			in_run = True
			run_start = col_idx
		elif not has_text[col_idx] and in_run:
			in_run = False
			runs.append((run_start, col_idx))
	if in_run:
		runs.append((run_start, len(has_text)))
	return runs


#============================================
def _measure_glyph_rows(
		pixels: numpy.ndarray,
		threshold: int = INTENSITY_THRESHOLD) -> tuple[int, int]:
	"""Find top and bottom row of the text bounding box."""
	inverted = 255 - pixels
	binary = (inverted > threshold).astype(numpy.uint8)
	row_sums = binary.sum(axis=1)
	has_text = row_sums > 0
	rows = numpy.where(has_text)[0]
	if len(rows) == 0:
		return (0, 0)
	return (int(rows[0]), int(rows[-1]))


#============================================
def _split_glyphs_by_gap(
		runs: list[tuple[int, int]],
		min_gap_px: int = 2) -> list[tuple[int, int]]:
	"""Merge adjacent column runs and split by gaps to isolate glyphs."""
	if not runs:
		return []
	merged = [runs[0]]
	for start, end in runs[1:]:
		prev_start, prev_end = merged[-1]
		# If gap between runs is small, merge them (they're part of same glyph)
		if start - prev_end <= min_gap_px:
			merged[-1] = (prev_start, end)
		else:
			merged.append((start, end))
	return merged


#============================================
def _pixel_to_svg(px_col: float) -> float:
	"""Convert pixel column to SVG x coordinate."""
	return px_col / RENDER_SCALE


#============================================
def _measure_actual_glyph_positions(
		display_text: str,
		anchor: str,
		renderer_markup: str = "") -> dict:
	"""Render text with rsvg and measure actual glyph positions.

	Returns dict with:
	- char_centers: list of (svg_x, char) for each character center
	- char_spans: list of (svg_x1, svg_x2, char) for each character
	- text_left: leftmost SVG x of text
	- text_right: rightmost SVG x of text
	- text_top: topmost SVG y of text
	- text_bottom: bottommost SVG y of text
	"""
	# Use subscript SVG when markup contains formatting tags
	if renderer_markup and ("<sub>" in renderer_markup or "<sup>" in renderer_markup):
		svg_content = _generate_subscript_svg(display_text, renderer_markup, anchor)
	else:
		svg_content = _generate_calibration_svg(display_text, anchor)
	pixels = _render_svg_to_array(svg_content)
	# Find column runs
	raw_runs = _measure_glyph_columns(pixels)
	# Find row bounds
	top_row, bottom_row = _measure_glyph_rows(pixels)
	if not raw_runs:
		return {
			"char_centers": [],
			"char_spans": [],
			"text_left": TEXT_X,
			"text_right": TEXT_X,
			"text_top": TEXT_Y,
			"text_bottom": TEXT_Y,
		}
	# Split into individual glyph regions
	glyph_runs = _split_glyphs_by_gap(raw_runs, min_gap_px=max(1, RENDER_SCALE // 4))
	# Convert pixel positions to SVG coordinates
	char_centers = []
	char_spans = []
	for idx, (col_start, col_end) in enumerate(glyph_runs):
		svg_x1 = _pixel_to_svg(col_start)
		svg_x2 = _pixel_to_svg(col_end)
		center_x = (svg_x1 + svg_x2) / 2.0
		char = display_text[idx] if idx < len(display_text) else "?"
		char_centers.append((center_x, char))
		char_spans.append((svg_x1, svg_x2, char))
	# Overall text bounds in SVG coordinates
	all_left = _pixel_to_svg(raw_runs[0][0])
	all_right = _pixel_to_svg(raw_runs[-1][1])
	svg_top = _pixel_to_svg(top_row)
	svg_bottom = _pixel_to_svg(bottom_row)
	return {
		"char_centers": char_centers,
		"char_spans": char_spans,
		"text_left": all_left,
		"text_right": all_right,
		"text_top": svg_top,
		"text_bottom": svg_bottom,
	}


#============================================
def _renderer_model_positions(
		display_text: str,
		renderer_markup: str,
		anchor: str) -> dict:
	"""Compute glyph positions using the renderer's Cairo-based model.

	Returns dict with:
	- char_centers: list of (svg_x, char) for each character center
	- text_left: leftmost x of text box
	- text_right: rightmost x of text box
	"""
	# The renderer calls _label_text_origin to convert from label position to text origin
	# Then uses _text_char_advances for per-character widths
	# For calibration, the SVG text is placed directly at (TEXT_X, TEXT_Y)
	# So the "text origin" IS (TEXT_X, TEXT_Y)
	# The renderer's model reverses this: label_attach_contract_from_text_origin
	# converts text_origin -> label_position -> text_origin (round trip)
	# For the renderer model, start from text_x, text_y
	text = renderer_markup
	visible_text = _visible_label_text(text)
	char_advances = _text_char_advances(text, FONT_SIZE, FONT_NAME)
	if not char_advances or len(char_advances) != len(visible_text):
		char_advances = [FONT_SIZE * 0.60] * len(visible_text)
	total_width = sum(char_advances)
	# Compute cursor start based on anchor
	if anchor == "start":
		cursor_x = TEXT_X
	elif anchor == "middle":
		cursor_x = TEXT_X - total_width / 2.0
	elif anchor == "end":
		cursor_x = TEXT_X - total_width
	else:
		cursor_x = TEXT_X
	char_centers = []
	for idx, char in enumerate(visible_text):
		advance = char_advances[idx]
		center_x = cursor_x + advance / 2.0
		char_centers.append((center_x, char))
		cursor_x += advance
	text_left = char_centers[0][0] - char_advances[0] / 2.0 if char_centers else TEXT_X
	text_right = cursor_x
	return {
		"char_centers": char_centers,
		"text_left": text_left,
		"text_right": text_right,
	}


#============================================
def _measurement_model_positions(display_text: str, anchor: str) -> dict:
	"""Compute glyph positions using the measurement tool's model.

	Returns dict with:
	- char_centers: list of (svg_x, char) for each character center
	- text_left: leftmost x of text box
	- text_right: rightmost x of text box
	"""
	# The measurement tool's label_svg_estimated_primitives takes a label dict
	label = {
		"x": TEXT_X,
		"y": TEXT_Y,
		"anchor": anchor,
		"font_size": FONT_SIZE,
		"font_name": FONT_NAME,
		"text": display_text,
		"text_display": display_text,
		"text_raw": display_text,
	}
	primitives = label_svg_estimated_primitives(label)
	char_centers = []
	for prim in primitives:
		char = prim.get("char", "?")
		if prim["kind"] == "ellipse":
			cx = prim["cx"]
		else:
			box = prim["box"]
			cx = (box[0] + box[2]) / 2.0
		char_centers.append((cx, char))
	# text bounds
	text_left = TEXT_X
	text_right = TEXT_X
	if primitives:
		all_x = []
		for prim in primitives:
			if prim["kind"] == "ellipse":
				all_x.extend([prim["cx"] - prim["rx"], prim["cx"] + prim["rx"]])
			else:
				all_x.extend([prim["box"][0], prim["box"][2]])
		text_left = min(all_x)
		text_right = max(all_x)
	return {
		"char_centers": char_centers,
		"text_left": text_left,
		"text_right": text_right,
	}


#============================================
def _compare_models(
		display_text: str,
		renderer_markup: str,
		anchor: str) -> dict:
	"""Compare all three models for one label configuration."""
	actual = _measure_actual_glyph_positions(display_text, anchor, renderer_markup)
	renderer = _renderer_model_positions(display_text, renderer_markup, anchor)
	measurement = _measurement_model_positions(display_text, anchor)
	# Compute deltas
	result = {
		"display_text": display_text,
		"anchor": anchor,
		"actual": actual,
		"renderer": renderer,
		"measurement": measurement,
		"renderer_deltas": [],
		"measurement_deltas": [],
	}
	# Compare per-character centers (renderer vs actual)
	actual_centers = actual["char_centers"]
	renderer_centers = renderer["char_centers"]
	measurement_centers = measurement["char_centers"]
	n_chars = min(len(actual_centers), len(renderer_centers))
	for i in range(n_chars):
		delta = renderer_centers[i][0] - actual_centers[i][0]
		result["renderer_deltas"].append(
			(renderer_centers[i][1], delta)
		)
	n_chars_m = min(len(actual_centers), len(measurement_centers))
	for i in range(n_chars_m):
		delta = measurement_centers[i][0] - actual_centers[i][0]
		result["measurement_deltas"].append(
			(measurement_centers[i][1], delta)
		)
	# Overall text width comparison
	result["actual_width"] = actual["text_right"] - actual["text_left"]
	result["renderer_width"] = renderer["text_right"] - renderer["text_left"]
	result["measurement_width"] = measurement["text_right"] - measurement["text_left"]
	return result


#============================================
def _format_delta(delta: float) -> str:
	"""Format a delta value with sign for display."""
	if delta >= 0:
		return f"+{delta:.3f}"
	return f"{delta:.3f}"


#============================================
def main() -> None:
	"""Run calibration and print comparison tables."""
	print("=" * 80)
	print("Glyph Model Calibration")
	print(f"Font: {FONT_NAME}, Size: {FONT_SIZE}, Scale: {RENDER_SCALE}x")
	print("=" * 80)
	print()
	all_renderer_deltas = []
	all_measurement_deltas = []
	for display_text, renderer_markup, anchor in CALIBRATION_LABELS:
		result = _compare_models(display_text, renderer_markup, anchor)
		# Print header
		print(f"--- {display_text} (anchor={anchor}) ---")
		actual = result["actual"]
		# Print text width comparison
		print(f"  Text width:  actual={result['actual_width']:.3f}  "
			f"renderer={result['renderer_width']:.3f}  "
			f"measure={result['measurement_width']:.3f}")
		# Print text bounds
		print(f"  Actual bounds: left={actual['text_left']:.3f}  right={actual['text_right']:.3f}  "
			f"top={actual['text_top']:.3f}  bottom={actual['text_bottom']:.3f}")
		# Print per-character centers comparison
		actual_centers = actual["char_centers"]
		renderer_centers = result["renderer"]["char_centers"]
		measurement_centers = result["measurement"]["char_centers"]
		n = max(len(actual_centers), len(renderer_centers), len(measurement_centers))
		if n > 0:
			print(f"  {'char':<5} {'actual_cx':>10} {'render_cx':>10} {'meas_cx':>10} "
				f"{'rend_delta':>11} {'meas_delta':>11}")
			for i in range(n):
				char = "?"
				act_x = "---"
				rend_x = "---"
				meas_x = "---"
				rend_d = "---"
				meas_d = "---"
				if i < len(actual_centers):
					char = actual_centers[i][1]
					act_x = f"{actual_centers[i][0]:.3f}"
				if i < len(renderer_centers):
					if char == "?":
						char = renderer_centers[i][1]
					rend_x = f"{renderer_centers[i][0]:.3f}"
				if i < len(measurement_centers):
					if char == "?":
						char = measurement_centers[i][1]
					meas_x = f"{measurement_centers[i][0]:.3f}"
				if i < len(actual_centers) and i < len(renderer_centers):
					delta = renderer_centers[i][0] - actual_centers[i][0]
					rend_d = _format_delta(delta)
					all_renderer_deltas.append(delta)
				if i < len(actual_centers) and i < len(measurement_centers):
					delta = measurement_centers[i][0] - actual_centers[i][0]
					meas_d = _format_delta(delta)
					all_measurement_deltas.append(delta)
				print(f"  {char:<5} {act_x:>10} {rend_x:>10} {meas_x:>10} "
					f"{rend_d:>11} {meas_d:>11}")
		# Check if glyph count matches character count
		if len(actual_centers) != len(display_text):
			print(f"  WARNING: detected {len(actual_centers)} glyphs "
				f"but text has {len(display_text)} chars")
		print()
	# Summary statistics
	print("=" * 80)
	print("SUMMARY")
	print("=" * 80)
	if all_renderer_deltas:
		arr = numpy.array(all_renderer_deltas)
		print("Renderer model vs rsvg actual:")
		print(f"  Mean delta:   {numpy.mean(arr):+.4f}")
		print(f"  Std delta:    {numpy.std(arr):.4f}")
		print(f"  Max abs:      {numpy.max(numpy.abs(arr)):.4f}")
		print(f"  Median delta: {numpy.median(arr):+.4f}")
	if all_measurement_deltas:
		arr = numpy.array(all_measurement_deltas)
		print("Measurement model vs rsvg actual:")
		print(f"  Mean delta:   {numpy.mean(arr):+.4f}")
		print(f"  Std delta:    {numpy.std(arr):.4f}")
		print(f"  Max abs:      {numpy.max(numpy.abs(arr)):.4f}")
		print(f"  Median delta: {numpy.median(arr):+.4f}")


if __name__ == "__main__":
	main()
