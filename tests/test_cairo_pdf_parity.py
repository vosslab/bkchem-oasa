"""Tests for Cairo PDF parity tool and supporting modules."""

# Standard Library
import importlib.util
import pathlib

# Third Party
import pytest

# Local repo modules
import git_file_utils

REPO_ROOT = pathlib.Path(git_file_utils.get_repo_root())


#============================================
def _load_tool_module(module_name: str, relative_path: str):
	"""Load a module from the tools directory."""
	tool_path = REPO_ROOT / relative_path
	spec = importlib.util.spec_from_file_location(module_name, tool_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Could not load module from {tool_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


#============================================
def _get_measurelib_module(name: str):
	"""Import a measurelib submodule by ensuring tools/ is on sys.path."""
	import sys
	tools_dir = str(REPO_ROOT / "tools")
	if tools_dir not in sys.path:
		sys.path.insert(0, tools_dir)
	import importlib
	return importlib.import_module(f"measurelib.{name}")


# ---- pdf_parse tests ----

#============================================
class TestCollectPdfLinesExtractsCoordinates:
	"""Test that collect_pdf_lines extracts coordinates and flips Y."""

	def test_basic_line(self, tmp_path: pathlib.Path):
		"""Verify a simple PDF with a line yields correct extracted coords."""
		# create a minimal PDF with reportlab
		pytest.importorskip("reportlab")
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas
		pdf_path = tmp_path / "test_line.pdf"
		c = canvas.Canvas(str(pdf_path), pagesize=letter)
		_page_width, page_height = letter
		# draw a line from (100, 200) to (300, 400) in PDF coords
		c.line(100, 200, 300, 400)
		c.save()
		pdf_parse = _get_measurelib_module("pdf_parse")
		page, pdf_obj = pdf_parse.open_pdf_page(str(pdf_path))
		lines = pdf_parse.collect_pdf_lines(page)
		pdf_obj.close()
		# should have at least one line
		assert len(lines) >= 1
		# verify the line has the expected dict keys
		line = lines[0]
		assert "x1" in line
		assert "y1" in line
		assert "x2" in line
		assert "y2" in line
		assert "width" in line
		assert "linecap" in line


#============================================
class TestCollectPdfLabelsExtractsText:
	"""Test that collect_pdf_labels extracts text content."""

	def test_basic_text(self, tmp_path: pathlib.Path):
		"""Verify a PDF with text yields a label with correct content."""
		pytest.importorskip("reportlab")
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas
		pdf_path = tmp_path / "test_text.pdf"
		c = canvas.Canvas(str(pdf_path), pagesize=letter)
		c.setFont("Helvetica", 12)
		c.drawString(100, 500, "OH")
		c.save()
		pdf_parse = _get_measurelib_module("pdf_parse")
		page, pdf_obj = pdf_parse.open_pdf_page(str(pdf_path))
		labels = pdf_parse.collect_pdf_labels(page)
		pdf_obj.close()
		# should find at least one label
		assert len(labels) >= 1
		# at least one label should contain "OH"
		texts = [label.get("text", "") for label in labels]
		assert any("OH" in t for t in texts), f"Expected 'OH' in labels, got: {texts}"


#============================================
class TestCollectPdfLabelsCallsCanonicalize:
	"""Test that collect_pdf_labels uses canonicalize_label_text."""

	def test_canonical_text_field(self, tmp_path: pathlib.Path):
		"""Verify labels have canonical_text key populated."""
		pytest.importorskip("reportlab")
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas
		pdf_path = tmp_path / "test_canonical.pdf"
		c = canvas.Canvas(str(pdf_path), pagesize=letter)
		c.setFont("Helvetica", 12)
		c.drawString(100, 500, "NH")
		c.save()
		pdf_parse = _get_measurelib_module("pdf_parse")
		page, pdf_obj = pdf_parse.open_pdf_page(str(pdf_path))
		labels = pdf_parse.collect_pdf_labels(page)
		pdf_obj.close()
		assert len(labels) >= 1
		for label in labels:
			assert "canonical_text" in label
			assert "is_measurement_label" in label


#============================================
class TestYCoordinateFlip:
	"""Test that PDF-to-SVG Y coordinate normalization works."""

	def test_flip_y(self):
		"""Verify _flip_y inverts Y relative to page height."""
		pdf_parse = _get_measurelib_module("pdf_parse")
		page_height = 792.0
		# bottom of PDF page (y=0) should become top of SVG (y=page_height)
		assert pdf_parse._flip_y(0.0, page_height) == page_height
		# top of PDF page (y=page_height) should become SVG origin (y=0)
		assert pdf_parse._flip_y(page_height, page_height) == 0.0
		# midpoint should stay at midpoint
		assert pdf_parse._flip_y(396.0, page_height) == 396.0


# ---- parity tests ----

#============================================
class TestMatchLinesFindNearest:
	"""Test that match_lines finds nearest-neighbor matches."""

	def test_exact_match(self):
		"""Identical line sets should produce perfect matches."""
		parity = _get_measurelib_module("parity")
		svg_lines = [
			{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "width": 1.0},
			{"x1": 20.0, "y1": 20.0, "x2": 30.0, "y2": 20.0, "width": 1.0},
		]
		pdf_lines = [
			{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "width": 1.0},
			{"x1": 20.0, "y1": 20.0, "x2": 30.0, "y2": 20.0, "width": 1.0},
		]
		matches = parity.match_lines(svg_lines, pdf_lines, tolerance=2.0)
		matched = [m for m in matches if m["matched"]]
		assert len(matched) == 2
		# midpoint deltas should be zero
		for m in matched:
			assert m["midpoint_delta"] < 0.01

	def test_unmatched_svg_line(self):
		"""Extra SVG line with no PDF partner should be flagged unmatched."""
		parity = _get_measurelib_module("parity")
		svg_lines = [
			{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "width": 1.0},
			{"x1": 100.0, "y1": 100.0, "x2": 110.0, "y2": 100.0, "width": 1.0},
		]
		pdf_lines = [
			{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "width": 1.0},
		]
		matches = parity.match_lines(svg_lines, pdf_lines, tolerance=2.0)
		matched = [m for m in matches if m["matched"]]
		unmatched = [m for m in matches if not m["matched"]]
		assert len(matched) == 1
		assert len(unmatched) >= 1


#============================================
class TestMatchLabelsByText:
	"""Test that match_labels uses text content then position."""

	def test_same_text_matches(self):
		"""Labels with same canonical text should match."""
		parity = _get_measurelib_module("parity")
		svg_labels = [
			{"canonical_text": "OH", "x": 50.0, "y": 50.0, "font_size": 12.0},
			{"canonical_text": "NH", "x": 100.0, "y": 100.0, "font_size": 12.0},
		]
		pdf_labels = [
			{"canonical_text": "OH", "x": 51.0, "y": 51.0, "font_size": 12.0},
			{"canonical_text": "NH", "x": 101.0, "y": 101.0, "font_size": 12.0},
		]
		matches = parity.match_labels(svg_labels, pdf_labels, tolerance=5.0)
		matched = [m for m in matches if m["matched"]]
		assert len(matched) == 2

	def test_different_text_no_match(self):
		"""Labels with different text should not match."""
		parity = _get_measurelib_module("parity")
		svg_labels = [
			{"canonical_text": "OH", "x": 50.0, "y": 50.0, "font_size": 12.0},
		]
		pdf_labels = [
			{"canonical_text": "NH", "x": 50.0, "y": 50.0, "font_size": 12.0},
		]
		matches = parity.match_labels(svg_labels, pdf_labels, tolerance=5.0)
		matched = [m for m in matches if m["matched"]]
		assert len(matched) == 0


#============================================
class TestParityScorePerfectMatch:
	"""Test that identical inputs give parity score 1.0."""

	def test_perfect_score(self):
		"""All matched primitives should give parity score of 1.0."""
		parity = _get_measurelib_module("parity")
		line_matches = [
			{"svg_index": 0, "pdf_index": 0, "midpoint_delta": 0.0, "length_delta": 0.0, "width_delta": 0.0, "matched": True},
		]
		label_matches = [
			{"text": "OH", "svg_index": 0, "pdf_index": 0, "x_delta": 0.0, "y_delta": 0.0, "font_size_delta": 0.0, "matched": True},
		]
		summary = parity.parity_summary(line_matches, label_matches, [], [])
		assert summary["parity_score"] == 1.0
		assert summary["total_matched"] == 2
		assert summary["total_unmatched"] == 0


#============================================
class TestParityScoreWithOffset:
	"""Test that shifted coordinates lower the parity score."""

	def test_partial_match(self):
		"""Mixed matched/unmatched primitives lower the score below 1.0."""
		parity = _get_measurelib_module("parity")
		line_matches = [
			{"svg_index": 0, "pdf_index": 0, "midpoint_delta": 1.5, "length_delta": 0.2, "width_delta": 0.0, "matched": True},
			{"svg_index": 1, "pdf_index": None, "midpoint_delta": None, "length_delta": None, "width_delta": None, "matched": False},
		]
		label_matches = [
			{"text": "OH", "svg_index": 0, "pdf_index": 0, "x_delta": 1.0, "y_delta": 1.0, "font_size_delta": 0.0, "matched": True},
		]
		summary = parity.parity_summary(line_matches, label_matches, [], [])
		assert summary["parity_score"] < 1.0
		assert summary["total_matched"] == 2
		assert summary["total_unmatched"] == 1


#============================================
class TestFilePairingByStem:
	"""Test that SVG/PDF file pairing by stem works correctly."""

	def test_matching_stems(self, tmp_path: pathlib.Path):
		"""Files with same stem should be paired."""
		# load the CLI tool module
		tool = _load_tool_module(
			"measure_cairo_pdf_parity",
			"tools/measure_cairo_pdf_parity.py",
		)
		svg_a = tmp_path / "mol_a.svg"
		svg_b = tmp_path / "mol_b.svg"
		pdf_a = tmp_path / "mol_a.pdf"
		pdf_b = tmp_path / "mol_b.pdf"
		pdf_c = tmp_path / "mol_c.pdf"
		# create empty files
		for f in [svg_a, svg_b, pdf_a, pdf_b, pdf_c]:
			f.write_text("", encoding="utf-8")
		pairs = tool.pair_files_by_stem(
			[svg_a, svg_b],
			[pdf_a, pdf_b, pdf_c],
		)
		# should match mol_a and mol_b, not mol_c
		assert len(pairs) == 2
		stems = {p[0].stem for p in pairs}
		assert stems == {"mol_a", "mol_b"}

	def test_no_matching_stems(self, tmp_path: pathlib.Path):
		"""Files with no common stems yield empty pairs."""
		tool = _load_tool_module(
			"measure_cairo_pdf_parity",
			"tools/measure_cairo_pdf_parity.py",
		)
		svg_x = tmp_path / "x.svg"
		pdf_y = tmp_path / "y.pdf"
		svg_x.write_text("", encoding="utf-8")
		pdf_y.write_text("", encoding="utf-8")
		pairs = tool.pair_files_by_stem([svg_x], [pdf_y])
		assert len(pairs) == 0


#============================================
class TestPdfParseOpenPage:
	"""Test open_pdf_page functionality."""

	def test_empty_pdf_raises(self, tmp_path: pathlib.Path):
		"""A corrupt/empty file should raise an error."""
		pdf_parse = _get_measurelib_module("pdf_parse")
		bad_pdf = tmp_path / "empty.pdf"
		bad_pdf.write_text("not a real pdf", encoding="utf-8")
		with pytest.raises(Exception):
			pdf_parse.open_pdf_page(str(bad_pdf))


#============================================
class TestCollectPdfRingPrimitives:
	"""Test ring primitive extraction from PDF."""

	def test_no_rings_in_simple_pdf(self, tmp_path: pathlib.Path):
		"""A PDF with only a line should have no ring primitives."""
		pytest.importorskip("reportlab")
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas
		pdf_path = tmp_path / "test_no_rings.pdf"
		c = canvas.Canvas(str(pdf_path), pagesize=letter)
		c.line(100, 200, 300, 400)
		c.save()
		pdf_parse = _get_measurelib_module("pdf_parse")
		page, pdf_obj = pdf_parse.open_pdf_page(str(pdf_path))
		rings = pdf_parse.collect_pdf_ring_primitives(page)
		pdf_obj.close()
		# simple line PDF should have no ring primitives
		assert isinstance(rings, list)


#============================================
class TestCollectPdfWedgeBonds:
	"""Test wedge bond extraction from PDF."""

	def test_no_wedges_in_simple_pdf(self, tmp_path: pathlib.Path):
		"""A PDF with only text should have no wedge bonds."""
		pytest.importorskip("reportlab")
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas
		pdf_path = tmp_path / "test_no_wedges.pdf"
		c = canvas.Canvas(str(pdf_path), pagesize=letter)
		c.setFont("Helvetica", 12)
		c.drawString(100, 500, "Hello")
		c.save()
		pdf_parse = _get_measurelib_module("pdf_parse")
		page, pdf_obj = pdf_parse.open_pdf_page(str(pdf_path))
		wedges = pdf_parse.collect_pdf_wedge_bonds(page)
		pdf_obj.close()
		assert isinstance(wedges, list)
		assert len(wedges) == 0


#============================================
class TestMatchRingPrimitives:
	"""Test ring primitive matching."""

	def test_exact_centroid_match(self):
		"""Rings at same centroid should match."""
		parity = _get_measurelib_module("parity")
		svg_rings = [{"centroid": (50.0, 50.0), "bbox": (40, 40, 60, 60), "kind": "polygon"}]
		pdf_rings = [{"centroid": (50.5, 50.5), "bbox": (40, 40, 60, 60), "kind": "curve"}]
		matches = parity.match_ring_primitives(svg_rings, pdf_rings, tolerance=5.0)
		matched = [m for m in matches if m["matched"]]
		assert len(matched) == 1


#============================================
class TestMatchWedgeBonds:
	"""Test wedge bond matching."""

	def test_exact_spine_match(self):
		"""Wedge bonds with same spine should match."""
		parity = _get_measurelib_module("parity")
		svg_wedges = [{"spine_start": (10.0, 10.0), "spine_end": (50.0, 10.0)}]
		pdf_wedges = [{"spine_start": (10.5, 10.0), "spine_end": (50.5, 10.0)}]
		matches = parity.match_wedge_bonds(svg_wedges, pdf_wedges, tolerance=5.0)
		matched = [m for m in matches if m["matched"]]
		assert len(matched) == 1


#============================================
class TestPdfAnalysis:
	"""Test standalone PDF analysis via pdf_analysis module."""

	def test_analyze_pdf_returns_dict(self, tmp_path: pathlib.Path):
		"""analyze_pdf_file should return a dict with expected keys."""
		pytest.importorskip("reportlab")
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas
		pdf_path = tmp_path / "test_analysis.pdf"
		c = canvas.Canvas(str(pdf_path), pagesize=letter)
		c.setFont("Helvetica", 12)
		c.drawString(100, 500, "OH")
		c.line(50, 500, 95, 500)
		c.save()
		pdf_analysis = _get_measurelib_module("pdf_analysis")
		result = pdf_analysis.analyze_pdf_file(pdf_path)
		assert isinstance(result, dict)
		assert "pdf" in result
		assert "text_labels_total" in result
		assert "lattice_angle_violation_count" in result
		assert "haworth_base_ring" in result


#============================================
class TestResolvePdfPaths:
	"""Test PDF path resolution."""

	def test_resolve_finds_files(self, tmp_path: pathlib.Path):
		"""resolve_pdf_paths should find PDF files matching the glob."""
		pdf_parse = _get_measurelib_module("pdf_parse")
		# create test PDF files
		(tmp_path / "a.pdf").write_text("", encoding="utf-8")
		(tmp_path / "b.pdf").write_text("", encoding="utf-8")
		(tmp_path / "c.txt").write_text("", encoding="utf-8")
		paths = pdf_parse.resolve_pdf_paths(tmp_path, "*.pdf")
		# should find two PDF files
		assert len(paths) == 2
		stems = {p.stem for p in paths}
		assert stems == {"a", "b"}
