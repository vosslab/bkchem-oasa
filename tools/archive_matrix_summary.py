#!/usr/bin/env python3
"""Build a human-friendly HTML summary for archive matrix smoke outputs."""

# Standard Library
import argparse
import datetime
import html
import os
import pathlib
import re
import subprocess
import sys
from xml.dom import minidom as xml_minidom

# Third Party
import defusedxml.ElementTree as ET

GENERATED_PREVIEW_SCALE = 0.80
GENERATED_PREVIEW_BG_COLOR = "#fafafa"


#============================================
def _box_intersection_area(
		box_a: tuple[float, float, float, float],
		box_b: tuple[float, float, float, float]) -> float:
	"""Return overlap area for two axis-aligned boxes."""
	ax1, ay1, ax2, ay2 = box_a
	bx1, by1, bx2, by2 = box_b
	overlap_w = min(ax2, bx2) - max(ax1, bx1)
	overlap_h = min(ay2, by2) - max(ay1, by1)
	if overlap_w <= 0.0 or overlap_h <= 0.0:
		return 0.0
	return overlap_w * overlap_h


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Build HTML summary for Haworth archive matrix outputs."
	)
	parser.add_argument(
		"--strict-render-checks",
		dest="strict_render_checks",
		action="store_true",
		help=(
			"Fail generated preview regeneration when bond/label or label/label "
			"overlaps are detected."
		),
	)
	parser.add_argument(
		"-r",
		"--regenerate-haworth-svgs",
		dest="regenerate_haworth_svgs",
		action="store_true",
		help=(
			"Regenerate generated Haworth SVG previews in "
			"output_smoke/archive_matrix_previews/generated. This mode always "
			"enforces strict overlap checks."
		),
	)
	strict_mode_group = parser.add_mutually_exclusive_group()
	strict_mode_group.add_argument(
		"--strict-report-all",
		dest="strict_mode",
		action="store_const",
		const="report_all",
		help=(
			"Collect and report all strict overlap failures while continuing "
			"generation, then exit non-zero if any strict failures occurred."
		),
	)
	strict_mode_group.add_argument(
		"--strict-fail-fast",
		dest="strict_mode",
		action="store_const",
		const="fail_fast",
		help="Stop immediately on first strict overlap failure and exit non-zero.",
	)
	parser.set_defaults(regenerate_haworth_svgs=False)
	parser.set_defaults(strict_render_checks=False)
	parser.set_defaults(strict_mode=None)
	args = parser.parse_args()
	if args.strict_mode and not args.regenerate_haworth_svgs:
		parser.error("--strict-report-all and --strict-fail-fast require --regenerate-haworth-svgs")
	if args.regenerate_haworth_svgs and args.strict_mode is None:
		args.strict_mode = "report_all"
	return args


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
def load_archive_mapping(repo_root: pathlib.Path) -> list[dict]:
	"""Load ordered mappable entries from mapping fixtures."""
	fixtures_dir = repo_root / "tests" / "fixtures"
	sys.path.insert(0, str(fixtures_dir))
	try:
		import neurotiker_archive_mapping as mapping
	except ImportError as error:
		raise RuntimeError("Could not import tests/fixtures/neurotiker_archive_mapping.py") from error
	rows = []
	for raw in mapping.all_mappable_entries():
		if isinstance(raw, dict):
			code = raw.get("code")
			ring_type = raw.get("ring_type")
			anomeric = raw.get("anomeric")
			sugar_name = raw.get("sugar_name") or raw.get("name")
			reference_svg_rel = raw.get("reference_svg_rel") or raw.get("archive_filename")
		else:
			if not isinstance(raw, tuple) or len(raw) != 5:
				raise ValueError(f"Unsupported mapping row format: {raw!r}")
			code, ring_type, anomeric, reference_svg_rel, sugar_name = raw
		if not code or not ring_type or not anomeric or not sugar_name:
			raise ValueError(f"Incomplete mapping row: {raw!r}")
		rows.append(
			{
				"code": str(code),
				"ring_type": str(ring_type),
				"anomeric": str(anomeric),
				"sugar_name": str(sugar_name),
				"reference_svg_rel": (
					str(reference_svg_rel) if reference_svg_rel else None
				),
			}
		)
	return rows


