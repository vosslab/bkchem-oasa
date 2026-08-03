"""Semantic coverage for backend-owned CDML linear-form conversion."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """<cdml xmlns:v="urn:vendor"><molecule id="m1"><atom id="a3" name="O"><point x="20" y="4"/><mark type="plus" x="21" y="5"/></atom><atom id="a1" name="C"><point x="0" y="0"/></atom><atom id="a2" name="C"><point x="7" y="9"/></atom><atom id="branch" name="Cl"><point x="9" y="12"/></atom><bond id="b2" start="a2" end="a3" type="n1"/><bond id="b1" start="a1" end="a2" type="n1"/><bond id="b3" start="a2" end="branch" type="n1"/><fragment id="legacy" type="linear_form"><name>imported</name><vertex id="a1"/></fragment><v:opaque id="f1">keep</v:opaque></molecule></cdml>"""


#============================================
def _linear_form_facts(cdml_text: str) -> tuple[dict[str, object], str]:
	"""Read accepted geometry and generated property through hardened CDML input."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	document = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	molecule = next(
		child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE and (child.localName or child.tagName) == "molecule"
	)
	positions = {}
	hydrogen_ids = []
	mark_position = None
	property_facts = None
	member_facts = None
	opaque_text = None
	for child in molecule.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		name = child.localName or child.tagName
		if name == "atom":
			point = next(grandchild for grandchild in child.childNodes if grandchild.nodeType == grandchild.ELEMENT_NODE and (grandchild.localName or grandchild.tagName) == "point")
			positions[child.getAttribute("id")] = (float(point.getAttribute("x")), float(point.getAttribute("y")))
			if child.getAttribute("hydrogens") == "on":
				hydrogen_ids.append(child.getAttribute("id"))
			if child.getAttribute("id") == "a3":
				mark = next(grandchild for grandchild in child.childNodes if grandchild.nodeType == grandchild.ELEMENT_NODE and (grandchild.localName or grandchild.tagName) == "mark")
				mark_position = (float(mark.getAttribute("x")), float(mark.getAttribute("y")))
		elif name == "fragment":
			fragment_name = next(grandchild for grandchild in child.childNodes if grandchild.nodeType == grandchild.ELEMENT_NODE and (grandchild.localName or grandchild.tagName) == "name")
			if "".join(node.data for node in fragment_name.childNodes if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE)) == "linear_form":
				member_facts = tuple(
					(grandchild.localName or grandchild.tagName, grandchild.getAttribute("id"))
					for grandchild in child.childNodes
					if grandchild.nodeType == grandchild.ELEMENT_NODE
					and (grandchild.localName or grandchild.tagName) in ("bond", "vertex")
				)
				property_element = next(grandchild for grandchild in child.childNodes if grandchild.nodeType == grandchild.ELEMENT_NODE and (grandchild.localName or grandchild.tagName) == "property")
				property_facts = (property_element.getAttribute("name"), property_element.getAttribute("value"), property_element.getAttribute("type"))
		elif child.namespaceURI == "urn:vendor" and name == "opaque":
			opaque_text = "".join(
				node.data for node in child.childNodes
				if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE)
			)
	if mark_position is None or member_facts is None or property_facts is None or opaque_text is None:
		raise AssertionError("Accepted CDML omitted generated linear-form facts")
	facts = {
		"positions": positions, "mark_position": mark_position,
		"members": member_facts, "property": property_facts,
		"hydrogen_ids": tuple(hydrogen_ids),
	}
	return facts, opaque_text


#============================================
def _has_fragment_name(cdml_text: str, expected: str) -> bool:
	"""Find one semantic fragment name after hardened complete-CDML acceptance."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	document = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for fragment in document.getElementsByTagName("fragment"):
		for child in fragment.childNodes:
			if child.nodeType != child.ELEMENT_NODE:
				continue
			if (child.localName or child.tagName) != "name":
				continue
			value = "".join(
				node.data for node in child.childNodes
				if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE)
			)
			if value == expected:
				return True
	return False


#============================================
def test_linear_form_owns_deterministic_geometry_metadata_and_attached_marks() -> None:
	"""A path is ordered by durable geometry, with its branch moved rigidly."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(
		0, "m1", ("a3", "a1", "a2"),
	))
	facts, opaque_text = _linear_form_facts(result.snapshot.cdml)
	expected = {
		"positions": {
			"a1": (0.0, 0.0), "a2": (10.0, 0.0),
			"a3": (20.0, 0.0), "branch": (12.0, 3.0),
		},
		"mark_position": (21.0, 1.0),
		"members": (
			("bond", "b1"), ("bond", "b2"),
			("vertex", "a1"), ("vertex", "a2"), ("vertex", "a3"),
		),
		"property": ("bond_length", "10", "IntType"),
		"hydrogen_ids": ("a3", "a1", "a2"),
	}
	accepted = (result.atom_ids, result.bond_ids, facts)
	wanted = (("a1", "a2", "a3"), ("b1", "b2"), expected)
	assert accepted == wanted
	preserved = (opaque_text, _has_fragment_name(result.snapshot.cdml, "imported"))
	assert result.fragment_id != "f1" and preserved == ("keep", True)


