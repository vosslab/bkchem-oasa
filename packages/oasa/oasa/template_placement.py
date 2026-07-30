"""Detached, frontend-neutral preparation of catalog template insertions."""

# Standard Library
import dataclasses

# local repo modules
import oasa.cdml_document
import oasa.cdml_writer
import oasa.insertion_geometry
import oasa.known_groups
import oasa.smiles_lib


TEMPLATE_TARGET_MEAN_BOND_LENGTH_PT = 40.0


class TemplatePlacementError(ValueError):
	"""Raised when one detached system-template proposal cannot be prepared."""


#============================================
def system_template_names() -> tuple[str, ...]:
	"""Return the ordered names accepted by detached system-template placement.

	The catalog stays an OASA implementation detail.  Callers receive only its
	immutable selection values and must still submit each selected value to OASA
	for final preparation and validation.
	"""
	catalog = oasa.known_groups.name_to_smiles
	if not isinstance(catalog, dict) or not catalog:
		raise TemplatePlacementError("system template catalog is unavailable")
	names = tuple(catalog)
	if (
		any(not isinstance(name, str) or not name for name in names)
		or len(set(names)) != len(names)
		or any(not isinstance(catalog[name], str) or not catalog[name] for name in names)
	):
		raise TemplatePlacementError("system template catalog is invalid")
	return names


@dataclasses.dataclass(frozen=True)
class CDMLTemplatePlacementRequest:
	"""Plain catalog selection and finite scene-point placement intent."""

	template_name: str
	anchor: tuple[float, float]
	token_stem: str


@dataclasses.dataclass(frozen=True)
class CDMLPreparedMoleculeInsertion:
	"""One detached, provisional molecule proposal ready for session insertion."""

	proposal_cdml: str
	label: str
	root_provisional_molecule_ids: tuple[str, ...]


#============================================
def _proposal_root_molecule_ids(proposal_cdml: str) -> tuple[str, ...]:
	"""Return the proposal's direct-root molecule tokens through the CDML boundary."""
	proposal = oasa.cdml_document.CDMLDocument.parse(proposal_cdml, validation="compat")
	identifiers = tuple(
		record.identifier
		for record in proposal.objects()
		if record.local_name == "molecule" and record.identifier is not None
	)
	if not identifiers:
		raise TemplatePlacementError(
			"template placement proposal has no provisional root molecule",
		)
	return identifiers


#============================================
def _validate_request(request: object) -> CDMLTemplatePlacementRequest:
	"""Return one exact public request after its plain values are validated."""
	if not isinstance(request, CDMLTemplatePlacementRequest):
		raise TemplatePlacementError("template placement request is invalid")
	if (
		not isinstance(request.template_name, str)
		or request.template_name not in system_template_names()
	):
		raise TemplatePlacementError("template placement name is unknown")
	if not isinstance(request.token_stem, str):
		raise TemplatePlacementError("template placement token stem is invalid")
	try:
		oasa.insertion_geometry.validate_insertion_placement(
			TEMPLATE_TARGET_MEAN_BOND_LENGTH_PT, request.anchor,
		)
	except ValueError as error:
		raise TemplatePlacementError(str(error)) from None
	return request


#============================================
def _prepare_catalog_molecule(template_name: str) -> object:
	"""Parse one system-catalog SMILES value into a detached positioned molecule."""
	smiles = oasa.known_groups.name_to_smiles[template_name]
	try:
		molecule = oasa.smiles_lib.text_to_mol(smiles, calc_coords=1)
	except (ArithmeticError, RuntimeError, TypeError, ValueError) as error:
		raise TemplatePlacementError("template placement molecule preparation failed") from error
	if molecule is None or not molecule.vertices:
		raise TemplatePlacementError("template placement molecule preparation failed")
	return molecule


#============================================
def prepare_template_molecule_insertion(
		request: CDMLTemplatePlacementRequest,
		) -> CDMLPreparedMoleculeInsertion:
	"""Prepare one detached system-template CDML proposal without document mutation.

	Real bonds are collectively scaled to the established 40-point visible
	mean before the molecule centroid is translated to the finite scene anchor.
	A bond-free template is only translated, so preparation never invents scale
	or chemistry for a single atom.
	"""
	validated_request = _validate_request(request)
	molecule = _prepare_catalog_molecule(validated_request.template_name)
	try:
		oasa.insertion_geometry.place_molecules_for_insertion(
			[molecule], TEMPLATE_TARGET_MEAN_BOND_LENGTH_PT,
			validated_request.anchor,
		)
		proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
			[molecule], token_stem=validated_request.token_stem,
		)
		root_provisional_molecule_ids = _proposal_root_molecule_ids(proposal_cdml)
	except (ArithmeticError, RuntimeError, TypeError, ValueError) as error:
		raise TemplatePlacementError("template placement proposal preparation failed") from error
	label = f"Insert template {validated_request.template_name}"
	prepared = CDMLPreparedMoleculeInsertion(
		proposal_cdml=proposal_cdml,
		label=label,
		root_provisional_molecule_ids=root_provisional_molecule_ids,
	)
	return prepared
