"""Behavioral tests for OASA complete-document CDML authority."""

# Standard Library
import ast
import pathlib
import re

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.cdml_ftext
import oasa.cdml_linear_form
import oasa.cdml_xml
import oasa.cdml_writer
import oasa.coords_generator
import oasa.smiles_lib


#============================================
MIXED_CDML = """\
<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml"
 xmlns:vendor="urn:example:vendor" version="26.02">
 <bk:paper id="paper_1" type="A4" />
 <bk:molecule id="molecule_1">
  <bk:atom id="atom_1" name="C"><bk:point x="1cm" y="1cm" /></bk:atom>
  <bk:atom id="atom_2" name="O"><bk:point x="2cm" y="1cm" /></bk:atom>
  <bk:bond id="bond_1" start="atom_1" end="atom_2" type="n1" />
  <bk:group id="group_1" atom="atom_1"><bk:metadata key="role">protecting</bk:metadata></bk:group>
  <bk:fragment id="fragment_1"><bk:vertex id="atom_1" /><bk:bond id="bond_1" /></bk:fragment>
  <bk:template id="template_1" atom="atom_1" bond_first="bond_1" bond_second="bond_1" />
 </bk:molecule>
 <bk:arrow id="arrow_1" type="normal"><bk:point x="1cm" y="2cm" /><bk:point x="3cm" y="2cm" /></bk:arrow>
 <bk:text id="text_1"><bk:ftext>yield</bk:ftext></bk:text>
 <bk:plus id="plus_1" pos="4cm 2cm" />
 <bk:bracket id="bracket_1"><bk:polyline points="5,1 5,3" /></bk:bracket>
 <bk:reaction id="reaction_1"><bk:reactant idref="molecule_1" /><bk:condition idref="text_1" /><bk:plus idref="plus_1" /><bk:arrow idref="arrow_1" /><bk:product idref="group_1" /></bk:reaction>
 <vendor:note id="vendor_1" vendor:flag="keep" marker="__bkchem_new__arrow">before <vendor:child flag="keep" /> after</vendor:note>
</bk:cdml>
"""


#============================================
def _persistent_fingerprint(cdml_text: str) -> tuple:
	"""Return the hardened complete-CDML preservation fingerprint."""
	inspection = oasa.cdml_xml.inspect_cdml_xml(cdml_text.encode("utf-8"))
	return inspection.semantic_fingerprint


#============================================
def _root_version(cdml_text: str) -> str:
	"""Return the literal format version from a complete CDML document root."""
	inspection = oasa.cdml_xml.inspect_cdml_xml(cdml_text.encode("utf-8"))
	return inspection.version


#============================================
def _with_arrow_id(cdml_text: str, arrow_id: str) -> str:
	"""Return a candidate that changes the persistent arrow identifier."""
	return cdml_text.replace('id="arrow_1"', f'id="{arrow_id}"', 1)


#============================================
def _with_inserted_arrow(cdml_text: str, arrow_id: str) -> str:
	"""Return a candidate with one persistent arrow before the text object."""
	arrow = (
		f'<bk:arrow id="{arrow_id}" type="normal">'
		'<bk:point x="6cm" y="2cm" /><bk:point x="7cm" y="2cm" />'
		'</bk:arrow>\n '
	)
	return cdml_text.replace(' <bk:text id="text_1">', f' {arrow}<bk:text id="text_1">')


#============================================
def _commit_arrow(session: cdml_document.CDMLDocumentSession, arrow_id: str) -> cdml_document.CDMLCommit:
	"""Commit one candidate arrow against the session's current revision."""
	snapshot = session.snapshot()
	candidate = _with_inserted_arrow(snapshot.cdml, arrow_id)
	return session.commit(expected_revision=snapshot.revision, complete_cdml=candidate)


#============================================
def _invalid_state_fingerprint(session: cdml_document.CDMLDocumentSession) -> tuple:
	"""Return the externally observable state that failed commits must preserve."""
	snapshot = session.snapshot()
	return snapshot.revision, _persistent_fingerprint(snapshot.cdml)


#============================================
def _imported_module_names(tree: ast.AST) -> set[str]:
	"""Return absolute module names declared by imports in one syntax tree."""
	module_names = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			module_names.update(alias.name for alias in node.names)
		elif isinstance(node, ast.ImportFrom) and node.module is not None:
			module_names.add(node.module)
	return module_names