#============================================
def parse_generated_key(path: pathlib.Path) -> tuple[str, str, str] | None:
	"""Parse (code, ring_type, anomeric) from an SVG filename."""
	parts = path.stem.split("_")
	if len(parts) != 3:
		return None
	return (parts[0], parts[1], parts[2])


#============================================
def _load_oasa_modules(repo_root: pathlib.Path) -> object:
	"""Load OASA modules needed for rendering generated previews."""
	try:
		import oasa.dom_extensions as dom_extensions
		import oasa.haworth_renderer as haworth_renderer
		import oasa.render_ops as render_ops
	except ImportError:
		oasa_path = repo_root / "packages" / "oasa"
		if str(oasa_path) not in sys.path:
			sys.path.insert(0, str(oasa_path))
		import oasa.dom_extensions as dom_extensions
		import oasa.haworth_renderer as haworth_renderer
		import oasa.render_ops as render_ops
	return dom_extensions, haworth_renderer, render_ops


#============================================
def _render_generated_preview_svg(
		repo_root: pathlib.Path,
		code: str,
		ring_type: str,
		anomeric: str,
		strict_render_checks: bool,
		dst_path: pathlib.Path) -> None:
	"""Render one generated preview SVG with hydrogens disabled."""
	dom_extensions, haworth_renderer, render_ops = _load_oasa_modules(repo_root)
	ops = haworth_renderer.render_from_code(
		code=code,
		ring_type=ring_type,
		anomeric=anomeric,
		show_hydrogens=False,
		bg_color=GENERATED_PREVIEW_BG_COLOR,
	)
	if strict_render_checks:
		_validate_ops_strict(
			repo_root=repo_root,
			render_ops_module=render_ops,
			ops=ops,
			context=f"{code}_{ring_type}_{anomeric}",
		)

	try:
		impl = xml_minidom.getDOMImplementation()
		doc = impl.createDocument(None, None, None)
	except Exception:
		doc = xml_minidom.Document()
	svg = dom_extensions.elementUnder(
		doc,
		"svg",
		attributes=(
			("xmlns", "http://www.w3.org/2000/svg"),
			("version", "1.1"),
			("width", "220"),
			("height", "220"),
			("viewBox", "0 0 220 220"),
		),
	)
	render_ops.ops_to_svg(svg, ops)
	svg_xml = doc.toxml("utf-8")
	if isinstance(svg_xml, bytes):
		svg_text = svg_xml.decode("utf-8")
	else:
		svg_text = str(svg_xml)
	dst_path.parent.mkdir(parents=True, exist_ok=True)
	dst_path.write_text(svg_text, encoding="utf-8")
	_normalize_generated_svg(dst_path, dst_path, scale=GENERATED_PREVIEW_SCALE)


#============================================
def _validate_ops_strict(repo_root: pathlib.Path, render_ops_module: object, ops: list, context: str) -> None:
	"""Fail on strict overlap checks for one rendered ops list."""
	try:
		import oasa.haworth_renderer as haworth_renderer
	except ImportError:
		oasa_path = repo_root / "packages" / "oasa"
		if str(oasa_path) not in sys.path:
			sys.path.insert(0, str(oasa_path))
		import oasa.haworth_renderer as haworth_renderer
	haworth_renderer.strict_validate_ops(
		ops=ops,
		context=context,
		epsilon=0.5,
	)


