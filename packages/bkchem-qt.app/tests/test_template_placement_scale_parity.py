"""Pure-model evidence for backend template placement scale and anchors."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.bridge.oasa_bridge
import oasa.cdml_document
import oasa.known_groups
import oasa.safe_xml
import oasa.smiles_lib
import oasa.template_placement


POINTS_PER_CM = 72.0 / 2.54


#============================================
def _local_name(element: object) -> str:
	"""Return one namespace-neutral CDML element name."""
	local_name = str(element.tag).rsplit("}", 1)[-1]
	return local_name


#============================================
def _model_mean_bond_length(molecule: object) -> float:
	"""Return a converted model's mean real-bond length in scene points."""
	lengths = []
	for bond in molecule.bonds:
		atom1 = bond.atom1
		atom2 = bond.atom2
		if atom1 is None or atom2 is None:
			raise AssertionError("Converted template has an incomplete bond")
		lengths.append(math.hypot(atom1.x - atom2.x, atom1.y - atom2.y))
	if not lengths:
		raise AssertionError("Scale comparison requires a bonded template")
	mean_length = math.fsum(lengths) / len(lengths)
	return mean_length


#============================================
def _prepared_geometry(proposal_cdml: str) -> tuple[float, tuple[float, float]]:
	"""Read proposal geometry after the CDML boundary accepts the document."""
	oasa.cdml_document.CDMLDocument.parse(proposal_cdml, validation="compat")
	root = oasa.safe_xml.parse_xml_string(proposal_cdml)
	coordinates = {}
	for element in root.iter():
		if _local_name(element) != "atom":
			continue
		point = next(child for child in element if _local_name(child) == "point")
		coordinates[element.attrib["id"]] = (
			float(point.attrib["x"].removesuffix("cm")) * POINTS_PER_CM,
			float(point.attrib["y"].removesuffix("cm")) * POINTS_PER_CM,
		)
	lengths = []
	for element in root.iter():
		if _local_name(element) != "bond":
			continue
		start_x, start_y = coordinates[element.attrib["start"]]
		end_x, end_y = coordinates[element.attrib["end"]]
		lengths.append(math.hypot(start_x - end_x, start_y - end_y))
	if not lengths:
		raise AssertionError("Scale comparison requires a bonded prepared proposal")
	mean_length = math.fsum(lengths) / len(lengths)
	centroid = (
		math.fsum(point[0] for point in coordinates.values()) / len(coordinates),
		math.fsum(point[1] for point in coordinates.values()) / len(coordinates),
	)
	geometry = (mean_length, centroid)
	return geometry


#============================================
@pytest.mark.parametrize("anchor", ((-125.5, 75.25), (315.0, -420.75)))
def test_prepared_template_matches_current_model_scale_at_each_anchor(
		anchor: tuple[float, float],
		) -> None:
	"""Prepared CDML retains current model scale while moving only its anchor.

	This comparison intentionally uses model coordinates, not a QApplication,
	widget, scene, graphics item, rendered pixels, or object counts.
	"""
	source_molecule = oasa.smiles_lib.text_to_mol(
		oasa.known_groups.name_to_smiles["Ph"], calc_coords=1,
	)
	if source_molecule is None:
		raise AssertionError("Stable catalog template did not parse")
	current_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(source_molecule)
	prepared = oasa.template_placement.prepare_template_molecule_insertion(
		oasa.template_placement.CDMLTemplatePlacementRequest(
			template_name="Ph", anchor=anchor, token_stem="scale-parity",
		)
	)
	prepared_mean, prepared_centroid = _prepared_geometry(prepared.proposal_cdml)

	assert (prepared_mean, *prepared_centroid) == pytest.approx(
		(_model_mean_bond_length(current_model), *anchor), abs=0.02,
	)
