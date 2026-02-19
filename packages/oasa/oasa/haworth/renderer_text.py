#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Text formatting and positioning helpers for Haworth rendering."""

# Standard Library
import re

from oasa.haworth.renderer_config import (
	HYDROXYL_GLYPH_WIDTH_FACTOR,
	HYDROXYL_O_X_CENTER_FACTOR,
	HYDROXYL_O_Y_CENTER_FROM_BASELINE,
	HYDROXYL_O_RADIUS_FACTOR,
	LEADING_C_X_CENTER_FACTOR,
)


#============================================
def chain_labels(label: str) -> list[str] | None:
	"""Convert compact exocyclic label markers to rendered segment labels."""
	if label == "CH(OH)CH2OH":
		return ["CHOH", "CH2OH"]
	match = re.match(r"^CHAIN(\d+)$", label or "")
	if not match:
		return None
	count = int(match.group(1))
	if count < 2:
		return None
	labels = []
	for _ in range(count - 1):
		labels.append("CHOH")
	labels.append("CH2OH")
	return labels


#============================================
def is_chain_like_label(label: str) -> bool:
	"""Return True for compact CH* labels that render as chain-like substituents."""
	text = str(label or "")
	if text.startswith("CH"):
		return True
	return chain_labels(text) is not None


#============================================
def is_chain_like_render_text(text: str) -> bool:
	"""Return True for rendered chain-like labels, including flipped CH2OH text."""
	value = str(text or "")
	if is_chain_like_label(value):
		return True
	visible = re.sub(r"<[^>]+>", "", value)
	if is_chain_like_label(visible):
		return True
	# Left-anchored CH2OH labels render as HOH2C but should keep chain-like
	# carbon-target attachment semantics.
	return visible.endswith("C") and ("H2" in visible)


#============================================
def is_two_carbon_tail_label(label: str) -> bool:
	"""Return True for labels rendered as a two-carbon branched sidechain."""
	segments = chain_labels(str(label or ""))
	return bool(segments) and segments == ["CHOH", "CH2OH"]


#============================================
def is_hydroxyl_render_text(text: str) -> bool:
	"""Return True when rendered text behaves as a hydroxyl token."""
	return hydroxyl_oxygen_center(
		text=text,
		anchor="start",
		text_x=0.0,
		text_y=0.0,
		font_size=1.0,
	) is not None


#============================================
def format_label_text(label: str, anchor: str = "middle") -> str:
	"""Convert plain labels to display text with side-aware hydroxyl ordering."""
	text = str(label)
	if text == "OH" and anchor == "end":
		text = "HO"
	text = apply_subscript_markup(text)
	return text


#============================================
def format_chain_label_text(label: str, anchor: str = "middle") -> str:
	"""Format exocyclic-chain segment labels with side-aware left-end flipping."""
	text = str(label)
	if anchor == "end":
		if text == "CH2OH":
			text = "HOH2C"
		elif text == "CHOH":
			text = "HOHC"
	text = apply_subscript_markup(text)
	return text


#============================================
def apply_subscript_markup(text: str) -> str:
	"""Apply numeric subscripts in compact molecular-fragment labels."""
	value = str(text or "")
	# Keep existing preformatted markup stable.
	if "<sub>" in value:
		return value
	# Subscript numeric runs that follow element/fragment characters.
	return re.sub(r"(?<=[A-Za-z\)])(\d+)", r"<sub>\1</sub>", value)


#============================================
def anchor_x_offset(text: str, anchor: str, font_size: float) -> float:
	"""Shift text origin for side-aware label placement."""
	if text == "OH":
		if anchor == "start":
			return -font_size * 0.30
		if anchor == "end":
			return font_size * 0.90
	if text == "HO":
		if anchor == "start":
			return -font_size * 0.90
		if anchor == "end":
			return font_size * 0.30
	carbon_offset = leading_carbon_anchor_offset(text, anchor, font_size)
	if carbon_offset is not None:
		return carbon_offset
	trailing_offset = trailing_carbon_anchor_offset(text, anchor, font_size)
	if trailing_offset is not None:
		return trailing_offset
	if anchor == "start":
		return font_size * 0.12
	if anchor == "end":
		return -font_size * 0.12
	return 0.0


