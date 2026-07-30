"""Focused backend tests for revision-bound CDML paper-properties patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns:v="urn:vendor" version="26.07">
 <standard paper_type="Letter" paper_orientation="landscape" />
 <paper type="legacy-preserve" orientation="portrait" size_x="123" size_y="456" v:raw="keep"><v:extension key="x">payload</v:extension></paper>
 <v:note id="before">keep</v:note>
 <paper type="A4" orientation="portrait" v:second="untouched"><v:later /></paper>
 <viewport viewport="0 0 10 10" />
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm" /></atom></molecule>
</cdml>
"""


#============================================
def _request(revision: object, changes: object) -> object:
	"""Build one patch request, including deliberately malformed shapes."""
	return cdml_document.CDMLPaperPropertiesPatch(revision, changes)


#============================================
def _dom(cdml_text: str) -> object:
	"""Read accepted complete CDML through the repository hardened parser."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	return oasa.safe_xml.parse_dom_from_string(accepted.serialize())


#============================================
def _direct_papers(cdml_text: str) -> tuple[object, ...]:
	"""Return direct paper records without treating nested or opaque nodes as paper."""
	return tuple(
		child for child in _dom(cdml_text).documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
		and (child.localName or child.tagName) == "paper"
		and child.namespaceURI in (None, "", cdml_document.CDML_NAMESPACE_URI)
	)


#============================================
def _root_order(cdml_text: str) -> tuple[str, ...]:
	"""Capture direct element order as the persistent document-order contract."""
	return tuple(
		child.tagName for child in _dom(cdml_text).documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)


#============================================
def test_patch_changes_only_explicit_fields_and_preserves_other_paper_records() -> None:
	"""A first-paper patch keeps legacy fields, extensions, later paper, and order."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before_papers = _direct_papers(session.snapshot().cdml)
	before_second = before_papers[1].toxml()
	before_order = _root_order(session.snapshot().cdml)
	commit = session.patch_paper_properties(_request(session.revision, (
		("orientation", "landscape"), ("crop_svg", True), ("crop_margin", 0),
	)))
	first, second = _direct_papers(commit.cdml)

	assert first.getAttribute("type") == "legacy-preserve"
	assert first.getAttribute("orientation") == "landscape"
	assert first.getAttribute("crop_svg") == "1"
	assert first.getAttribute("crop_margin") == "0"
	assert first.getAttribute("size_x") == "123"
	assert first.getAttribute("size_y") == "456"
	assert first.getAttribute("v:raw") == "keep"
	assert tuple(child.toxml() for child in first.childNodes if child.nodeType == child.ELEMENT_NODE) == (
		'<v:extension key="x">payload</v:extension>',
	)
	assert second.toxml() == before_second
	assert _root_order(commit.cdml) == before_order


#============================================
def test_empty_patch_is_a_stale_checked_noop_and_keeps_absent_paper_absent() -> None:
	"""Empty intent neither creates paper nor bypasses optimistic concurrency."""
	session = cdml_document.CDMLDocumentSession.load('<cdml version="26.07" />')
	before = session.snapshot()
	no_op = session.patch_paper_properties(_request(session.revision, ()))

	assert no_op.snapshot == before
	assert _direct_papers(no_op.cdml) == ()
	session.edit_structure(cdml_document.CDMLStructuralEditRequest(
		expected_revision=session.revision,
		kind="create-bonded-pair",
		source_position=(0.0, 0.0),
		target_position=(40.0, 0.0),
		element="C",
		bond_type="n",
		bond_order=1,
		simple_double=False,
	))
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.patch_paper_properties(_request(0, ()))