#============================================
def build_summary_html(
		rows: list[dict],
		generated_count: int,
		mappable_count: int,
	missing_generated: int,
		missing_reference: int) -> str:
	"""Build complete summary page HTML."""
	generated_status = f"{generated_count} generated preview SVG files written"
	map_status = f"{mappable_count} mappable archive targets"
	timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	row_html = []
	for entry in rows:
		code = html.escape(entry["code"])
		name = html.escape(entry["name"])
		ring_type = html.escape(entry["ring_type"])
		anomeric = html.escape(entry["anomeric"])
		generated_rel = entry["generated_rel"]
		reference_rel = entry["reference_rel"]
		generated_block = _preview_block("Generated", generated_rel)
		reference_block = _preview_block("Reference", reference_rel)
		row_html.append(
			f"""
			<section class="card">
				<h2>{code} | {name}</h2>
				<p class="meta">{ring_type} | {anomeric}</p>
				<div class="grid">
					{generated_block}
					{reference_block}
				</div>
			</section>
			"""
		)

	return f"""<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Haworth Archive Matrix Summary</title>
	<style>
		:root {{
			--bg: #f7f6f2;
			--ink: #222;
			--panel: #fff;
			--line: #d8d3c8;
			--ok: #0b6e4f;
			--warn: #8a2f1f;
		}}
		body {{
			margin: 0;
			font-family: "Menlo", "Monaco", "Consolas", monospace;
			background: var(--bg);
			color: var(--ink);
		}}
		header {{
			position: sticky;
			top: 0;
			z-index: 2;
			background: linear-gradient(90deg, #f2efe6, #ebe7dc);
			border-bottom: 1px solid var(--line);
			padding: 12px 18px;
		}}
		h1 {{
			margin: 0 0 6px 0;
			font-size: 18px;
		}}
		.stats {{
			margin: 0;
			font-size: 12px;
			line-height: 1.4;
		}}
		.ok {{
			color: var(--ok);
		}}
		.warn {{
			color: var(--warn);
		}}
		main {{
			padding: 14px;
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(560px, 1fr));
			gap: 12px;
		}}
		.card {{
			border: 1px solid var(--line);
			background: var(--panel);
			border-radius: 8px;
			padding: 10px;
			box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
		}}
		h2 {{
			margin: 0;
			font-size: 14px;
		}}
		.meta {{
			margin: 4px 0 8px 0;
			font-size: 12px;
			color: #555;
		}}
		.grid {{
			display: grid;
			grid-template-columns: 1fr 1fr;
			gap: 8px;
		}}
		.block {{
			border: 1px solid var(--line);
			border-radius: 6px;
			padding: 6px;
			min-height: 240px;
			background: #fff;
		}}
		.block h3 {{
			margin: 0 0 4px 0;
			font-size: 12px;
		}}
		.frame {{
			width: 100%;
			height: 230px;
			border: 1px solid #e3e0d8;
			border-radius: 4px;
			background: #fafafa;
			display: flex;
			align-items: center;
			justify-content: center;
			overflow: hidden;
		}}
		.preview {{
			max-width: 100%;
			max-height: 100%;
			width: auto;
			height: auto;
			display: block;
		}}
		.link {{
			margin-top: 6px;
			font-size: 11px;
			word-break: break-all;
		}}
		.missing {{
			font-size: 12px;
			color: var(--warn);
			padding-top: 12px;
		}}
		@media (max-width: 800px) {{
			main {{
				grid-template-columns: 1fr;
			}}
		}}
	</style>
</head>
<body>
	<header>
		<h1>Haworth Archive Matrix Summary</h1>
		<p class="stats">
			{html.escape(generated_status)} | {html.escape(map_status)}<br>
			<span class="{ 'warn' if missing_generated else 'ok' }">Missing generated: {missing_generated}</span> |
			<span class="{ 'warn' if missing_reference else 'ok' }">Missing reference: {missing_reference}</span><br>
			Generated at {html.escape(timestamp)}
		</p>
	</header>
	<main>
		{''.join(row_html)}
	</main>
</body>
</html>
"""


#============================================
def _preview_block(label: str, rel_path: str | None) -> str:
	"""Build one preview block."""
	if not rel_path:
		return (
			f"<div class='block'><h3>{html.escape(label)}</h3>"
			"<div class='missing'>Missing file</div></div>"
		)
	escaped = html.escape(rel_path)
	return (
		f"<div class='block'><h3>{html.escape(label)}</h3>"
		f"<div class='frame'><img class='preview' src='{escaped}' alt='{html.escape(label)} preview'></div>"
		f"<div class='link'><a href='{escaped}' target='_blank'>{escaped}</a></div></div>"
	)


