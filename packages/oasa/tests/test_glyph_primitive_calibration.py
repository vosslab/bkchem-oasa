"""Tests for glyph primitive calibration harness and threshold gates."""

# Standard Library
import math

# Third Party
import pytest

# local repo modules
from oasa import render_geometry
import glyph_primitive_calibration as glyph_calibration


#============================================
def test_attach_site_contract_includes_closed_center():
	assert "core_center" in render_geometry.VALID_ATTACH_SITES
	assert "stem_centerline" in render_geometry.VALID_ATTACH_SITES
	assert "closed_center" in render_geometry.VALID_ATTACH_SITES


#============================================
def test_glyph_primitive_p_uses_explicit_special_contract():
	primitive = render_geometry.glyph_attach_primitive(
		symbol="P",
		span_x1=0.0,
		span_x2=1.0,
		y1=0.0,
		y2=1.0,
		font_size=16.0,
		font_name="sans-serif",
	)
	assert primitive.glyph_class == "special_p"


#============================================
def test_glyph_calibration_table_has_required_fonts_and_glyphs():
	if glyph_calibration.cairo is None:
		pytest.skip("cairo not available for glyph calibration tests")
	report = glyph_calibration.build_calibration_report()
	fonts = set(report["font_names"])
	glyphs = set(report["glyphs"])
	assert set(glyph_calibration.CALIBRATION_FONTS).issubset(fonts)
	assert set(glyph_calibration.CALIBRATION_GLYPHS).issubset(glyphs)
	for font_name in glyph_calibration.CALIBRATION_FONTS:
		assert font_name in report["calibration_table"]
		for symbol in glyph_calibration.CALIBRATION_GLYPHS:
			assert symbol in report["calibration_table"][font_name]


#============================================
def test_glyph_calibration_errors_within_thresholds():
	if glyph_calibration.cairo is None:
		pytest.skip("cairo not available for glyph calibration tests")
	report = glyph_calibration.build_calibration_report()
	for row in report["rows"]:
		assert "max_centerline_error" in row
		assert "max_boundary_hit_error" in row
		assert isinstance(row["max_centerline_error"], (int, float))
		assert isinstance(row["max_boundary_hit_error"], (int, float))
		assert math.isfinite(row["max_centerline_error"])
		assert math.isfinite(row["max_boundary_hit_error"])
		assert row["max_centerline_error"] >= 0.0
		assert row["max_boundary_hit_error"] >= 0.0
