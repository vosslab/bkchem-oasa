# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for the OASA codec registry."""

# Standard Library
import io
# Third Party
import pytest
# local repo modules
import oasa


#============================================
def _make_simple_mol():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="C")
	a1.x = 0.0
	a1.y = 0.0
	a2 = oasa.atom(symbol="O")
	a2.x = 1.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	bond = oasa.bond(order=1, type="n")
	bond.vertices = (a1, a2)
	mol.add_edge(a1, a2, bond)
	return mol


#============================================
def test_codec_registry_defaults():
	oasa.codec_registry.reset_registry()
	codecs = oasa.codec_registry.list_codecs()
	assert "smiles" in codecs
	assert "inchi" in codecs
	assert "molfile" in codecs
	assert "cdml" in codecs
	assert "cdsvg" in codecs
	assert "cml" in codecs
	assert "cml2" in codecs
	assert "cdxml" in codecs
	assert "svg" in codecs
	assert "pdf" in codecs
	assert "png" in codecs
	assert "ps" in codecs
	smiles_codec = oasa.codec_registry.get_codec("s")
	assert smiles_codec.name == "smiles"
	by_ext = oasa.codec_registry.get_codec_by_extension(".smi")
	assert by_ext.name == "smiles"
	by_ext = oasa.codec_registry.get_codec_by_extension(".cml")
	assert by_ext.name == "cml"
	by_ext = oasa.codec_registry.get_codec_by_extension(".cdxml")
	assert by_ext.name == "cdxml"
	by_ext = oasa.codec_registry.get_codec_by_extension(".svg")
	assert by_ext.name == "svg"
	by_ext = oasa.codec_registry.get_codec_by_extension(".cdsvg")
	assert by_ext.name == "cdsvg"


#============================================
def test_codec_registry_smiles_roundtrip():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("smiles")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert isinstance(text, str)
	assert text
	loaded = codec.read_text(text)
	assert loaded is not None


#============================================
def test_codec_registry_cdml_roundtrip():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cdml")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert "<cdml" in text
	assert "<metadata>" in text
	assert "docs/CDML_FORMAT_SPEC.md" in text
	loaded = codec.read_text(text)
	assert loaded is not None


#============================================
def test_codec_registry_cml_import_only():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cml")
	assert codec.writes_text is False
	assert codec.writes_files is False
	with pytest.raises(ValueError):
		codec.write_text(_make_simple_mol())
	text = (
		"<cml><molecule><atomArray>"
		"<atom id='a1' elementType='C' x2='0.0' y2='0.0'/>"
		"<atom id='a2' elementType='O' x2='1.0' y2='0.0'/>"
		"</atomArray><bondArray>"
		"<bond atomRefs2='a1 a2' order='1'/>"
		"</bondArray></molecule></cml>"
	)
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_cml2_import_only():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cml2")
	assert codec.writes_text is False
	assert codec.writes_files is False
	with pytest.raises(ValueError):
		codec.write_text(_make_simple_mol())
	text = (
		"<cml><molecule><atomArray>"
		"<atom id='a1' elementType='C' x2='0.0' y2='0.0'/>"
		"<atom id='a2' elementType='N' x2='1.0' y2='0.0'/>"
		"</atomArray><bondArray>"
		"<bond atomRefs2='a1 a2' order='1'/>"
		"</bondArray></molecule></cml>"
	)
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_cdxml_roundtrip():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cdxml")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert "<CDXML" in text
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_file_fallback():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("smiles")
	stream = io.StringIO("C")
	mol = codec.read_file(stream)
	assert mol is not None


#============================================
def test_codec_registry_pdf_write_file_non_empty():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("pdf")
	out = io.BytesIO()
	codec.write_file(_make_simple_mol(), out)
	assert len(out.getvalue()) > 0


#============================================
def test_codec_registry_render_write_file_non_empty_for_png_and_ps():
	oasa.codec_registry.reset_registry()
	for codec_name in ("png", "ps"):
		codec = oasa.codec_registry.get_codec(codec_name)
		out = io.BytesIO()
		codec.write_file(_make_simple_mol(), out)
		assert len(out.getvalue()) > 0


#============================================
def test_codec_registry_svg_write_file_non_empty():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("svg")
	out = io.BytesIO()
	codec.write_file(_make_simple_mol(), out)
	text = out.getvalue().decode("utf-8")
	assert "<svg" in text


#============================================
def test_codec_registry_cdsvg_roundtrip_and_safe_export():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cdsvg")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert "<svg" in text
	assert "<cdml" in text
	lower_text = text.lower()
	assert "<script" not in lower_text
	assert " onload=" not in lower_text
	assert "<foreignobject" not in lower_text
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_cdsvg_forwards_cdml_writer_kwargs():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cdsvg")
	mol = _make_simple_mol()
	text = codec.write_text(
		mol,
		version="77.01",
		namespace="http://example.org/custom-cdml",
	)
	assert 'version="77.01"' in text
	assert 'xmlns="http://example.org/custom-cdml"' in text


#============================================
def test_registry_snapshot_contains_capabilities():
	oasa.codec_registry.reset_registry()
	snapshot = oasa.codec_registry.get_registry_snapshot()
	assert "smiles" in snapshot
	assert "cml" in snapshot
	assert "cml2" in snapshot
	assert "pdf" in snapshot
	assert "png" in snapshot
	assert "svg" in snapshot
	assert "ps" in snapshot
	assert "cdsvg" in snapshot
	assert snapshot["smiles"]["writes_files"] is True
	assert snapshot["cml"]["writes_files"] is False
	assert snapshot["cml"]["writes_text"] is False
	assert snapshot["cml2"]["writes_files"] is False
	assert snapshot["cml2"]["writes_text"] is False
	assert snapshot["pdf"]["reads_files"] is False
	assert snapshot["pdf"]["writes_files"] is True
	assert snapshot["cdsvg"]["reads_files"] is True
