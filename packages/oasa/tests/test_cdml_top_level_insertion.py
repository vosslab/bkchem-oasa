"""Behavioral tests for authoritative top-level CDML fragment insertion."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


#============================================
def _request(
		revision: int, fragment: str, translation: tuple[float, float] = (0.0, 0.0),
		) -> cdml_document.CDMLTopLevelInsertionRequest:
	"""Build a plain backend request without frontend correlation tokens."""
	return cdml_document.CDMLTopLevelInsertionRequest(revision, fragment, translation)


#============================================
def test_top_level_insertion_appends_closed_records_and_rewrites_internal_references() -> None:
	"""A mixed fragment retains order and joins its bond/reaction only to new IDs."""
	session = cdml_document.CDMLDocumentSession.load(
		"<cdml><text id=\"old\"><ftext>old</ftext></text></cdml>",
	)
	fragment = (
		"<cdml><molecule id=\"m\"><atom id=\"a\"><point x=\"0\" y=\"0\" /></atom>"
		"<atom id=\"b\"><point x=\"1\" y=\"0\" /></atom>"
		"<bond id=\"bond\" start=\"a\" end=\"b\" /></molecule>"
		"<arrow id=\"arrow\"><point x=\"0\" y=\"0\" /><point x=\"1\" y=\"0\" />"
		"</arrow><reaction id=\"reaction\"><reactant idref=\"m\" />"
		"<arrow idref=\"arrow\" /></reaction></cdml>"
	)
	commit = session.insert_top_level(_request(session.revision, fragment))
	root = oasa.safe_xml.parse_xml_string(commit.cdml)
	assert tuple(child.tag.rsplit("}", 1)[-1] for child in root) == (
		"text", "molecule", "arrow", "reaction",
	)
	assert all(not value.startswith("__bkchem_new__") for value in commit.id_map.values())


#============================================
def test_top_level_insertion_moves_all_molecular_vertex_and_mark_geometry() -> None:
	"""All established vertex kinds and explicit marks receive the same offset."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	fragment = (
		"<cdml><molecule><atom><point x=\"0\" y=\"0\" z=\"2cm\" />"
		"<mark x=\"0\" y=\"0\" auto=\"true\" /></atom><group>"
		"<point x=\"0\" y=\"0\" /><mark x=\"0\" y=\"0\" /></group>"
		"<text><point x=\"0\" y=\"0\" /><ftext><b>label</b></ftext></text>"
		"<query><point x=\"0\" y=\"0\" /></query></molecule></cdml>"
	)
	commit = session.insert_top_level(_request(session.revision, fragment, (72.0, 36.0)))
	assert commit.cdml.count('x="2.540cm" y="1.270cm"') == 6
	assert 'z="2cm"' in commit.cdml and "<b>label</b>" in commit.cdml