#============================================
def test_backend_roundtrip_preserves_complete_persistent_document() -> None:
	"""A backend session preserves every namespaced persistent CDML object."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	reloaded = cdml_document.CDMLDocumentSession.load(session.snapshot().cdml)
	assert _persistent_fingerprint(reloaded.snapshot().cdml) == _persistent_fingerprint(MIXED_CDML)


#============================================
def test_imported_document_uses_empty_saved_baseline_until_backend_save() -> None:
	"""An external complete document is authoritative yet dirty before CDML Save."""
	session = cdml_document.CDMLDocumentSession.load_imported(MIXED_CDML)
	imported = session.snapshot()
	assert imported.is_dirty
	saved = session.mark_saved(expected_revision=imported.revision)
	assert not saved.is_dirty


#============================================
def test_complete_import_document_gives_detached_components_unique_durable_ids() -> None:
	"""Backend import serialization keeps disconnected chemistry independently addressable."""
	molecule = oasa.smiles_lib.text_to_mol("CC.O")
	oasa.coords_generator.calculate_coords(molecule, bond_length=1.0, force=1)
	components = list(molecule.get_disconnected_subgraphs())
	complete_cdml = oasa.cdml_writer.molecules_to_complete_document(components)
	document = cdml_document.CDMLDocument.parse(complete_cdml, validation="strict")
	molecule_records = [record for record in document.objects() if record.local_name == "molecule"]
	all_records = tuple(
		document.find_by_id(identifier)
		for identifier in ("m1", "m2", "a1", "a2", "a3", "b1")
	)
	atom_ids = {
		record.identifier for record in all_records if record.local_name == "atom"
	}
	bond = next(record for record in all_records if record.local_name == "bond")
	endpoint_ids = set(re.findall(r'(?:start|end)="([^"]+)"', bond.raw_xml))
	identifiers = [record.identifier for record in all_records]

	assert len(molecule_records) == 2
	assert len(identifiers) == len(set(identifiers))
	assert endpoint_ids <= atom_ids
	assert len(endpoint_ids) == 2


#============================================
def test_complete_26_02_document_keeps_its_declared_profile_without_migration() -> None:
	"""Backend authority preserves a supported old profile unless a caller transforms it."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	commit = session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	assert _root_version(commit.cdml) == "26.02"


#============================================
def test_unknown_future_profile_survives_backend_load_snapshot_and_commit() -> None:
	"""Complete-document authority treats a future root version as opaque metadata."""
	future_cdml = MIXED_CDML.replace('version="26.02"', 'version="99.99"')
	session = cdml_document.CDMLDocumentSession.load(future_cdml)
	snapshot = session.snapshot()
	commit = session.commit(expected_revision=snapshot.revision, complete_cdml=snapshot.cdml)
	assert (_root_version(snapshot.cdml), _root_version(commit.cdml)) == ("99.99", "99.99")


#============================================
def test_records_are_top_level_and_recursive_lookup_finds_definition() -> None:
	"""Ordered document records omit nested chemistry while lookup finds atom IDs."""
	document = cdml_document.CDMLDocument.parse(MIXED_CDML, validation="strict")
	assert all(record.local_name not in ("atom", "bond", "point") for record in document.objects())
	assert document.find_by_id("atom_1").identifier == "atom_1"


#============================================
def test_commit_allocates_durable_arrow_id_and_keeps_id_map_read_only() -> None:
	"""A valid frontend token becomes durable and its correlation mapping cannot mutate."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	commit = _commit_arrow(session, "__bkchem_new__arrow")
	assert commit.id_map["__bkchem_new__arrow"] != "__bkchem_new__arrow"
	with pytest.raises(TypeError):
		commit.id_map["__bkchem_new__arrow"] = "tampered"


#============================================
def test_accepted_provisional_token_reuse_is_rejected_without_state_change() -> None:
	"""A successful commit consumes its recognized provisional declaration token."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	token = "__bkchem_new__single_use"
	_commit_arrow(session, token)
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLValidationError):
		_commit_arrow(session, token)
	assert session.snapshot() == before


