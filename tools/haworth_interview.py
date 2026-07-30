#!/usr/bin/env python3
"""Interactive Haworth projection generator for instructors.

Guides the user through selecting a sugar by carbon count, type,
stereochemistry, ring form, and anomeric configuration, then renders
the Haworth projection as SVG and PNG.
"""

# Standard Library
import argparse
import io
import os
import re
import sys
# PIP3 modules
import PIL.Image
import PIL.ImageChops
import yaml

# local repo modules
import oasa.sugar_code
import oasa.haworth.renderer
import oasa.render_ops
import oasa.render_out
import oasa.svg_out
import oasa.dom_extensions


# ring form constraints: (prefix, ring_type) -> min carbons
_RING_RULES = {
	("ALDO", "furanose"): 4,
	("ALDO", "pyranose"): 5,
	("KETO", "furanose"): 5,
	("KETO", "pyranose"): 6,
	("3-KETO", "furanose"): 6,
	("3-KETO", "pyranose"): 7,
}

# prefix detection from code string
_PREFIX_MAP = {
	"MRK": "3-KETO",
	"MLK": "3-KETO",
	"MK": "KETO",
	"A": "ALDO",
}


#============================================
def _detect_prefix(code: str) -> tuple:
	"""Return (prefix_token, prefix_kind) for a sugar code string."""
	for token, kind in _PREFIX_MAP.items():
		if code.startswith(token):
			return token, kind
	raise ValueError(f"Unknown sugar code prefix: {code}")


#============================================
def _carbon_count(code: str) -> int:
	"""Return the number of backbone carbons from a sugar code."""
	prefix_token, _kind = _detect_prefix(code)
	# remaining characters after prefix: each is one backbone carbon
	# except prefix itself encodes carbon(s) too
	# prefix A = C1, MK = C1+C2, MRK/MLK = C1+C2+C3
	remaining = len(code) - len(prefix_token)
	prefix_carbons = len(prefix_token)
	return prefix_carbons + remaining


#============================================
def _config_letter(code: str) -> str:
	"""Return D or L config letter from a sugar code (second to last char)."""
	return code[-2]


#============================================
def _load_sugar_database() -> list:
	"""Load sugar_codes.yaml and return list of (code, name, n_carbons, prefix_kind, config)."""
	# find the yaml file relative to oasa package
	yaml_path = os.path.join(
		os.path.dirname(oasa.sugar_code.__file__),
		"..", "oasa_data", "sugar_codes.yaml"
	)
	yaml_path = os.path.normpath(yaml_path)
	with open(yaml_path, "r") as fh:
		data = yaml.safe_load(fh)
	entries = []
	for _section, sugars in data.items():
		if not isinstance(sugars, dict):
			continue
		for code, name in sugars.items():
			prefix_token, prefix_kind = _detect_prefix(code)
			n_carbons = _carbon_count(code)
			config = _config_letter(code)
			entries.append((code, name, n_carbons, prefix_kind, config))
	return entries


# carbon-count display names
_CARBON_NAMES = {
	3: "triose",
	4: "tetrose",
	5: "pentose",
	6: "hexose",
	7: "heptose",
}


#============================================
def _prompt_carbon_count(prompt_text: str, available: list) -> int:
	"""Prompt for carbon count using the actual number as the input key."""
	print(f"\n{prompt_text}")
	for nc in available:
		label = _CARBON_NAMES.get(nc, "")
		if label:
			print(f"  {nc}. {nc} carbons ({label})")
		else:
			print(f"  {nc}. {nc} carbons")
	while True:
		raw = input("Enter number of carbons: ").strip()
		if raw.isdigit() and int(raw) in available:
			n = int(raw)
			label = _CARBON_NAMES.get(n, "")
			suffix = f" ({label})" if label else ""
			print(f"  -> {n} carbons{suffix}")
			return n
		valid = ", ".join(str(c) for c in available)
		print(f"  Please enter one of: {valid}")


#============================================
def _prompt_choice(prompt_text: str, options: list) -> str:
	"""Display numbered options and return the selected value."""
	print(f"\n{prompt_text}")
	for i, (label, _value) in enumerate(options, 1):
		print(f"  {i}. {label}")
	while True:
		raw = input("Enter choice number: ").strip()
		if raw.isdigit() and 1 <= int(raw) <= len(options):
			chosen = options[int(raw) - 1]
			print(f"  -> {chosen[0]}")
			return chosen[1]
		print(f"  Please enter a number between 1 and {len(options)}")


