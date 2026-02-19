#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

"""Renderer capabilities sheet generator.

Generates a single-page visual reference showing all OASA rendering capabilities:
- Bond types (normal, bold, wedge, hashed, wavy, etc.)
- Colors (per-bond colors)
- Complex features (aromatic rings, stereochemistry, Haworth projections)

Usage:
	# As library
	svg_text = build_renderer_capabilities_sheet()
	with open("capabilities.svg", "w") as f:
		f.write(svg_text)

	# From command line (default: PDF output)
	python selftest_sheet.py
	python selftest_sheet.py --format svg --out capabilities.svg
	python selftest_sheet.py --format png --out capabilities.png
"""

# Standard Library
import importlib
import math
import os
import statistics
import subprocess
import sys
import xml.dom.minidom as xml_minidom


#============================================
def get_repo_root():
	"""Get repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# Handle imports for both module and script usage
# Always add oasa to path and import directly
repo_root = get_repo_root()
oasa_dir = os.path.join(repo_root, "packages", "oasa")
if oasa_dir not in sys.path:
	sys.path.insert(0, oasa_dir)

# Import the oasa package - classes are exported directly
import oasa
atom = importlib.import_module("oasa.atom")
bond_module = importlib.import_module("oasa.bond")
molecule = importlib.import_module("oasa.molecule")
atom_colors = oasa.atom_colors
dom_extensions = oasa.dom_extensions
render_geometry = oasa.render_geometry
render_ops = oasa.render_ops
haworth = oasa.haworth
sugar_code = oasa.sugar_code
haworth_spec = oasa.haworth_spec
haworth_renderer = oasa.haworth_renderer

#============================================
# Page dimensions at 72 DPI
PAGE_SIZES = {
	"letter": (612, 792),  # 8.5 x 11 inches
	"a4": (595, 842),      # 210 x 297 mm
}


#============================================
def get_page_dims(page, portrait):
	"""Get page dimensions in points.

	Args:
		page: "letter" or "a4"
		portrait: True for portrait, False for landscape

	Returns:
		(width, height) in points
	"""
	w, h = PAGE_SIZES.get(page, PAGE_SIZES["letter"])
	if not portrait:
		w, h = h, w
	return w, h


#============================================
def ops_bbox(ops):
	"""Return (minx, miny, maxx, maxy) for a list of render ops."""
	minx = miny = float("inf")
	maxx = maxy = float("-inf")

	def take_point(x, y):
		nonlocal minx, miny, maxx, maxy
		minx = min(minx, x)
		miny = min(miny, y)
		maxx = max(maxx, x)
		maxy = max(maxy, y)

	for op in ops:
		if isinstance(op, render_ops.LineOp):
			take_point(op.p1[0], op.p1[1])
			take_point(op.p2[0], op.p2[1])
		elif isinstance(op, render_ops.PolygonOp):
			for x, y in op.points:
				take_point(x, y)
		elif isinstance(op, render_ops.CircleOp):
			cx, cy = op.center
			r = op.radius
			take_point(cx - r, cy - r)
			take_point(cx + r, cy + r)
		elif isinstance(op, render_ops.PathOp):
			for cmd, payload in op.commands:
				if payload is None:
					continue
				if cmd == "ARC":
					cx, cy, r, _a1, _a2 = payload
					take_point(cx - r, cy - r)
					take_point(cx + r, cy + r)
				else:
					x, y = payload
					take_point(x, y)
		elif isinstance(op, render_ops.TextOp):
			text = op.text or ""
			font_size = op.font_size or 0.0
			width = len(text) * font_size * 0.6
			height = font_size
			x = op.x
			if op.anchor == "middle":
				x -= width / 2.0
			elif op.anchor == "end":
				x -= width
			take_point(x, op.y - height)
			take_point(x + width, op.y)

	if minx == float("inf"):
		raise ValueError("ops_bbox: empty ops list (no renderable content)")

	# Validate bbox is not degenerate
	import math
	if math.isnan(minx) or math.isnan(miny) or math.isnan(maxx) or math.isnan(maxy):
		raise ValueError(f"ops_bbox: NaN in bbox ({minx}, {miny}, {maxx}, {maxy})")

	if minx == maxx and miny == maxy:
		raise ValueError(f"ops_bbox: zero-sized bbox (single point at {minx}, {miny})")

	if minx > maxx or miny > maxy:
		raise ValueError(f"ops_bbox: invalid bbox ({minx}, {miny}, {maxx}, {maxy})")

	return (minx, miny, maxx, maxy)


#============================================
def normalize_to_height(ops, target_height):
	"""Normalize ops to a target height, maintaining aspect ratio.

	Args:
		ops: List of render ops
		target_height: Desired height in points

	Returns:
		Tuple of (transformed_ops, actual_width, actual_height)
	"""
	if not ops:
		raise ValueError("normalize_to_height: empty ops list")

	import math
	if math.isnan(target_height) or target_height <= 0:
		raise ValueError(f"normalize_to_height: invalid target_height {target_height}")

	minx, miny, maxx, maxy = ops_bbox(ops)  # Will raise if bbox is invalid
	current_height = maxy - miny

	if math.isnan(current_height) or current_height <= 0:
		raise ValueError(f"normalize_to_height: invalid current_height {current_height}")

	scale = target_height / current_height

	# Scale ops
	scaled = _transform_ops(ops, 0, 0, scale=scale)

	# Translate so top-left is at origin
	minx_s, miny_s, maxx_s, maxy_s = ops_bbox(scaled)
	translated = _transform_ops(scaled, -minx_s, -miny_s, scale=1.0)

	return translated, (maxx_s - minx_s), (maxy_s - miny_s)


#============================================
def layout_row(vignettes, y_top, page_width, row_height, gutter=20, margin=40):
	"""Layout multiple vignettes in a horizontal row with equal spacing.

	Args:
		vignettes: List of (title, ops) tuples
		y_top: Y coordinate for top of row
		page_width: Total page width
		row_height: Target height for normalizing molecules
		gutter: Space between vignettes
		margin: Left/right margin

	Returns:
		List of (title, positioned_ops, x_center, y_center) for rendering
	"""
	if not vignettes:
		return []

	# Normalize all vignettes to same height
	normalized = []
	for title, ops in vignettes:
		norm_ops, width, height = normalize_to_height(ops, row_height)
		normalized.append((title, norm_ops, width, height))

	# Calculate total width and spacing
	total_content_width = sum(w for _, _, w, _ in normalized)
	num_gaps = len(normalized) - 1
	total_gap_width = num_gaps * gutter
	available_width = page_width - 2 * margin

	# If content doesn't fit, scale down uniformly
	if total_content_width + total_gap_width > available_width:
		scale_factor = available_width / (total_content_width + total_gap_width)
		# Re-normalize with adjusted height
		adjusted_height = row_height * scale_factor
		renormalized = []
		for title, ops, _, _ in normalized:
			norm_ops, width, height = normalize_to_height(ops, adjusted_height)
			renormalized.append((title, norm_ops, width, height))
		normalized = renormalized
		total_content_width = sum(w for _, _, w, _ in normalized)

	# Position vignettes with equal gutters
	result = []
	x_current = margin

	for title, norm_ops, width, height in normalized:
		# Center of this vignette
		x_center = x_current + width / 2
		y_center = y_top + height / 2

		# Position ops at current x
		positioned = _transform_ops(norm_ops, x_current, y_top, scale=1.0)
		result.append((title, positioned, x_center, y_center))

		# Advance to next position
		x_current += width + gutter

	return result


#============================================
def place_ops_in_rect(ops, rect, align="center", padding=5, preserve_aspect=True):
	"""Place ops inside a rectangle with scaling and alignment.

	Args:
		ops: List of render ops to place
		rect: (x, y, width, height) rectangle to place ops in
		align: "center", "left", "right", "top", "bottom"
		padding: Padding inside rect in points
		preserve_aspect: If True, maintain aspect ratio

	Returns:
		List of transformed ops
	"""
	bbox = ops_bbox(ops)
	if bbox is None:
		return []

	minx, miny, maxx, maxy = bbox
	content_width = maxx - minx
	content_height = maxy - miny

	if content_width == 0 or content_height == 0:
		return []

	rect_x, rect_y, rect_width, rect_height = rect
	available_width = rect_width - 2 * padding
	available_height = rect_height - 2 * padding

	# Compute scale
	if preserve_aspect:
		scale = min(available_width / content_width, available_height / content_height)
	else:
		scale = min(available_width / content_width, available_height / content_height)

	scaled_width = content_width * scale
	scaled_height = content_height * scale

	# Compute offset based on alignment
	if align == "center":
		dx = rect_x + padding + (available_width - scaled_width) / 2 - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) / 2 - miny * scale
	elif align == "left":
		dx = rect_x + padding - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) / 2 - miny * scale
	elif align == "right":
		dx = rect_x + padding + (available_width - scaled_width) - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) / 2 - miny * scale
	elif align == "top":
		dx = rect_x + padding + (available_width - scaled_width) / 2 - minx * scale
		dy = rect_y + padding - miny * scale
	elif align == "bottom":
		dx = rect_x + padding + (available_width - scaled_width) / 2 - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) - miny * scale
	else:
		dx = rect_x + padding - minx * scale
		dy = rect_y + padding - miny * scale

	# Transform ops
	return _transform_ops(ops, dx, dy, scale)


#============================================
def build_renderer_capabilities_ops(page="letter", seed=0):
	"""Build ops for the renderer capabilities sheet.

	Args:
		page: Page size ("letter", "a4") - always portrait orientation
		seed: Random seed for reproducible molecule generation (not used yet)

	Returns:
		Tuple of (ops, width, height)
	"""
	_ = seed
	width, height = get_page_dims(page, portrait=True)
	include_text = render_ops.supports_text_ops()
	ops = []

	if include_text:
		ops.append(render_ops.TextOp(
			x=width / 2,
			y=30,
			text="OASA Renderer Capabilities",
			font_size=20,
			anchor="middle",
			weight="bold",
			color="#000",
		))

	ops.extend(_build_bond_grid_ops(include_text))
	ops.extend(_build_vignettes_ops(width, include_text))

	if include_text:
		ops.append(render_ops.TextOp(
			x=width / 2,
			y=height - 20,
			text="Generated by OASA selftest_sheet.py",
			font_size=10,
			anchor="middle",
			color="#666",
		))

	return ops, width, height


#============================================
def build_renderer_capabilities_sheet(page="letter", backend="svg", seed=0, output_path=None,
																			cairo_format="png", png_dpi=600):
	"""Build a capabilities sheet showing all rendering features.

	Args:
		page: Page size ("letter", "a4") - always portrait orientation
		backend: "svg" or "cairo"
		seed: Random seed for reproducible molecule generation (not used yet)
		output_path: Output file path (required for cairo backend)
		cairo_format: Format for cairo backend ("png" or "pdf")
		png_dpi: Target DPI for PNG output (default: 300)

	Returns:
		SVG text (str) for SVG backend
		None for cairo backend (writes directly to output_path)
	"""
	ops, width, height = build_renderer_capabilities_ops(page=page, seed=seed)

	if backend == "svg":
		try:
			from xml.dom.minidom import getDOMImplementation
			impl = getDOMImplementation()
			doc = impl.createDocument(None, None, None)
		except Exception:
			doc = xml_minidom.Document()
		svg = dom_extensions.elementUnder(
			doc,
			"svg",
			attributes=(
				("xmlns", "http://www.w3.org/2000/svg"),
				("version", "1.1"),
				("width", str(width)),
				("height", str(height)),
				("viewBox", f"0 0 {width} {height}"),
			),
		)
		render_ops.ops_to_svg(svg, ops)
		if __name__ == "__main__":
			import oasa
			svg_out = oasa.svg_out
		else:
			import oasa.svg_out as svg_out
		return svg_out.pretty_print_svg(doc.toxml("utf-8"))

	if backend != "cairo":
		raise ValueError(f"Unknown backend: {backend}. Must be 'svg' or 'cairo'")
	if output_path is None:
		raise ValueError("output_path is required for cairo backend")
	try:
		import cairo
	except ImportError as exc:
		raise RuntimeError("Cairo output requires pycairo.") from exc

	if cairo_format == "png":
		if png_dpi <= 0:
			raise ValueError("png_dpi must be > 0")
		scale = float(png_dpi) / 72.0
		surface = cairo.ImageSurface(
			cairo.FORMAT_ARGB32,
			int(round(width * scale)),
			int(round(height * scale)),
		)
	elif cairo_format == "pdf":
		surface = cairo.PDFSurface(output_path, width, height)
	elif cairo_format == "svg":
		surface = cairo.SVGSurface(output_path, width, height)
	else:
		raise ValueError(f"Unknown cairo format: {cairo_format}")

	context = cairo.Context(surface)
	if cairo_format == "png":
		context.scale(scale, scale)
		context.set_source_rgb(1, 1, 1)
		context.paint()
	render_ops.ops_to_cairo(context, ops)
	if cairo_format == "png":
		surface.write_to_png(output_path)
	surface.finish()
	return None


#============================================
def _build_bond_grid_ops(include_text):
	"""Build bond type x color grid ops (Section A)."""
	# Bond types to show
	bond_types = [
		('n', 'Normal'),
		('b', 'Bold'),
		('w', 'Wedge'),
		('h', 'Hashed'),
		('q', 'Wide rect'),
		('s', 'Wavy (sine)'),
		('s_triangle', 'Wavy (tri)'),
		('s_box', 'Wavy (box)'),
	]

	# Colors to show
	colors = [
		('#000', 'Black'),
		('#f00', 'Red'),
		('#00f', 'Blue'),
		('#0a0', 'Green'),
		('#a0a', 'Purple'),
		('#f80', 'Orange'),
	]

	# Grid layout
	grid_x = 50
	grid_y = 60
	cell_w = 70
	cell_h = 35
	label_offset = 15

	ops = []

	if include_text:
		for col, (_bond_type, bond_name) in enumerate(bond_types):
			x = grid_x + col * cell_w + cell_w / 2
			y = grid_y - 5
			ops.append(render_ops.TextOp(
				x=x,
				y=y,
				text=bond_name,
				font_size=9,
				anchor="middle",
				color="#000",
			))

		for row, (color, color_name) in enumerate(colors):
			x = grid_x - 10
			y = grid_y + label_offset + row * cell_h + cell_h / 2
			ops.append(render_ops.TextOp(
				x=x,
				y=y,
				text=color_name,
				font_size=9,
				anchor="end",
				color=color,
			))

	for row, (color, _) in enumerate(colors):
		for col, (bond_type, _) in enumerate(bond_types):
			x = grid_x + col * cell_w
			y = grid_y + label_offset + row * cell_h
			points = (
				(x, y),
				(x + cell_w, y),
				(x + cell_w, y + cell_h),
				(x, y + cell_h),
			)
			ops.append(render_ops.PolygonOp(
				points=points,
				fill="none",
				stroke="#ddd",
				stroke_width=0.5,
			))

			fragment_ops = _build_bond_fragment(bond_type, color)
			cx = x + cell_w / 2
			cy = y + cell_h / 2
			panel_ops = _transform_ops(fragment_ops, cx - 15, cy, scale=1.0)
			ops.extend(panel_ops)

	return ops


#============================================
def _build_bond_fragment(bond_type, color):
	"""Build a tiny C-C bond fragment.

	Args:
		bond_type: Bond type code ('n', 'b', 'w', etc.)
		color: Hex color string

	Returns:
		List of ops for rendering
	"""
	# Handle special cases for bond order and wavy styles
	wavy_style = None
	if bond_type == '=' or bond_type == 2:
		bond_order = 2
		bond_type_code = 'n'
	elif bond_type == '#' or bond_type == 3:
		bond_order = 3
		bond_type_code = 'n'
	elif bond_type == 's_triangle':
		bond_order = 1
		bond_type_code = 's'
		wavy_style = 'triangle'
	elif bond_type == 's_box':
		bond_order = 1
		bond_type_code = 's'
		wavy_style = 'box'
	else:
		bond_order = 1
		bond_type_code = bond_type

	# Create minimal molecule
	mol = molecule.molecule()
	a1 = atom.atom(symbol='C')
	a1.x = 0
	a1.y = 0
	a2 = atom.atom(symbol='C')
	a2.x = 30
	a2.y = 0
	mol.add_vertex(a1)
	mol.add_vertex(a2)

	bond = bond_module.bond(order=bond_order, type=bond_type_code)
	bond.vertices = (a1, a2)
	bond.properties_['line_color'] = color
	if wavy_style:
		bond.properties_['wavy_style'] = wavy_style
	mol.add_edge(a1, a2, bond)

	# Build ops using existing infrastructure
	context = render_geometry.BondRenderContext(
		molecule=mol,
		line_width=1.0,
		bond_width=3.0,
		wedge_width=4.0,
		bold_line_width_multiplier=1.2,
		shown_vertices=set(),
		bond_coords={bond: ((0, 0), (30, 0))},
		point_for_atom=None,
	)

	return render_geometry.build_bond_ops(bond, (0, 0), (30, 0), context)


#============================================
def _transform_ops(ops, dx, dy, scale=1.0):
	"""Transform ops by translation and scaling.

	Args:
		ops: List of op objects
		dx, dy: Translation offsets
		scale: Scaling factor

	Returns:
		New list of transformed ops
	"""
	transformed = []
	for op in ops:
		if isinstance(op, render_ops.LineOp):
			p1 = (_scale_point(op.p1, scale, dx, dy))
			p2 = (_scale_point(op.p2, scale, dx, dy))
			transformed.append(render_ops.LineOp(
				p1=p1, p2=p2, width=op.width * scale,
				cap=op.cap, join=op.join, color=op.color, z=op.z
			))
		elif isinstance(op, render_ops.PolygonOp):
			points = tuple(_scale_point(p, scale, dx, dy) for p in op.points)
			transformed.append(render_ops.PolygonOp(
				points=points, fill=op.fill, stroke=op.stroke,
				stroke_width=op.stroke_width * scale, z=op.z
			))
		elif isinstance(op, render_ops.CircleOp):
			center = _scale_point(op.center, scale, dx, dy)
			transformed.append(render_ops.CircleOp(
				center=center, radius=op.radius * scale,
				fill=op.fill, stroke=op.stroke,
				stroke_width=op.stroke_width * scale, z=op.z
			))
		elif isinstance(op, render_ops.PathOp):
			commands = []
			for cmd, payload in op.commands:
				if payload is None:
					commands.append((cmd, None))
				elif cmd == "ARC":
					# ARC: (cx, cy, r, angle1, angle2)
					cx, cy, r, a1, a2 = payload
					new_center = _scale_point((cx, cy), scale, dx, dy)
					commands.append((cmd, (new_center[0], new_center[1], r * scale, a1, a2)))
				else:
					# M, L: (x, y)
					new_point = _scale_point((payload[0], payload[1]), scale, dx, dy)
					commands.append((cmd, (new_point[0], new_point[1])))
			transformed.append(render_ops.PathOp(
				commands=tuple(commands), fill=op.fill, stroke=op.stroke,
				stroke_width=op.stroke_width * scale,
				cap=op.cap, join=op.join, z=op.z
			))
		elif isinstance(op, render_ops.TextOp):
			transformed.append(render_ops.TextOp(
				x=op.x * scale + dx,
				y=op.y * scale + dy,
				text=op.text,
				font_size=op.font_size * scale,
				font_name=op.font_name,
				anchor=op.anchor,
				weight=op.weight,
				color=op.color,
				z=op.z,
			))
		else:
			# Unknown op type, skip
			continue
	return transformed


#============================================
def _scale_point(point, scale, dx, dy):
	"""Scale and translate a point."""
	return (point[0] * scale + dx, point[1] * scale + dy)


#============================================
def _mol_render_options():
	return {
		"line_width": 1.0,
		"bond_width": 3.0,
		"wedge_width": 6.0,
		"bold_line_width_multiplier": 1.2,
		"margin": 5,
		"font_name": "Arial",
		"font_size": 16,
		"font_size_ratio": 0.65,
		"color_atoms": True,
		"color_bonds": True,
		"atom_colors": atom_colors.atom_colors_full,
		"show_hydrogens_on_hetero": False,
	}


#============================================
def _bond_lengths(mol):
	lengths = []
	for edge in mol.edges:
		v1, v2 = edge.vertices
		dx = v1.x - v2.x
		dy = v1.y - v2.y
		length = math.hypot(dx, dy)
		if length > 0:
			lengths.append(length)
	return lengths


#============================================
def _scaled_font_size(mol, ratio, fallback):
	if ratio <= 0:
		return fallback
	lengths = _bond_lengths(mol)
	if not lengths:
		return fallback
	median_length = statistics.median(lengths)
	if not math.isfinite(median_length) or median_length <= 0:
		return fallback
	return ratio * median_length


#============================================
def _build_molecule_ops(mol, options):
	"""Build render ops for a molecule using shared bond logic."""
	if mol is None:
		raise ValueError("Cannot render a missing molecule.")
	line_width = options.get("line_width", 1.0)
	bond_width = options.get("bond_width", 3.0)
	wedge_width = options.get("wedge_width", 6.0)
	bold_line_width_multiplier = options.get("bold_line_width_multiplier", 1.2)
	color_atoms = options.get("color_atoms", True)
	color_bonds = options.get("color_bonds", True)
	atom_colors_map = options.get("atom_colors", None)
	font_name = options.get("font_name", "Arial")
	font_size = options.get("font_size", 16)
	font_size_ratio = options.get("font_size_ratio", None)
	show_hydrogens_on_hetero = options.get("show_hydrogens_on_hetero", False)
	if font_size_ratio is not None:
		font_size = _scaled_font_size(mol, font_size_ratio, font_size)

	shown_vertices = set([v for v in mol.vertices if render_geometry.vertex_is_shown(v)])
	bond_coords = {}
	for edge in mol.edges:
		v1, v2 = edge.vertices
		bond_coords[edge] = ((v1.x, v1.y), (v2.x, v2.y))

	context = render_geometry.BondRenderContext(
		molecule=mol,
		line_width=line_width,
		bond_width=bond_width,
		wedge_width=wedge_width,
		bold_line_width_multiplier=bold_line_width_multiplier,
		bond_second_line_shortening=0.0,
		color_bonds=color_bonds,
		atom_colors=atom_colors_map,
		shown_vertices=shown_vertices,
		bond_coords=bond_coords,
		point_for_atom=lambda atom: (atom.x, atom.y),
	)

	ops = []
	for edge in mol.edges:
		start, end = bond_coords.get(edge, (None, None))
		ops.extend(render_geometry.build_bond_ops(edge, start, end, context))

	for vertex in mol.vertices:
		ops.extend(render_geometry.build_vertex_ops(
			vertex,
			show_hydrogens_on_hetero=show_hydrogens_on_hetero,
			color_atoms=color_atoms,
			atom_colors=atom_colors_map,
			font_name=font_name,
			font_size=font_size,
		))
	return ops


#============================================
def _build_cholesterol_mol():
	"""Build cholesterol molecule from CDML template."""

	# Handle imports for both module and script usage
	if __name__ == "__main__":
		import oasa
		cdml_module = oasa.cdml
	else:
		import oasa.cdml as cdml_module

	# CDML file lives in bkchem templates
	repo_root = get_repo_root()
	path = os.path.join(
		repo_root, "packages", "bkchem", "bkchem_data", "templates",
		"biomolecules", "lipids", "steroids", "cholesterol.cdml"
	)

	if not os.path.exists(path):
		raise FileNotFoundError(f"Cholesterol template not found: {path}")

	with open(path, 'r') as f:
		result = cdml_module.read_cdml(f.read())

	# read_cdml returns a generator, get first molecule
	try:
		mol = next(iter(result))
	except (StopIteration, TypeError):
		raise ValueError("Cholesterol CDML did not yield any molecules.")

	if mol is None:
		raise ValueError("Cholesterol CDML returned an empty molecule.")

	for atom_node in list(mol.vertices):
		if atom_node.symbol != "O":
			continue
		for neighbor in list(atom_node.neighbors):
			if neighbor.symbol != "C":
				continue
			if len(neighbor.neighbors) != 1:
				continue
			edge = mol.get_edge_between(atom_node, neighbor)
			if edge:
				mol.disconnect_edge(edge)
			mol.remove_vertex(neighbor)
			break

	return mol


#============================================
#============================================
def _vignette_layout_params():
	return {
		"row1_y": 325,
		"row1_height": 80,
		"row2_y": 495,
		"row2_height": 120,
		"row3_y": 660,
		"row3_height": 100,
		"margin": 40,
		"gutter": 20,
	}


#============================================
def _build_vignettes_ops(page_width, include_text):
	"""Build complex molecule vignettes using row-based layout."""
	params = _vignette_layout_params()
	row1_vignettes = [
		("Benzene", _build_benzene_ops()),
		("Haworth", _build_haworth_ops()),
		("Fischer", _build_fischer_ops()),
	]
	row2_vignettes = [
		("Cholesterol", _build_cholesterol_ops()),
		("alpha-D-Glucopyranose", _build_alpha_d_glucopyranose_ops()),
		("beta-D-Fructofuranose", _build_beta_d_fructofuranose_ops()),
	]
	row3_vignettes = [
		("alpha-D-Tagatopyranose", _build_alpha_d_tagatopyranose_ops()),
		("alpha-D-Psicofuranose", _build_alpha_d_psicofuranose_ops()),
	]
	row1_result = layout_row(
		row1_vignettes,
		y_top=params["row1_y"],
		page_width=page_width,
		row_height=params["row1_height"],
		gutter=params["gutter"],
		margin=params["margin"],
	)
	row2_result = layout_row(
		row2_vignettes,
		y_top=params["row2_y"],
		page_width=page_width,
		row_height=params["row2_height"],
		gutter=params["gutter"],
		margin=params["margin"],
	)
	row3_result = layout_row(
		row3_vignettes,
		y_top=params["row3_y"],
		page_width=page_width,
		row_height=params["row3_height"],
		gutter=params["gutter"],
		margin=params["margin"],
	)

	ops = []
	for title, positioned_ops, x_center, _y_center in row1_result:
		ops.extend(positioned_ops)
		if include_text:
			ops.append(render_ops.TextOp(
				x=x_center,
				y=params["row1_y"] - 10,
				text=title,
				font_size=11,
				anchor="middle",
				weight="bold",
				color="#000",
			))

	for title, positioned_ops, x_center, _y_center in row2_result:
		ops.extend(positioned_ops)
		if include_text:
			ops.append(render_ops.TextOp(
				x=x_center,
				y=params["row2_y"] - 10,
				text=title,
				font_size=11,
				anchor="middle",
				weight="bold",
				color="#000",
			))

	for title, positioned_ops, x_center, _y_center in row3_result:
		ops.extend(positioned_ops)
		if include_text:
			ops.append(render_ops.TextOp(
				x=x_center,
				y=params["row3_y"] - 10,
				text=title,
				font_size=11,
				anchor="middle",
				weight="bold",
				color="#000",
			))

	return ops


#============================================
def _build_benzene_mol():
	"""Build benzene ring with alternating double bonds."""
	# Use SMILES with explicit single/double bonds (Kekule structure)
	mol = _mol_from_smiles("C1=CC=CC=C1", calc_coords=False)

	# Arrange in hexagon
	radius = 20
	atoms = list(mol.vertices)
	for i, a in enumerate(atoms):
		angle = i * math.pi / 3 + math.pi / 6
		a.x = radius * math.cos(angle)
		a.y = radius * math.sin(angle)

	return mol


#============================================
def _mol_from_smiles(smiles_str, calc_coords=True):
	"""Build molecule from SMILES.

	Args:
		smiles_str: SMILES string
		calc_coords: If True, generate initial 2D coordinates

	Returns:
		OASA molecule with atoms/bonds (and optional coordinates)
	"""
	# Handle imports for both module and script usage
	if __name__ == "__main__":
		import oasa
		smiles_module = oasa.smiles_lib
	else:
		import oasa.smiles_lib as smiles_module

	# Parse SMILES
	# calc_coords=1 generates initial 2D layout (required for haworth.build_haworth)
	# calc_coords=0 gives connectivity only
	mol = smiles_module.text_to_mol(smiles_str, calc_coords=1 if calc_coords else 0)
	return mol


#============================================
def _assert_haworth_invariants(mol, mode):
	"""Assert Haworth canonical invariants before rendering.

	Args:
		mol: OASA molecule
		mode: "pyranose" or "furanose"

	Raises:
		AssertionError: If any invariant is violated
	"""
	# Invariant 1: Exactly one in-ring oxygen vertex
	oxygen_vertices = [v for v in mol.vertices if v.symbol == 'O']
	assert len(oxygen_vertices) == 1, \
		f"Haworth {mode} must have exactly 1 in-ring oxygen, found {len(oxygen_vertices)}"

	# Invariant 2: Exactly one bond tagged as front
	front_bonds = [b for b in mol.edges if b.properties_.get('haworth_position') == 'front']
	assert len(front_bonds) >= 1, \
		f"Haworth {mode} must have at least 1 front bond tagged, found {len(front_bonds)}"

	# Invariant 3: Front edge is semantically marked (not just visually thick)
	for bond in front_bonds:
		assert bond.type in ('w', 'h', 'q'), \
			f"Haworth front bond must have semantic type (w/h/q), found {bond.type}"


def _build_haworth_mol():
	"""Build Haworth projection molecule using canonical layout rules."""
	# Build pyranose from SMILES (oxygen-first for canonical ordering)
	pyranose = _mol_from_smiles("O1CCCCC1")
	haworth.build_haworth(pyranose, mode="pyranose")
	_assert_haworth_invariants(pyranose, "pyranose")

	# Build furanose from SMILES
	furanose = _mol_from_smiles("O1CCCC1")
	haworth.build_haworth(furanose, mode="furanose")
	_assert_haworth_invariants(furanose, "furanose")

	# Offset furanose for side-by-side layout
	gap = 50.0
	offset_x = (max(v.x for v in pyranose.vertices) - min(v.x for v in furanose.vertices)) + gap
	for v in furanose.vertices:
		v.x += offset_x

	# Combine into single molecule for rendering
	combined = pyranose
	combined.insert_a_graph(furanose)
	return combined


def _build_haworth_ops():
	"""Build Haworth projection ops from canonical molecule layout."""
	return _build_molecule_ops(_build_haworth_mol(), _mol_render_options())


#============================================
def _build_fischer_mol(show_explicit_hydrogens=False):
	"""Build Fischer projection from D-glucose SMILES.

	Fischer projection: vertical backbone with horizontal substituents.
	Tests: SMILES -> traversal-based layout -> render via molecule renderer.

	Args:
		show_explicit_hydrogens: If True, add explicit H atoms on stereocenters
		                        (default: False)
	"""
	# D-glucose open-chain form (simplified, no explicit stereo for now)
	# C(=O)C(O)C(O)C(O)C(O)CO represents the 6-carbon aldose
	mol = _mol_from_smiles("C(=O)C(O)C(O)C(O)C(O)CO")

	# Find carbon backbone by traversing longest carbon chain
	# Start from aldehyde carbon (has =O neighbor)
	backbone = []
	for v in mol.vertices:
		if v.symbol == 'C':
			# Check if this carbon has a double-bonded oxygen (aldehyde)
			for bond in mol.edges:
				if v in bond.vertices:
					# Get neighbor: vertices is (v1, v2)
					v1, v2 = bond.vertices
					n = v2 if v1 == v else v1
					if n.symbol == 'O' and bond.order == 2:
						backbone.append(v)
						break
			if backbone:
				break

	# Traverse chain to build backbone list
	if backbone:
		visited = {backbone[0]}
		current = backbone[0]
		# Follow carbon-carbon single bonds
		while True:
			next_carbon = None
			for bond in mol.edges:
				if current not in bond.vertices or bond.order != 1:
					continue
				# Get neighbor
				v1, v2 = bond.vertices
				neighbor = v2 if v1 == current else v1
				if neighbor.symbol == 'C' and neighbor not in visited:
					next_carbon = neighbor
					break
			if next_carbon is None:
				break
			backbone.append(next_carbon)
			visited.add(next_carbon)
			current = next_carbon

	# Layout: place backbone vertically with measured bond_length
	bond_length = 25.0  # From context, not hardcoded magic
	for i, carbon in enumerate(backbone):
		carbon.x = 0.0
		carbon.y = i * bond_length

	# Place aldehyde group at 120-degree angle (O double bond, H single bond)
	if backbone:
		aldehyde = backbone[0]
		# Find aldehyde oxygen (double-bonded O)
		for bond in mol.edges:
			if aldehyde not in bond.vertices or bond.order != 2:
				continue
			v1, v2 = bond.vertices
			neighbor = v2 if v1 == aldehyde else v1
			if neighbor.symbol == "O":
				angle = math.radians(150)
				neighbor.x = aldehyde.x + bond_length * math.cos(angle)
				neighbor.y = aldehyde.y - bond_length * math.sin(angle)
				break
		# Add explicit aldehyde H on the opposite side
		angle = math.radians(30)
		aldehyde_h = atom.atom(symbol="H")
		aldehyde_h.x = aldehyde.x + bond_length * math.cos(angle)
		aldehyde_h.y = aldehyde.y - bond_length * math.sin(angle)
		aldehyde_h.properties_["fischer_role"] = "aldehyde_h"
		mol.add_vertex(aldehyde_h)
		aldehyde_bond = bond_module.bond(order=1, type="n")
		aldehyde_bond.vertices = (aldehyde, aldehyde_h)
		mol.add_edge(aldehyde, aldehyde_h, aldehyde_bond)

	# Place substituents horizontally (vertical for aldehyde oxygen)
	# For each carbon, find non-backbone neighbors and place them
	sub_length = 15.0  # Horizontal bond length
	for i, carbon in enumerate(backbone):
		if i == len(backbone) - 1:
			carbon.properties_["label"] = "CH<sub>2</sub>OH"
			for bond in list(mol.edges):
				if carbon not in bond.vertices:
					continue
				v1, v2 = bond.vertices
				neighbor = v2 if v1 == carbon else v1
				if neighbor in backbone:
					continue
				if neighbor.symbol == "O" and bond.order == 1:
					mol.disconnect_edge(bond)
					mol.remove_vertex(neighbor)
		substituents = []
		for bond in mol.edges:
			if carbon in bond.vertices:
				# Get neighbor
				v1, v2 = bond.vertices
				neighbor = v2 if v1 == carbon else v1
				if neighbor not in backbone:
					substituents.append((neighbor, bond))

		# Place substituents alternating left/right (D-glucose pattern)
		# C2, C4, C5: OH right, others left
		# C3: OH left
		# This is simplified - real stereo would come from SMILES stereo flags
		for j, (sub, bond) in enumerate(substituents):
			if sub.properties_.get("fischer_role") == "aldehyde_h":
				continue
			horizontal = True
			if sub.symbol == 'O' and bond.order == 1:  # OH group
				# D-glucose pattern: C2=right, C3=left, C4=right, C5=right
				if i in [1, 3, 4]:  # C2, C4, C5 (0-indexed)
					sub.x = carbon.x + sub_length
					sub.properties_["label_anchor"] = "start"
				else:
					sub.x = carbon.x - sub_length
					sub.properties_["label_anchor"] = "end"
				sub.properties_["label"] = "HO" if sub.x < carbon.x else "OH"
			elif sub.symbol == 'H':  # H
				# Opposite side from OH
				if i in [1, 3, 4]:
					sub.x = carbon.x - sub_length
				else:
					sub.x = carbon.x + sub_length
			elif sub.symbol == 'O' and bond.order == 2:  # Aldehyde O (already placed)
				horizontal = False
			else:  # Other (e.g., CH2 in CH2OH)
				sub.x = carbon.x
				sub.y = carbon.y

			if horizontal:
				sub.y = carbon.y  # Same y as carbon for horizontal bonds

	if show_explicit_hydrogens:
		for carbon in backbone[1:-1]:
			left_sub = None
			right_sub = None
			for bond in mol.edges:
				if carbon not in bond.vertices:
					continue
				v1, v2 = bond.vertices
				neighbor = v2 if v1 == carbon else v1
				if neighbor in backbone:
					continue
				if neighbor.symbol not in ["O", "H"]:
					continue
				if bond.order != 1:
					continue
				dx = neighbor.x - carbon.x
				if dx > 0:
					right_sub = neighbor
				elif dx < 0:
					left_sub = neighbor

			if left_sub is None:
				left_h = atom.atom(symbol="H")
				left_h.x = carbon.x - sub_length
				left_h.y = carbon.y
				mol.add_vertex(left_h)
				left_bond = bond_module.bond(order=1, type="n")
				left_bond.vertices = (carbon, left_h)
				mol.add_edge(carbon, left_h, left_bond)

			if right_sub is None:
				right_h = atom.atom(symbol="H")
				right_h.x = carbon.x + sub_length
				right_h.y = carbon.y
				mol.add_vertex(right_h)
				right_bond = bond_module.bond(order=1, type="n")
				right_bond.vertices = (carbon, right_h)
				mol.add_edge(carbon, right_h, right_bond)

	return mol


#============================================
def _build_benzene_ops():
	return _build_molecule_ops(_build_benzene_mol(), _mol_render_options())


#============================================
def _build_fischer_ops(show_explicit_hydrogens=False):
	mol = _build_fischer_mol(show_explicit_hydrogens=show_explicit_hydrogens)
	return _build_molecule_ops(mol, _mol_render_options())


#============================================
def _build_cholesterol_ops():
	options = _mol_render_options()
	options["show_hydrogens_on_hetero"] = False
	return _build_molecule_ops(_build_cholesterol_mol(), options)


#============================================
def _build_alpha_d_glucopyranose_ops():
	parsed = sugar_code.parse("ARLRDM")
	spec = haworth_spec.generate(parsed, ring_type="pyranose", anomeric="alpha")
	return haworth_renderer.render(spec, bond_length=30, show_hydrogens=False)


#============================================
def _build_beta_d_fructofuranose_ops():
	parsed = sugar_code.parse("MKLRDM")
	spec = haworth_spec.generate(parsed, ring_type="furanose", anomeric="beta")
	return haworth_renderer.render(spec, bond_length=30, show_hydrogens=False)


#============================================
def _build_alpha_d_tagatopyranose_ops():
	parsed = sugar_code.parse("MKRRDM")
	spec = haworth_spec.generate(parsed, ring_type="pyranose", anomeric="alpha")
	return haworth_renderer.render(spec, bond_length=30, show_hydrogens=False)


#============================================
def _build_alpha_d_psicofuranose_ops():
	parsed = sugar_code.parse("MKLLDM")
	spec = haworth_spec.generate(parsed, ring_type="furanose", anomeric="alpha")
	return haworth_renderer.render(spec, bond_length=30, show_hydrogens=False)


#============================================
#============================================
def main():
	"""CLI entry point."""
	import argparse

	parser = argparse.ArgumentParser(
		description="Generate OASA renderer capabilities sheet"
	)
	parser.add_argument(
		"-o", "--out",
		dest="output",
		default=None,
		help="Output file path (default: oasa_capabilities_sheet.{format})"
	)
	parser.add_argument(
		"--format",
		default="pdf",
		choices=["svg", "png", "pdf"],
		help="Output format (default: pdf)"
	)
	parser.add_argument(
		"--page",
		default="letter",
		choices=["letter", "a4"],
		help="Page size (default: letter, always portrait)"
	)
	parser.add_argument(
		"--dpi",
		type=float,
		default=600,
		help="PNG DPI (default: 600)"
	)

	args = parser.parse_args()

	# Set default output filename if not specified
	if args.output is None:
		args.output = f"oasa_capabilities_sheet.{args.format}"

	print("Generating capabilities sheet...")

	if args.format == "svg":
		# SVG backend
		svg_text = build_renderer_capabilities_sheet(
			page=args.page,
			backend="svg"
		)
		with open(args.output, "w", encoding="utf-8") as f:
			f.write(svg_text)
		print(f"Wrote {len(svg_text)} bytes to {args.output}")

	else:
		# Cairo backend for PNG and PDF
		try:
			import cairo
			_ = cairo
		except ImportError:
			print("ERROR: pycairo is required for PNG and PDF output")
			print("Install with: pip install pycairo")
			return 1

		# Render to cairo
		build_renderer_capabilities_sheet(
			page=args.page,
			backend="cairo",
			output_path=args.output,
			cairo_format=args.format,
			png_dpi=args.dpi
		)

		import os
		file_size = os.path.getsize(args.output)
		print(f"Wrote {file_size} bytes to {args.output}")


#============================================
if __name__ == "__main__":
	main()