#============================================
def test_rejected_provisional_token_reuse_remains_rejected() -> None:
	"""A rejected reuse cannot make an already-consumed token available again."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	token = "__bkchem_new__still_consumed"
	_commit_arrow(session, token)
	with pytest.raises(cdml_document.CDMLValidationError):
		_commit_arrow(session, token)
	with pytest.raises(cdml_document.CDMLValidationError):
		_commit_arrow(session, token)


#============================================
def test_rejected_candidate_does_not_consume_provisional_token() -> None:
	"""A corrected candidate may use a token from a candidate rejected before commit."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	token = "__bkchem_new__corrected"
	candidate = _with_inserted_arrow(session.snapshot().cdml, token)
	candidate = candidate.replace('end="atom_2"', 'end="missing_atom"')
	with pytest.raises(cdml_document.CDMLValidationError):
		session.commit(expected_revision=session.revision, complete_cdml=candidate)
	commit = _commit_arrow(session, token)
	assert token in commit.id_map


#============================================
def test_new_backend_session_starts_a_fresh_provisional_token_scope() -> None:
	"""Loading a document starts a new scope for recognized correlation tokens."""
	token = "__bkchem_new__new_session"
	first_session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	_commit_arrow(first_session, token)
	new_session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	commit = _commit_arrow(new_session, token)
	assert token in commit.id_map


#============================================
def test_repeated_opaque_provisional_lookalike_remains_untracked() -> None:
	"""Opaque extension tokens remain literal XML across accepted backend commits."""
	cdml_text = """\
<cdml xmlns:vendor="urn:vendor"><vendor:note marker="__bkchem_new__opaque" /></cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	first = session.commit(expected_revision=session.revision, complete_cdml=cdml_text)
	second = session.commit(expected_revision=session.revision, complete_cdml=cdml_text)
	assert first.id_map == second.id_map == {}


#============================================
def test_opaque_ids_reserve_durable_ids_for_backend_allocation() -> None:
	"""Extension IDs reserve document-wide names even when their XML stays opaque."""
	candidate = _with_inserted_arrow(
		MIXED_CDML.replace('id="vendor_1"', 'id="a1"'),
		"__bkchem_new__arrow",
	)
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	commit = session.commit(expected_revision=session.revision, complete_cdml=candidate)
	assert commit.id_map["__bkchem_new__arrow"] != "a1"


#============================================
def test_opaque_duplicate_id_is_rejected_atomically() -> None:
	"""An opaque extension cannot duplicate an ID already owned by CDML content."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	before = _invalid_state_fingerprint(session)
	candidate = MIXED_CDML.replace('id="vendor_1"', 'id="molecule_1"')
	with pytest.raises(cdml_document.CDMLValidationError):
		session.commit(expected_revision=session.revision, complete_cdml=candidate)
	assert _invalid_state_fingerprint(session) == before


#============================================
def test_commit_rewrites_known_provisional_references_without_touching_opaque_xml() -> None:
	"""Known references follow allocated IDs while opaque extension values stay intact."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	candidate = _with_arrow_id(session.snapshot().cdml, "__bkchem_new__arrow")
	candidate = candidate.replace('idref="arrow_1"', 'idref="__bkchem_new__arrow"')
	commit = session.commit(expected_revision=session.revision, complete_cdml=candidate)
	allocated_id = commit.id_map["__bkchem_new__arrow"]
	assert f'idref="{allocated_id}"' in commit.cdml
	assert 'marker="__bkchem_new__arrow"' in commit.cdml


#============================================
@pytest.mark.parametrize(
	("candidate", "error_type"),
	(
		(MIXED_CDML[:-8], cdml_document.CDMLParseError),
		('<!DOCTYPE cdml [<!ENTITY value "unsafe">]><cdml>&value;</cdml>', cdml_document.CDMLParseError),
		("<not-cdml />", cdml_document.CDMLParseError),
		(MIXED_CDML.replace('id="atom_2"', 'id="atom_1"'), cdml_document.CDMLValidationError),
		(MIXED_CDML.replace('end="atom_2"', 'end="missing_atom"'), cdml_document.CDMLValidationError),
		(MIXED_CDML.replace('idref="arrow_1"', 'idref="__bkchem_new__missing"'), cdml_document.CDMLValidationError),
	),
)
def test_invalid_commits_raise_public_errors_without_state_change(
	candidate: str,
	error_type: type[Exception],
) -> None:
	"""Invalid whole-document submissions remain atomic and report their public error."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	before = _invalid_state_fingerprint(session)
	with pytest.raises(error_type):
		session.commit(expected_revision=session.revision, complete_cdml=candidate)
	assert _invalid_state_fingerprint(session) == before


