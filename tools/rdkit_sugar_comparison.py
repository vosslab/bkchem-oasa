#!/usr/bin/env python3
"""Build side-by-side HTML galleries comparing Haworth SVGs with RDKit 2D depictions.

For each sugar code, renders:
- Haworth projection SVG via the existing haworth_renderer pipeline
- RDKit 2D structure SVG via rdkit.Chem.Draw.MolDraw2DSVG

Outputs separate HTML galleries for pyranose and furanose ring types.
"""

# Standard Library
import datetime
import html
import os
import pathlib
import re
import subprocess
import sys
from xml.dom import minidom as xml_minidom

# PIP3 modules
import defusedxml.ElementTree as ET
import rdkit.Chem
import rdkit.Chem.AllChem
import rdkit.Chem.Draw
import yaml

PREVIEW_SCALE = 0.80
PREVIEW_BG_COLOR = "#fafafa"

# anomeric combos per ring type
ANOMERIC_FORMS = ["alpha", "beta"]

# each output HTML gets one ring type
RING_TYPES = ["pyranose", "furanose"]


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
def load_oasa_modules(repo_root: pathlib.Path):
	"""Load OASA modules needed for rendering."""
	try:
		import oasa.dom_extensions as dom_extensions
		import oasa.haworth_renderer as haworth_renderer
		import oasa.render_ops as render_ops
		import oasa.sugar_code_smiles as sugar_code_smiles
	except ImportError:
		oasa_path = repo_root / "packages" / "oasa"
		if str(oasa_path) not in sys.path:
			sys.path.insert(0, str(oasa_path))
		import oasa.dom_extensions as dom_extensions
		import oasa.haworth_renderer as haworth_renderer
		import oasa.render_ops as render_ops
		import oasa.sugar_code_smiles as sugar_code_smiles
	return dom_extensions, haworth_renderer, render_ops, sugar_code_smiles


#============================================
def load_sugar_codes(repo_root: pathlib.Path) -> dict:
	"""Load sugar codes from YAML file."""
	yaml_path = repo_root / "packages" / "oasa" / "oasa_data" / "sugar_codes.yml"
	with open(yaml_path, encoding="utf-8") as fh:
		data = yaml.safe_load(fh)
	return data


#============================================
def _visible_text_length(text: str) -> int:
	"""Estimate visible text length for SVG text bbox approximation."""
	stripped = re.sub(r"<[^>]+>", "", text or "")
	normalized = re.sub(r"\s+", " ", stripped).strip()
	return len(normalized)


#============================================
def _update_bbox(bbox: list, x: float, y: float) -> list:
	"""Expand bbox to include one point."""
	if bbox is None:
		return [x, y, x, y]
	bbox[0] = min(bbox[0], x)
	bbox[1] = min(bbox[1], y)
	bbox[2] = max(bbox[2], x)
	bbox[3] = max(bbox[3], y)
	return bbox


#============================================
def _parse_points(points_text: str) -> list:
	"""Parse SVG polygon/polyline points text into tuples."""
	points = []
	for token in points_text.replace("\n", " ").split():
		xy = token.split(",")
		if len(xy) != 2:
			continue
		try:
			points.append((float(xy[0]), float(xy[1])))
		except ValueError:
			continue
	return points


#============================================
def _svg_tag_name(tag: str) -> str:
	"""Return XML tag without namespace."""
	if "}" in tag:
		return tag.split("}", 1)[1]
	return tag


