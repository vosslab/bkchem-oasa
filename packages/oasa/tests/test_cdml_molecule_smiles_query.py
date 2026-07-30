"""Behavioral tests for backend-owned CDML molecule SMILES queries."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.cdml_writer


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m_selected">
  <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="O"><point x="1cm" y="0cm" /></atom>
  <bond id="b1" start="a1" end="a2" type="n1" />
 </molecule>
 <arrow id="arrow_keep"><point x="0cm" y="2cm" /><point x="1cm" y="2cm" /></arrow>
 <v:molecule id="m_opaque"><v:atom id="a_hidden" name="C"><v:point x="0cm" y="0cm" /></v:atom></v:molecule>
 <v:opaque><molecule id="m_nested"><atom id="a_nested" name="C"><point x="0cm" y="0cm" /></atom></molecule></v:opaque>
</cdml>
"""

_FOREIGN_CHEMISTRY_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m_selected">
  <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
  <bond id="b_direct" start="a1" end="a2" type="n1" />
  <v:opaque>
   <v:atom id="a_hidden" name="O"><v:point x="2cm" y="0cm" /></v:atom>
   <v:bond id="b_hidden" start="a2" end="a_hidden" type="n1" />
  </v:opaque>
 </molecule>
</cdml>
"""

_FOREIGN_DIRECT_RECORDS_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m_selected">
  <v:atom id="a_foreign" name="O"><v:point x="80cm" y="80cm" /></v:atom>
  <atom id="a1" name="C"><v:point x="99cm" y="99cm" /><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
  <v:bond id="b_foreign" start="a1" end="a_foreign" type="n1" />
  <bond id="b_direct" start="a1" end="a2" type="n1" />
 </molecule>
</cdml>
"""

_LEGACY_NAMESPACE_FREE_CDML = """\
<cdml version="26.02">
 <molecule id="m_legacy">
  <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
  <bond id="b1" start="a1" end="a2" type="n1" />
 </molecule>
</cdml>
"""

_LEGACY_WRAPPER_CDML = """\
<cdml version="26.02">
 <molecule id="m_wrapped">
  <wrapper><atom id="a_wrapped" name="C"><point x="3cm" y="4cm" /></atom></wrapper>
 </molecule>
</cdml>
"""


#============================================
def _styled_tetrahedral_cdml(
		style: str, bond_start: str,
		substituents: tuple[str, str, str, str] = ("F", "Cl", "Br", "I"),
		bond_order: int = 1, target_x: float = 1.0,
		) -> str:
	"""Build one direct-core CDML tetrahedral depiction with a styled C-F bond."""
	fluorine, chlorine, bromine, iodine = substituents
	cdml_text = f"""\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="m_stereo">
  <atom id="c" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="f" name="{fluorine}"><point x="{target_x}cm" y="0cm" /></atom>
  <atom id="cl" name="{chlorine}"><point x="-0.5cm" y="0.9cm" /></atom>
  <atom id="br" name="{bromine}"><point x="-0.5cm" y="-0.9cm" /></atom>
  <atom id="i" name="{iodine}"><point x="0cm" y="1.5cm" /></atom>
  <bond id="b_stereo" start="{bond_start}" end="{'f' if bond_start == 'c' else 'c'}" type="{style}{bond_order}" />
  <bond id="b_cl" start="c" end="cl" type="n1" />
  <bond id="b_br" start="c" end="br" type="n1" />
  <bond id="b_i" start="c" end="i" type="n1" />
 </molecule>
</cdml>
"""
	return cdml_text


#============================================
def _query(revision: object, molecule_id: object) -> object:
	"""Build one plain query, including deliberately invalid runtime shapes."""
	return cdml_document.CDMLMoleculeSmilesQuery(revision, molecule_id)


#============================================
def _opaque_record(cdml_text: str, identifier: str) -> object:
	"""Return one opaque record after the owning CDML parser accepted the text."""
	document = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	return next(record for record in document.objects() if record.identifier == identifier)


#============================================
def _parsed_root_molecule(cdml_text: str, identifier: str) -> object:
	"""Return one parsed root molecule element for legacy decoder compatibility tests."""
	document = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	root = document._dom_document.documentElement
	molecule = next(
			child for child in root.childNodes
			if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") == identifier
		)
	return molecule


#============================================
def test_molecule_smiles_query_observes_one_authoritative_snapshot_without_mutation() -> None:
	"""A molecule query leaves its revision, dirty state, and persistent siblings intact."""
	session = cdml_document.CDMLDocumentSession.load_imported(_CDML)
	before = session.snapshot()
	result = session.query_molecule_smiles(_query(before.revision, "m_selected"))
	after = session.snapshot()

	assert (result.revision, result.molecule_id, result.smiles, after) == (
		before.revision, "m_selected", "CO", before,
	)
	assert _opaque_record(after.cdml, "m_opaque").opaque