#============================================
@pytest.mark.parametrize(
	"record",
	(
		"<arrow><point x=\"0cm\" y=\"0cm\" /><point x=\"1cm\" y=\"0cm\" /></arrow>",
		"<plus><point x=\"0cm\" y=\"0cm\" /></plus>",
		"<text><point x=\"0cm\" y=\"0cm\" /><ftext>x</ftext></text>",
		"<rect x1=\"0cm\" y1=\"0cm\" x2=\"1cm\" y2=\"1cm\" />",
		"<square x1=\"0cm\" y1=\"0cm\" x2=\"1cm\" y2=\"1cm\" />",
		"<oval x1=\"0cm\" y1=\"0cm\" x2=\"1cm\" y2=\"1cm\" />",
		"<circle x1=\"0cm\" y1=\"0cm\" x2=\"1cm\" y2=\"1cm\" />",
		"<polygon><point x=\"0cm\" y=\"0cm\" /><point x=\"1cm\" y=\"0cm\" /><point x=\"1cm\" y=\"1cm\" /></polygon>",
		"<polyline><point x=\"0cm\" y=\"0cm\" /><point x=\"1cm\" y=\"0cm\" /></polyline>",
		"<reaction />",
	),
)
def test_top_level_insertion_accepts_each_allowlisted_geometry_family(record: str) -> None:
	"""Every named first-slice top-level record has a backend-owned grammar."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = session.insert_top_level(_request(session.revision, f"<cdml>{record}</cdml>", (72.0, 0.0)))
	if record == "<reaction />":
		root = oasa.safe_xml.parse_xml_string(commit.cdml)
		reaction = root.find("reaction")
		durable_id = reaction.get("id") if reaction is not None else None
		assert durable_id and not durable_id.startswith("__bkchem_new__")
	elif record.startswith(("<rect", "<square", "<oval", "<circle")):
		expectation = 'x1="2.540cm"'
	else:
		expectation = 'x="2.540cm"'
	if record != "<reaction />":
		assert expectation in commit.cdml


#============================================
@pytest.mark.parametrize(
	"fragment",
	(
		"<cdml><paper /></cdml>",
		"<cdml><molecule><atom id=\"a\"><point x=\"0cm\" y=\"0cm\" /></atom><bond start=\"a\" end=\"outside\" /></molecule></cdml>",
		"<cdml><molecule><atom><point x=\"0cm\" y=\"0cm\" /><mark x=\"0cm\" /></atom></molecule></cdml>",
		"<cdml><molecule><atom><point x=\"nan\" y=\"0cm\" /></atom></molecule></cdml>",
		"<cdml xmlns:vendor=\"urn:vendor\"><arrow><vendor:point x=\"0cm\" y=\"0cm\" /><vendor:point x=\"1cm\" y=\"0cm\" /></arrow></cdml>",
	),
)
def test_top_level_insertion_rejections_are_atomic(fragment: str) -> None:
	"""Unsupported, dangling, partial, and nonfinite fragments leave state intact."""
	session = cdml_document.CDMLDocumentSession.load("<cdml><plus id=\"old\"><point x=\"0cm\" y=\"0cm\" /></plus></cdml>")
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(_request(session.revision, fragment))
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("translation", ((True, 0.0), (float("inf"), 0.0), (0.0,), "bad"))
def test_top_level_insertion_rejects_invalid_request_translation(translation: object) -> None:
	"""Only exactly two finite non-boolean plain numeric translation values work."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(_request(session.revision, "<cdml><plus><point x=\"0cm\" y=\"0cm\" /></plus></cdml>", translation))


#============================================
def test_repeated_top_level_insertion_uses_fresh_durable_ids_without_client_tokens() -> None:
	"""The same ordinary-source-ID fragment is safe to insert more than once."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	fragment = "<cdml><plus id=\"source\"><point x=\"0cm\" y=\"0cm\" /></plus></cdml>"
	first = session.insert_top_level(_request(session.revision, fragment))
	second = session.insert_top_level(_request(session.revision, fragment))
	assert first.id_map != second.id_map
	assert "__bkchem_new__" not in second.cdml


#============================================
@pytest.mark.parametrize(
	"fragment",
	(
		"<cdml><molecule><atom id=\"a\"><point x=\"0cm\" y=\"0cm\" /></atom>"
		"<atom id=\"a\"><point x=\"1cm\" y=\"0cm\" /></atom></molecule></cdml>",
		"<cdml><molecule><atom id=\"a\"><point x=\"0cm\" y=\"0cm\" /></atom>"
		"<bond start=\"a\" end=\"old\" /></molecule></cdml>",
		"<cdml><molecule><atom><point x=\"1px\" y=\"0cm\" /></atom></molecule></cdml>",
		"<cdml><molecule><display-form /></molecule></cdml>",
		"<cdml><molecule><user-data /></molecule></cdml>",
	),
)
def test_top_level_insertion_rejects_closed_grammar_failures(fragment: str) -> None:
	"""Duplicates, destination links, invalid units, and opaque molecule data reject."""
	session = cdml_document.CDMLDocumentSession.load(
		"<cdml><plus id=\"old\"><point x=\"0cm\" y=\"0cm\" /></plus></cdml>",
	)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(_request(session.revision, fragment))


#============================================
def test_top_level_insertion_remaps_fragment_member_references() -> None:
	"""Fragment vertex and bond member IDs follow the freshly allocated records."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	fragment = """<cdml><molecule id="m"><atom id="a"><point x="0cm" y="0cm" /></atom><atom id="b"><point x="1cm" y="0cm" /></atom><bond id="bond" start="a" end="b" /><fragment id="f"><vertex id="a" /><bond id="bond" /></fragment></molecule></cdml>"""
	commit = session.insert_top_level(_request(session.revision, fragment))
	root = oasa.safe_xml.parse_xml_string(commit.cdml)
	molecule = root.find("molecule")
	fragment_element = molecule.find("fragment")
	assert (
		fragment_element.find("vertex").get("id"), fragment_element.find("bond").get("id"),
	) == (molecule.find("atom").get("id"), molecule.find("bond").get("id"))


#============================================
def test_top_level_insertion_rejects_reaction_role_id_atomically() -> None:
	"""Reaction roles remain IDREF records and cannot declare persistent IDs."""
	session = cdml_document.CDMLDocumentSession.load("<cdml><plus id=\"old\"><point x=\"0cm\" y=\"0cm\" /></plus></cdml>")
	before = session.snapshot()
	fragment = "<cdml><plus id=\"source\"><point x=\"0cm\" y=\"0cm\" /></plus><reaction><plus id=\"role\" idref=\"source\" /></reaction></cdml>"
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(_request(session.revision, fragment))
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(
	"role",
	(
		'<plus idref="source" extra="accepted" />',
		'<plus idref="source" xmlns:vendor="urn:vendor" vendor:extra="accepted" />',
	),
)
def test_top_level_insertion_rejects_reaction_role_extra_attributes_atomically(role: str) -> None:
	"""Reaction roles accept only their one unqualified nonempty IDREF."""
	session = cdml_document.CDMLDocumentSession.load("<cdml><plus id=\"old\"><point x=\"0cm\" y=\"0cm\" /></plus></cdml>")
	before = session.snapshot()
	fragment = f'<cdml><plus id="source"><point x="0cm" y="0cm" /></plus><reaction>{role}</reaction></cdml>'
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(_request(session.revision, fragment))
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(
	"fragment",
	(
		"<cdml><molecule><atom id=\"a\"><point x=\"0cm\" y=\"0cm\" /></atom>"
		"<template atom=\"a\" /></molecule></cdml>",
		"<cdml><molecule><atom id=\"a\"><point x=\"0cm\" y=\"0cm\" /></atom>"
		"<template atom=\"a\" bond_first=\"\" /></molecule></cdml>",
	),
)
def test_top_level_insertion_enforces_template_optional_reference_grammar(fragment: str) -> None:
	"""A missing optional template bond differs from a present empty reference."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	if "bond_first=\"\"" in fragment:
		with pytest.raises(cdml_document.CDMLValidationError):
			session.insert_top_level(_request(session.revision, fragment))
	else:
		assert session.insert_top_level(_request(session.revision, fragment)).revision == 1