#============================================
def _bbox_from_generated_svg(root) -> list:
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
			for x_val, y_val in _parse_points(element.attrib.get("points", "")):
				bbox = _update_bbox(bbox, x_val, y_val)
		elif tag == "text":
			try:
				x_val = float(element.attrib.get("x", "0"))
				y_val = float(element.attrib.get("y", "0"))
				font_size = float(element.attrib.get("font-size", "12"))
			except ValueError:
				continue
			visible_chars = _visible_text_length("".join(element.itertext()))
			text_width = visible_chars * font_size * 0.60
			text_height = font_size
			anchor = element.attrib.get("text-anchor", "start")
			if anchor == "middle":
				x_left = x_val - (text_width / 2.0)
			elif anchor == "end":
				x_left = x_val - text_width
			else:
				x_left = x_val
			x_right = x_left + text_width
			y_top = y_val - text_height
			y_bottom = y_val
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
def render_haworth_svg(
		dom_extensions,
		haworth_renderer,
		render_ops,
		code: str,
		ring_type: str,
		anomeric: str,
		dst_path: pathlib.Path) -> None:
	"""Render one sugar code combo as a Haworth projection SVG."""
	ops = haworth_renderer.render_from_code(
		code=code,
		ring_type=ring_type,
		anomeric=anomeric,
		show_hydrogens=False,
		bg_color=PREVIEW_BG_COLOR,
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

	# normalize viewBox for tight fit
	_normalize_generated_svg(dst_path, dst_path, scale=PREVIEW_SCALE)


#============================================
def render_rdkit_svg(smiles_text: str, dst_path: pathlib.Path) -> None:
	"""Render a SMILES string as a 2D structure SVG using RDKit.

	Args:
		smiles_text: SMILES string to render.
		dst_path: Output SVG file path.
	"""
	mol = rdkit.Chem.MolFromSmiles(smiles_text)
	if mol is None:
		raise ValueError(f"RDKit could not parse SMILES: {smiles_text!r}")
	rdkit.Chem.AllChem.Compute2DCoords(mol)
	rdkit.Chem.AllChem.StraightenDepiction(mol)

	# render to SVG using MolDraw2DSVG
	drawer = rdkit.Chem.Draw.MolDraw2DSVG(260, 260)
	drawer.drawOptions().addStereoAnnotation = True
	drawer.DrawMolecule(mol)
	drawer.FinishDrawing()
	svg_text = drawer.GetDrawingText()

	dst_path.parent.mkdir(parents=True, exist_ok=True)
	dst_path.write_text(svg_text, encoding="utf-8")


#============================================
def build_html(
		ring_type: str,
		categories: list,
		total_sugars: int,
		total_rendered: int,
		other_html_filename: str) -> str:
	"""Build complete HTML page for one ring type with side-by-side comparison."""
	timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	title = f"Sugar Codes - {ring_type.capitalize()} - Haworth vs RDKit"
	other_ring = "furanose" if ring_type == "pyranose" else "pyranose"
	sections_html = ""
	for category_name, cards in categories:
		cards_html = ""
		for card in cards:
			code = html.escape(card["code"])
			name = html.escape(card["name"])
			previews_html = ""
			if card["previews"]:
				for combo_label, haworth_svg_rel, rdkit_svg_rel in card["previews"]:
					escaped_haworth = html.escape(haworth_svg_rel)
					escaped_rdkit = html.escape(rdkit_svg_rel)
					# side-by-side: Haworth on left, RDKit on right
					previews_html += (
						f"<div class='comparison-pair'>"
						f"<div class='combo-label'>{html.escape(combo_label)}</div>"
						f"<div class='side-by-side'>"
						f"<div class='render-cell'>"
						f"<div class='render-label'>Haworth</div>"
						f"<div class='svg-frame'>"
						f"<img class='preview' src='{escaped_haworth}' "
						f"alt='{code} {html.escape(combo_label)} Haworth'>"
						f"</div></div>"
						f"<div class='render-cell'>"
						f"<div class='render-label'>RDKit</div>"
						f"<div class='svg-frame'>"
						f"<img class='preview' src='{escaped_rdkit}' "
						f"alt='{code} {html.escape(combo_label)} RDKit'>"
						f"</div></div>"
						f"</div></div>\n"
					)
			else:
				previews_html = (
					f"<div class='no-render'>"
					f"No valid {ring_type} ring forms"
					f"</div>"
				)
			cards_html += (
				f"<div class='card'>"
				f"<div class='card-header'>"
				f"<span class='code'>{code}</span>"
				f"<span class='name'>{name}</span>"
				f"</div>"
				f"<div class='previews'>{previews_html}</div>"
				f"</div>\n"
			)
		sections_html += (
			f"<div class='category-section'>"
			f"<h2>{html.escape(category_name)}</h2>"
			f"<div class='cards-grid'>{cards_html}</div>"
			f"</div>\n"
		)

	page_html = f"""<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{html.escape(title)}</title>
	<style>
		:root {{
			--bg: #f7f6f2;
			--ink: #222;
			--panel: #fff;
			--line: #d8d3c8;
			--ok: #0b6e4f;
			--warn: #8a2f1f;
			--accent: #5b4a3f;
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
		.nav-link {{
			display: inline-block;
			margin-top: 6px;
			font-size: 12px;
			color: var(--accent);
		}}
		main {{
			padding: 14px;
		}}
		.category-section {{
			margin-bottom: 24px;
		}}
		.category-section h2 {{
			font-size: 16px;
			margin: 0 0 10px 0;
			padding-bottom: 4px;
			border-bottom: 2px solid var(--accent);
			color: var(--accent);
			text-transform: capitalize;
		}}
		.cards-grid {{
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(580px, 1fr));
			gap: 12px;
		}}
		.card {{
			border: 1px solid var(--line);
			background: var(--panel);
			border-radius: 8px;
			padding: 10px;
			box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
		}}
		.card-header {{
			margin-bottom: 8px;
		}}
		.code {{
			font-weight: bold;
			font-size: 14px;
			margin-right: 10px;
			color: var(--accent);
		}}
		.name {{
			font-size: 13px;
			color: #555;
		}}
		.previews {{
			display: flex;
			flex-wrap: wrap;
			gap: 12px;
		}}
		.comparison-pair {{
			border: 1px solid var(--line);
			border-radius: 6px;
			padding: 6px;
			background: #fafafa;
		}}
		.combo-label {{
			font-size: 10px;
			color: #777;
			margin-bottom: 4px;
			text-align: center;
		}}
		.side-by-side {{
			display: flex;
			gap: 6px;
		}}
		.render-cell {{
			text-align: center;
		}}
		.render-label {{
			font-size: 9px;
			color: #999;
			margin-bottom: 2px;
			text-transform: uppercase;
		}}
		.svg-frame {{
			width: 200px;
			height: 200px;
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
		.no-render {{
			font-size: 12px;
			color: var(--warn);
			padding: 12px;
			font-style: italic;
		}}
		@media (max-width: 600px) {{
			.cards-grid {{
				grid-template-columns: 1fr;
			}}
		}}
	</style>
</head>
<body>
	<header>
		<h1>{html.escape(title)}</h1>
		<p class="stats">
			{total_sugars} sugar codes |
			{total_rendered} rendered comparison pairs<br>
			Generated at {html.escape(timestamp)}
		</p>
		<a class="nav-link" href="{html.escape(other_html_filename)}">&rarr; View {html.escape(other_ring)} gallery</a>
	</header>
	<main>
		{sections_html}
	</main>
</body>
</html>
"""
	return page_html


#============================================
def render_all_comparisons(
		sugar_data: dict,
		dom_ext,
		haworth_renderer,
		render_ops_mod,
		sugar_code_smiles_mod,
		svg_dir: pathlib.Path,
		output_dir: pathlib.Path) -> dict:
	"""Render Haworth + RDKit SVGs for all sugar codes.

	Returns:
		Dict keyed by ring_type, each value is a dict with keys:
			categories: list of (category_name, cards) tuples
			total_sugars: int
			total_rendered: int
	"""
	results = {}
	for ring_type in RING_TYPES:
		results[ring_type] = {
			"categories": [],
			"total_sugars": 0,
			"total_rendered": 0,
		}

	for category_name, codes_dict in sugar_data.items():
		ring_cards = {rt: [] for rt in RING_TYPES}
		for code, name in codes_dict.items():
			for ring_type in RING_TYPES:
				results[ring_type]["total_sugars"] += 1
				previews = []
				for anomeric in ANOMERIC_FORMS:
					combo_label = f"{ring_type} {anomeric}"
					haworth_filename = f"{code}_{ring_type}_{anomeric}_haworth.svg"
					rdkit_filename = f"{code}_{ring_type}_{anomeric}_rdkit.svg"
					haworth_path = svg_dir / haworth_filename
					rdkit_path = svg_dir / rdkit_filename
					# render Haworth SVG
					haworth_ok = False
					try:
						render_haworth_svg(
							dom_ext, haworth_renderer, render_ops_mod,
							code, ring_type, anomeric, haworth_path,
						)
						haworth_ok = True
					except ValueError:
						pass

					# render RDKit SVG from SMILES
					rdkit_ok = False
					try:
						smiles_text = sugar_code_smiles_mod.sugar_code_to_smiles(
							code, ring_type, anomeric,
						)
						render_rdkit_svg(smiles_text, rdkit_path)
						rdkit_ok = True
					except (ValueError, KeyError):
						pass

					# only include if at least the Haworth render succeeded
					if haworth_ok and rdkit_ok:
						haworth_rel = os.path.relpath(haworth_path, output_dir)
						rdkit_rel = os.path.relpath(rdkit_path, output_dir)
						previews.append((combo_label, haworth_rel, rdkit_rel))
						results[ring_type]["total_rendered"] += 1

				ring_cards[ring_type].append({
					"code": code,
					"name": name,
					"previews": previews,
				})
		for ring_type in RING_TYPES:
			results[ring_type]["categories"].append(
				(category_name, ring_cards[ring_type])
			)
	return results


#============================================
def main() -> None:
	"""Render all sugar codes and write side-by-side comparison HTML galleries."""
	repo_root = get_repo_root()
	output_dir = repo_root / "output_smoke"
	output_dir.mkdir(exist_ok=True)
	svg_dir = output_dir / "rdkit_comparison_svgs"
	svg_dir.mkdir(exist_ok=True)

	# load data and rendering modules
	sugar_data = load_sugar_codes(repo_root)
	dom_ext, haworth_renderer, render_ops_mod, sugar_code_smiles_mod = load_oasa_modules(repo_root)

	# render all SVGs and collect per-ring-type data
	results = render_all_comparisons(
		sugar_data, dom_ext, haworth_renderer, render_ops_mod,
		sugar_code_smiles_mod, svg_dir, output_dir,
	)

	# map ring type to output filename
	html_filenames = {
		"pyranose": "rdkit_comparison_pyranose.html",
		"furanose": "rdkit_comparison_furanose.html",
	}

	# write one HTML file per ring type
	for ring_type in RING_TYPES:
		data = results[ring_type]
		other_ring = "furanose" if ring_type == "pyranose" else "pyranose"
		output_path = output_dir / html_filenames[ring_type]
		page_html = build_html(
			ring_type=ring_type,
			categories=data["categories"],
			total_sugars=data["total_sugars"],
			total_rendered=data["total_rendered"],
			other_html_filename=html_filenames[other_ring],
		)
		output_path.write_text(page_html, encoding="utf-8")
		print(f"Wrote {ring_type} comparison gallery: {output_path}")
		print(f"  {data['total_sugars']} sugar codes | "
			f"{data['total_rendered']} comparison pairs")

	print(f"SVG files: {svg_dir}")


#============================================
if __name__ == "__main__":
	main()
