#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""High-level render output helpers built on render_ops painters."""

# Standard Library
import io
import os
import xml.dom.minidom as dom

# local repo modules
from oasa import dom_extensions
from oasa import molecule_utils
from oasa import render_geometry
from oasa import render_ops
from oasa import svg_out


_RENDER_STYLE_KEYS = (
	"line_width",
	"bond_width",
	"wedge_width",
	"bold_line_width_multiplier",
	"bond_second_line_shortening",
	"color_atoms",
	"color_bonds",
	"atom_colors",
	"show_hydrogens_on_hetero",
	"font_name",
	"font_size",
	"show_carbon_symbol",
)


#============================================
def _resolve_format(output_target, format_override):
	if format_override:
		return format_override.lower()
	if hasattr(output_target, "write"):
		raise ValueError("Format is required when output target has no filename.")
	extension = os.path.splitext(str(output_target))[1].lower().lstrip(".")
	if extension in ("svg", "png", "pdf", "ps"):
		return extension
	raise ValueError(
		"Output format could not be determined; use format=svg|png|pdf|ps or a matching filename."
	)


#============================================
def _molecule_bounds(mol):
	if not mol.vertices:
		return (0.0, 0.0, 1.0, 1.0)
	xs = [vertex.x for vertex in mol.vertices]
	ys = [vertex.y for vertex in mol.vertices]
	x1 = min(xs)
	x2 = max(xs)
	y1 = min(ys)
	y2 = max(ys)
	if x1 == x2:
		x2 = x1 + 1.0
	if y1 == y2:
		y2 = y1 + 1.0
	return (x1, y1, x2, y2)


#============================================
def _extract_style(options, scaling):
	style = {}
	for key in _RENDER_STYLE_KEYS:
		if key in options:
			style[key] = options[key]
	for metric in ("line_width", "bond_width", "wedge_width", "font_size"):
		if metric in style:
			style[metric] = float(style[metric]) * scaling
	return style


#============================================
def _render_ops_for_mol(mol, *, margin, scaling, options):
	x1, y1, _x2, _y2 = _molecule_bounds(mol)

	def _transform_xy(x, y):
		return ((x - x1 + margin) * scaling, (y - y1 + margin) * scaling)

	style = _extract_style(options, scaling)
	ops = render_geometry.molecule_to_ops(mol, style=style, transform_xy=_transform_xy)
	width = int(round(((_molecule_bounds(mol)[2] - x1) + 2 * margin) * scaling))
	height = int(round(((_molecule_bounds(mol)[3] - y1) + 2 * margin) * scaling))
	return ops, max(1, width), max(1, height)


#============================================
def _ops_to_svg_document(ops, width, height):
	document = dom.Document()
	root = dom_extensions.elementUnder(
		document,
		"svg",
		attributes=(
			("xmlns", "http://www.w3.org/2000/svg"),
			("version", "1.0"),
			("width", str(width)),
			("height", str(height)),
		),
	)
	group = dom_extensions.elementUnder(root, "g")
	render_ops.ops_to_svg(group, ops)
	return document


#============================================
def _set_cairo_background(context, width, height, background_color):
	rgba = background_color
	if rgba is None:
		rgba = (1.0, 1.0, 1.0, 1.0)
	if len(rgba) == 3:
		rgba = (rgba[0], rgba[1], rgba[2], 1.0)
	context.save()
	context.set_source_rgba(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3]))
	context.rectangle(0, 0, width, height)
	context.fill()
	context.restore()


#============================================
def _render_cairo(ops, output_target, fmt, width, height, options):
	try:
		import cairo
	except ImportError as exc:
		raise RuntimeError("Cairo output requires pycairo.") from exc
	if fmt == "png":
		surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
	elif fmt == "pdf":
		surface = cairo.PDFSurface(output_target, width, height)
	elif fmt == "svg":
		surface = cairo.SVGSurface(output_target, width, height)
	elif fmt == "ps":
		surface = cairo.PSSurface(output_target, width, height)
	else:
		raise ValueError(f"Unsupported cairo format: {fmt}")
	context = cairo.Context(surface)
	_set_cairo_background(
		context,
		width,
		height,
		options.get("background_color", (1.0, 1.0, 1.0, 1.0)),
	)
	render_ops.ops_to_cairo(context, ops)
	context.show_page()
	if fmt == "png":
		surface.write_to_png(output_target)
	surface.finish()


#============================================
def render_to_svg(mol, output_target, **options):
	margin = float(options.get("margin", 15))
	scaling = float(options.get("scaling", 1.0))
	ops, width, height = _render_ops_for_mol(
		mol,
		margin=margin,
		scaling=scaling,
		options=options,
	)
	document = _ops_to_svg_document(ops, width, height)
	text = svg_out.pretty_print_svg(document.toxml("utf-8"))
	if hasattr(output_target, "write"):
		if isinstance(output_target, io.TextIOBase):
			output_target.write(text)
		else:
			output_target.write(text.encode("utf-8"))
	else:
		with open(output_target, "w", encoding="utf-8") as handle:
			handle.write(text)
	return output_target


#============================================
def render_to_png(mol, output_target, **options):
	margin = float(options.get("margin", 15))
	scaling = float(options.get("scaling", 2.0))
	ops, width, height = _render_ops_for_mol(
		mol,
		margin=margin,
		scaling=scaling,
		options=options,
	)
	_render_cairo(ops, output_target, "png", width, height, options)
	return output_target


#============================================
def render_to_pdf(mol, output_target, **options):
	margin = float(options.get("margin", 15))
	scaling = float(options.get("scaling", 1.0))
	ops, width, height = _render_ops_for_mol(
		mol,
		margin=margin,
		scaling=scaling,
		options=options,
	)
	_render_cairo(ops, output_target, "pdf", width, height, options)
	return output_target


#============================================
def render_to_ps(mol, output_target, **options):
	margin = float(options.get("margin", 15))
	scaling = float(options.get("scaling", 1.0))
	ops, width, height = _render_ops_for_mol(
		mol,
		margin=margin,
		scaling=scaling,
		options=options,
	)
	_render_cairo(ops, output_target, "ps", width, height, options)
	return output_target


#============================================
def mol_to_output(mol, output_target, fmt=None, **options):
	"""Render one molecule to SVG/PDF/PNG/PS."""
	legacy_format = options.pop("format", None)
	output_format = _resolve_format(output_target, fmt or legacy_format)
	if output_format == "svg":
		return render_to_svg(mol, output_target, **options)
	if output_format == "png":
		return render_to_png(mol, output_target, **options)
	if output_format == "pdf":
		return render_to_pdf(mol, output_target, **options)
	if output_format == "ps":
		return render_to_ps(mol, output_target, **options)
	raise ValueError(f"Unsupported output format: {output_format}")


#============================================
def mols_to_output(mols, output_target, fmt=None, **options):
	"""Render multiple molecules by merging disconnected parts."""
	legacy_format = options.pop("format", None)
	mol = molecule_utils.merge_molecules(list(mols))
	if mol is None:
		raise ValueError("No molecules supplied for rendering.")
	return mol_to_output(mol, output_target, fmt=fmt or legacy_format, **options)
