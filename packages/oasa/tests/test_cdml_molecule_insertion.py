"""Behavioral tests for backend-only molecule proposal insertion."""

# Standard Library
import math

# PIP3 modules
from lxml import etree
import pytest

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.cdml_document as cdml_document
import oasa.cdml_writer as cdml_writer
import oasa.insertion_geometry
import oasa.molecule_lib
import oasa.safe_xml


#============================================
BASE_CDML = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:note id="opaque_1" marker="literal">keep</vendor:note>
 <text id="text_1"><ftext>existing</ftext></text>
 <molecule id="m_existing">
  <atom id="a_existing" name="C"><point x="0cm" y="0cm" /></atom>
 </molecule>
</cdml>
"""


#============================================
def _parse_xml(text: str) -> etree._Element:
	"""Parse test XML without entities, DTDs, network access, or recovery."""
	parser = etree.XMLParser(
		resolve_entities=False,
		no_network=True,
		load_dtd=False,
		dtd_validation=False,
		recover=False,
		huge_tree=False,
	)
	return etree.fromstring(text.encode("utf-8"), parser=parser)


#============================================
def _request(revision: int, proposal_cdml: str) -> cdml_document.CDMLMoleculeInsertionRequest:
	"""Build one plain-data insertion request with nonpersistent display metadata."""
	return cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=revision,
		proposal_cdml=proposal_cdml,
		label="Insert prepared molecules",
	)


#============================================
def _proposal(token_stem: str, *, molecule_count: int = 1) -> str:
	"""Return a complete, valid molecule-only proposal with one internal bond."""
	molecules = []
	for serial in range(1, molecule_count + 1):
		molecules.append(
			f'<bk:molecule id="__bkchem_new__{token_stem}_m{serial}">'
			f'<bk:atom id="__bkchem_new__{token_stem}_a{serial}a" name="C">'
			'<bk:point x="1cm" y="1cm" /></bk:atom>'
			f'<bk:atom id="__bkchem_new__{token_stem}_a{serial}b" name="O">'
			'<bk:point x="2cm" y="1cm" /></bk:atom>'
			f'<bk:bond id="__bkchem_new__{token_stem}_b{serial}" '
			f'start="__bkchem_new__{token_stem}_a{serial}a" '
			f'end="__bkchem_new__{token_stem}_a{serial}b" type="n1" />'
			'</bk:molecule>'
		)
	proposal = (
		'<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml">'
		+ ''.join(molecules)
		+ '</bk:cdml>'
	)
	return proposal


#============================================
def _direct_local_names(cdml_text: str) -> list[str]:
	"""Return direct persistent element names without asserting XML byte layout."""
	root = oasa.safe_xml.parse_xml_string(cdml_text)
	names = [child.tag.rsplit("}", 1)[-1] for child in root]
	return names


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str]:
	"""Return the immutable state facts expected after an atomic rejection."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml


#============================================
def _two_atom_molecule() -> oasa.molecule_lib.Molecule:
	"""Build one detached OASA molecule with deliberately durable-looking IDs."""
	mol = oasa.molecule_lib.Molecule()
	mol.id = "m9"
	first = oasa.atom_lib.Atom(symbol="C", coords=(0.0, 0.0, 0.0))
	second = oasa.atom_lib.Atom(symbol="O", coords=(40.0, 0.0, 0.0))
	first.id = "a9"
	second.id = "a10"
	mol.add_vertex(first)
	mol.add_vertex(second)
	bond = oasa.bond_lib.Bond(order=1, type="n")
	bond.id = "b9"
	mol.add_edge(first, second, bond)
	return mol


#============================================
def _atom_only_molecule(coords: tuple[float, float]) -> oasa.molecule_lib.Molecule:
	"""Build one detached atom-only proposal graph at a known coordinate."""
	mol = oasa.molecule_lib.Molecule()
	mol.add_vertex(oasa.atom_lib.Atom(symbol="C", coords=(*coords, 0.0)))
	return mol


