"""Fast behavioral checks for the public CDML 26.07 conformance layer."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_conformance as cdml_conformance
import oasa.cdml_document as cdml_document
import oasa.cdml_xml as cdml_xml


CANONICAL_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm" /></atom></molecule>
</cdml>
"""

PROPOSAL_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <bracket id="__bkchem_new__bracket" />
 <vector id="__bkchem_new__vector" />
</cdml>
"""


REACTION_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="m1" />
 <arrow id="arrow1" />
 <text id="text1"><ftext>heat</ftext></text>
 <plus id="plus1" />
 <reaction id="reaction1">
  <reactant idref="m1" />
  <product idref="m1" />
  <arrow idref="arrow1" />
  <condition idref="text1" />
  <plus idref="plus1" />
 </reaction>
</cdml>
"""


#============================================
def test_canonical_document_satisfies_the_authored_profile() -> None:
	"""A current canonical document succeeds in the authored 26.07 profile."""
	report = cdml_conformance.inspect_cdml(CANONICAL_CDML, profile="authored-26.07")
	assert report.is_valid


#============================================
def test_legacy_namespace_free_document_is_compatibility_only() -> None:
	"""A retained namespace-free document stays readable but is not new authored CDML."""
	legacy = '<cdml version="26.02"><molecule id="m1" /></cdml>'
	profiles = tuple(
		cdml_conformance.inspect_cdml(legacy, profile=profile).is_valid
		for profile in ("compat", "authored-26.07")
	)
	assert profiles == (True, False)


#============================================
@pytest.mark.parametrize("local_name", (
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline", "reaction",
))
def test_authored_selectable_direct_children_require_ids(local_name: str) -> None:
	"""Only authored output requires an ID for each selectable top-level family."""
	cdml = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">'
		f"<{local_name} /></cdml>"
	)
	compat = cdml_conformance.inspect_cdml(cdml, profile="compat")
	session = cdml_document.CDMLDocumentSession.load(cdml)
	session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	authored = cdml_conformance.inspect_cdml(cdml, profile="authored-26.07")
	assert compat.is_valid
	assert "CDML-A2607-003" in {issue.code for issue in authored.issues}


#============================================
@pytest.mark.parametrize("local_name", (
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline", "reaction",
))
def test_authored_selectable_direct_child_with_id_satisfies_profile(local_name: str) -> None:
	"""A nonempty durable ID satisfies the authored record-identity requirement."""
	cdml = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">'
		f'<{local_name} id="{local_name}1" /></cdml>'
	)
	report = cdml_conformance.inspect_cdml(cdml, profile="authored-26.07")
	assert report.is_valid


#============================================
@pytest.mark.parametrize("identifier", ("", "   "))
def test_authored_selectable_direct_child_rejects_an_empty_or_whitespace_id(
		identifier: str,
		) -> None:
	"""An authored ID must contain non-whitespace durable identifier text."""
	cdml = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">'
		f'<arrow id="{identifier}" /></cdml>'
	)
	report = cdml_conformance.inspect_cdml(cdml, profile="authored-26.07")
	assert "CDML-A2607-003" in {issue.code for issue in report.issues}


#============================================
@pytest.mark.parametrize("record", (
	'<arrow><point x="0cm" y="0cm" /><point x="1cm" y="0cm" /></arrow>',
	"<reaction />",
))
def test_idless_legacy_selectable_content_round_trips_without_fabricated_ids(record: str) -> None:
	"""Compatibility Load and Commit retain ID-less arrow and reaction records."""
	cdml = f'<cdml version="26.07">{record}</cdml>'
	session = cdml_document.CDMLDocumentSession.load(cdml)
	accepted = session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	assert cdml_xml.inspect_cdml_xml(accepted.cdml.encode("utf-8")).semantic_fingerprint == (
		cdml_xml.inspect_cdml_xml(cdml.encode("utf-8")).semantic_fingerprint
	)


#============================================
@pytest.mark.parametrize("local_name", (
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline", "reaction",
))
def test_whitespace_only_ids_are_authored_invalid_but_compatibly_preserved(
		local_name: str,
		) -> None:
	"""Compatibility retains literal whitespace IDs without authoring-profile approval."""
	cdml = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">'
		f'<{local_name} id="   " /></cdml>'
	)
	session = cdml_document.CDMLDocumentSession.load(cdml)
	accepted = session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	authored = cdml_conformance.inspect_cdml(cdml, profile="authored-26.07")
	assert 'id="   "' in accepted.cdml
	assert "CDML-A2607-003" in {issue.code for issue in authored.issues}
	assert cdml_xml.inspect_cdml_xml(accepted.cdml.encode("utf-8")).semantic_fingerprint == (
		cdml_xml.inspect_cdml_xml(cdml.encode("utf-8")).semantic_fingerprint
	)