#============================================
def baseline_shift(direction: str, font_size: float, text: str = "") -> float:
	"""Compute vertical baseline correction for label text."""
	if text in ("OH", "HO"):
		if direction == "down":
			return font_size * 0.90
		return -font_size * 0.10
	if direction == "down":
		return font_size * 0.35
	return -font_size * 0.10


#============================================
def leading_carbon_anchor_offset(text: str, anchor: str, font_size: float) -> float | None:
	"""Return text-x offset for labels that should connect at leading-carbon center."""
	visible = re.sub(r"<[^>]+>", "", text or "")
	if not visible.startswith("C"):
		return None
	text_width = len(visible) * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	c_center = font_size * LEADING_C_X_CENTER_FACTOR
	if anchor == "start":
		return -c_center
	if anchor == "middle":
		return (text_width / 2.0) - c_center
	if anchor == "end":
		return text_width - c_center
	return None


#============================================
def trailing_carbon_anchor_offset(text: str, anchor: str, font_size: float) -> float | None:
	"""Return text-x offset for labels that connect at trailing-carbon center."""
	visible = re.sub(r"<[^>]+>", "", text or "")
	if not visible.endswith("C"):
		return None
	text_width = len(visible) * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	c_center = font_size * LEADING_C_X_CENTER_FACTOR
	if anchor == "start":
		return -(text_width - c_center)
	if anchor == "middle":
		return -((text_width / 2.0) - c_center)
	if anchor == "end":
		return c_center
	return None


#============================================
def hydroxyl_oxygen_radius(font_size: float) -> float:
	"""Approximate oxygen glyph radius for OH/HO overlap checks."""
	return font_size * HYDROXYL_O_RADIUS_FACTOR


#============================================
def leading_carbon_center(
		text: str,
		anchor: str,
		text_x: float,
		text_y: float,
		font_size: float) -> tuple[float, float] | None:
	"""Approximate leading-carbon glyph center for C* labels."""
	visible = re.sub(r"<[^>]+>", "", text or "")
	if not visible.startswith("C"):
		return None
	text_width = len(visible) * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	if anchor == "start":
		start_x = text_x
	elif anchor == "end":
		start_x = text_x - text_width
	elif anchor == "middle":
		start_x = text_x - (text_width / 2.0)
	else:
		start_x = text_x
	c_center_x = start_x + (font_size * LEADING_C_X_CENTER_FACTOR)
	c_center_y = text_y - (font_size * HYDROXYL_O_Y_CENTER_FROM_BASELINE)
	return (c_center_x, c_center_y)


#============================================
def hydroxyl_oxygen_center(
		text: str,
		anchor: str,
		text_x: float,
		text_y: float,
		font_size: float) -> tuple[float, float] | None:
	"""Approximate oxygen glyph center in OH/HO label coordinates."""
	visible_text = re.sub(r"<[^>]+>", "", text or "")
	if visible_text not in ("OH", "HO"):
		return None
	visible = visible_text_length(visible_text)
	text_width = visible * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	if anchor == "start":
		start_x = text_x
	elif anchor == "end":
		start_x = text_x - text_width
	elif anchor == "middle":
		start_x = text_x - (text_width / 2.0)
	else:
		start_x = text_x
	o_index = visible_text.find("O")
	if o_index < 0:
		return None
	o_center_x = start_x + ((o_index * HYDROXYL_GLYPH_WIDTH_FACTOR) + HYDROXYL_O_X_CENTER_FACTOR) * font_size
	o_center_y = text_y - (font_size * HYDROXYL_O_Y_CENTER_FROM_BASELINE)
	return (o_center_x, o_center_y)


#============================================
def visible_text_length(text: str) -> int:
	"""Count visible characters, ignoring HTML-like tags."""
	return len(re.sub(r"<[^>]+>", "", text or ""))