#============================================
def _three_atom_extreme_molecule() -> oasa.molecule_lib.Molecule:
	"""Build a finite graph whose collective length sum would overflow."""
	mol = oasa.molecule_lib.Molecule()
	first = oasa.atom_lib.Atom(symbol="C", coords=(0.0, 0.0, 0.0))
	second = oasa.atom_lib.Atom(symbol="C", coords=(1e308, 0.0, 0.0))
	third = oasa.atom_lib.Atom(symbol="C", coords=(0.0, 0.0, 0.0))
	for atom in (first, second, third):
		mol.add_vertex(atom)
	for atom_one, atom_two in ((first, second), (second, third)):
		mol.add_edge(atom_one, atom_two, oasa.bond_lib.Bond(order=1, type="n"))
	return mol


#============================================
def _three_atom_subnormal_molecule() -> oasa.molecule_lib.Molecule:
	"""Build two smallest-subnormal real bonds without coordinate collapse."""
	minimum = math.nextafter(0.0, 1.0)
	mol = oasa.molecule_lib.Molecule()
	atoms = [
		oasa.atom_lib.Atom(symbol="C", coords=(coordinate, 0.0, 0.0))
		for coordinate in (0.0, minimum, 2.0 * minimum)
	]
	for atom in atoms:
		mol.add_vertex(atom)
	for atom_one, atom_two in ((atoms[0], atoms[1]), (atoms[1], atoms[2])):
		mol.add_edge(atom_one, atom_two, oasa.bond_lib.Bond(order=1, type="n"))
	return mol


