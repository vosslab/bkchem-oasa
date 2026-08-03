"""Detached OASA preparation for packaged biomolecule template placement."""

# Standard Library
import dataclasses
import math
import pathlib
import urllib.parse

# PIP3 modules
import yaml

# local repo modules
import oasa.cdml_document
import oasa.cdml_writer
import oasa.insertion_geometry
import oasa.smiles_lib
import oasa.template_placement


BIOMOLECULE_TARGET_MEAN_BOND_LENGTH_PT = 40.0
_YAML_PATH = pathlib.Path(__file__).resolve().parent.parent / "oasa_data" / "biomolecule_smiles.yaml"


class BiomoleculeTemplatePlacementError(ValueError):
	"""Raised when a packaged biomolecule placement cannot be prepared."""


@dataclasses.dataclass(frozen=True)
class BiomoleculeTemplateDescriptor:
	"""One immutable, frontend-neutral packaged biomolecule catalog entry."""

	catalog_key: str
	category: str
	subcategory: str
	name: str
	label: str


@dataclasses.dataclass(frozen=True)
class BiomoleculeTemplatePlacementRequest:
	"""One immutable catalog selection and detached scene-point placement."""

	catalog_key: str
	anchor: tuple[float, float]
	token_stem: str


#============================================
def _catalog_key(category: str, subcategory: str, name: str) -> str:
	"""Return the escaped stable catalog key for one packaged entry."""
	return "/".join(
		urllib.parse.quote(value, safe="")
		for value in (category, subcategory, name)
	)


#============================================
def _load_catalog() -> tuple[tuple[BiomoleculeTemplateDescriptor, str], ...]:
	"""Load and validate the complete OASA-owned biomolecule catalog."""
	try:
		with _YAML_PATH.open("r", encoding="utf-8") as handle:
			data = yaml.safe_load(handle)
	except (OSError, yaml.YAMLError) as error:
		raise BiomoleculeTemplatePlacementError("biomolecule catalog is unavailable") from error
	if not isinstance(data, dict) or not data:
		raise BiomoleculeTemplatePlacementError("biomolecule catalog is invalid")
	entries = []
	for category, subcategories in data.items():
		if not isinstance(category, str) or not category.strip() or not isinstance(subcategories, dict):
			raise BiomoleculeTemplatePlacementError("biomolecule catalog is invalid")
		for subcategory, molecules in subcategories.items():
			if not isinstance(subcategory, str) or not subcategory.strip() or not isinstance(molecules, dict):
				raise BiomoleculeTemplatePlacementError("biomolecule catalog is invalid")
			for name, properties in molecules.items():
				if (
					not isinstance(name, str) or not name.strip()
					or not isinstance(properties, dict)
					or not isinstance(properties.get("smiles"), str)
					or not properties["smiles"].strip()
				):
					raise BiomoleculeTemplatePlacementError("biomolecule catalog is invalid")
				label = properties.get("label", name)
				if not isinstance(label, str) or not label.strip():
					raise BiomoleculeTemplatePlacementError("biomolecule catalog is invalid")
				entries.append((
					BiomoleculeTemplateDescriptor(
						_catalog_key(category, subcategory, name), category, subcategory, name, label,
					),
					properties["smiles"],
				))
	if not entries or len({entry.catalog_key for entry, _smiles in entries}) != len(entries):
		raise BiomoleculeTemplatePlacementError("biomolecule catalog has duplicate keys")
	return tuple(entries)


#============================================
def biomolecule_template_catalog() -> tuple[BiomoleculeTemplateDescriptor, ...]:
	"""Return ordered immutable descriptors for OASA's packaged catalog."""
	return tuple(entry for entry, _smiles in _load_catalog())


#============================================
def _validated_request(request: object) -> BiomoleculeTemplatePlacementRequest:
	"""Return one exact request with valid plain placement values."""
	if type(request) is not BiomoleculeTemplatePlacementRequest:
		raise BiomoleculeTemplatePlacementError("biomolecule placement request is invalid")
	if not isinstance(request.catalog_key, str) or not request.catalog_key.strip():
		raise BiomoleculeTemplatePlacementError("biomolecule catalog key is invalid")
	if not isinstance(request.token_stem, str) or not request.token_stem.strip():
		raise BiomoleculeTemplatePlacementError("biomolecule token stem is invalid")
	if (
		type(request.anchor) is not tuple or len(request.anchor) != 2
		or any(
			isinstance(value, bool) or not isinstance(value, (int, float))
			or not math.isfinite(value)
			for value in request.anchor
		)
	):
		raise BiomoleculeTemplatePlacementError("biomolecule anchor is invalid")
	return request


#============================================
def prepare_biomolecule_template_insertion(
		request: BiomoleculeTemplatePlacementRequest,
		) -> oasa.template_placement.CDMLPreparedMoleculeInsertion:
	"""Return one detached molecule-only proposal from a packaged catalog key."""
	validated = _validated_request(request)
	catalog = _load_catalog()
	smiles_by_key = {entry.catalog_key: smiles for entry, smiles in catalog}
	if validated.catalog_key not in smiles_by_key:
		raise BiomoleculeTemplatePlacementError("biomolecule catalog key is unknown")
	try:
		molecule = oasa.smiles_lib.text_to_mol(
			smiles_by_key[validated.catalog_key], calc_coords=1,
		)
		if molecule is None or not molecule.vertices:
			raise ValueError("empty molecule")
		oasa.insertion_geometry.place_molecules_for_insertion(
			[molecule], BIOMOLECULE_TARGET_MEAN_BOND_LENGTH_PT, validated.anchor,
		)
		proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
			[molecule], token_stem=validated.token_stem,
		)
		proposal = oasa.cdml_document.CDMLDocument.parse(proposal_cdml, validation="compat")
		root_ids = tuple(
			record.identifier for record in proposal.objects()
			if record.local_name == "molecule" and record.identifier is not None
		)
		if not root_ids:
			raise ValueError("proposal has no molecule root")
	except (ArithmeticError, RuntimeError, TypeError, ValueError) as error:
		raise BiomoleculeTemplatePlacementError(
			"biomolecule placement preparation failed",
		) from error
	return oasa.template_placement.CDMLPreparedMoleculeInsertion(
		proposal_cdml, "Insert biomolecule template", root_ids,
	)