#============================================
@pytest.mark.parametrize(
	"insertion_request",
	(
		cdml_document.CDMLTopLevelInsertionRequest(0, 7, (0.0, 0.0)),
		cdml_document.CDMLTopLevelInsertionRequest(0, "<cdml />", (0.0, 0.0), 7),
		cdml_document.CDMLTopLevelInsertionRequest(0, "<cdml />", [0.0, 0.0]),
		cdml_document.CDMLTopLevelInsertionRequest(0, "<cdml />", (10 ** 10000, 0.0)),
	),
)
def test_top_level_insertion_rejects_invalid_request_values(insertion_request: object) -> None:
	"""Public request values are plain immutable data with finite tuple offsets."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(insertion_request)


#============================================
def test_top_level_insertion_rejects_boolean_expected_revision_atomically() -> None:
	"""A boolean cannot enter the exact built-in integer revision boundary."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	session.commit(expected_revision=0, complete_cdml="<cdml />")
	before = session.snapshot()
	request = cdml_document.CDMLTopLevelInsertionRequest(
		True, "<cdml><plus><point x=\"0cm\" y=\"0cm\" /></plus></cdml>", (0.0, 0.0),
	)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(request)
	assert session.snapshot() == before


#============================================
def test_top_level_insertion_rejects_adversarial_numeric_subclass_atomically() -> None:
	"""Translation validation rejects subclasses before their conversion hooks run."""
	class AdversarialFloat(float):
		def __float__(self) -> float:
			raise ValueError("conversion hook must not run")

	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	before = session.snapshot()
	request = cdml_document.CDMLTopLevelInsertionRequest(
		0, "<cdml><plus><point x=\"0cm\" y=\"0cm\" /></plus></cdml>",
		(AdversarialFloat(0.0), 0.0),
	)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_top_level(request)
	assert session.snapshot() == before


#============================================
def test_top_level_insertion_rejects_stale_revision_before_fragment_work() -> None:
	"""A stale request is an atomic optimistic-concurrency rejection."""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	session.commit(expected_revision=0, complete_cdml="<cdml />")
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.insert_top_level(_request(0, "<cdml><plus><point x=\"0cm\" y=\"0cm\" /></plus></cdml>"))
	assert session.snapshot() == before
