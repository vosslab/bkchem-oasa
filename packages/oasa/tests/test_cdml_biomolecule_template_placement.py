"""Backend-only tests for packaged biomolecule template placement."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.biomolecule_template_placement
import oasa.cdml_document
import oasa.safe_xml


_CATALOG = oasa.biomolecule_template_placement.biomolecule_template_catalog()
_BASE_CDML = """
<cdml xmlns:vendor="urn:vendor" version="26.07">
 <vendor:note id="opaque_1" marker="literal">keep<vendor:detail>payload</vendor:detail>tail</vendor:note>
 <text id="text_1"><ftext>unrelated</ftext></text>
</cdml>
"""
_POINTS_PER_CM = 72.0 / 2.54


#============================================
def _local_name(element: object) -> str:
	"""Return one namespace-neutral XML element name."""
	return str(element.tag).rsplit("}", 1)[-1]


#============================================
def _proposal_root(prepared: object) -> object:
	"""Enter proposal XML through the public CDML boundary."""
	oasa.cdml_document.CDMLDocument.parse(prepared.proposal_cdml, validation="compat")
	return oasa.safe_xml.parse_xml_string(prepared.proposal_cdml)


#============================================
def _coordinates_by_id(prepared: object) -> dict[str, tuple[float, float]]:
	"""Read serialized proposal atom coordinates as scene points."""
	coordinates = {}
	for element in _proposal_root(prepared).iter():
		if _local_name(element) != "atom":
			continue
		point = next(child for child in element if _local_name(child) == "point")
		coordinates[element.attrib["id"]] = (
			float(point.attrib["x"].removesuffix("cm")) * _POINTS_PER_CM,
			float(point.attrib["y"].removesuffix("cm")) * _POINTS_PER_CM,
		)
	return coordinates


#============================================
def _mean_bond_length(prepared: object) -> float:
	"""Measure the serialized detached proposal's mean bond length."""
	coordinates = _coordinates_by_id(prepared)
	lengths = []
	for element in _proposal_root(prepared).iter():
		if _local_name(element) != "bond":
			continue
		start = coordinates[element.attrib["start"]]
		end = coordinates[element.attrib["end"]]
		lengths.append(math.dist(start, end))
	if not lengths:
		raise AssertionError("Representative biomolecule proposal has no bonds")
	return math.fsum(lengths) / len(lengths)


#============================================
def _prepared(
		catalog_key: str, anchor: tuple[float, float], token_stem: str,
		) -> object:
	"""Prepare one OASA-owned packaged molecule insertion."""
	request = oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementRequest(
		catalog_key, anchor, token_stem,
	)
	return oasa.biomolecule_template_placement.prepare_biomolecule_template_insertion(request)


#============================================
def test_biomolecule_catalog_exposes_stable_semantic_descriptor() -> None:
	"""A known packaged entry keeps its durable frontend-neutral identity."""
	descriptor = next(entry for entry in _CATALOG if entry.name == "alpha-D-glucopyranose")
	assert descriptor == oasa.biomolecule_template_placement.BiomoleculeTemplateDescriptor(
		"carbs/monosaccharides/alpha-D-glucopyranose", "carbs", "monosaccharides",
		"alpha-D-glucopyranose", "Glc",
	)


#============================================
@pytest.mark.parametrize("descriptor", _CATALOG, ids=lambda item: item.catalog_key)
def test_each_packaged_entry_prepares_one_detached_molecule(descriptor: object) -> None:
	"""Every shipped entry reaches the public molecule-only CDML boundary."""
	prepared = _prepared(descriptor.catalog_key, (15.0, 25.0), "catalog-test")
	proposal = oasa.cdml_document.CDMLDocument.parse(prepared.proposal_cdml, validation="compat")
	record, = tuple(proposal.objects())
	declared_root, = prepared.root_provisional_molecule_ids
	assert (record.local_name, record.identifier) == ("molecule", declared_root)


#============================================
def test_representative_biomolecule_uses_requested_scale_and_anchor() -> None:
	"""OASA keeps a bonded template at 40 points and at the requested centroid."""
	prepared = _prepared("carbs/monosaccharides/alpha-D-glucopyranose", (125.0, -35.0), "geometry")
	coordinates = tuple(_coordinates_by_id(prepared).values())
	centroid = tuple(math.fsum(axis) / len(coordinates) for axis in zip(*coordinates))
	assert (_mean_bond_length(prepared), *centroid) == pytest.approx((40.0, 125.0, -35.0), abs=0.02)


#============================================
@pytest.mark.parametrize("placement_request", (
	oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementRequest("unknown", (0.0, 0.0), "token"),
	oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementRequest("carbs/rings/furanose_scaffold", (True, 0.0), "token"),
	oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementRequest("carbs/rings/furanose_scaffold", (float("nan"), 0.0), "token"),
	oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementRequest("carbs/rings/furanose_scaffold", (0.0, 0.0), " "),
))
def test_invalid_biomolecule_request_has_one_typed_failure(placement_request: object) -> None:
	"""Malformed plain requests fail before a detached proposal is returned."""
	with pytest.raises(oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementError):
		oasa.biomolecule_template_placement.prepare_biomolecule_template_insertion(placement_request)


#============================================
def test_biomolecule_insertion_preserves_opaque_root_maps_and_restores_exact_snapshots() -> None:
	"""Normal insertion is durable, opaque-preserving, and reversible in history."""
	prepared = _prepared("carbs/rings/furanose_scaffold", (30.0, 40.0), "accepted")
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	baseline = session.snapshot()
	commit = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		baseline.revision, prepared.proposal_cdml, prepared.label,
	))
	accepted = commit.snapshot
	accepted_document = oasa.cdml_document.CDMLDocument.parse(accepted.cdml, validation="strict")
	mapped_root = commit.id_map[prepared.root_provisional_molecule_ids[0]]
	undone = session.restore(target_revision=baseline.revision, expected_revision=accepted.revision)
	redone = session.restore(target_revision=accepted.revision, expected_revision=undone.snapshot.revision)
	root_ids = tuple(
		record.identifier for record in accepted_document.objects()
		if record.identifier is not None
	)
	assert (
		prepared.root_provisional_molecule_ids[0] not in root_ids
		and accepted_document.find_by_id(mapped_root).local_name == "molecule"
		and root_ids[-1] == mapped_root
		and accepted_document.find_by_id("opaque_1").raw_xml in accepted.cdml
		and accepted_document.find_by_id("text_1").raw_xml in accepted.cdml
	)
	assert (undone.snapshot.cdml, redone.snapshot.cdml) == (baseline.cdml, accepted.cdml)