#============================================
def test_molecule_smiles_query_ignores_foreign_descendant_chemistry() -> None:
	"""A query reads direct core chemistry and retains nested XML unchanged."""
	session = cdml_document.CDMLDocumentSession.load_imported(_FOREIGN_CHEMISTRY_CDML)
	before = session.snapshot()

	result = session.query_molecule_smiles(_query(before.revision, "m_selected"))

	assert result.smiles == "CC"
	assert session.snapshot() == before


#============================================
def test_molecule_smiles_query_uses_direct_core_records_and_canonical_points() -> None:
	"""The authoritative query ignores direct foreign lookalikes and foreign points."""
	session = cdml_document.CDMLDocumentSession.load_imported(_FOREIGN_DIRECT_RECORDS_CDML)
	before = session.snapshot()
	result = session.query_molecule_smiles(_query(before.revision, "m_selected"))
	molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(
		_parsed_root_molecule(_FOREIGN_DIRECT_RECORDS_CDML, "m_selected"),
	)
	atom = next(atom for atom in molecule.vertices if atom.id == "a1")

	assert result.smiles == "CC"
	assert atom.coords == pytest.approx((0.0, 0.0, 0.0))


#============================================
def test_molecule_smiles_query_supports_namespace_free_legacy_direct_core_cdml() -> None:
	"""A namespace-free legacy root remains a direct-core query compatibility path."""
	session = cdml_document.CDMLDocumentSession.load(_LEGACY_NAMESPACE_FREE_CDML)
	result = session.query_molecule_smiles(_query(session.revision, "m_legacy"))

	assert result.smiles == "CC"


#============================================
def test_legacy_molecule_decoder_keeps_descendant_compatibility_outside_direct_core() -> None:
	"""Legacy decode finds wrapped chemistry while direct-core decoding excludes it."""
	molecule_element = _parsed_root_molecule(_LEGACY_WRAPPER_CDML, "m_wrapped")
	legacy_molecule = oasa.cdml_writer.read_cdml_molecule_element(molecule_element)
	direct_core_molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(molecule_element)
	legacy_atom = next(iter(legacy_molecule.vertices))

	assert legacy_atom.coords == pytest.approx((
		3 * oasa.cdml_writer.POINTS_PER_CM,
		4 * oasa.cdml_writer.POINTS_PER_CM,
		0.0,
	))
	assert tuple(direct_core_molecule.vertices) == ()


#============================================
@pytest.mark.parametrize(("style", "bond_start", "expected_smiles"), (
	("w", "c", "F[C@](Cl)(Br)I"),
	("h", "c", "F[C@@](Cl)(Br)I"),
	("w", "f", "F[C@@](Cl)(Br)I"),
	("h", "f", "F[C@](Cl)(Br)I"),
))
def test_molecule_smiles_query_maps_directed_stereo_depiction_without_mutation(
		style: str, bond_start: str, expected_smiles: str,
		) -> None:
	"""A directed wedge/hash emits its corresponding canonical isomeric SMILES."""
	session = cdml_document.CDMLDocumentSession.load(_styled_tetrahedral_cdml(style, bond_start))
	before = session.snapshot()
	result = session.query_molecule_smiles(_query(before.revision, "m_stereo"))

	assert result.smiles == expected_smiles
	assert session.snapshot() == before


#============================================
def test_molecule_smiles_query_maps_an_implicit_hydrogen_tetrahedral_center() -> None:
	"""A degree-three stereo center retains its implicit hydrogen in isomeric SMILES."""
	cdml_text = _styled_tetrahedral_cdml("w", "c").replace(
		'<bond id="b_i" start="c" end="i" type="n1" />', "",
	).replace('<atom id="i" name="I"><point x="0cm" y="1.5cm" /></atom>', "")
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.query_molecule_smiles(_query(session.revision, "m_stereo"))

	assert result.smiles == "F[C@H](Cl)Br"


#============================================
@pytest.mark.parametrize("cdml_text", (
	_styled_tetrahedral_cdml("w", "c", substituents=("F", "F", "Br", "I")),
	_styled_tetrahedral_cdml("w", "c", bond_order=2),
	_styled_tetrahedral_cdml("w", "c", target_x=0.0),
	_styled_tetrahedral_cdml("w", "c", target_x=float("nan")),
))
def test_molecule_smiles_query_rejects_unrepresentable_styled_stereo_without_mutation(
		cdml_text: str,
		) -> None:
	"""Styled stereo fails atomically when CDML cannot yield an isomeric result."""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLMoleculeSmilesUnavailableError) as exc_info:
		session.query_molecule_smiles(_query(before.revision, "m_stereo"))

	assert isinstance(exc_info.value.__cause__, ValueError)
	assert session.snapshot() == before