#============================================
def build_generated_only_html(rows: list[dict], missing_generated: int) -> str:
	"""Build generated-only summary page for rows without references."""
	timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	row_html = []
	for entry in rows:
		code = html.escape(entry["code"])
		name = html.escape(entry["name"])
		ring_type = html.escape(entry["ring_type"])
		anomeric = html.escape(entry["anomeric"])
		generated_block = _preview_block("Generated", entry["generated_rel"])
		row_html.append(
			f"""
			<section class="card">
				<h2>{code} | {name}</h2>
				<p class="meta">{ring_type} | {anomeric}</p>
				<div class="grid single">
					{generated_block}
				</div>
			</section>
			"""
		)

	return f"""<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Generated-Only Matrix</title>
	<style>
		:root {{
			--bg: #f7f6f2;
			--ink: #222;
			--panel: #fff;
			--line: #d8d3c8;
			--warn: #8a2f1f;
		}}
		body {{
			margin: 0;
			font-family: "Menlo", "Monaco", "Consolas", monospace;
			background: var(--bg);
			color: var(--ink);
		}}
		header {{
			position: sticky;
			top: 0;
			z-index: 2;
			background: linear-gradient(90deg, #f2efe6, #ebe7dc);
			border-bottom: 1px solid var(--line);
			padding: 12px 18px;
		}}
		h1 {{
			margin: 0 0 6px 0;
			font-size: 18px;
		}}
		.stats {{
			margin: 0;
			font-size: 12px;
			line-height: 1.4;
		}}
		main {{
			padding: 14px;
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(560px, 1fr));
			gap: 12px;
		}}
		.card {{
			border: 1px solid var(--line);
			background: var(--panel);
			border-radius: 8px;
			padding: 10px;
			box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
		}}
		h2 {{
			margin: 0;
			font-size: 14px;
		}}
		.meta {{
			margin: 4px 0 8px 0;
			font-size: 12px;
			color: #555;
		}}
		.grid.single {{
			display: grid;
			grid-template-columns: 1fr;
			gap: 8px;
		}}
		.block {{
			border: 1px solid var(--line);
			border-radius: 6px;
			padding: 6px;
			min-height: 240px;
			background: #fff;
		}}
		.block h3 {{
			margin: 0 0 4px 0;
			font-size: 12px;
		}}
		.frame {{
			width: 100%;
			height: 230px;
			border: 1px solid #e3e0d8;
			border-radius: 4px;
			background: #fafafa;
			display: flex;
			align-items: center;
			justify-content: center;
			overflow: hidden;
		}}
		.preview {{
			max-width: 100%;
			max-height: 100%;
			width: auto;
			height: auto;
			display: block;
		}}
		.link {{
			margin-top: 6px;
			font-size: 11px;
			word-break: break-all;
		}}
		.missing {{
			font-size: 12px;
			color: var(--warn);
			padding-top: 12px;
		}}
		@media (max-width: 800px) {{
			main {{
				grid-template-columns: 1fr;
			}}
		}}
	</style>
</head>
<body>
	<header>
		<h1>Generated-Only Matrix</h1>
		<p class="stats">
			Reference panel intentionally omitted for generated-only rows.<br>
			Rows: {len(rows)} | Missing generated: {missing_generated}<br>
			Generated at {html.escape(timestamp)}
		</p>
	</header>
	<main>
		{''.join(row_html)}
	</main>
</body>
</html>
"""


#============================================
def _svg_tag_name(tag: str) -> str:
	"""Return XML tag without namespace."""
	if "}" in tag:
		return tag.split("}", 1)[1]
	return tag


#============================================
def _parse_points(points_text: str) -> list[tuple[float, float]]:
	"""Parse SVG polygon/polyline points text into tuples."""
	points = []
	for token in points_text.replace("\n", " ").split():
		xy = token.split(",")
		if len(xy) != 2:
			continue
		try:
			x_value = float(xy[0])
			y_value = float(xy[1])
		except ValueError:
			continue
		points.append((x_value, y_value))
	return points


#============================================
def _visible_text_length(text: str) -> int:
	"""Estimate visible text length for SVG text bbox approximation."""
	stripped = re.sub(r"<[^>]+>", "", text or "")
	normalized = re.sub(r"\s+", " ", stripped).strip()
	return len(normalized)


#============================================
def _update_bbox(
		bbox: list[float] | None,
		x_value: float,
		y_value: float) -> list[float]:
	"""Expand bbox to include one point."""
	if bbox is None:
		return [x_value, y_value, x_value, y_value]
	bbox[0] = min(bbox[0], x_value)
	bbox[1] = min(bbox[1], y_value)
	bbox[2] = max(bbox[2], x_value)
	bbox[3] = max(bbox[3], y_value)
	return bbox


