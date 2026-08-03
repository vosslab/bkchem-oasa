"""Backend chemistry preparation facts consumed by Qt insertion actions.

This adapter owns OASA graph construction, layout, placement, and PubChem
normalization.  Its public results contain only immutable scalar display facts
and the existing immutable CDML insertion proposal, allowing Qt actions to
remain worker and session clients rather than chemistry implementations.
"""

# Standard Library
import dataclasses

# local repo modules
import oasa.cdml_writer
import oasa.coords_generator
import oasa.haworth.direct_glycosidic
import oasa.haworth.layout
import oasa.haworth.verified_sucrose
import oasa.insertion_geometry
import oasa.pubchem
import oasa.pubchem_http
import oasa.smiles_lib
import oasa.sugar_code
import oasa.sugar_code_smiles
import bkchem_qt.bridge.worker


@dataclasses.dataclass(frozen=True)
class PubChemDisplayFacts:
	"""Immutable frontend-neutral fields suitable for a lookup result view."""

	name: str
	cid: int
	molecular_formula: str
	molecular_weight: float
	inchikey: str
	smiles: str


@dataclasses.dataclass(frozen=True)
class MoleculeInsertionProposal:
	"""One validated immutable proposal crossing a worker-to-session seam.

	The action layer receives this stable scalar view rather than the worker's
	implementation-specific result class.  It is intentionally suitable for a
	future non-Qt worker delivery mechanism as well.
	"""

	proposal_cdml: str
	expected_revision: int
	label: str | None


@dataclasses.dataclass(frozen=True)
class PreparedPubChemLookup:
	"""One immutable PubChem display record and insertion proposal."""

	display: PubChemDisplayFacts
	insertion: MoleculeInsertionProposal


@dataclasses.dataclass(frozen=True)
class TextImportFailureFacts:
	"""Plain user-facing failure data for one text-import preparation attempt."""

	stage: str
	message: str


#============================================
def fetch_pubchem_json(url: str) -> dict:
	"""Fetch one caller-initiated PubChem response through OASA's transport."""
	return oasa.pubchem_http.fetch_json(url)


#============================================
def prepare_haworth_insertion(
		sugar_code: str, ring_type: str, anomeric: str, expected_revision: int,
		token_stem: str, bond_length_pt: float, insertion_anchor: tuple[float, float],
		) -> MoleculeInsertionProposal:
	"""Return one detached, positioned Haworth CDML insertion proposal."""
	_validate_revision(expected_revision, "Haworth")
	molecules = _prepare_haworth_sugar(sugar_code, ring_type, anomeric)
	return _prepare_molecule_insertion(
		molecules, expected_revision, token_stem, bond_length_pt, insertion_anchor,
		"Insert Haworth sugar",
	)


#============================================
def prepare_verified_sucrose_insertion(
		expected_revision: int, token_stem: str, bond_length_pt: float,
		insertion_anchor: tuple[float, float],
		) -> MoleculeInsertionProposal:
	"""Return the detached proposal for the fixed backend-owned sucrose preset."""
	_validate_revision(expected_revision, "Verified sucrose")
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	return _prepare_molecule_insertion(
		[molecule], expected_revision, token_stem, bond_length_pt, insertion_anchor,
		"Insert verified sucrose Haworth",
	)


#============================================
def prepare_direct_glycosidic_haworth_insertion(
		smiles: str, expected_revision: int, token_stem: str,
		bond_length_pt: float, insertion_anchor: tuple[float, float],
		) -> MoleculeInsertionProposal:
	"""Prepare one supported direct-glycosidic Haworth drawing for insertion.

	The backend owns SMILES parsing, topology recognition, coordinate planning,
	and serialization.  The returned proposal is detached CDML plus scalar
	metadata, so a worker never exposes the mutable OASA graph to Qt actions.
	"""
	_validate_revision(expected_revision, "Direct glycosidic Haworth")
	molecule = oasa.haworth.direct_glycosidic.prepare_direct_glycosidic_haworth(
		smiles, bond_length=bond_length_pt,
	)
	return _prepare_molecule_insertion(
		[molecule], expected_revision, token_stem, bond_length_pt, insertion_anchor,
		"Insert direct glycosidic Haworth",
	)