#============================================
def _prompt_config(prompt_text: str, available: list) -> str:
	"""Prompt for D/L configuration, accepting letter or number."""
	print(f"\n{prompt_text}")
	for i, c in enumerate(available, 1):
		print(f"  {i}. {c}-sugar")
	while True:
		raw = input("Enter choice (D/L or number): ").strip().upper()
		# accept the letter directly
		if raw in available:
			print(f"  -> {raw}-sugar")
			return raw
		# accept number index
		if raw.isdigit() and 1 <= int(raw) <= len(available):
			chosen = available[int(raw) - 1]
			print(f"  -> {chosen}-sugar")
			return chosen
		valid_letters = "/".join(available)
		print(f"  Please enter {valid_letters} or a number 1-{len(available)}")


#============================================
def _get_available_types(n_carbons: int, entries: list) -> list:
	"""Return list of prefix kinds available for a given carbon count."""
	available = set()
	for _code, _name, nc, prefix_kind, _config in entries:
		if nc == n_carbons:
			available.add(prefix_kind)
	# sort in a stable display order
	order = ["ALDO", "KETO", "3-KETO"]
	result = [t for t in order if t in available]
	return result


#============================================
def _get_available_configs(n_carbons: int, prefix_kind: str, entries: list) -> list:
	"""Return list of D/L configs available for a carbon count and type."""
	available = set()
	for _code, _name, nc, pk, config in entries:
		if nc == n_carbons and pk == prefix_kind:
			available.add(config)
	result = sorted(available)
	return result


#============================================
def _get_matching_sugars(n_carbons: int, prefix_kind: str, config: str, entries: list) -> list:
	"""Return list of (code, name) tuples matching the criteria."""
	matches = []
	for code, name, nc, pk, cfg in entries:
		if nc == n_carbons and pk == prefix_kind and cfg == config:
			matches.append((code, name))
	return matches


#============================================
def _get_available_ring_forms(n_carbons: int, prefix_kind: str) -> list:
	"""Return list of valid ring forms for the given carbon count and type."""
	forms = []
	for (pk, ring_type), min_c in _RING_RULES.items():
		if pk == prefix_kind and n_carbons >= min_c:
			forms.append(ring_type)
	return forms


#============================================
def _strip_markup(text: str) -> str:
	"""Remove simple XML/HTML tags from text to get plain character count."""
	return re.sub(r"<[^>]+>", "", text)


#============================================
def _compute_ops_bbox(ops: list) -> tuple:
	"""Compute (min_x, min_y, width, height) bounding box from render ops.

	Handles all five op types from oasa.render_ops: LineOp, PolygonOp,
	CircleOp, PathOp, and TextOp. Text width is estimated from character
	count and font size since exact metrics are not available.
	"""
	all_x = []
	all_y = []
	for op in ops:
		# LineOp: p1 and p2 are (x, y) tuples
		if hasattr(op, "p1") and hasattr(op, "p2"):
			all_x.extend([op.p1[0], op.p2[0]])
			all_y.extend([op.p1[1], op.p2[1]])
		# PolygonOp: points is a tuple of (x, y) tuples
		if hasattr(op, "points"):
			for pt in op.points:
				all_x.append(pt[0])
				all_y.append(pt[1])
		# CircleOp: center is (x, y), radius is float
		if hasattr(op, "center") and hasattr(op, "radius"):
			cx, cy = op.center
			r = op.radius
			all_x.extend([cx - r, cx + r])
			all_y.extend([cy - r, cy + r])
		# PathOp: commands is a tuple of (cmd_str, payload_tuple|None)
		if hasattr(op, "commands"):
			for cmd, payload in op.commands:
				if payload is None:
					continue
				if cmd in ("M", "L"):
					# payload is (x, y)
					all_x.append(payload[0])
					all_y.append(payload[1])
				elif cmd == "ARC":
					# payload is (cx, cy, r, angle1, angle2)
					# conservative bbox: use full circle extent around center
					arc_cx, arc_cy, arc_r = payload[0], payload[1], payload[2]
					all_x.extend([arc_cx - arc_r, arc_cx + arc_r])
					all_y.extend([arc_cy - arc_r, arc_cy + arc_r])
		# TextOp: x, y, text, font_size, anchor
		if hasattr(op, "text") and hasattr(op, "anchor"):
			font_size = getattr(op, "font_size", 12.0)
			plain = _strip_markup(op.text)
			# estimate text width: ~0.6 * font_size per character
			text_width = len(plain) * font_size * 0.6
			anchor = getattr(op, "anchor", "start")
			if anchor == "middle":
				all_x.extend([op.x - text_width / 2, op.x + text_width / 2])
			elif anchor == "end":
				all_x.extend([op.x - text_width, op.x])
			else:
				# anchor == "start"
				all_x.extend([op.x, op.x + text_width])
			# vertical extent: text baseline is at y, top is roughly y - font_size
			all_y.extend([op.y - font_size, op.y])
	if not all_x:
		return (0, 0, 100, 100)
	margin = 20
	min_x = min(all_x) - margin
	min_y = min(all_y) - margin
	width = int(max(all_x) - min_x + margin)
	height = int(max(all_y) - min_y + margin)
	return (min_x, min_y, width, height)