#============================================
def test_stale_revision_is_typed_and_atomic() -> None:
	"""A stale complete-document request reports a typed error without changing state."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	obsolete = session.snapshot()
	_commit_arrow(session, "__bkchem_new__stale")
	before_failure = session.snapshot()
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.commit(expected_revision=obsolete.revision, complete_cdml=obsolete.cdml)
	assert _invalid_state_fingerprint(session) == (
		before_failure.revision,
		_persistent_fingerprint(before_failure.cdml),
	)


#============================================
def test_backend_authority_module_has_no_qt_imports() -> None:
	"""The backend CDML authority modules remain independent of Qt imports."""
	module_names = set()
	for backend_module in (cdml_document, oasa.cdml_ftext, oasa.cdml_linear_form):
		source_path = pathlib.Path(backend_module.__file__)
		tree = ast.parse(source_path.read_text(encoding="utf-8"))
		module_names.update(_imported_module_names(tree))
	assert not any(name == "PySide6" or name.startswith("PySide6.") for name in module_names)


#============================================
@pytest.mark.parametrize(
	"candidate",
	(
		MIXED_CDML.replace('id="arrow_1"', 'id="__bkchem_new__"'),
		MIXED_CDML.replace('id="arrow_1"', 'id="__bkchem_new__1bad"'),
		MIXED_CDML.replace('id="arrow_1"', 'id="__bkchem_new__bad.name"'),
		MIXED_CDML.replace('id="arrow_1"', 'id="__bkchem_new__bad$name"'),
		MIXED_CDML.replace('id="arrow_1"', f'id="__bkchem_new__a{"b" * 64}"'),
		MIXED_CDML.replace('end="atom_2"', 'end="__bkchem_new__"'),
		MIXED_CDML.replace('end="atom_2"', 'end="__bkchem_new__1bad"'),
		MIXED_CDML.replace('end="atom_2"', 'end="__bkchem_new__bad.name"'),
		MIXED_CDML.replace('end="atom_2"', 'end="__bkchem_new__bad$name"'),
		MIXED_CDML.replace('end="atom_2"', f'end="__bkchem_new__a{"b" * 64}"'),
	),
)
def test_malformed_reserved_tokens_are_rejected_atomically(candidate: str) -> None:
	"""Malformed reserved IDs and known references cannot become durable content."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	before = _invalid_state_fingerprint(session)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.commit(expected_revision=session.revision, complete_cdml=candidate)
	assert _invalid_state_fingerprint(session) == before


#============================================
def test_opaque_reserved_looking_text_remains_unchanged() -> None:
	"""Reserved-looking extension data remains opaque when it is not an ID or known ref."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	assert _persistent_fingerprint(session.snapshot().cdml) == _persistent_fingerprint(MIXED_CDML)


#============================================
@pytest.mark.parametrize(
	"candidate",
	(
		MIXED_CDML.replace('idref="text_1"', 'idref="missing_condition"'),
		MIXED_CDML.replace('idref="plus_1"', 'idref="missing_plus"'),
		MIXED_CDML.replace('<bk:vertex id="atom_1"', '<bk:vertex id="missing_vertex"'),
		MIXED_CDML.replace('<bk:bond id="bond_1" /></bk:fragment>', '<bk:bond id="missing_bond" /></bk:fragment>'),
	),
)
def test_documented_references_reject_dangling_targets(candidate: str) -> None:
	"""Reaction and fragment references must resolve inside the authoritative document."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.commit(expected_revision=session.revision, complete_cdml=candidate)


#============================================
def test_prior_snapshot_keeps_its_content_after_commit() -> None:
	"""A previously received backend snapshot remains stable after a later commit."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	before = session.snapshot()
	_commit_arrow(session, "__bkchem_new__snapshot")
	assert _persistent_fingerprint(before.cdml) == _persistent_fingerprint(MIXED_CDML)


#============================================
def test_dirty_state_tracks_saved_content_after_restore() -> None:
	"""Returning to saved content is clean even though restore creates a new revision."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	saved = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__dirty")
	assert session.is_dirty
	session.restore(target_revision=saved.revision, expected_revision=changed.revision)
	assert not session.is_dirty