#============================================
def test_linear_form_repeat_is_semantic_noop_and_restore_recovers_predecessor() -> None:
	"""Canonical repeats do not create history, while restore remains exact."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	baseline = session.snapshot().cdml
	first = session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2", "a3")))
	repeat = session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(1, "m1", ("a2", "a3", "a1")))
	restored = session.restore(target_revision=0, expected_revision=1)
	assert (first.changed, repeat.changed, restored.cdml) == (True, False, baseline)


#============================================
def test_noncanonical_narrow_form_is_reused_without_duplicate_metadata() -> None:
	"""An existing exact narrow form is repaired in place under its durable ID."""
	cdml = """<cdml><molecule id="m1"><atom id="a1" name="C"><point x="0" y="0"/></atom><atom id="a2" name="O"><point x="4" y="8"/></atom><bond id="b1" start="a1" end="a2" type="n1"/><fragment id="owned" type="linear_form"><name>linear_form</name><bond id="b1"/><vertex id="a2"/><vertex id="a1"/><property name="bond_length" value="10" type="IntType"/></fragment></molecule></cdml>"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	converted = session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a2", "a1")))
	repeat = session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(1, "m1", ("a1", "a2")))
	assert (converted.fragment_id, repeat.changed) == ("owned", False)


#============================================
def test_multiple_matching_narrow_forms_are_ambiguous() -> None:
	"""Two exact narrow records for one path reject without choosing an owner."""
	cdml = """<cdml><molecule id="m1"><atom id="a1"><point x="0" y="0"/></atom><atom id="a2"><point x="4" y="8"/></atom><bond id="b1" start="a1" end="a2" type="n1"/>"""
	cdml += """<fragment id="first" type="linear_form"><name>linear_form</name><bond id="b1"/><vertex id="a1"/><vertex id="a2"/><property name="bond_length" value="10" type="IntType"/></fragment>"""
	cdml += """<fragment id="second" type="linear_form"><name>linear_form</name><bond id="b1"/><vertex id="a2"/><vertex id="a1"/><property name="bond_length" value="10" type="IntType"/></fragment></molecule></cdml>"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	baseline = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLLinearFormError):
		session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2")))
	assert session.snapshot() == baseline


#============================================
def test_linear_form_rejects_stale_request_without_mutation() -> None:
	"""An obsolete request leaves the accepted authoritative snapshot intact."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	baseline = session.snapshot().cdml
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(1, "m1", ("a1",)))
	assert session.snapshot().cdml == baseline


#============================================
def test_linear_form_rejects_multianchor_external_component_atomically() -> None:
	"""An external bridge cannot follow two reflow offsets in one conversion."""
	cdml = """<cdml><molecule id="m1"><atom id="a1" name="C"><point x="0" y="0"/></atom><atom id="a2" name="C"><point x="7" y="9"/></atom><atom id="a3" name="O"><point x="20" y="4"/></atom><atom id="bridge" name="Cl"><point x="9" y="12"/></atom><bond id="b1" start="a1" end="a2" type="n1"/><bond id="b2" start="a2" end="a3" type="n1"/><bond id="left" start="a1" end="bridge" type="n1"/><bond id="right" start="a2" end="bridge" type="n1"/></molecule></cdml>"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	baseline = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLLinearFormError):
		session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2", "a3")))
	assert session.snapshot() == baseline


#============================================
def test_partial_later_atom_motion_retires_only_narrow_generated_metadata() -> None:
	"""A later bend invalidates generated metadata but preserves imported form."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2", "a3")))
	result = session.translate_atoms(oasa.cdml_document.CDMLAtomTranslateRequest(
		1, (("m1", "a2"),), (0.0, 1.0),
	))
	assert result.changed and not _has_fragment_name(result.snapshot.cdml, "linear_form")
	assert _has_fragment_name(result.snapshot.cdml, "imported")


#============================================
def test_atom_alignment_retires_generated_linear_metadata() -> None:
	"""A non-translation coordinate operation uses the shared validity invariant."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2", "a3")))
	result = session.align_atoms(oasa.cdml_document.CDMLAtomAlignRequest(
		1, "vertical", (("m1", "a1"), ("m1", "a2"), ("m1", "a3")),
	))
	assert result.changed and not _has_fragment_name(result.snapshot.cdml, "linear_form")
	assert _has_fragment_name(result.snapshot.cdml, "imported")


#============================================
def test_topology_edit_retires_generated_linear_metadata() -> None:
	"""A later path-closing bond invalidates only narrow generated metadata."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	session.convert_linear_form(oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2", "a3")))
	result = session.edit_structure(oasa.cdml_document.CDMLStructuralEditRequest(
		1, "join-atoms", molecule_id="m1", source_atom_id="a1", target_atom_id="a3",
		bond_type="n", bond_order=1, simple_double=False,
	))
	assert not _has_fragment_name(result.snapshot.cdml, "linear_form")
	assert _has_fragment_name(result.snapshot.cdml, "imported")


#============================================
def test_structure_delete_accepts_and_retires_invalid_generated_metadata() -> None:
	"""Deleting a generated path edge remains one accepted structural commit."""
	cdml = """<cdml><molecule id="m1"><atom id="a1"><point x="0" y="0"/></atom><atom id="a2"><point x="4" y="8"/></atom><bond id="b1" start="a1" end="a2" type="n1"/></molecule></cdml>"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	session.convert_linear_form(
		oasa.cdml_document.CDMLLinearFormConvertRequest(0, "m1", ("a1", "a2")),
	)
	result = session.delete_structure(
		oasa.cdml_document.CDMLStructureDeleteRequest(1, "m1", (), ("b1",)),
	)
	assert result.commit.snapshot.revision == 2
	assert not _has_fragment_name(result.commit.snapshot.cdml, "linear_form")