#============================================
def test_backend_top_level_insertion_emits_an_authored_profile_document() -> None:
	"""One backend insertion result contains durable IDs suitable for authored output."""
	session = cdml_document.CDMLDocumentSession.load(CANONICAL_CDML)
	request = cdml_document.CDMLTopLevelInsertionRequest(
		session.revision,
		'<cdml><plus><point x="0cm" y="0cm" /></plus></cdml>',
		(0.0, 0.0),
	)
	accepted = session.insert_top_level(request)
	report = cdml_conformance.inspect_cdml(accepted.cdml, profile="authored-26.07")
	assert report.is_valid


#============================================
def test_authored_reaction_roles_target_their_direct_root_categories() -> None:
	"""An authored reaction uses stable IDs for all five typed direct targets."""
	report = cdml_conformance.inspect_cdml(REACTION_CDML, profile="authored-26.07")
	assert report.is_valid


#============================================
@pytest.mark.parametrize(
	("role_name", "current_target", "wrong_target"),
	(
		("reactant", "m1", "arrow1"),
		("product", "m1", "text1"),
		("arrow", "arrow1", "m1"),
		("condition", "text1", "plus1"),
		("plus", "plus1", "m1"),
	),
)
def test_authored_reaction_role_rejects_a_wrong_direct_root_category(
		role_name: str,
		current_target: str,
		wrong_target: str,
		) -> None:
	"""Compatibility retains role references while authored output types them."""
	candidate = REACTION_CDML.replace(
		f'<{role_name} idref="{current_target}" />',
		f'<{role_name} idref="{wrong_target}" />',
	)
	session = cdml_document.CDMLDocumentSession.load(candidate)
	session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	report = cdml_conformance.inspect_cdml(candidate, profile="authored-26.07")
	assert "CDML-A2607-004" in {issue.code for issue in report.issues}


#============================================
@pytest.mark.parametrize("target", ("", "   ", "missing", "nested_group"))
def test_authored_reaction_role_requires_a_durable_direct_root_target(target: str) -> None:
	"""Missing, unstable, unknown, and nested role IDs stay authored-invalid."""
	candidate = REACTION_CDML.replace(
		'<product idref="m1" />',
		f'<product idref="{target}" />',
	).replace(
		'<molecule id="m1" />',
		'<molecule id="m1"><group id="nested_group" /></molecule>',
	)
	report = cdml_conformance.inspect_cdml(candidate, profile="authored-26.07")
	assert "CDML-A2607-004" in {issue.code for issue in report.issues}


#============================================
def test_authored_reaction_role_rejects_a_provisional_direct_root_target() -> None:
	"""The authored role diagnostic supplements generic escaped-token findings."""
	candidate = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="__bkchem_new__m" />
 <reaction id="reaction1"><product idref="__bkchem_new__m" /></reaction>
</cdml>
"""
	compat = cdml_conformance.inspect_cdml(candidate, profile="compat")
	authored = cdml_conformance.inspect_cdml(candidate, profile="authored-26.07")
	assert compat.is_valid
	assert {
		("CDML-ID-002", "/cdml/molecule"),
		("CDML-REF-002", "/cdml/reaction/product"),
		("CDML-A2607-004", "/cdml/reaction/product"),
	} <= {(issue.code, issue.path) for issue in authored.issues}


#============================================
def test_legacy_nested_reaction_target_stays_compatibly_preserved() -> None:
	"""Generic Load and Commit preserve a historical nested reaction target."""
	legacy = REACTION_CDML.replace(
		'<molecule id="m1" />',
		'<molecule id="m1"><group id="group1" /></molecule>',
	).replace('<product idref="m1" />', '<product idref="group1" />')
	session = cdml_document.CDMLDocumentSession.load(legacy)
	accepted = session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	assert cdml_conformance.inspect_cdml(accepted.cdml, profile="compat").is_valid
	assert "CDML-A2607-004" in {
		issue.code
		for issue in cdml_conformance.inspect_cdml(legacy, profile="authored-26.07").issues
	}


#============================================
@pytest.mark.parametrize(
	"compatible_cdml",
	(
		"""\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <arrow type="normal"><point x="0cm" y="0cm" /><point x="1cm" y="0cm" /></arrow>
</cdml>
""",
		"""\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <text><ftext /></text>
</cdml>
""",
		"""\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <arrow type="normal"><point x="0cm" y="0cm" /></arrow>
