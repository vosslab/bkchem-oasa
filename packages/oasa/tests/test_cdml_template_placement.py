"""Behavioral tests for backend-owned system-template placement preparation."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml
import oasa.template_placement


POINTS_PER_CM = 72.0 / 2.54
BASE_CDML = """
<cdml xmlns:vendor="urn:vendor">
 <vendor:note id="opaque_1" marker="literal">keep<vendor:detail role="preserve">payload</vendor:detail>tail</vendor:note>
 <text id="text_1"><ftext>unrelated</ftext></text>
</cdml>
"""


#============================================
def _prepared(name: str, anchor: tuple[float, float], token_stem: str) -> object:
	"""Prepare one plain system-template insertion request."""
	request = oasa.template_placement.CDMLTemplatePlacementRequest(
		template_name=name,
		anchor=anchor,
		token_stem=token_stem,
	)
	prepared = oasa.template_placement.prepare_template_molecule_insertion(request)
	return prepared


#============================================
def _local_name(element: object) -> str:
	"""Return one namespace-neutral CDML local element name."""
	name = str(element.tag)
	local_name = name.rsplit("}", 1)[-1]
	return local_name


#============================================
def _compatibility_root(cdml: str) -> object:
	"""Enter complete CDML through its boundary before DOM inspection."""
	oasa.cdml_document.CDMLDocument.parse(cdml, validation="compat")
	return oasa.safe_xml.parse_xml_string(cdml)


#============================================
def _element_signature(element: object) -> tuple:
	"""Return the meaningful opaque XML content needed for preservation checks."""
	return (
		_local_name(element),
		tuple(sorted(element.attrib.items())),
		element.text,
		tuple((_element_signature(child), child.tail) for child in element),
	)


#============================================
def _proposal_atom_coordinates(proposal_cdml: str) -> list[tuple[float, float]]:
	"""Read positioned proposal atoms through the hardened CDML XML boundary."""
	root = _compatibility_root(proposal_cdml)
	coordinates = []
	for element in root.iter():
		if _local_name(element) != "atom":
			continue
		point = next(child for child in element if _local_name(child) == "point")
		x_value = float(point.attrib["x"].removesuffix("cm")) * POINTS_PER_CM
		y_value = float(point.attrib["y"].removesuffix("cm")) * POINTS_PER_CM
		coordinates.append((x_value, y_value))
	return coordinates


#============================================
def _proposal_mean_bond_length(proposal_cdml: str) -> float | None:
	"""Measure the serialized proposal's real bond geometry in scene points."""
	root = _compatibility_root(proposal_cdml)
	coordinates_by_id = {}
	for element in root.iter():
		if _local_name(element) != "atom":
			continue
		point = next(child for child in element if _local_name(child) == "point")
		coordinates_by_id[element.attrib["id"]] = (
			float(point.attrib["x"].removesuffix("cm")) * POINTS_PER_CM,
			float(point.attrib["y"].removesuffix("cm")) * POINTS_PER_CM,
		)
	lengths = []
	for element in root.iter():
		if _local_name(element) != "bond":
			continue
		start_x, start_y = coordinates_by_id[element.attrib["start"]]
		end_x, end_y = coordinates_by_id[element.attrib["end"]]
		lengths.append(math.hypot(start_x - end_x, start_y - end_y))
	mean = math.fsum(lengths) / len(lengths) if lengths else None
	return mean


#============================================
def _proposal_ids(proposal_cdml: str) -> list[str]:
	"""Return serialized IDs from a complete detached proposal."""
	root = _compatibility_root(proposal_cdml)
	identifiers = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
	return identifiers


#============================================
def test_bonded_catalog_template_has_visible_scale_and_requested_centroid() -> None:
	"""A normal catalog template keeps the established scale and finite anchor."""
	prepared = _prepared("Et", (125.0, -35.0), "ethyl")
	coordinates = _proposal_atom_coordinates(prepared.proposal_cdml)
	centroid = tuple(math.fsum(axis) / len(coordinates) for axis in zip(*coordinates))

	assert (_proposal_mean_bond_length(prepared.proposal_cdml), *centroid) == pytest.approx(
		(40.0, 125.0, -35.0), abs=0.02,
	)


