"""Behavioral tests for CDML preservation-only container ownership."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.cdml_xml


#============================================
def _candidate_with_preservation_only_payloads() -> str:
	"""Return one candidate with literal CDML-looking payloads and one real arrow."""
	return """\
<cdml>
 <molecule id="m1">
  <display-form><atom id="__bkchem_new__display_atom" /><bond
   id="__bkchem_new__display_bond" start="__bkchem_new__display_atom"
   end="__bkchem_new__display_atom" /></display-form>
  <user-data><atom id="__bkchem_new__user_atom" /><bond
   id="__bkchem_new__user_bond" start="__bkchem_new__user_atom"
   end="__bkchem_new__user_atom" /></user-data>
 </molecule>
 <molecule id="__bkchem_new__core_molecule">
  <atom id="__bkchem_new__core_atom_one" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="__bkchem_new__core_atom_two" name="O"><point x="1cm" y="0cm" /></atom>
  <bond id="__bkchem_new__core_bond" start="__bkchem_new__core_atom_one"
   end="__bkchem_new__core_atom_two" type="n1" />
 </molecule>
 <external-data id="__bkchem_new__external"><atom
  id="__bkchem_new__external_atom" /><bond id="__bkchem_new__external_bond"
  start="__bkchem_new__external_atom" end="__bkchem_new__external_atom" /></external-data>
 <arrow id="__bkchem_new__arrow"><point x="0cm" y="0cm" /><point x="1cm" y="0cm" /></arrow>
</cdml>
"""


#============================================
def _payload_with_literal_id(container_name: str, identifier: str) -> str:
	"""Return one preservation-only container holding one literal identifier."""
	if container_name == "external-data":
		return f'<external-data id="{identifier}"><atom id="nested_{identifier}" /></external-data>'
	return (
		f'<molecule id="m1"><{container_name}><atom id="{identifier}" />'
		f'</{container_name}></molecule>'
	)


#============================================
def _semantic_fingerprint(payload: str) -> tuple:
	"""Inspect complete CDML through the public hardened semantic boundary."""
	document = (
		'<cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml">'
		f'<molecule id="m1"><display-form>{payload}</display-form></molecule>'
		'</cdml>'
	)
	return oasa.cdml_xml.inspect_cdml_xml(document.encode("utf-8")).semantic_fingerprint


#============================================
def test_preservation_only_payloads_stay_literal_while_direct_core_records_map() -> None:
	"""Opaque payload tokens remain literal while direct core records map and rewrite."""
	candidate = _candidate_with_preservation_only_payloads()
	baseline = candidate
	for token, durable_id in (
		("__bkchem_new__core_molecule", "m2"),
		("__bkchem_new__core_atom_one", "a2"),
		("__bkchem_new__core_atom_two", "a3"),
		("__bkchem_new__core_bond", "b2"),
		("__bkchem_new__arrow", "arrow_initial"),
	):
		baseline = baseline.replace(token, durable_id)
	session = cdml_document.CDMLDocumentSession.load(baseline)
	commit = session.commit(expected_revision=session.revision, complete_cdml=candidate)
	literal_values = (
		'__bkchem_new__display_atom', '__bkchem_new__display_bond',
		'__bkchem_new__user_atom', '__bkchem_new__user_bond',
		'__bkchem_new__external', '__bkchem_new__external_atom',
		'__bkchem_new__external_bond',
	)

	assert set(commit.id_map) == {
		"__bkchem_new__arrow", "__bkchem_new__core_atom_one",
		"__bkchem_new__core_atom_two", "__bkchem_new__core_bond",
		"__bkchem_new__core_molecule",
	}
	assert (
		all(value in commit.cdml for value in literal_values)
		and f'start="{commit.id_map["__bkchem_new__core_atom_one"]}"' in commit.cdml
		and f'end="{commit.id_map["__bkchem_new__core_atom_two"]}"' in commit.cdml
	)


#============================================
@pytest.mark.parametrize("container_name", ("display-form", "user-data", "external-data"))
def test_preservation_only_literal_ids_reserve_durable_allocation_names(
		container_name: str,
		) -> None:
	"""Each container's literal ID prevents a direct declaration from taking that name."""
	candidate = (
		'<cdml>' + _payload_with_literal_id(container_name, "a1")
		+ '<arrow id="__bkchem_new__arrow"><point x="0cm" y="0cm" />'
		'<point x="1cm" y="0cm" /></arrow></cdml>'
	)
	baseline = candidate.replace('__bkchem_new__arrow', 'arrow_initial')
	session = cdml_document.CDMLDocumentSession.load(baseline)
	commit = session.commit(expected_revision=session.revision, complete_cdml=candidate)

	assert (commit.id_map["__bkchem_new__arrow"], 'id="a1"' in commit.cdml) == ("a2", True)


#============================================
def test_duplicate_literal_ids_in_preservation_only_containers_reject_atomically() -> None:
	"""Literal IDs in all three containers share one collision namespace."""
	candidate = """\
<cdml>
 <molecule id="m1"><display-form><atom id="literal" /></display-form>
  <user-data><atom id="literal" /></user-data></molecule>
 <external-data id="literal" />
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load("<cdml />")
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLValidationError, match="duplicate CDML id"):
		session.commit(expected_revision=before.revision, complete_cdml=candidate)
	assert session.snapshot() == before


#============================================
def test_semantic_inspection_preserves_lexical_payload_names_under_display_form() -> None:
	"""A CDML-looking payload child remains opaque rather than core-normalized."""
	canonical_child = '<bk:atom id="payload" />'
	legacy_child = '<atom id="payload" />'

	assert _semantic_fingerprint(canonical_child) != _semantic_fingerprint(legacy_child)