#============================================
def test_restore_creates_forward_revision_with_requested_content() -> None:
	"""Undo-style restore records a forward revision rather than rewinding history."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	first = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__restore")
	restored = session.restore(target_revision=first.revision, expected_revision=changed.revision)
	assert restored.revision > changed.revision
	assert _persistent_fingerprint(restored.cdml) == _persistent_fingerprint(first.cdml)


#============================================
def test_minimum_history_capacity_keeps_immediate_redo_content() -> None:
	"""The minimum retained history permits immediate redo after an undo-style restore."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML, history_capacity=3)
	first = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__redo")
	restored = session.restore(target_revision=first.revision, expected_revision=changed.revision)
	redone = session.restore(target_revision=changed.revision, expected_revision=restored.revision)
	assert redone.revision > restored.revision
	assert _persistent_fingerprint(redone.cdml) == _persistent_fingerprint(changed.cdml)


#============================================
def test_failed_commit_after_restore_keeps_immediate_redo_content() -> None:
	"""A rejected candidate cannot discard the redo target retained by restore."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML, history_capacity=3)
	original = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__failed_redo")
	restored = session.restore(target_revision=original.revision, expected_revision=changed.revision)
	with pytest.raises(cdml_document.CDMLParseError):
		session.commit(expected_revision=restored.revision, complete_cdml="<not-cdml />")
	redone = session.restore(target_revision=changed.revision, expected_revision=restored.revision)
	assert _persistent_fingerprint(redone.cdml) == _persistent_fingerprint(changed.cdml)


#============================================
def test_mark_saved_after_restore_keeps_immediate_redo_content() -> None:
	"""Saving restored content cannot discard the redo target retained by restore."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML, history_capacity=3)
	original = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__saved_redo")
	restored = session.restore(target_revision=original.revision, expected_revision=changed.revision)
	saved = session.mark_saved(expected_revision=restored.revision)
	redone = session.restore(target_revision=changed.revision, expected_revision=saved.revision)
	assert _persistent_fingerprint(redone.cdml) == _persistent_fingerprint(changed.cdml)


#============================================
def test_normal_edit_after_restore_eventually_evicts_former_redo_content() -> None:
	"""A replacement edit clears redo protection, allowing its content to evict."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML, history_capacity=3)
	original = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__former_redo")
	session.restore(target_revision=original.revision, expected_revision=changed.revision)
	_commit_arrow(session, "__bkchem_new__replacement")
	later = _commit_arrow(session, "__bkchem_new__later")
	with pytest.raises(cdml_document.CDMLRevisionUnavailableError):
		session.restore(target_revision=changed.revision, expected_revision=later.revision)


#============================================
def test_capacity_keeps_saved_revision_and_evicts_intermediate_history() -> None:
	"""Bounded history protects saved content while making old intermediate revisions unavailable."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML, history_capacity=3)
	saved = session.snapshot()
	first = _commit_arrow(session, "__bkchem_new__first")
	_commit_arrow(session, "__bkchem_new__second")
	third = _commit_arrow(session, "__bkchem_new__third")
	with pytest.raises(cdml_document.CDMLRevisionUnavailableError):
		session.restore(target_revision=first.revision, expected_revision=third.revision)
	restored = session.restore(target_revision=saved.revision, expected_revision=third.revision)
	assert not restored.snapshot.is_dirty


#============================================
def test_history_capacity_requires_room_for_saved_and_current_revisions() -> None:
	"""A caller cannot configure history too small to protect its required revisions."""
	with pytest.raises(cdml_document.CDMLValidationError):
		cdml_document.CDMLDocumentSession.load(MIXED_CDML, history_capacity=2)


#============================================
def test_vendor_local_name_collisions_remain_opaque_and_roundtrip() -> None:
	"""Vendor arrows and bonds remain literal extension XML, not core CDML objects."""
	cdml_text = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:arrow id="__bkchem_new__opaque" />
 <vendor:bond start="missing" end="missing" />
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	assert _persistent_fingerprint(session.snapshot().cdml) == _persistent_fingerprint(cdml_text)