#============================================
def _bbox_from_generated_svg(root: object) -> list[float] | None:
	"""Approximate bbox for generated Haworth SVG primitives."""
	bbox = None
	for element in root.iter():
		tag = _svg_tag_name(element.tag)
		if tag == "line":
			try:
				x1 = float(element.attrib.get("x1", "0"))
				y1 = float(element.attrib.get("y1", "0"))
				x2 = float(element.attrib.get("x2", "0"))
				y2 = float(element.attrib.get("y2", "0"))
			except ValueError:
				continue
			bbox = _update_bbox(bbox, x1, y1)
			bbox = _update_bbox(bbox, x2, y2)
		elif tag in ("polygon", "polyline"):
			for x_value, y_value in _parse_points(element.attrib.get("points", "")):
				bbox = _update_bbox(bbox, x_value, y_value)
		elif tag == "text":
			try:
				x_value = float(element.attrib.get("x", "0"))
				y_value = float(element.attrib.get("y", "0"))
				font_size = float(element.attrib.get("font-size", "12"))
			except ValueError:
				continue
			visible_chars = _visible_text_length("".join(element.itertext()))
			text_width = visible_chars * font_size * 0.60
			text_height = font_size
			anchor = element.attrib.get("text-anchor", "start")
			if anchor == "middle":
				x_left = x_value - (text_width / 2.0)
			elif anchor == "end":
				x_left = x_value - text_width
			else:
				x_left = x_value
			x_right = x_left + text_width
			y_top = y_value - text_height
			y_bottom = y_value
			bbox = _update_bbox(bbox, x_left, y_top)
			bbox = _update_bbox(bbox, x_right, y_bottom)
	return bbox


#============================================
def _normalize_generated_svg(
		src_path: pathlib.Path,
		dst_path: pathlib.Path,
		scale: float = 1.0) -> None:
	"""Write a preview SVG with a tight, centered viewBox."""
	tree = ET.parse(src_path)
	root = tree.getroot()
	bbox = _bbox_from_generated_svg(root)
	if bbox is None:
		dst_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")
		return

	padding = 6.0
	min_x = bbox[0] - padding
	min_y = bbox[1] - padding
	width = max(1.0, (bbox[2] - bbox[0]) + (2.0 * padding))
	height = max(1.0, (bbox[3] - bbox[1]) + (2.0 * padding))
	if scale > 0 and abs(scale - 1.0) > 1e-9:
		center_x = min_x + (width / 2.0)
		center_y = min_y + (height / 2.0)
		width = width / scale
		height = height / scale
		min_x = center_x - (width / 2.0)
		min_y = center_y - (height / 2.0)

	root.set("viewBox", f"{min_x:.3f} {min_y:.3f} {width:.3f} {height:.3f}")
	root.set("preserveAspectRatio", "xMidYMid meet")
	root.set("width", "260")
	root.set("height", "260")
	dst_path.parent.mkdir(parents=True, exist_ok=True)
	tree.write(dst_path, encoding="utf-8", xml_declaration=True)


