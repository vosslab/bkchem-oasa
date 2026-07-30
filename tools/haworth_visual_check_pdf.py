#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

"""Generate a one-page Haworth Phase 3 visual-check PDF."""

# Standard Library
import argparse
import os
import re
import subprocess
import sys
import tempfile

# Third Party
import cairo


#============================================
def get_repo_root() -> str:
	"""Return repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


repo_root = get_repo_root()
oasa_dir = os.path.join(repo_root, "packages", "oasa")
if oasa_dir not in sys.path:
	sys.path.insert(0, oasa_dir)

# local repo modules
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
import oasa.render_ops as render_ops
import oasa.sugar_code as sugar_code


PAGE_WIDTH = 792.0
PAGE_HEIGHT = 612.0
MARGIN = 18.0
GAP_X = 14.0
GAP_Y = 14.0
COLS = 2
ROWS = 4
TITLE_HEIGHT = 18.0

CASES = [
	{
		"title": "ARLRDM pyranose alpha: C1 OH down",
		"code": "ARLRDM",
		"ring_type": "pyranose",
		"anomeric": "alpha",
	},
	{
		"title": "ARLRDM pyranose beta: C1 OH up",
		"code": "ARLRDM",
		"ring_type": "pyranose",
		"anomeric": "beta",
	},
	{
		"title": "MKLRDM furanose alpha: C2 OH down",
		"code": "MKLRDM",
		"ring_type": "furanose",
		"anomeric": "alpha",
	},
	{
		"title": "MKLRDM furanose beta: C2 OH up",
		"code": "MKLRDM",
		"ring_type": "furanose",
		"anomeric": "beta",
	},
	{
		"title": "ARLRDM furanose: C4 chain CHOH -> CH2OH",
		"code": "ARLRDM",
		"ring_type": "furanose",
		"anomeric": "alpha",
	},
	{
		"title": "ARRDM pyranose: closure has no exocyclic chain",
		"code": "ARRDM",
		"ring_type": "pyranose",
		"anomeric": "alpha",
	},
	{
		"title": "ARDM furanose: no exocyclic chain",
		"code": "ARDM",
		"ring_type": "furanose",
		"anomeric": "beta",
	},
	{
		"title": "ARLRDM pyranose alpha with bg_color f0f0f0",
		"code": "ARLRDM",
		"ring_type": "pyranose",
		"anomeric": "alpha",
		"bg_color": "#f0f0f0",
		"panel_bg": "#f0f0f0",
	},
]


#============================================
def _visible_text_length(text: object) -> int:
	return len(re.sub(r"<[^>]+>", "", text or ""))


#============================================
def _bbox(ops: object) -> tuple[float, float, float, float]:
	minx = float("inf")
	miny = float("inf")
	maxx = float("-inf")
	maxy = float("-inf")

	def _take(x: float, y: float) -> None:
		nonlocal minx
		nonlocal miny
		nonlocal maxx
		nonlocal maxy
		minx = min(minx, x)
		miny = min(miny, y)
		maxx = max(maxx, x)
		maxy = max(maxy, y)

	for op in ops:
		if isinstance(op, render_ops.LineOp):
			_take(op.p1[0], op.p1[1])
			_take(op.p2[0], op.p2[1])
		elif isinstance(op, render_ops.PolygonOp):
			for x, y in op.points:
				_take(x, y)
		elif isinstance(op, render_ops.TextOp):
			visible = _visible_text_length(op.text)
			width = visible * op.font_size * 0.6
			height = op.font_size
			x = op.x
			if op.anchor == "middle":
				x -= width / 2.0
			elif op.anchor == "end":
				x -= width
			_take(x, op.y - height)
			_take(x + width, op.y)
	if minx == float("inf"):
		return (0.0, 0.0, 1.0, 1.0)
	return (minx, miny, maxx, maxy)


#============================================
def _transform_ops(ops: object, dx: float, dy: float, scale: float) -> list[object]:
	transformed = []
	for op in ops:
		if isinstance(op, render_ops.LineOp):
			transformed.append(
				render_ops.LineOp(
					p1=(op.p1[0] * scale + dx, op.p1[1] * scale + dy),
					p2=(op.p2[0] * scale + dx, op.p2[1] * scale + dy),
					width=op.width * scale,
					cap=op.cap,
					join=op.join,
					color=op.color,
					z=op.z,
					op_id=op.op_id,
				)
			)
		elif isinstance(op, render_ops.PolygonOp):
			points = tuple((x * scale + dx, y * scale + dy) for x, y in op.points)
			transformed.append(
				render_ops.PolygonOp(
					points=points,
					fill=op.fill,
					stroke=op.stroke,
					stroke_width=op.stroke_width * scale,
					z=op.z,
					op_id=op.op_id,
				)
			)
		elif isinstance(op, render_ops.TextOp):
			transformed.append(
				render_ops.TextOp(
					x=op.x * scale + dx,
					y=op.y * scale + dy,
					text=op.text,
					font_size=op.font_size * scale,
					font_name=op.font_name,
					anchor=op.anchor,
					weight=op.weight,
					color=op.color,
					z=op.z,
					op_id=op.op_id,
				)
			)
	return transformed


#============================================
def _build_case_ops(case: dict, show_carbon_numbers: bool = False) -> object:
	parsed = sugar_code.parse(case["code"])
	spec = haworth_spec.generate(
		parsed,
		ring_type=case["ring_type"],
		anomeric=case["anomeric"],
	)
	return haworth_renderer.render(
		spec,
		bond_length=30.0,
		show_carbon_numbers=show_carbon_numbers,
		show_hydrogens=False,
		bg_color=case.get("bg_color", "#fff"),
		line_color="#000",
		label_color="#000",
	)


#============================================
def _add_panel_decoration(
		all_ops: list[object], x: float, y: float, width: float,
		height: float, title: str, panel_bg: str) -> None:
	panel_points = (
		(x, y),
		(x + width, y),
		(x + width, y + height),
		(x, y + height),
	)
	all_ops.append(
		render_ops.PolygonOp(
			points=panel_points,
			fill=panel_bg,
			stroke=None,
			stroke_width=0.0,
			z=0,
		)
	)
	border = "#bcbcbc"
	all_ops.append(
		render_ops.LineOp(p1=(x, y), p2=(x + width, y), width=0.8, color=border, z=9)
	)
	all_ops.append(
		render_ops.LineOp(
			p1=(x + width, y),
			p2=(x + width, y + height),
			width=0.8,
			color=border,
			z=9,
		)
	)
	all_ops.append(
		render_ops.LineOp(
			p1=(x + width, y + height),
			p2=(x, y + height),
			width=0.8,
			color=border,
			z=9,
		)
	)
	all_ops.append(
		render_ops.LineOp(p1=(x, y + height), p2=(x, y), width=0.8, color=border, z=9)
	)
	all_ops.append(
		render_ops.TextOp(
			x=x + (width / 2.0),
			y=y + 13.0,
			text=title,
			font_size=9.0,
			font_name="sans-serif",
			anchor="middle",
			weight="bold",
			color="#222",
			z=10,
		)
	)


#============================================
def generate_pdf(output_path: str, show_carbon_numbers: bool = False) -> None:
	cell_width = (PAGE_WIDTH - (2 * MARGIN) - ((COLS - 1) * GAP_X)) / COLS
	cell_height = (PAGE_HEIGHT - (2 * MARGIN) - ((ROWS - 1) * GAP_Y)) / ROWS

	all_ops = []
	for index, case in enumerate(CASES):
		row = index // COLS
		col = index % COLS
		cell_x = MARGIN + col * (cell_width + GAP_X)
		cell_y = MARGIN + row * (cell_height + GAP_Y)

		panel_bg = case.get("panel_bg", "#fff")
		_add_panel_decoration(
			all_ops,
			cell_x,
			cell_y,
			cell_width,
			cell_height,
			case["title"],
			panel_bg,
		)

		case_ops = _build_case_ops(case, show_carbon_numbers=show_carbon_numbers)
		minx, miny, maxx, maxy = _bbox(case_ops)
		content_width = max(1.0, maxx - minx)
		content_height = max(1.0, maxy - miny)

		draw_x = cell_x + 8.0
		draw_y = cell_y + TITLE_HEIGHT + 6.0
		draw_width = cell_width - 16.0
		draw_height = cell_height - TITLE_HEIGHT - 12.0

		scale = min(draw_width / content_width, draw_height / content_height)
		dx = draw_x + ((draw_width - (content_width * scale)) / 2.0) - (minx * scale)
		dy = draw_y + ((draw_height - (content_height * scale)) / 2.0) - (miny * scale)
		all_ops.extend(_transform_ops(case_ops, dx, dy, scale))

	all_ops.append(
		render_ops.TextOp(
			x=PAGE_WIDTH / 2.0,
			y=12.0,
			text="Phase 3 Haworth Visual Checksheet",
			font_size=11.0,
			font_name="sans-serif",
			anchor="middle",
			weight="bold",
			color="#111",
			z=20,
		)
	)
	all_ops.append(
		render_ops.TextOp(
			x=PAGE_WIDTH / 2.0,
			y=24.0,
			text="Confirm alpha/beta flips, chain behavior, edge depth cue, and O-mask blending",
			font_size=8.0,
			font_name="sans-serif",
			anchor="middle",
			weight="normal",
			color="#444",
			z=20,
		)
	)

	surface = cairo.PDFSurface(output_path, PAGE_WIDTH, PAGE_HEIGHT)
	context = cairo.Context(surface)
	context.set_source_rgb(1, 1, 1)
	context.paint()
	render_ops.ops_to_cairo(context, all_ops)
	surface.finish()


#============================================
def parse_args() -> argparse.Namespace:
	default_output = os.path.join(tempfile.gettempdir(), "haworth_phase3_checks.pdf")
	parser = argparse.ArgumentParser(
		description="Generate Haworth visual-check PDF for manual review"
	)
	parser.add_argument(
		"-o",
		"--out",
		dest="output",
		default=default_output,
		help=f"Output PDF path (default: {default_output})",
	)
	parser.add_argument(
		"--show-carbon-numbers",
		action="store_true",
		default=False,
		help="Render carbon-number labels inside each Haworth ring",
	)
	return parser.parse_args()


#============================================
def main() -> None:
	args = parse_args()
	generate_pdf(args.output, show_carbon_numbers=args.show_carbon_numbers)
	print(args.output)


#============================================
if __name__ == "__main__":
	main()