#============================================
def test_molecule_smiles_query_rejects_any_unrepresentable_styled_component_atomically() -> None:
	"""One valid wedge cannot mask a second styled component without tetrahedral identity."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="m_stereo">
  <atom id="c_valid" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="f_valid" name="F"><point x="1cm" y="0cm" /></atom>
  <atom id="cl_valid" name="Cl"><point x="-0.5cm" y="0.9cm" /></atom>
  <atom id="br_valid" name="Br"><point x="-0.5cm" y="-0.9cm" /></atom>
  <atom id="i_valid" name="I"><point x="0cm" y="1.5cm" /></atom>
  <bond id="b_valid_stereo" start="c_valid" end="f_valid" type="w1" />
  <bond id="b_valid_cl" start="c_valid" end="cl_valid" type="n1" />
  <bond id="b_valid_br" start="c_valid" end="br_valid" type="n1" />
  <bond id="b_valid_i" start="c_valid" end="i_valid" type="n1" />
  <atom id="c_invalid" name="C"><point x="4cm" y="0cm" /></atom>
  <atom id="f_invalid_one" name="F"><point x="5cm" y="0cm" /></atom>
  <atom id="f_invalid_two" name="F"><point x="3.5cm" y="0.9cm" /></atom>
  <atom id="br_invalid" name="Br"><point x="3.5cm" y="-0.9cm" /></atom>
  <atom id="i_invalid" name="I"><point x="4cm" y="1.5cm" /></atom>
  <bond id="b_invalid_stereo" start="c_invalid" end="f_invalid_one" type="w1" />
  <bond id="b_invalid_f" start="c_invalid" end="f_invalid_two" type="n1" />
  <bond id="b_invalid_br" start="c_invalid" end="br_invalid" type="n1" />
  <bond id="b_invalid_i" start="c_invalid" end="i_invalid" type="n1" />
 </molecule>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLMoleculeSmilesUnavailableError) as exc_info:
		session.query_molecule_smiles(_query(before.revision, "m_stereo"))

	assert isinstance(exc_info.value.__cause__, ValueError)
	assert session.snapshot() == before


#============================================
def test_molecule_smiles_query_rejects_non_tetrahedral_styled_bond_without_mutation() -> None:
	"""A wedge from a non-tetrahedral direct-core atom has no SMILES stereo meaning."""
	cdml_text = _styled_tetrahedral_cdml("w", "c").replace(
		'<bond id="b_i" start="c" end="i" type="n1" />', "",
	).replace('<bond id="b_br" start="c" end="br" type="n1" />', "")
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLMoleculeSmilesUnavailableError):
		session.query_molecule_smiles(_query(before.revision, "m_stereo"))

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("request_builder", (
	lambda revision: object(),
	lambda revision: _query(True, "m_selected"),
	lambda revision: _query(revision, ""),
	lambda revision: _query(revision, "missing"),
	lambda revision: _query(revision, "arrow_keep"),
	lambda revision: _query(revision, "m_opaque"),
	lambda revision: _query(revision, "m_nested"),
))
def test_molecule_smiles_query_rejects_invalid_or_nonroot_targets_atomically(
		request_builder: object,
		) -> None:
	"""Malformed, missing, wrong-kind, opaque, and nested queries leave state intact."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLValidationError):
		session.query_molecule_smiles(request_builder(before.revision))

	assert session.snapshot() == before


#============================================
def test_molecule_smiles_query_rejects_a_stale_snapshot_request_atomically() -> None:
	"""A stale query cannot observe or alter a newer authoritative revision."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	stale = _query(session.revision, "m_selected")
	session.commit(expected_revision=session.revision, complete_cdml=session.snapshot().cdml)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.query_molecule_smiles(stale)

	assert session.snapshot() == before


#============================================
def test_molecule_smiles_query_reports_unsupported_chemistry_without_mutation() -> None:
	"""A compatible but nonconvertible molecule produces one typed query failure."""
	session = cdml_document.CDMLDocumentSession.load(
		_CDML.replace('name="C"', 'name="Unobtainium"', 1),
	)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLMoleculeSmilesUnavailableError) as exc_info:
		session.query_molecule_smiles(_query(before.revision, "m_selected"))

	assert isinstance(exc_info.value.__cause__, ValueError)
	assert session.snapshot() == before