#============================================
def main() -> None:
	"""Create archive matrix summary page in output_smoke."""
	args = parse_args()
	repo_root = get_repo_root()
	output_dir = repo_root / "output_smoke"
	matrix_dir = output_dir / "archive_matrix"
	preview_dir = output_dir / "archive_matrix_previews"
	preview_generated_dir = preview_dir / "generated"
	summary_path = output_dir / "archive_matrix_summary.html"
	l_sugar_summary_path = output_dir / "l-sugar_matrix.html"
	archive_dir = repo_root / "neurotiker_haworth_archive"
	strict_render_checks = bool(
		args.strict_render_checks
		or args.regenerate_haworth_svgs
		or args.strict_mode is not None
	)

	if matrix_dir.exists() and not matrix_dir.is_dir():
		raise FileNotFoundError(f"Archive matrix path exists but is not a folder: {matrix_dir}")
	matrix_dir.mkdir(parents=True, exist_ok=True)
	if not archive_dir.is_dir():
		raise FileNotFoundError(f"Missing reference archive folder: {archive_dir}")

	generated_paths = sorted(matrix_dir.glob("**/*.svg"))
	generated_by_key: dict[tuple[str, str, str], pathlib.Path] = {}
	for generated_path in generated_paths:
		key = parse_generated_key(generated_path)
		if key is None:
			continue
		if key not in generated_by_key:
			generated_by_key[key] = generated_path

	entries = load_archive_mapping(repo_root)
	rows = []
	generated_only_rows = []
	missing_generated = 0
	missing_reference = 0
	generated_only_missing_generated = 0
	strict_overlap_failures: list[str] = []
	for entry in entries:
		code = entry["code"]
		ring_type = entry["ring_type"]
		anomeric = entry["anomeric"]
		sugar_name = entry["sugar_name"]
		reference_svg_rel = entry["reference_svg_rel"]
		reference_path = (archive_dir / reference_svg_rel) if reference_svg_rel else None
		has_reference_declared = bool(reference_svg_rel)
		has_reference_file = bool(reference_path and reference_path.is_file())
		generated_rel = None
		key = (code, ring_type, anomeric)
		preview_name = f"{code}_{ring_type}_{anomeric}.svg"
		preview_path = preview_generated_dir / preview_name
		if args.regenerate_haworth_svgs:
			try:
				_render_generated_preview_svg(
					repo_root=repo_root,
					code=code,
					ring_type=ring_type,
					anomeric=anomeric,
					strict_render_checks=strict_render_checks,
					dst_path=preview_path,
				)
				generated_rel = os.path.relpath(preview_path, output_dir)
			except RuntimeError as error:
				error_text = str(error)
				if "Strict overlap failure" in error_text:
					failure_text = f"{code}_{ring_type}_{anomeric}: {error_text}"
					strict_overlap_failures.append(failure_text)
					print(f"Strict overlap failure: {failure_text}")
					if args.strict_mode == "fail_fast":
						raise SystemExit(2)
				else:
					raise
		if generated_rel is None and preview_path.is_file():
			generated_rel = os.path.relpath(preview_path, output_dir)
		if generated_rel is None:
			generated_path = generated_by_key.get(key)
			if generated_path is not None:
				generated_rel = os.path.relpath(generated_path, output_dir)
		if generated_rel is None:
			if has_reference_declared:
				missing_generated += 1
			else:
				generated_only_missing_generated += 1
		if has_reference_declared and (not has_reference_file):
			missing_reference += 1
		row_data = (
			{
				"code": code,
				"name": sugar_name,
				"ring_type": ring_type,
				"anomeric": anomeric,
				"generated_rel": generated_rel,
				"reference_rel": (
					os.path.relpath(reference_path, output_dir) if has_reference_file else None
				),
			}
		)
		if has_reference_declared:
			rows.append(row_data)
		else:
			generated_only_rows.append(row_data)

	html_text = build_summary_html(
		rows=rows,
		generated_count=(len(rows) - missing_generated),
		mappable_count=len(rows),
		missing_generated=missing_generated,
		missing_reference=missing_reference,
	)
	l_sugar_html_text = build_generated_only_html(
		rows=generated_only_rows,
		missing_generated=generated_only_missing_generated,
	)
	output_dir.mkdir(exist_ok=True)
	summary_path.write_text(html_text, encoding="utf-8")
	l_sugar_summary_path.write_text(l_sugar_html_text, encoding="utf-8")
	print(f"Wrote summary: {summary_path}")
	print(f"Wrote generated-only summary: {l_sugar_summary_path}")
	print(f"Regenerate generated previews: {args.regenerate_haworth_svgs}")
	print(f"Strict mode: {args.strict_mode or 'off'}")
	print(f"Strict render checks: {strict_render_checks}")
	print(f"Generated previews written (with references): {len(rows) - missing_generated}")
	print(f"Generated previews written (generated-only): {len(generated_only_rows) - generated_only_missing_generated}")
	print(f"Matrix source SVG files discovered: {len(generated_paths)}")
	print(f"Mappable entries (with references): {len(rows)}")
	print(f"Mappable entries (generated-only): {len(generated_only_rows)}")
	print(f"Missing generated (with references): {missing_generated}")
	print(f"Missing generated (generated-only): {generated_only_missing_generated}")
	print(f"Missing reference: {missing_reference}")
	print(f"Strict-overlap failures: {len(strict_overlap_failures)}")
	for failure in strict_overlap_failures:
		print(f"  - {failure}")
	if args.strict_mode == "report_all" and strict_overlap_failures:
		raise SystemExit(2)


#============================================
if __name__ == "__main__":
	main()