#============================================
def prepare_pubchem_lookup(
		kind: str, query: str, transport: object, expected_revision: int,
		token_stem: str, target_mean_bond_length: float,
		insertion_anchor: tuple[float, float],
		) -> PreparedPubChemLookup:
	"""Look up one compound and return immutable display data plus CDML proposal."""
	_validate_revision(expected_revision, "PubChem")
	compound = _lookup_pubchem_compound(kind, query, transport)
	molecule = oasa.smiles_lib.text_to_mol(compound.smiles)
	oasa.coords_generator.calculate_coords(molecule, bond_length=1.0, force=1)
	if molecule.is_connected():
		molecules = [molecule]
	else:
		molecules = list(molecule.get_disconnected_subgraphs())
	insertion = _prepare_molecule_insertion(
		molecules, expected_revision, token_stem, target_mean_bond_length,
		insertion_anchor, "Insert PubChem structure",
	)
	display_name = compound.display_name
	if not display_name and compound.synonyms:
		display_name = compound.synonyms[0]
	display = PubChemDisplayFacts(
		name=display_name,
		cid=compound.cid,
		molecular_formula=compound.molecular_formula,
		molecular_weight=compound.molecular_weight,
		inchikey=compound.inchikey,
		smiles=compound.smiles,
	)
	return PreparedPubChemLookup(display, insertion)


#============================================
def is_prepared_molecule_insertion(value: object) -> bool:
	"""Return whether a worker value has the stable insertion-proposal grammar."""
	if not isinstance(value, MoleculeInsertionProposal):
		return False
	return (
		type(value.proposal_cdml) is str
		and type(value.expected_revision) is int
		and (value.label is None or type(value.label) is str)
	)


#============================================
def molecule_insertion_proposal(value: object) -> MoleculeInsertionProposal | None:
	"""Copy one prepared worker proposal into the stable bridge value grammar."""
	if isinstance(value, bkchem_qt.bridge.worker.PreparedMoleculeInsertion):
		value = MoleculeInsertionProposal(
			value.proposal_cdml, value.expected_revision, value.label,
		)
	if not is_prepared_molecule_insertion(value):
		return None
	return value


#============================================
def build_molecule_insertion_request(
		proposal: MoleculeInsertionProposal, fallback_label: str,
		) -> object:
	"""Build the session request for one already-validated detached proposal.

	The persistent operation remains a session-owned Qt adapter detail.  Actions
	provide only immutable proposal values and do not rebuild CDML request
	carriers themselves.
	"""
	if not isinstance(proposal, MoleculeInsertionProposal):
		raise TypeError("Molecule insertion requires a validated proposal")
	if not isinstance(fallback_label, str) or not fallback_label:
		raise ValueError("Molecule insertion fallback label must be nonempty text")
	import bkchem_qt.models.document_session
	return bkchem_qt.models.document_session.PersistentOperationRequest(
		operation_key="molecule.insert",
		label=proposal.label or fallback_label,
		payload=(
			("expected_revision", proposal.expected_revision),
			("proposal_cdml", proposal.proposal_cdml),
		),
		target_keys=frozenset(),
	)


#============================================
def create_text_molecule_insertion_worker(
		codec_name: str, source_text: str, expected_revision: int,
		token_stem: str, target_mean_bond_length: float,
		insertion_anchor: tuple[float, float], label: str,
		) -> object:
	"""Create the named worker that prepares one immutable text proposal."""
	return bkchem_qt.bridge.worker.TextMoleculeInsertionWorker(
		codec_name, source_text, expected_revision, token_stem,
		target_mean_bond_length, insertion_anchor, label,
	)


