"""Focused tests for hardened lxml CDXML input parsing."""

# PIP3 modules
import pytest

# local repo modules
import oasa.codecs.cdxml


_SUPPORTED_CDXML = (
	"<?probe before?><CDXML xmlns='urn:cdxml'><!-- root -->"
	"<page><fragment><n id='a1' p='1 2'><t><s>O</s></t></n>"
	"<n id='a2' p='bad'/><b B='a1' E='a2' Order='2' "
	"Display='WedgeBegin'/></fragment></page></CDXML>"
)


#============================================
def test_cdxml_lxml_input_preserves_supported_label_coordinates_and_wedge() -> None:
	"""A default-namespace CDXML page imports through the private lxml boundary."""
	molecule = oasa.codecs.cdxml.text_to_mol(_SUPPORTED_CDXML.encode("utf-8"))
	signature = (
		[(vertex.symbol, vertex.x, vertex.y) for vertex in molecule.vertices],
		[(edge.order, edge.type) for edge in molecule.edges],
	)
	assert signature == ([("O", 1.0, 2.0), ("C", 0.0, 0.0)], [(2, "w")])


#============================================
def test_cdxml_lxml_input_ignores_prefixed_and_nested_fragments() -> None:
	"""Legacy direct unprefixed page-fragment selection remains intentionally narrow."""
	text = (
		"<CDXML xmlns:c='urn:cdxml'><c:page><c:fragment><c:n id='skip'/>"
		"</c:fragment></c:page><page><fragment><n id='outer'><fragment>"
		"<n id='nested'/></fragment></n></fragment></page></CDXML>"
	)
	molecule = oasa.codecs.cdxml.text_to_mol(text)
	assert len(molecule.vertices) == 1


#============================================
def test_cdxml_lxml_input_keeps_malformed_value_and_page_order_behavior() -> None:
	"""Malformed fields retain legacy defaults while direct pages retain their order."""
	text = (
		"<CDXML><page><fragment><n id='a1' p='bad'/><n id='a2'/>"
		"<b B='a1' E='missing' Order='bad'/><b B='a1' E='a2' Order='bad' "
		"Display='WedgedHashBegin'/></fragment></page><page><fragment>"
		"<n id='a3' p='3 4'/></fragment></page></CDXML>"
	)
	molecule = oasa.codecs.cdxml.text_to_mol(text)
	signature = (
		[(vertex.x, vertex.y) for vertex in molecule.vertices],
		[(edge.order, edge.type) for edge in molecule.edges],
	)
	assert signature == ([(0.0, 0.0), (0.0, 0.0), (3.0, 4.0)], [(1, "h")])


#============================================
@pytest.mark.parametrize(
	"source",
	(
		"<!DOCTYPE CDXML><CDXML><page><fragment><n id='a1'/></fragment></page></CDXML>",
		"<!DOCTYPE CDXML SYSTEM 'https://example.invalid/cdxml.dtd'><CDXML/>",
		"<!DOCTYPE CDXML [<!ENTITY label 'O'>]><CDXML/>",
	),
)
def test_cdxml_lxml_input_rejects_every_doctype(source: str) -> None:
	"""CDXML accepts no DTD or entity declarations at its external input boundary."""
	with pytest.raises(ValueError, match="CDXML DOCTYPE is not accepted"):
		oasa.codecs.cdxml.text_to_mol(source)