#============================================
def _placement_facts(molecules: list) -> tuple[float | None, tuple[float, float]]:
	"""Measure collective real-bond mean and atom centroid after placement."""
	atoms = [atom for molecule in molecules for atom in molecule.vertices]
	lengths = [
		((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** 0.5
		for molecule in molecules for bond in molecule.edges
		for first, second in (bond.vertices,)
	]
	mean = sum(lengths) / len(lengths) if lengths else None
	return mean, (
		sum(atom.x for atom in atoms) / len(atoms),
		sum(atom.y for atom in atoms) / len(atoms),
	)


#============================================
def test_insertion_placement_scales_a_bonded_set_and_anchors_its_centroid() -> None:
	"""One collective bonded proposal adopts its captured scene geometry."""
	molecules = [_two_atom_molecule()]
	oasa.insertion_geometry.place_molecules_for_insertion(molecules, 25.0, (7.0, -3.0))

	mean, centroid = _placement_facts(molecules)
	assert (mean, *centroid) == pytest.approx((25.0, 7.0, -3.0))


#============================================
def test_insertion_placement_scales_disconnected_components_collectively() -> None:
	"""Disconnected components retain their transformed relative arrangement."""
	first = _two_atom_molecule()
	second = _two_atom_molecule()
	for atom in second.vertices:
		atom.x += 80.0
	molecules = [first, second]
	oasa.insertion_geometry.place_molecules_for_insertion(molecules, 20.0, (10.0, 15.0))

	mean, centroid = _placement_facts(molecules)
	assert (mean, *centroid) == pytest.approx((20.0, 10.0, 15.0))
	assert second.vertices[0].x - first.vertices[0].x == pytest.approx(40.0)


#============================================
def test_insertion_placement_anchors_an_atom_only_proposal() -> None:
	"""Atom-only proposals translate to the anchor without fabricated bonds."""
	molecules = [_atom_only_molecule((4.0, 9.0))]
	oasa.insertion_geometry.place_molecules_for_insertion(molecules, 40.0, (12.0, -5.0))

	assert _placement_facts(molecules) == (None, (12.0, -5.0))


#============================================
def test_insertion_placement_handles_finite_extreme_coordinate_aggregates() -> None:
	"""Finite extreme coordinates retain the requested collective geometry."""
	molecules = [_three_atom_extreme_molecule()]
	oasa.insertion_geometry.place_molecules_for_insertion(molecules, 40.0, (2000.0, 1500.0))

	mean, centroid = _placement_facts(molecules)
	assert (mean, *centroid) == pytest.approx((40.0, 2000.0, 1500.0))


#============================================
def test_insertion_placement_retains_smallest_subnormal_bonds() -> None:
	"""Subnormal real bonds retain their target length without zero collapse."""
	minimum = math.nextafter(0.0, 1.0)
	molecules = [_three_atom_subnormal_molecule()]
	oasa.insertion_geometry.place_molecules_for_insertion(molecules, minimum, (0.0, 0.0))

	assert [atom.x for atom in molecules[0].vertices] == [-minimum, 0.0, minimum]


#============================================
@pytest.mark.parametrize("case, message", (
	("empty", "at least one positioned atom"),
	("incomplete", "incomplete atom coordinates"),
	("nonfinite", "non-finite atom coordinates"),
	("zero_bond", "invalid bond length"),
))
def test_insertion_placement_rejects_invalid_graphs_atomically(
		case: str, message: str,
		) -> None:
	"""Malformed detached graphs fail before any atom coordinates are applied."""
	molecules = [] if case == "empty" else [_two_atom_molecule()]
	if case == "incomplete":
		molecules[0].vertices[0].x = None
	elif case == "nonfinite":
		molecules[0].vertices[0].x = float("inf")
	elif case == "zero_bond":
		molecules[0].vertices[1].x = 0.0
	original_coordinates = [(atom.x, atom.y) for molecule in molecules for atom in molecule.vertices]

	with pytest.raises(ValueError, match=message):
		oasa.insertion_geometry.place_molecules_for_insertion(molecules, 40.0, (7.0, -3.0))
	assert [
		(atom.x, atom.y) for molecule in molecules for atom in molecule.vertices
	] == original_coordinates


#============================================
@pytest.mark.parametrize("target, anchor", (
	(0.0, (1.0, 2.0)),
	(40.0, [1.0, 2.0]),
	(float("nan"), (1.0, 2.0)),
))
def test_insertion_placement_rejects_invalid_plain_boundary_values(
		target: object, anchor: object,
		) -> None:
	"""The public plain boundary rejects malformed placement inputs deterministically."""
	with pytest.raises(ValueError, match="Insertion (bond length|anchor)"):
		oasa.insertion_geometry.place_molecules_for_insertion(
			[_two_atom_molecule()], target, anchor,
		)


#============================================
def test_insertion_placement_rejects_huge_builtin_integer_target() -> None:
	"""An unrepresentable integer target fails through the public ValueError API."""
	with pytest.raises(ValueError, match="Insertion bond length"):
		oasa.insertion_geometry.place_molecules_for_insertion(
			[_two_atom_molecule()], 10 ** 1000, (7.0, -3.0),
		)


#============================================
def test_insertion_placement_rejects_huge_builtin_integer_coordinates_atomically() -> None:
	"""An unrepresentable integer coordinate retains the original detached graph."""
	molecules = [_two_atom_molecule()]
	molecules[0].vertices[0].x = 10 ** 1000
	original_coordinates = [(atom.x, atom.y) for atom in molecules[0].vertices]

	with pytest.raises(ValueError, match="non-finite atom coordinates"):
		oasa.insertion_geometry.place_molecules_for_insertion(molecules, 40.0, (7.0, -3.0))
	assert [(atom.x, atom.y) for atom in molecules[0].vertices] == original_coordinates


#============================================
def test_insertion_placement_rejects_late_nonrepresentable_outputs_atomically() -> None:
	"""A finite graph leaves no partial coordinate update when placement overflows."""
	molecules = [_atom_only_molecule((1e308, 0.0)), _atom_only_molecule((-1e308, 0.0))]
	original_coordinates = [
		(atom.x, atom.y) for molecule in molecules for atom in molecule.vertices
	]

	with pytest.raises(ValueError, match="non-finite atom coordinates"):
		oasa.insertion_geometry.place_molecules_for_insertion(molecules, 40.0, (1e308, 0.0))
	assert [
		(atom.x, atom.y) for molecule in molecules for atom in molecule.vertices
	] == original_coordinates


#============================================
def _proposal_molecule_facts(
		proposal: str,
		) -> tuple[tuple[str, tuple[str, ...], str, str, str], ...]:
	"""Return ordered molecule tokens and the atom tokens used by each bond."""
	root = _parse_xml(proposal)
	facts = []
	for molecule in root:
		atoms = [child for child in molecule if child.tag.rsplit("}", 1)[-1] == "atom"]
		bond = next(child for child in molecule if child.tag.rsplit("}", 1)[-1] == "bond")
		facts.append(
			(
				molecule.attrib["id"],
				tuple(atom.attrib["id"] for atom in atoms),
				bond.attrib["id"],
				bond.attrib["start"],
				bond.attrib["end"],
			)
		)
	return tuple(facts)


#============================================
def test_insert_molecules_preserves_existing_records_and_appends_proposal_order() -> None:
	"""Insertion retains opaque/presentation content and appends molecules in proposal order."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	proposal = _proposal("ordered", molecule_count=2)
	commit = session.insert_molecules(_request(session.revision, proposal))
	assert _direct_local_names(commit.cdml) == ["note", "text", "molecule", "molecule", "molecule"]
	assert 'marker="literal"' in commit.cdml


#============================================
def test_insertion_label_is_nonpersistent_operation_metadata() -> None:
	"""A caller display label cannot become persistent CDML content."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	commit = session.insert_molecules(_request(session.revision, _proposal("label")))
	assert "Insert prepared molecules" not in commit.cdml


#============================================
def test_insert_molecules_rewrites_bond_endpoints_and_returns_durable_mapping() -> None:
	"""A proposal exposes root-only and declaration-level durable mappings."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	result = session.insert_molecules(
		_request(session.revision, _proposal("mapping", molecule_count=2)),
	)
	root = _parse_xml(result.cdml)
	bond = next(element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "bond")
	assert (bond.attrib["start"], bond.attrib["end"]) == (
		result.id_map["__bkchem_new__mapping_a1a"],
		result.id_map["__bkchem_new__mapping_a1b"],
	)
	assert result.root_id_map == {
		"__bkchem_new__mapping_m1": result.id_map["__bkchem_new__mapping_m1"],
		"__bkchem_new__mapping_m2": result.id_map["__bkchem_new__mapping_m2"],
	}
	direct_molecule_ids = {
		element.attrib["id"]
		for element in root
		if element.tag.rsplit("}", 1)[-1] == "molecule"
	}
	assert set(result.root_id_map.values()) <= direct_molecule_ids
	assert all(
		not identifier.startswith("__bkchem_new__")
		for identifier in result.id_map.values()
	)
	with pytest.raises(TypeError):
		result.root_id_map["invalid"] = "invalid"


#============================================
def test_provisional_serializer_does_not_mutate_or_reuse_source_graph_ids() -> None:
	"""The OASA serializer makes a detached provisional proposal from one graph."""
	mol = _two_atom_molecule()
	before_ids = (
		mol.id,
		tuple(atom.id for atom in mol.vertices),
		tuple(bond.id for bond in mol.edges),
	)
	proposal = cdml_writer.molecules_to_insertion_proposal([mol], token_stem="writer")
	proposal_ids = [
		element.attrib["id"]
		for element in _parse_xml(proposal).iter()
		if "id" in element.attrib
	]
	assert before_ids == (
		mol.id,
		tuple(atom.id for atom in mol.vertices),
		tuple(bond.id for bond in mol.edges),
	)
	assert all(identifier.startswith("__bkchem_new__writer_") for identifier in proposal_ids)


#============================================
def test_provisional_serializer_orders_distinct_tokens_for_multiple_molecules() -> None:
	"""Two source molecules retain proposal order and use distinct token endpoints."""
	proposal = cdml_writer.molecules_to_insertion_proposal(
		[_two_atom_molecule(), _two_atom_molecule()],
		token_stem="multiple",
	)
	assert _proposal_molecule_facts(proposal) == (
		(
			"__bkchem_new__multiple_m1",
			("__bkchem_new__multiple_a1", "__bkchem_new__multiple_a2"),
			"__bkchem_new__multiple_b1",
			"__bkchem_new__multiple_a1",
			"__bkchem_new__multiple_a2",
		),
		(
			"__bkchem_new__multiple_m2",
			("__bkchem_new__multiple_a3", "__bkchem_new__multiple_a4"),
			"__bkchem_new__multiple_b2",
			"__bkchem_new__multiple_a3",
			"__bkchem_new__multiple_a4",
		),
	)


#============================================
@pytest.mark.parametrize(
	("molecules", "token_stem", "message"),
	(
		([], "producer", "requires at least one molecule"),
		([_two_atom_molecule()], "invalid stem", "token stem is invalid"),
	),
)
def test_provisional_serializer_rejects_invalid_public_inputs(
		molecules: list[oasa.molecule_lib.Molecule], token_stem: str, message: str,
		) -> None:
	"""Public producer validation reports empty input and invalid token stems."""
	with pytest.raises(ValueError, match=message):
		cdml_writer.molecules_to_insertion_proposal(molecules, token_stem=token_stem)


#============================================
def test_provisional_serializer_reports_writer_atom_mismatch(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A writer that omits an atom reaches the producer's explicit mismatch error."""
	original_writer = cdml_writer.write_cdml_molecule_element

	def writer_without_first_atom(
			molecule: oasa.molecule_lib.Molecule, **kwargs: object,
			) -> object:
		molecule_el = original_writer(molecule, **kwargs)
		first_atom = molecule_el.getElementsByTagName("atom")[0]
		molecule_el.removeChild(first_atom)
		return molecule_el

	monkeypatch.setattr(cdml_writer, "write_cdml_molecule_element", writer_without_first_atom)
	with pytest.raises(ValueError, match="could not serialize every atom"):
		cdml_writer.molecules_to_insertion_proposal([_two_atom_molecule()], token_stem="mismatch")


#============================================
def test_provisional_serializer_proposal_commits_as_one_backend_revision() -> None:
	"""A detached OASA molecule produces a complete proposal accepted by the session."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	proposal = cdml_writer.molecules_to_insertion_proposal(
		[_two_atom_molecule()],
		token_stem="producer",
	)
	commit = session.insert_molecules(_request(session.revision, proposal))
	assert commit.revision == 1
	root = _parse_xml(commit.cdml)
	bond = next(element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "bond")
	assert (bond.attrib["start"], bond.attrib["end"]) == (
		commit.id_map["__bkchem_new__producer_a1"],
		commit.id_map["__bkchem_new__producer_a2"],
	)


#============================================
@pytest.mark.parametrize(
	"proposal_cdml",
	(
		"<cdml />",
		"<cdml><text id=\"text_proposal\" /></cdml>",
		"<cdml><molecule id=\"m_client_supplied\" /></cdml>",
		(
			"<cdml><molecule id=\"__bkchem_new__duplicate\">"
			"<atom id=\"__bkchem_new__duplicate\" name=\"C\">"
			"<point x=\"0cm\" y=\"0cm\" /></atom></molecule></cdml>"
		),
		(
			"<cdml><molecule id=\"__bkchem_new__dangling_m\">"
			"<atom id=\"__bkchem_new__dangling_a\" name=\"C\">"
			"<point x=\"0cm\" y=\"0cm\" /></atom>"
			"<bond id=\"__bkchem_new__dangling_b\" "
			"start=\"__bkchem_new__dangling_a\" "
			"end=\"__bkchem_new__missing\" type=\"n1\" />"
			"</molecule></cdml>"
		),
	),
)
def test_invalid_molecule_proposals_reject_atomically(proposal_cdml: str) -> None:
	"""Malformed bounded content cannot change the session or consume its tokens."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = _state(session)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_molecules(_request(session.revision, proposal_cdml))
	assert _state(session) == before


#============================================
def test_malformed_molecule_proposal_rejects_atomically() -> None:
	"""A non-XML proposal reports the public parse failure without changing state."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = _state(session)
	with pytest.raises(cdml_document.CDMLParseError):
		session.insert_molecules(_request(session.revision, "<cdml>"))
	assert _state(session) == before


#============================================
def test_rejected_proposal_does_not_consume_its_provisional_tokens() -> None:
	"""A corrected retry may use the token from an earlier rejected proposal."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	broken = _proposal("retry").replace('__bkchem_new__retry_a1b', '__bkchem_new__missing', 1)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_molecules(_request(session.revision, broken))
	commit = session.insert_molecules(_request(session.revision, _proposal("retry")))
	assert "__bkchem_new__retry_m1" in commit.id_map


#============================================
def test_accepted_proposal_tokens_are_single_use() -> None:
	"""A successfully inserted proposal cannot be submitted a second time."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	proposal = _proposal("once")
	session.insert_molecules(_request(session.revision, proposal))
	before = _state(session)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.insert_molecules(_request(session.revision, proposal))
	assert _state(session) == before


#============================================
def test_stale_molecule_proposal_is_typed_and_atomic() -> None:
	"""A stale proposal is not rebased, reconstructed, or silently resubmitted."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	stale_revision = session.revision
	session.insert_molecules(_request(stale_revision, _proposal("first")))
	before = _state(session)
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.insert_molecules(_request(stale_revision, _proposal("stale")))
	assert _state(session) == before