#============================================
def _trim_whitespace(image: PIL.Image.Image, padding: int = 4) -> PIL.Image.Image:
	"""Trim white borders from a PIL image, keeping a small padding.

	Uses corner-pixel sampling to detect the background color, then crops
	to the content bounding box plus padding on each side.
	"""
	# detect background from the four corner pixels
	bg_color = image.getpixel((0, 0))
	bg = PIL.Image.new(image.mode, image.size, bg_color)
	diff = PIL.ImageChops.difference(image, bg)
	bbox = diff.getbbox()
	if bbox is None:
		return image
	# expand bbox by padding, clamped to image bounds
	x1 = max(0, bbox[0] - padding)
	y1 = max(0, bbox[1] - padding)
	x2 = min(image.width, bbox[2] + padding)
	y2 = min(image.height, bbox[3] + padding)
	return image.crop((x1, y1, x2, y2))


#============================================
def _render_svg(ops: list, output_path: str) -> None:
	"""Write render ops to an SVG file."""
	min_x, min_y, width, height = _compute_ops_bbox(ops)
	doc = oasa.render_out._ops_to_svg_document(ops, width, height)
	root = doc.documentElement
	root.setAttribute("viewBox", f"{min_x:.1f} {min_y:.1f} {width} {height}")
	svg_text = doc.toxml()
	svg_text = oasa.svg_out.pretty_print_svg(svg_text)
	with open(output_path, "w") as fh:
		fh.write(svg_text)
	print(f"  SVG: {output_path} ({len(svg_text)} bytes)")


#============================================
def _render_png(ops: list, output_path: str, target_size: int = 1024, transparent: bool = False) -> None:
	"""Write render ops to a PNG file via Cairo, scaled to ~target_size pixels."""
	try:
		import cairo
	except ImportError:
		print("  PNG: skipped (pycairo not installed)")
		return
	min_x, min_y, width, height = _compute_ops_bbox(ops)
	# scale so the larger dimension is ~target_size
	raw_max = max(width, height)
	scale = target_size / raw_max if raw_max > 0 else 1.0
	px_width = int(width * scale)
	px_height = int(height * scale)
	surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, px_width, px_height)
	context = cairo.Context(surface)
	if not transparent:
		# white background
		context.set_source_rgba(1.0, 1.0, 1.0, 1.0)
		context.rectangle(0, 0, px_width, px_height)
		context.fill()
	# scale and translate so render ops map into the pixel surface
	context.scale(scale, scale)
	context.translate(-min_x, -min_y)
	oasa.render_ops.ops_to_cairo(context, ops)
	# write to a temporary buffer, then trim whitespace with PIL
	buf = io.BytesIO()
	surface.write_to_png(buf)
	buf.seek(0)
	image = PIL.Image.open(buf)
	image = _trim_whitespace(image)
	image.save(output_path)
	final_w, final_h = image.size
	print(f"  PNG: {output_path} ({final_w}x{final_h}, {os.path.getsize(output_path)} bytes)")


#============================================
def _sanitize_filename(name: str) -> str:
	"""Convert a sugar name to a safe filename fragment."""
	# replace spaces, commas, and special chars with underscores
	safe = name.replace(" ", "_").replace(",", "").replace("-", "_")
	safe = safe.lower()
	return safe