</cdml>
""",
	),
)
def test_compatibility_content_loads_and_commits_without_authored_geometry_claims(
	compatible_cdml: str,
) -> None:
	"""Compatible incomplete records remain authoritative preservation content."""
	report = cdml_conformance.inspect_cdml(compatible_cdml)
	session = cdml_document.CDMLDocumentSession.load(compatible_cdml)
	accepted = session.commit(
		expected_revision=session.revision,
		complete_cdml=session.snapshot().cdml,
	)
	assert report.is_valid
	assert cdml_xml.inspect_cdml_xml(accepted.cdml.encode("utf-8")).semantic_fingerprint == (
		cdml_xml.inspect_cdml_xml(compatible_cdml.encode("utf-8")).semantic_fingerprint
	)


#============================================
def test_corpus_foreign_subtree_survives_semantic_preservation() -> None:
	"""The public corpus proves that an opaque foreign subtree survives a DOM round trip."""
	repository_root = pathlib.Path(__file__).resolve().parents[3]
	manifest = repository_root / "docs/cdml_conformance/cdml_26_07_manifest.json"
	results = cdml_conformance.inspect_manifest(manifest, repository_root)
	foreign_case = next(result for result in results if result.case_id == "foreign-opaque-subtree")
	assert foreign_case.preservation_matches


#============================================
def test_corpus_preserves_whitespace_only_rich_text_and_opaque_content() -> None:
	"""Whitespace character data survives a CDML DOM round trip without byte matching."""
	repository_root = pathlib.Path(__file__).resolve().parents[3]
	manifest = repository_root / "docs/cdml_conformance/cdml_26_07_manifest.json"
	results = cdml_conformance.inspect_manifest(manifest, repository_root)
	whitespace_case = next(
		result for result in results
		if result.case_id == "whitespace-bearing-rich-text-and-opaque-content"
	)
	assert whitespace_case.preservation_matches


#============================================
def test_corpus_preserves_comments_pis_and_namespaced_opaque_content() -> None:
	"""A semantic round trip retains non-element persistent XML content."""
	repository_root = pathlib.Path(__file__).resolve().parents[3]
	manifest = repository_root / "docs/cdml_conformance/cdml_26_07_manifest.json"
	results = cdml_conformance.inspect_manifest(manifest, repository_root)
	case = next(
		result for result in results
		if result.case_id == "comment-pi-and-namespaced-opaque-preservation"
	)
	assert case.preservation_matches


#============================================
@pytest.mark.parametrize(
	"xml",
	(
		'<!DOCTYPE cdml [<!ENTITY value "unsafe">]><cdml>&value;</cdml>',
		'<!DOCTYPE cdml SYSTEM "https://example.invalid/cdml.dtd"><cdml />',
	),
)
def test_unsafe_doctype_is_one_typed_backend_and_conformance_failure(xml: str) -> None:
	"""Unsafe complete CDML cannot enter either the backend or its public inspector."""
	with pytest.raises(cdml_document.CDMLParseError):
		cdml_document.CDMLDocument.parse(xml)
	report = cdml_conformance.inspect_cdml(xml)
	assert report.issues[0].code == "CDML-XML-001"


#============================================
def test_core_cdml_prefix_renames_have_equal_semantic_fingerprints() -> None:
	"""Known CDML syntax compares by expanded names rather than prefix spelling."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		b'c:version="26.07"><c:molecule c:id="m1" /></c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml" '
		b'd:version="26.07"><d:molecule d:id="m1" /></d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		== cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_writer_metadata_prefix_renames_have_equal_semantic_fingerprints() -> None:
	"""Writer-shaped metadata uses expanded-name rather than prefix semantics."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<c:metadata><c:doc href="https://example.invalid/spec" /></c:metadata>'
		b'</c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<d:metadata><d:doc href="https://example.invalid/spec" /></d:metadata>'
		b'</d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		== cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_documented_info_prefix_renames_have_equal_semantic_fingerprints() -> None:
	"""Documented information records use expanded-name semantics."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<c:info><c:author_program version="26.02">BKChem</c:author_program>'
		b'<c:author>Author</c:author><c:note>Note</c:note></c:info></c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<d:info><d:author_program version="26.02">BKChem</d:author_program>'
		b'<d:author>Author</d:author><d:note>Note</d:note></d:info></d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		== cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_atom_explicit_hydrogens_prefix_renames_have_equal_semantic_fingerprints() -> None:
	"""The writer's nonzero explicit hydrogen count is known atom syntax."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<c:molecule c:id="m1"><c:atom c:id="a1" c:explicit_hydrogens="2" />'
		b'</c:molecule></c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<d:molecule d:id="m1"><d:atom d:id="a1" d:explicit_hydrogens="2" />'
		b'</d:molecule></d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		== cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_legacy_direct_ftext_markup_retains_its_lexical_prefix() -> None:
	"""Pre-0.16 direct rich-text nodes remain opaque preservation content."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<c:ftext><c:i>x</c:i></c:ftext>'
		b'</c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<d:ftext><d:i>x</d:i></d:ftext>'
		b'</d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		!= cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_unknown_core_attribute_requires_its_lexical_namespace_context() -> None:
	"""An unknown core attribute cannot lose QName-like namespace meaning."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		b'xmlns:q="urn:one" kind="q:Thing"><c:molecule /></c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml" '
		b'xmlns:q="urn:two" kind="q:Thing"><d:molecule /></d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		!= cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_foreign_core_attribute_requires_its_lexical_namespace_context() -> None:
	"""A foreign attribute on core CDML retains its QName-like value context."""
	first = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		b'xmlns:v="urn:vendor" xmlns:q="urn:one" v:kind="q:Thing">'
		b'<c:molecule /></c:cdml>'
	)
	second = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml" '
		b'xmlns:v="urn:vendor" xmlns:q="urn:two" v:kind="q:Thing">'
		b'<d:molecule /></d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(first).semantic_fingerprint
		!= cdml_xml.inspect_cdml_xml(second).semantic_fingerprint
	)


#============================================
def test_cdata_uses_character_data_semantics_in_the_public_fingerprint() -> None:
	"""CDATA sections and escaped text compare by their shared character data."""
	cdata = (
		b'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<c:ftext><![CDATA[A < B]]></c:ftext></c:cdml>'
	)
	escaped = (
		b'<d:cdml xmlns:d="http://www.freesoftware.fsf.org/bkchem/cdml">'
		b'<d:ftext>A &lt; B</d:ftext></d:cdml>'
	)
	assert (
		cdml_xml.inspect_cdml_xml(cdata).semantic_fingerprint
		== cdml_xml.inspect_cdml_xml(escaped).semantic_fingerprint
	)


#============================================
@pytest.mark.parametrize(
	("xml", "code"),
	(
		(
			CANONICAL_CDML.replace('id="a1"', 'id="m1"'),
			"CDML-ID-001",
		),
		(
			CANONICAL_CDML.replace('id="a1"', 'id="__bkchem_new__atom"'),
			"CDML-ID-002",
		),
		(
			CANONICAL_CDML.replace('<atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>', '<bond id="b1" type="n1" start="missing" end="missing" />'),
			"CDML-REF-001",
		),
	),
)
def test_authored_profile_exposes_stable_backend_safety_codes(xml: str, code: str) -> None:
	"""Existing durable-ID and reference safety rules have stable public diagnostics."""
	report = cdml_conformance.inspect_cdml(xml, profile="authored-26.07")
	assert code in {issue.code for issue in report.issues}


#============================================
def test_malformed_xml_has_a_stable_parse_code() -> None:
	"""Unsafe or malformed XML reports a public parser diagnostic instead of raising."""
	report = cdml_conformance.inspect_cdml('<cdml><molecule></cdml>')
	assert report.issues[0].code == "CDML-XML-001"


#============================================
def test_non_cdml_root_has_a_stable_root_code() -> None:
	"""A structurally parsed non-CDML root differs from malformed XML."""
	report = cdml_conformance.inspect_cdml('<drawing version="26.07" />')
	assert report.issues[0].code == "CDML-ROOT-001"


#============================================
def test_validation_issues_are_read_only_while_validate_keeps_raising() -> None:
	"""Pure conformance can inspect backend findings without changing legacy raising behavior."""
	document = cdml_document.CDMLDocument.parse(
		CANONICAL_CDML.replace('id="a1"', 'id="m1"'), validation="compat",
	)
	issues = document.validation_issues()
	with pytest.raises(cdml_document.CDMLValidationError):
		document.validate()
	assert issues[0].code == "duplicate_id"


#============================================
def test_proposal_elements_do_not_allocate_provisional_ids() -> None:
	"""Bracket and vector proposals remain outside current ID allocation."""
	session = cdml_document.CDMLDocumentSession.load(PROPOSAL_CDML)
	commit = session.commit(expected_revision=session.revision, complete_cdml=PROPOSAL_CDML)
	assert commit.id_map == {}


#============================================
def test_proposal_elements_retain_opaque_serialized_content() -> None:
	"""Bracket and vector proposals persist as opaque CDML content."""
	session = cdml_document.CDMLDocumentSession.load(PROPOSAL_CDML)
	commit = session.commit(expected_revision=session.revision, complete_cdml=PROPOSAL_CDML)
	assert '__bkchem_new__bracket' in commit.cdml


#============================================
def test_opaque_proposal_ids_still_reserve_the_document_wide_id_namespace() -> None:
	"""Proposal content stays opaque without allowing a duplicate literal document ID."""
	proposal = CANONICAL_CDML.replace(
		'<molecule id="m1">',
		'<vector id="m1" /><molecule id="m1">',
	)
	report = cdml_conformance.inspect_cdml(proposal, profile="authored-26.07")
	assert "CDML-ID-001" in {issue.code for issue in report.issues}