#============================================
def test_new_paper_uses_valid_direct_standard_defaults_and_viewport_insertion() -> None:
	"""A first explicit field creates paper before the first direct core viewport."""
	session = cdml_document.CDMLDocumentSession.load("""\
<cdml xmlns:v="urn:vendor">
 <standard paper_type="Letter" paper_orientation="landscape" />
 <v:note>opaque</v:note><viewport viewport="0 0 1 1" />
</cdml>""")
	commit = session.patch_paper_properties(_request(session.revision, (("crop_margin", 12),)))
	paper, = _direct_papers(commit.cdml)

	assert paper.getAttribute("type") == "Letter"
	assert paper.getAttribute("orientation") == "landscape"
	assert paper.getAttribute("crop_margin") == "12"
	assert _root_order(commit.cdml) == ("standard", "v:note", "paper", "viewport")
	fallback = cdml_document.CDMLDocumentSession.load(
		'<cdml><standard paper_type="obsolete" paper_orientation="sideways" /><viewport /></cdml>',
	)
	fallback_commit = fallback.patch_paper_properties(_request(
		fallback.revision, (("crop_svg", False),),
	))
	fallback_paper, = _direct_papers(fallback_commit.cdml)
	assert (fallback_paper.getAttribute("type"), fallback_paper.getAttribute("orientation")) == (
		"A4", "portrait",
	)


#============================================
def test_paper_properties_context_uses_the_same_direct_core_boundary_as_patch() -> None:
	"""The client observation ignores foreign paper-like XML and exposes backend defaults."""
	session = cdml_document.CDMLDocumentSession.load("""\
<cdml xmlns:v="urn:vendor">
 <v:paper type="vendor" /><standard paper_type="Letter" paper_orientation="landscape" />
</cdml>""")

	assert session.paper_properties_context() == {
		"paper_present": False,
		"attributes": {},
		"default_type": "Letter",
		"default_orientation": "landscape",
	}
	created = session.patch_paper_properties(_request(session.revision, (("crop_svg", True),)))
	paper, = _direct_papers(created.cdml)
	assert (paper.getAttribute("type"), paper.getAttribute("orientation")) == (
		"Letter", "landscape",
	)


#============================================
def test_catalog_and_custom_transition_cover_broad_authoring_types() -> None:
	"""OASA publishes all authored names and enforces the custom-pair transition."""
	catalog = cdml_document.paper_catalog()
	assert catalog["A0"] == [841.0, 1189.0]
	assert catalog["C10"] == [28.0, 40.0]
	assert catalog["Tabloid"] == [279.4, 431.8]
	assert catalog["custom"] is None
	session = cdml_document.CDMLDocumentSession.load('<cdml><paper type="A4" orientation="portrait" /></cdml>')
	custom = session.patch_paper_properties(_request(session.revision, (
		("type", "custom"), ("dimensions", (200.5, 300.25)),
	)))
	paper, = _direct_papers(custom.cdml)
	assert (paper.getAttribute("type"), paper.getAttribute("size_x"), paper.getAttribute("size_y")) == (
		"custom", "200.5", "300.25",
	)
	named = session.patch_paper_properties(_request(session.revision, (("type", "C10"),)))
	paper, = _direct_papers(named.cdml)
	assert paper.getAttribute("type") == "C10"
	assert not paper.hasAttribute("size_x")
	assert not paper.hasAttribute("size_y")


#============================================
@pytest.mark.parametrize("changes", (
	[],
	(("type", "A4", "extra"),),
	(("type", "custom"),),
	(("type", "A4"), ("dimensions", (210, 297))),
	(("dimensions", (210, 297, 1)),),
	(("dimensions", (210, float("nan"))),),
	(("crop_margin", True),),
	(("orientation", "sideways"),),
	(("type", "A4"), ("type", "Letter")),
	(("unknown", 1),),
))
def test_invalid_patch_shapes_and_values_are_atomic(changes: object) -> None:
	"""Invalid field grammar is rejected before any detached candidate becomes live."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLPaperPropertiesError):
		session.patch_paper_properties(_request(session.revision, changes))

	assert session.snapshot() == before


#============================================
def test_patch_restore_returns_the_exact_prior_authoritative_paper_state() -> None:
	"""Paper patches use ordinary backend history and restore semantics."""
	session = cdml_document.CDMLDocumentSession.load('<cdml><paper type="A4" orientation="portrait" /></cdml>')
	before = session.snapshot()
	changed = session.patch_paper_properties(_request(session.revision, (("type", "B10"),)))
	restored = session.restore(target_revision=before.revision, expected_revision=changed.revision)

	assert restored.revision == 2
	assert restored.cdml == before.cdml
