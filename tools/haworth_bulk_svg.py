#!/usr/bin/env python3
"""Bulk Haworth projection SVG generator.

Generates SVG files for all sugars matching the specified filters
(carbon count, type, configuration, ring form, anomeric state).
"""

# Standard Library
import os
import re
import argparse

# PIP3 modules
import yaml

# local repo modules
import oasa.sugar_code
import oasa.haworth.renderer
import oasa.render_out
import oasa.svg_out


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

# carbon-count display names
_CARBON_NAMES = {
	3: "triose",
	4: "tetrose",
	5: "pentose",
	6: "hexose",
	7: "heptose",
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
	remaining = len(code) - len(prefix_token)
	prefix_carbons = len(prefix_token)
	total = prefix_carbons + remaining
	return total


#============================================
def _config_letter(code: str) -> str:
	"""Return D or L config letter from a sugar code (second to last char)."""
	return code[-2]


#============================================
def _load_sugar_database() -> list:
	"""Load sugar_codes.yaml and return list of (code, name, n_carbons, prefix_kind, config)."""
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


#============================================
def _can_form_ring(prefix_kind: str, ring_type: str, n_carbons: int) -> bool:
	"""Check if the sugar can form the specified ring type."""
	key = (prefix_kind, ring_type)
	if key not in _RING_RULES:
		return False
	min_carbons = _RING_RULES[key]
	return n_carbons >= min_carbons


#============================================
def _strip_markup(text: str) -> str:
	"""Remove simple XML/HTML tags from text to get plain character count."""
	return re.sub(r"<[^>]+>", "", text)


#============================================
def _compute_ops_bbox(ops: list) -> tuple:
	"""Compute (min_x, min_y, width, height) bounding box from render ops."""
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
					all_x.append(payload[0])
					all_y.append(payload[1])
				elif cmd == "ARC":
					arc_cx, arc_cy, arc_r = payload[0], payload[1], payload[2]
					all_x.extend([arc_cx - arc_r, arc_cx + arc_r])
					all_y.extend([arc_cy - arc_r, arc_cy + arc_r])
		# TextOp: x, y, text, font_size, anchor
		if hasattr(op, "text") and hasattr(op, "anchor"):
			font_size = getattr(op, "font_size", 12.0)
			plain = _strip_markup(op.text)
			text_width = len(plain) * font_size * 0.6
			anchor = getattr(op, "anchor", "start")
			if anchor == "middle":
				all_x.extend([op.x - text_width / 2, op.x + text_width / 2])
			elif anchor == "end":
				all_x.extend([op.x - text_width, op.x])
			else:
				all_x.extend([op.x, op.x + text_width])
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


#============================================
def _sanitize_filename(name: str) -> str:
	"""Convert a sugar name to a safe filename fragment."""
	safe = name.replace(" ", "_").replace(",", "").replace("-", "_")
	safe = safe.lower()
	return safe


#============================================
def _filter_entries(entries: list, n_carbons: int, prefix_kind: str,
		config: str, ring_type: str) -> list:
	"""Filter sugar entries by all criteria including ring form validity."""
	results = []
	for code, name, nc, pk, cfg in entries:
		# apply carbon count filter
		if n_carbons is not None and nc != n_carbons:
			continue
		# apply sugar type filter
		if prefix_kind is not None and pk != prefix_kind:
			continue
		# apply D/L configuration filter
		if config is not None and cfg != config:
			continue
		# check ring form compatibility
		if not _can_form_ring(pk, ring_type, nc):
			continue
		results.append((code, name, nc, pk, cfg))
	return results


#============================================
def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Bulk Haworth projection SVG generator. "
		"Generates SVG files for all sugars matching the specified filters."
	)
	parser.add_argument(
		'-c', '--carbons', dest='n_carbons', type=int,
		choices=[3, 4, 5, 6, 7],
		help='Filter by number of backbone carbons',
	)
	parser.add_argument(
		'-t', '--type', dest='sugar_type', type=str,
		choices=('ALDO', 'KETO', '3-KETO'),
		help='Filter by sugar type',
	)
	parser.add_argument(
		'-g', '--config', dest='config', type=str,
		choices=('D', 'L'),
		help='Filter by D or L configuration',
	)
	parser.add_argument(
		'-r', '--ring', dest='ring_type', type=str, required=True,
		choices=('pyranose', 'furanose'),
		help='Ring form (required)',
	)
	# anomeric: default both
	anomeric_group = parser.add_mutually_exclusive_group()
	anomeric_group.add_argument(
		'-a', '--anomeric', dest='anomeric', type=str,
		choices=('alpha', 'beta', 'both'),
		help='Anomeric configuration (default: both)',
	)
	parser.set_defaults(anomeric='both')
	parser.add_argument(
		'-o', '--output-dir', dest='output_dir', default='output',
		help='Output directory for SVG files (default: output)',
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
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	"""Generate bulk Haworth projection SVGs."""
	args = parse_args()

	entries = _load_sugar_database()

	# filter entries by criteria
	filtered = _filter_entries(
		entries, args.n_carbons, args.sugar_type,
		args.config, args.ring_type
	)

	if not filtered:
		print("No sugars match the specified filters.")
		return

	# determine which anomeric forms to generate
	if args.anomeric == 'both':
		anomeric_list = ['alpha', 'beta']
	else:
		anomeric_list = [args.anomeric]

	# create output directory
	os.makedirs(args.output_dir, exist_ok=True)

	# generate SVGs
	total = 0
	for code, name, n_carbons, prefix_kind, config in filtered:
		for anomeric in anomeric_list:
			base_name = _sanitize_filename(f"{anomeric}_{name}_{args.ring_type}")
			svg_path = os.path.join(args.output_dir, f"{base_name}.svg")
			# render the haworth projection
			ops = oasa.haworth.renderer.render_from_code(
				code=code,
				ring_type=args.ring_type,
				anomeric=anomeric,
				bond_length=30.0,
				font_size=12.0,
				show_hydrogens=args.show_hydrogens,
				show_carbon_numbers=False,
			)
			_render_svg(ops, svg_path)
			total += 1
			# print progress line
			full_name = f"{anomeric}-{name}"
			print(f"  {total:3d}. {full_name:<40s} -> {svg_path}")

	print(f"\nGenerated {total} SVG files in {args.output_dir}/")


#============================================
if __name__ == "__main__":
	main()