#============================================
def test_single_atom_catalog_template_anchors_without_inventing_scale() -> None:
	"""A bond-free catalog template remains a translated one-atom proposal."""
	prepared = _prepared("Me", (-12.5, 88.0), "methyl")

	coordinates = _proposal_atom_coordinates(prepared.proposal_cdml)
	assert _proposal_mean_bond_length(prepared.proposal_cdml) is None
	assert coordinates[0] == pytest.approx((-12.5, 88.0), abs=0.02)


#============================================
def test_system_template_catalog_returns_immutable_usable_selection_names() -> None:
	"""Catalog selections are immutable plain names accepted by OASA preparation."""
	names = oasa.template_placement.system_template_names()
	prepared = _prepared(names[0], (0.0, 0.0), "catalog")

	assert isinstance(names, tuple) and "<molecule" in prepared.proposal_cdml


#============================================
def test_prepared_proposal_contains_only_provisional_detached_records() -> None:
	"""Preparation creates one isolated molecule proposal with request-local IDs."""
	prepared = _prepared("Et", (0.0, 0.0), "local")
	root = _compatibility_root(prepared.proposal_cdml)

	assert ([_local_name(child) for child in root], all(identifier.startswith("__bkchem_new__local_") for identifier in _proposal_ids(prepared.proposal_cdml))) == (["molecule"], True)


#============================================
@pytest.mark.parametrize("placement_request", (
	oasa.template_placement.CDMLTemplatePlacementRequest("missing", (0.0, 0.0), "valid"),
	oasa.template_placement.CDMLTemplatePlacementRequest("Me", (float("nan"), 0.0), "valid"),
	oasa.template_placement.CDMLTemplatePlacementRequest("Me", (0.0, 0.0), "invalid stem"),
))
def test_invalid_template_placement_input_has_one_typed_failure(
		placement_request: oasa.template_placement.CDMLTemplatePlacementRequest,
		) -> None:
	"""Unknown names and malformed scalar input retain one typed public error."""
	with pytest.raises(oasa.template_placement.TemplatePlacementError):
		oasa.template_placement.prepare_template_molecule_insertion(placement_request)


#============================================
def test_prepared_template_insertion_preserves_unrelated_root_and_maps_durable_ids() -> None:
	"""A normal session insertion preserves roots while assigning durable IDs."""
	session = oasa.cdml_document.CDMLDocumentSession.load(BASE_CDML)
	prepared = _prepared("Et", (30.0, 40.0), "accepted")
	provisional_ids = _proposal_ids(prepared.proposal_cdml)
	commit = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=session.revision,
		proposal_cdml=prepared.proposal_cdml,
		label=prepared.label,
	))
	accepted = oasa.cdml_document.CDMLDocument.parse(commit.cdml, validation="compat")
	root = _compatibility_root(commit.cdml)
	opaque_root = next(child for child in root if _local_name(child) == "note")
	mapped_ids = tuple(commit.id_map[identifier] for identifier in provisional_ids)
	mapped_root_ids = tuple(
		commit.id_map[identifier] for identifier in prepared.root_provisional_molecule_ids
	)

	assert (
		[_local_name(child) for child in root],
		_element_signature(opaque_root),
		all(accepted.find_by_id(identifier) is not None for identifier in mapped_ids),
		all(
			accepted.find_by_id(identifier).local_name == "molecule"
			for identifier in mapped_root_ids
		),
		all(not identifier.startswith("__bkchem_new__") for identifier in mapped_ids),
	) == (
		["note", "text", "molecule"],
		("note", (("id", "opaque_1"), ("marker", "literal")), "keep", ((("detail", (("role", "preserve"),), "payload", ()), "tail"),)),
		True,
		True,
		True,
	)
