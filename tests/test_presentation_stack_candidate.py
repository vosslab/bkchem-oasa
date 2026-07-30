"""Behavior checks for backend-authoritative presentation-stack candidates."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.io.cdml_candidate
import oasa.cdml_document
import oasa.safe_xml


_MIXED_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'xmlns:x="urn:opaque" version="0.15">'
	'<info/><paper type="A4"/><viewport><transform/></viewport>'
	'<molecule id="mol-1"><atom id="atom-1" name="C"><point x="1cm" y="1cm"/>'
	'</atom></molecule><arrow id="arrow-1"><point x="1cm" y="1cm"/>'
	'<point x="2cm" y="1cm"/></arrow><!--preserve--><?keep value?><plus id="plus-1"><point x="3cm" y="1cm"/>'
	'</plus><plus><point x="3.5cm" y="1cm"/></plus><x:external keep="yes"/>'
	'<text id="text-1"><point x="4cm" y="1cm"/><font/><ftext>note</ftext></text></cdml>'
)


#============================================
def _complete_cdml(text: str) -> str:
	"""Cross the CDML boundary before any compatibility-DOM assertion."""
	return oasa.cdml_document.CDMLDocument.parse(text).serialize()


#============================================
def _root_node_slots(text: str) -> tuple[str, ...]:
	"""Return compact DOM slots after the CDML input was accepted."""
	document = oasa.safe_xml.parse_dom_from_string(text)
	return tuple(
		"comment" if child.nodeType == child.COMMENT_NODE else
		"pi" if child.nodeType == child.PROCESSING_INSTRUCTION_NODE else
		(child.localName or child.tagName)
		for child in document.documentElement.childNodes
	)


#============================================
def test_bring_to_front_preserves_root_records_and_non_element_slots() -> None:
	"""A source-order reorder retains opaque roots and comment/PI node slots."""
	source = _complete_cdml(_MIXED_CDML)
	candidate = bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(
		source, ("text-1", "arrow-1"), "bring-to-front",
	)
	accepted = oasa.cdml_document.CDMLDocumentSession.load(source).commit(
		expected_revision=0, complete_cdml=candidate,
	)
	before_slots = _root_node_slots(source)
	after_slots = _root_node_slots(candidate)

	assert candidate.index('id="arrow-1"') < candidate.index('id="text-1"')
	assert candidate.index('id="mol-1"') < candidate.index("x:external") < candidate.index('id="arrow-1"')
	assert (after_slots.index("comment"), after_slots.index("pi")) == (before_slots.index("comment"), before_slots.index("pi"))
	assert after_slots[after_slots.index("comment") - 1:after_slots.index("pi") + 2] == ("plus", "comment", "pi", "plus")
	assert accepted.snapshot.cdml.index('id="plus-1"') < accepted.snapshot.cdml.index('id="text-1"')


#============================================
def test_stack_candidate_rejects_non_direct_idless_and_foreign_roots() -> None:
	"""Only one direct core durable presentation record is targetable."""
	source = _complete_cdml(_MIXED_CDML)
	foreign_source = _complete_cdml(
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:x="urn:x" version="0.15">'
		'<x:arrow id="foreign-arrow"/></cdml>',
	)
	with pytest.raises(ValueError, match="presentation root"):
		bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(source, ("atom-1",), "send-back")
	with pytest.raises(ValueError, match="root IDs"):
		bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(source, ("",), "send-back")
	with pytest.raises(ValueError, match="presentation root"):
		bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(foreign_source, ("foreign-arrow",), "send-back")


#============================================
def test_stack_candidate_returns_exact_source_for_noop() -> None:
	"""An already-front request is a byte-preserving semantic no-op."""
	source = _complete_cdml(_MIXED_CDML)
	candidate = bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(
		source, ("arrow-1", "text-1"), "bring-to-front",
	)
	no_op = bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(
		candidate, ("text-1", "arrow-1"), "bring-to-front",
	)
	assert candidate != source and no_op == candidate
