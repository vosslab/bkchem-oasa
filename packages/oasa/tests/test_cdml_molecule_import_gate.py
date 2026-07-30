"""Behavioral coverage for the CDML chemistry-import security boundary."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml
import oasa.cdml_document
import oasa.cdml_xml
import oasa.codecs.cdsvg


_COMPATIBLE_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">'
	'<molecule id="m1"><atom id="a1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule></cdml>'
)
_COMPATIBLE_CDSVG = (
	'<svg xmlns="http://www.w3.org/2000/svg"><metadata>'
	+ _COMPATIBLE_CDML
	+ '</metadata></svg>'
)


#============================================
@pytest.mark.parametrize(
	"source",
	(
		'<!DOCTYPE cdml [<!ENTITY unsafe "value">]><cdml>&unsafe;</cdml>',
		'<!DOCTYPE cdml SYSTEM "https://example.invalid/cdml.dtd"><cdml/>',
		'<!DOCTYPE cdml PUBLIC "id" "https://example.invalid/cdml.dtd"><cdml/>',
	),
)
def test_molecule_import_rejects_every_doctype_form(source: str) -> None:
	"""Chemistry import and native CDML reject each prohibited DOCTYPE form."""
	with pytest.raises(oasa.cdml_xml.CDMLXMLParseError):
		oasa.cdml.text_to_mol(source)
	with pytest.raises(oasa.cdml_document.CDMLParseError):
		oasa.cdml_document.CDMLDocument.parse(source)


#============================================
def test_molecule_import_extracts_compatible_complete_cdml() -> None:
	"""A compatible complete document remains available as chemistry import."""
	molecule = oasa.cdml.text_to_mol(_COMPATIBLE_CDML)
	assert molecule is not None


#============================================
def test_cdsvg_import_extracts_embedded_compatible_cdml() -> None:
	"""CD-SVG uses the same chemistry-only embedded-CDML extraction path."""
	molecule = oasa.codecs.cdsvg.text_to_mol(_COMPATIBLE_CDSVG)
	assert molecule is not None