#============================================
def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Interactive Haworth projection generator for instructors. "
		"Walks through selecting a sugar by carbon count, type, configuration, "
		"ring form, and anomeric state, then renders SVG and PNG output."
	)
	parser.add_argument(
		'-o', '--output-dir', dest='output_dir', default='output',
		help='Output directory for rendered files (default: output)',
	)
	parser.add_argument(
		'-H', '--show-hydrogens', dest='show_hydrogens',
		help='Show hydrogen labels on the projection', action='store_true',
	)
	parser.add_argument(
		'--hide-hydrogens', dest='show_hydrogens',
		help='Hide hydrogen labels (default)', action='store_false',
	)
	parser.set_defaults(show_hydrogens=False)
	parser.add_argument(
		'-t', '--transparent', dest='transparent',
		help='Use transparent background for PNG', action='store_true',
	)
	parser.add_argument(
		'--white-bg', dest='transparent',
		help='Use white background for PNG (default)', action='store_false',
	)
	parser.set_defaults(transparent=False)
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	"""Interactive Haworth projection interview."""
	args = parse_args()

	print("=" * 50)
	print("  Haworth Projection Generator")
	print("=" * 50)

	entries = _load_sugar_database()

	# step 1: number of carbons
	available_carbons = sorted(set(nc for _, _, nc, _, _ in entries))
	n_carbons = _prompt_carbon_count("How many carbons?", available_carbons)

	# step 2: sugar type
	available_types = _get_available_types(n_carbons, entries)
	if len(available_types) == 1:
		prefix_kind = available_types[0]
		print(f"\n  Only one type available: {prefix_kind}")
	else:
		type_labels = {
			"ALDO": "Aldose",
			"KETO": "Ketose (2-keto)",
			"3-KETO": "3-Ketose",
		}
		type_options = [(type_labels.get(t, t), t) for t in available_types]
		prefix_kind = _prompt_choice("Sugar type?", type_options)

	# step 3: D or L
	available_configs = _get_available_configs(n_carbons, prefix_kind, entries)
	if len(available_configs) == 1:
		config = available_configs[0]
		print(f"\n  Only one configuration available: {config}")
	else:
		config = _prompt_config("Configuration?", available_configs)

	# step 4: ring form
	ring_forms = _get_available_ring_forms(n_carbons, prefix_kind)
	if not ring_forms:
		print(f"\nNo ring forms available for {n_carbons}-carbon {prefix_kind} sugar.")
		print("Open-chain form only -- Haworth projection requires a ring.")
		sys.exit(0)
	if len(ring_forms) == 1:
		ring_type = ring_forms[0]
		print(f"\n  Only one ring form available: {ring_type}")
	else:
		ring_options = [(rt.capitalize(), rt) for rt in ring_forms]
		ring_type = _prompt_choice("Ring form?", ring_options)

	# step 5: anomeric form
	anomeric_options = [
		("Alpha (axial OH at anomeric carbon)", "alpha"),
		("Beta (equatorial OH at anomeric carbon)", "beta"),
	]
	anomeric = _prompt_choice("Anomeric configuration?", anomeric_options)

	# step 6: specific sugar
	matching = _get_matching_sugars(n_carbons, prefix_kind, config, entries)
	if len(matching) == 1:
		code, name = matching[0]
		print(f"\n  Only one sugar matches: {name} ({code})")
	else:
		sugar_options = [(f"{name} ({code})", (code, name)) for code, name in matching]
		code, name = _prompt_choice("Which sugar?", sugar_options)

	# build the full IUPAC-style name
	full_name = f"{anomeric}-{name}{ring_type}"
	print("\n" + "=" * 50)
	print(f"  Sugar:    {full_name}")
	print(f"  Code:     {code}")
	print(f"  Ring:     {ring_type}")
	print(f"  Anomeric: {anomeric}")
	print("=" * 50)

	# render
	ops = oasa.haworth.renderer.render_from_code(
		code=code,
		ring_type=ring_type,
		anomeric=anomeric,
		bond_length=30.0,
		font_size=12.0,
		show_hydrogens=args.show_hydrogens,
		show_carbon_numbers=False,
	)
	print(f"\nGenerated {len(ops)} render ops")

	# output files
	out_dir = args.output_dir
	os.makedirs(out_dir, exist_ok=True)
	base_name = _sanitize_filename(f"{anomeric}_{name}_{ring_type}")
	svg_path = os.path.join(out_dir, f"{base_name}.svg")
	png_path = os.path.join(out_dir, f"{base_name}.png")

	_render_svg(ops, svg_path)
	_render_png(ops, png_path, transparent=args.transparent)

	print("\nDone!")


#============================================
if __name__ == "__main__":
	main()
