"""Normalized frontend-neutral appearance facts for CDML presentation roots."""

# Standard Library
import dataclasses
import math
import re


_COLOR = re.compile(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?")
_YES = frozenset({"1", "both", "true", "yes"})
_NO = frozenset({"0", "false", "no"})
_FILLED_KINDS = frozenset({"circle", "oval", "polygon", "rect", "square"})
_FONT_KINDS = frozenset({"plus", "text"})


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLPresentationAppearance:
	"""Effective visible scalars after applying the authoritative standard."""

	line_width: float
	line_color: str
	fill_color: str | None
	font_family: str | None
	font_size: int | None
	font_color: str | None
	start_head: bool | None
	end_head: bool | None
	spline: bool


#============================================
def _color(value: str, description: str) -> str:
	"""Normalize one supported CDML color spelling to six-digit lowercase."""
	if _COLOR.fullmatch(value) is None:
		raise ValueError(f"{description} is not a hexadecimal color")
	digits = value[1:].lower()
	if len(digits) == 3:
		digits = "".join(character * 2 for character in digits)
	return f"#{digits}"


#============================================
def _positive_number(value: str, description: str) -> float:
	"""Return one finite positive authored presentation number."""
	try:
		number = float(value)
	except ValueError as error:
		raise ValueError(f"{description} is not a number") from error
	if not math.isfinite(number) or number <= 0.0:
		raise ValueError(f"{description} must be finite and positive")
	return number


#============================================
def _font_size(value: str, description: str) -> int:
	"""Return one supported presentation font size."""
	if not value.isdecimal():
		raise ValueError(f"{description} is not an integer")
	size = int(value)
	if not 4 <= size <= 144:
		raise ValueError(f"{description} must be from 4 to 144")
	return size


#============================================
def _boolean(value: str, default: bool, description: str) -> bool:
	"""Resolve one historical yes/no spelling with an explicit default."""
	if not value:
		return default
	normalized = value.lower()
	if normalized in _YES:
		return True
	if normalized in _NO:
		return False
	raise ValueError(f"{description} is not a supported yes/no value")


#============================================
def resolve(
		kind: str, attributes: tuple[tuple[str, str], ...],
		font_attributes: tuple[tuple[str, str], ...], standard: object,
		) -> CDMLPresentationAppearance:
	"""Resolve authored presentation attributes against one OASA standard fact."""
	root = dict(attributes)
	font = dict(font_attributes)
	line_width = (
		_positive_number(root["width"], f"{kind} width")
		if "width" in root else float(standard.line_width)
	)
	line_color = _color(
		root.get("line_color", root.get("color", standard.line_color)),
		f"{kind} line color",
	)
	fill_color = None
	if kind in _FILLED_KINDS:
		fill_value = root.get("area_color", root.get("background-color", standard.area_color))
		if fill_value and fill_value != "none":
			fill_color = _color(fill_value, f"{kind} fill color")
	elif kind in _FONT_KINDS:
		fill_value = root.get("background-color", "")
		if fill_value:
			fill_color = _color(fill_value, f"{kind} background color")
	font_family = None
	font_size = None
	font_color = None
	if kind in _FONT_KINDS:
		font_family = font.get("family", "").strip() or standard.font_family
		if not font_family:
			raise ValueError(f"{kind} font family is empty")
		font_size_value = font.get("size", root.get("font_size"))
		if font_size_value is None:
			font_size = 14 if kind == "plus" else int(standard.font_size)
		else:
			font_size = _font_size(font_size_value, f"{kind} font size")
		font_color = _color(
			font.get("color", root.get("line_color", root.get("color", standard.line_color))),
			f"{kind} font color",
		)
	start_head = None
	end_head = None
	if kind == "arrow":
		start_head = _boolean(root.get("start", ""), False, "arrow start head")
		end_head = _boolean(root.get("end", ""), True, "arrow end head")
	spline = False
	if kind in {"arrow", "polyline"}:
		spline = _boolean(root.get("spline", ""), False, f"{kind} spline")
	return CDMLPresentationAppearance(
		line_width, line_color, fill_color, font_family, font_size, font_color,
		start_head, end_head, spline,
	)