#============================================
def test_unknown_wrapper_keeps_no_namespace_core_lookalikes_opaque() -> None:
	"""An extension wrapper protects its no-namespace descendants from CDML rewrites."""
	cdml_text = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:wrap xmlns=""><arrow id="__bkchem_new__opaque" start="__bkchem_new__start" end="__bkchem_new__end" marker="__bkchem_new__marker">literal __bkchem_new__text <unknown flag="keep" /> tail</arrow></vendor:wrap>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	commit = session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	assert _persistent_fingerprint(session.snapshot().cdml) == _persistent_fingerprint(cdml_text)
	assert _persistent_fingerprint(commit.cdml) == _persistent_fingerprint(cdml_text)


#============================================
def test_unknown_wrapper_keeps_canonical_namespace_descendants_opaque() -> None:
	"""A canonical namespace below an extension wrapper does not regain core ownership."""
	cdml_text = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:wrap><bk:arrow xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml" id="__bkchem_new__opaque" start="__bkchem_new__start" end="__bkchem_new__end" marker="keep">literal __bkchem_new__text</bk:arrow></vendor:wrap>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	commit = session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	assert _persistent_fingerprint(session.snapshot().cdml) == _persistent_fingerprint(cdml_text)
	assert _persistent_fingerprint(commit.cdml) == _persistent_fingerprint(cdml_text)


#============================================
def test_opaque_descendant_duplicate_id_is_rejected_atomically() -> None:
	"""Opaque descendants reserve durable IDs even when their local names look core."""
	cdml_text = """\
<cdml xmlns:vendor="urn:vendor">
 <arrow id="core_arrow" />
 <vendor:wrap xmlns=""><arrow id="opaque_arrow" /></vendor:wrap>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _invalid_state_fingerprint(session)
	candidate = cdml_text.replace('id="opaque_arrow"', 'id="core_arrow"')
	with pytest.raises(cdml_document.CDMLValidationError):
		session.commit(expected_revision=session.revision, complete_cdml=candidate)
	assert _invalid_state_fingerprint(session) == before


#============================================
def test_vendor_cdml_root_is_not_a_cdml_document() -> None:
	"""A matching extension local name cannot impersonate the canonical CDML root."""
	with pytest.raises(cdml_document.CDMLParseError) as error:
		cdml_document.CDMLDocument.parse('<vendor:cdml xmlns:vendor="urn:vendor" />')
	assert type(error.value) is cdml_document.CDMLParseError


#============================================
def test_prefixed_core_query_receives_a_durable_backend_id() -> None:
	"""The backend allocates core provisional IDs without pinning its durable spelling."""
	provisional_id = "__bkchem_new__query"
	cdml_text = f"""\
<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml">
<bk:query id="{provisional_id}" />
</bk:cdml>
"""
	session = cdml_document.CDMLDocumentSession.load('<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml" />')
	commit = session.commit(expected_revision=session.revision, complete_cdml=cdml_text)
	assert commit.id_map[provisional_id] != provisional_id
	assert provisional_id not in commit.cdml


#============================================
def test_prefixed_core_and_vendor_local_name_collisions_have_distinct_opacity() -> None:
	"""Namespace ownership, rather than local name alone, identifies core CDML objects."""
	document = cdml_document.CDMLDocument.parse("""\
<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:vendor="urn:vendor">
 <bk:arrow id="arrow_1" />
 <vendor:arrow id="vendor_arrow_1" />
</bk:cdml>
""", validation="strict")
	core_arrow, vendor_arrow = document.objects()
	assert not core_arrow.opaque
	assert vendor_arrow.opaque


#============================================
def test_mark_saved_resets_baseline_and_old_content_becomes_dirty() -> None:
	"""Saving accepted content makes it clean, while restoring older content is dirty."""
	session = cdml_document.CDMLDocumentSession.load(MIXED_CDML)
	original = session.snapshot()
	changed = _commit_arrow(session, "__bkchem_new__saved")
	marked = session.mark_saved(expected_revision=changed.revision)
	assert marked.is_dirty is False and marked == session.snapshot()
	restored = session.restore(target_revision=original.revision, expected_revision=marked.revision)
	assert restored.snapshot.is_dirty