#============================================
def text_import_failure_facts(value: object) -> TextImportFailureFacts:
	"""Normalize a worker failure into stable presentation-only scalar facts."""
	if isinstance(value, bkchem_qt.bridge.worker.TextImportPreparationError):
		return TextImportFailureFacts(value.stage, str(value))
	return TextImportFailureFacts("unknown", str(value))


#============================================
def supported_peptide_codes() -> tuple[str, ...]:
	"""Return the backend's sorted single-letter peptide alphabet for a prompt."""
	from oasa import peptide_utils
	return tuple(sorted(peptide_utils.AMINO_ACID_SMILES))


#============================================
def is_prepared_pubchem_lookup(value: object) -> bool:
	"""Return whether a worker value has the immutable PubChem-result grammar."""
	if not isinstance(value, PreparedPubChemLookup):
		return False
	display = value.display
	return (
		isinstance(display, PubChemDisplayFacts)
		and type(display.name) is str
		and type(display.cid) is int
		and type(display.molecular_formula) is str
		and type(display.molecular_weight) in (int, float)
		and type(display.inchikey) is str
		and type(display.smiles) is str
		and is_prepared_molecule_insertion(value.insertion)
	)


#============================================
def _prepare_haworth_sugar(
		sugar_code: str, ring_type: str, anomeric: str,
		bond_length: float = 1.0,
		) -> list:
	"""Build one positioned OASA Haworth molecule for detached serialization."""
	parsed = oasa.sugar_code.parse(sugar_code)
	series_by_config = {"DEXTER": "D", "LAEVUS": "L"}
	series = series_by_config.get(parsed.config)
	if series is None:
		raise ValueError(
			"Haworth insertion requires a D or L sugar code; got '%s'."
			% parsed.sugar_code
		)
	smiles_text = oasa.sugar_code_smiles.sugar_code_to_smiles(
		sugar_code, ring_type, anomeric,
	)
	molecule = oasa.smiles_lib.text_to_mol(smiles_text)
	oasa.coords_generator.calculate_coords(
		molecule, bond_length=bond_length, force=1,
	)
	oasa.haworth.layout.build_haworth(
		molecule,
		mode=ring_type,
		bond_length=bond_length,
		series=series,
		stereo=anomeric,
	)
	return [molecule]


#============================================
def _prepare_molecule_insertion(
		molecules: list, expected_revision: int, token_stem: str,
		target_mean_bond_length: float, insertion_anchor: tuple[float, float],
		label: str,
		) -> MoleculeInsertionProposal:
	"""Place detached molecules once and serialize one immutable insertion proposal."""
	oasa.insertion_geometry.place_molecules_for_insertion(
		molecules, target_mean_bond_length, insertion_anchor,
	)
	proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
		molecules, token_stem=token_stem,
	)
	return MoleculeInsertionProposal(
		proposal_cdml, expected_revision, label,
	)


#============================================
def _lookup_pubchem_compound(kind: str, query: str, transport: object) -> object:
	"""Resolve one declared PubChem lookup kind through OASA's typed API."""
	if kind == "Name":
		return oasa.pubchem.lookup_by_name(query, transport)
	if kind == "CID":
		try:
			cid = int(query)
		except ValueError as error:
			raise ValueError("PubChem CID must be a positive integer") from error
		return oasa.pubchem.lookup_by_cid(cid, transport)
	if kind == "InChI":
		return oasa.pubchem.lookup_by_inchi(query, transport)
	if kind == "InChIKey":
		return oasa.pubchem.lookup_by_inchikey(query, transport)
	raise ValueError("Unsupported PubChem lookup type: %s" % kind)


#============================================
def _validate_revision(expected_revision: int, label: str) -> None:
	"""Require one ordinary integer revision before preparation begins."""
	if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
		raise ValueError("%s insertion revision must be an integer" % label)
