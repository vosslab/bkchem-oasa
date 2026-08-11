"""Bridge between OASA chemistry objects and BKChem-Qt model wrappers."""

# Standard Library
import dataclasses
import math

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import oasa.periodic_table
import oasa.codec_registry
import oasa.cdml_bond_io
import oasa.cdml_document
import oasa.cdml_ftext
import oasa.cdml_molecule_summary
import oasa.cdml_standard
import oasa.codecs.rdkit_formats
import oasa.render_lib.bond_ops
import oasa.render_lib.data_types
import oasa.render_lib.molecule_ops
from oasa import coords_generator
from oasa import transform3d_lib
from oasa.cdml_writer import CPK_COLORS

import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.molecule_model

# default canvas center and bond length for initial display
DEFAULT_CENTER_X = 2000.0
DEFAULT_CENTER_Y = 1500.0
DEFAULT_BOND_LENGTH_PT = 40.0
_BACKEND_DOCUMENT_BACKGROUND = "__backend_document_background__"
_BACKEND_FOREGROUND = "__backend_foreground__"
_LEGACY_DEFAULT_LINE_COLOR = "#000000"


@dataclasses.dataclass(frozen=True)
class BackendQueryFailure:
	"""Typed display-safe failure returned by a read-only backend observation."""

	kind: str
	message: str


@dataclasses.dataclass(frozen=True)
class BackendQueryResult:
	"""One backend observation result or its typed presentation-safe failure."""

	value: object | None
	failure: BackendQueryFailure | None


@dataclasses.dataclass(frozen=True)
class MoleculeIdentifierObservation:
	"""Exact-revision standard identifiers for one authoritative molecule."""

	revision: int
	molecule_id: str
	smiles: str
	inchi: str
	inchikey: str
	warnings: tuple[str, ...]


#============================================
def atom_creation_facts(symbol: str) -> tuple[str, int]:
	"""Return the canonical element and its default valency as plain values."""
	if type(symbol) is not str or not symbol:
		raise TypeError("symbol must be a nonempty string")
	try:
		valency = oasa.periodic_table.periodic_table[symbol]["valency"][0]
	except KeyError as error:
		raise ValueError(f"unsupported element symbol: {symbol!r}") from error
	return symbol, int(valency)


#============================================
def observe_atom_chemistry_facts(
		session: object, expected_revision: int,
		) -> BackendQueryResult:
	"""Read one exact-revision chemistry observation through a session port.

	The Qt action receives either the immutable backend observation or a typed
	plain failure.  Concrete OASA failure classes and session implementation
	details remain inside this adapter.
	"""
	try:
		observation = session.observe_atom_chemistry_facts(expected_revision)
	except Exception as error:
		failure = _backend_observation_failure(error, "atom-chemistry")
		if failure is None:
			raise
		return BackendQueryResult(None, failure)
	return BackendQueryResult(observation, None)


#============================================
def query_molecule_summary(
		session: object, expected_revision: int, molecule_ids: tuple[str, ...],
		) -> BackendQueryResult:
	"""Read one exact-revision molecular-composition batch through a session port."""
	try:
		result = session.query_molecule_summary(expected_revision, molecule_ids)
	except Exception as error:
		failure = _backend_observation_failure(error, "molecule-summary")
		if failure is None:
			raise
		return BackendQueryResult(None, failure)
	return BackendQueryResult(result, None)


#============================================
def query_molecule_smiles(
		session: object, expected_revision: int, molecule_id: str,
		) -> BackendQueryResult:
	"""Read one exact-revision SMILES observation through a session port."""
	try:
		result = session.query_molecule_smiles(expected_revision, molecule_id)
	except Exception as error:
		failure = _backend_observation_failure(error, "molecule-smiles")
		if failure is None:
			raise
		return BackendQueryResult(None, failure)
	return BackendQueryResult(result, None)


#============================================
def query_molecule_identifiers(
		session: object, expected_revision: int, molecule_id: str,
		) -> BackendQueryResult:
	"""Derive standard identifiers from one authoritative CDML observation."""
	response = query_molecule_smiles(session, expected_revision, molecule_id)
	if response.failure is not None or response.value is None:
		return response
	result = response.value
	try:
		facts = oasa.codecs.rdkit_formats.identifiers_from_smiles(result.smiles)
	except (RuntimeError, TypeError, ValueError) as error:
		return BackendQueryResult(
			None, BackendQueryFailure("unavailable", str(error)),
		)
	observation = MoleculeIdentifierObservation(
		result.revision, result.molecule_id, facts.smiles, facts.inchi,
		facts.inchikey, facts.warnings,
	)
	return BackendQueryResult(observation, None)


#============================================
def _backend_observation_failure(
		error: Exception, operation: str,
		) -> BackendQueryFailure | None:
	"""Map declared backend observation failures to frontend-neutral facts."""
	if error.__class__.__name__ == "BackendProjectionOutOfSyncError":
		return BackendQueryFailure("projection-unavailable", str(error))
	if isinstance(error, oasa.cdml_document.CDMLRevisionConflictError):
		return BackendQueryFailure("revision-conflict", str(error))
	if operation == "atom-chemistry" and isinstance(
			error, oasa.cdml_document.CDMLAtomChemistryFactsError,
		):
		return BackendQueryFailure("validation", str(error))
	if operation == "molecule-smiles" and isinstance(
			error, oasa.cdml_document.CDMLMoleculeSmilesUnavailableError,
		):
		return BackendQueryFailure("unavailable", str(error))
	if operation == "molecule-summary" and isinstance(
			error, oasa.cdml_molecule_summary.CDMLMoleculeSummaryError,
		):
		return BackendQueryFailure("unavailable", str(error))
	if isinstance(error, (oasa.cdml_document.CDMLDocumentError, ValueError)):
		return BackendQueryFailure("validation", str(error))
	if operation == "molecule-smiles" and isinstance(error, RuntimeError):
		return BackendQueryFailure("backend-error", str(error))
	return None


#============================================
def decode_authored_ftext_runs(
		authored: str,
		) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
	"""Decode authored ftext character data into frontend-only plain runs.

	The OASA codec owns the compact CDML grammar.  This bridge deliberately
	returns only immutable strings and tuples, so a disposable Qt projection
	never retains an OASA ftext object.
	"""
	if type(authored) is not str:
		raise TypeError("Authored ftext must be a string")
	try:
		runs = oasa.cdml_ftext.decode(authored)
	except oasa.cdml_ftext.CDMLFTextCodecError:
		return None
	plain_runs = tuple((run.text, run.styles) for run in runs)
	return plain_runs


#============================================
def paper_catalog() -> dict[str, list[float] | None]:
	"""Return OASA's plain CDML paper catalog for Qt display adapters."""
	return oasa.cdml_document.paper_catalog()


#============================================
def oasa_mol_to_qt_mol(
		mol: oasa.molecule_lib.Molecule,
		bond_length_pt: float | None = DEFAULT_BOND_LENGTH_PT,
		) -> bkchem_qt.models.molecule_model.MoleculeModel:
	"""Convert an OASA molecule to a Qt MoleculeModel.

	Creates AtomModel and BondModel wrappers for every vertex and edge in
	the OASA molecule. When the atoms already carry coordinates, the
	molecule is rescaled so that the average bond length matches a numeric
	``bond_length_pt`` and centered at (DEFAULT_CENTER_X, DEFAULT_CENTER_Y).
	Passing ``None`` preserves the input coordinate system for native CDML.

	Args:
		mol: OASA molecule object.
		bond_length_pt: Target average bond length in scene-space points.

	Returns:
		MoleculeModel wrapping the converted atoms and bonds.
	"""
	# The bridge copies backend values into a new disposable Qt projection.
	# MoleculeModel deliberately retains no OASA molecule after this boundary.
	mol_model = bkchem_qt.models.molecule_model.MoleculeModel()
	mol_model.mol_id = str(getattr(mol, "id", "") or "")
	mol_model.name = str(getattr(mol, "name", "") or "")

	# check whether every atom already has valid coordinates
	has_coords = True
	for a in mol.vertices:
		if a.x is None or a.y is None:
			has_coords = False
			break

	# build a mapping from oasa vertex to AtomModel for bond wiring
	oasa_to_qt_atom = {}
	for a in mol.vertices:
		atom_model = oasa_atom_to_qt_atom(a)
		mol_model.add_atom(atom_model)
		oasa_to_qt_atom[id(a)] = atom_model

	# create bonds and wire them to the correct atom endpoints
	for b in mol.edges:
		bond_model = oasa_bond_to_qt_bond(b)
		v1, v2 = b.vertices
		atom1_model = oasa_to_qt_atom[id(v1)]
		atom2_model = oasa_to_qt_atom[id(v2)]
		mol_model.add_bond(atom1_model, atom2_model, bond_model)

	# rescale and center if coordinates are present
	if has_coords and mol_model.atoms and bond_length_pt is not None:
		_rescale_and_center(mol_model, bond_length_pt)

	return mol_model


#============================================
def _rescale_and_center(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		bond_length_pt: float,
		) -> None:
	"""Rescale atom positions so avg bond length matches target, then center.

	Computes the average bond length from current positions, builds a
	Transform3d that scales to match ``bond_length_pt``, and translates
	the centroid to (DEFAULT_CENTER_X, DEFAULT_CENTER_Y).

	Args:
		mol_model: MoleculeModel with positioned atoms.
		bond_length_pt: Target average bond length in scene-space points.
	"""
	atoms = mol_model.atoms
	bonds = mol_model.bonds

	# measure current average bond length
	bond_lengths = []
	for bm in bonds:
		a1 = bm.atom1
		a2 = bm.atom2
		if a1 is None or a2 is None:
			continue
		dx = a1.x - a2.x
		dy = a1.y - a2.y
		length = math.sqrt(dx * dx + dy * dy)
		bond_lengths.append(length)
	avg_bl = sum(bond_lengths) / len(bond_lengths) if bond_lengths else 1.0
	# avoid division by zero for single-atom molecules
	if avg_bl < 1e-6:
		avg_bl = 1.0
	scale = bond_length_pt / avg_bl

	# compute centroid of current positions
	xs = [am.x for am in atoms]
	ys = [am.y for am in atoms]
	cx = sum(xs) / len(xs)
	cy = sum(ys) / len(ys)

	# build transform: translate centroid to origin, scale, move to default center
	trans = transform3d_lib.Transform3d()
	trans.set_move(-cx, -cy, 0)
	trans.set_scaling(scale)
	trans.set_move(DEFAULT_CENTER_X, DEFAULT_CENTER_Y, 0)

	# apply transform to every atom
	for am in atoms:
		new_x, new_y, new_z = trans.transform_xyz(am.x, am.y, am.z)
		am.set_xyz(new_x, new_y, new_z)


#============================================
def oasa_atom_to_qt_atom(
		oasa_atom: oasa.atom_lib.Atom,
		) -> bkchem_qt.models.atom_model.AtomModel:
	"""Convert an OASA atom to an AtomModel.

	Copies coordinates, element symbol, charge, isotope, valency,
	multiplicity, free sites, and explicit hydrogens. Applies CPK color
	for non-carbon heteroatoms.

	Args:
		oasa_atom: OASA atom object.

	Returns:
		AtomModel with chemistry and display properties populated.
	"""
	properties = oasa_atom.properties_
	explicit_fields = frozenset(
		field for field in ("show", "show_hydrogens", "font_size", "font_family", "line_color")
		if field in properties
	)
	atom_model = bkchem_qt.models.atom_model.AtomModel()
	atom_model.install_projection(
		atom_id=str(getattr(oasa_atom, "id", "") or "") or None,
		symbol=oasa_atom.symbol,
		charge=oasa_atom.charge,
		valency=oasa_atom.valency,
		authored_valency=oasa_atom.valency,
		isotope=oasa_atom.isotope,
		multiplicity=oasa_atom.multiplicity,
		free_sites=oasa_atom.free_sites,
		explicit_hydrogens=oasa_atom.explicit_hydrogens,
		x=oasa_atom.x if oasa_atom.x is not None else 0.0,
		y=oasa_atom.y if oasa_atom.y is not None else 0.0,
		z=oasa_atom.z if oasa_atom.z is not None else 0.0,
		show=properties.get("show", "yes") == "yes",
		show_hydrogens=properties.get("show_hydrogens", "on") == "on",
		font_size=int(properties.get("font_size", 12)),
		font_family=properties.get("font_family", "Arial"),
		line_color=properties.get("line_color", "#000000"),
		explicit_fields=explicit_fields,
	)

	# apply CPK color for non-carbon heteroatoms
	symbol = oasa_atom.symbol
	cpk_color = CPK_COLORS.get(symbol)
	if cpk_color and symbol != "C" and "line_color" not in atom_model.cdml_display_fields:
		atom_model._line_color = cpk_color

	return atom_model


#============================================
def _display_atom_properties_to_qt(
		oasa_atom: oasa.atom_lib.Atom,
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		) -> None:
	"""Copy supported CDML atom depiction fields into the Qt atom model."""
	# Retained for callers that intentionally apply a local compatibility edit.
	properties = oasa_atom.properties_
	if "show" in properties:
		atom_model.show = properties["show"] == "yes"
	if "show_hydrogens" in properties:
		atom_model.show_hydrogens = properties["show_hydrogens"] == "on"
	if "font_size" in properties:
		atom_model.font_size = int(properties["font_size"])
	if "font_family" in properties:
		atom_model.font_family = properties["font_family"]
	if "line_color" in properties:
		atom_model.line_color = properties["line_color"]


#============================================
def oasa_bond_to_qt_bond(
		oasa_bond: oasa.bond_lib.Bond,
		) -> bkchem_qt.models.bond_model.BondModel:
	"""Convert an OASA bond to a BondModel.

	Copies bond chemistry and all supported CDML depiction fields. Endpoint
	atoms are wired separately by the molecule-level converter.

	Args:
		oasa_bond: OASA bond object.

	Returns:
		BondModel with chemistry properties populated.
	"""
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(oasa_bond)
	bond_model = bkchem_qt.models.bond_model.BondModel.create(
		order=oasa_bond.order,
		bond_type=oasa_bond.type,
		bond_id=str(getattr(oasa_bond, "id", "") or "") or None,
	)
	bond_model.install_projection(
		bond_id=bond_model.bond_id,
		order=oasa_bond.order,
		bond_type=oasa_bond.type,
		aromatic=oasa_bond.aromatic,
		line_width=depiction.line_width,
		bond_width=depiction.bond_width,
		wedge_width=depiction.wedge_width,
		double_ratio=depiction.double_ratio,
		center=depiction.center,
		auto_sign=depiction.auto_sign,
		equithick=depiction.equithick,
		simple_double=depiction.simple_double,
		line_color=depiction.color,
		wavy_style=depiction.wavy_style,
		haworth_position=depiction.haworth_position,
		explicit_fields=depiction.explicit_fields,
	)
	return bond_model


#============================================
def _display_bond_properties_to_qt(
		oasa_bond: oasa.bond_lib.Bond,
		bond_model: bkchem_qt.models.bond_model.BondModel,
		) -> None:
	"""Copy supported CDML depiction fields from OASA to a Qt bond model."""
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(oasa_bond)
	bond_model.install_projection(
		bond_id=str(getattr(oasa_bond, "id", "") or "") or None,
		order=oasa_bond.order,
		bond_type=oasa_bond.type,
		aromatic=oasa_bond.aromatic,
		line_width=depiction.line_width,
		bond_width=depiction.bond_width,
		wedge_width=depiction.wedge_width,
		double_ratio=depiction.double_ratio,
		center=depiction.center,
		auto_sign=depiction.auto_sign,
		equithick=depiction.equithick,
		simple_double=depiction.simple_double,
		line_color=depiction.color,
		wavy_style=depiction.wavy_style,
		haworth_position=depiction.haworth_position,
		explicit_fields=depiction.explicit_fields,
	)


#============================================
def materialize_oasa_bond(
		bond_model: bkchem_qt.models.bond_model.BondModel,
		) -> oasa.bond_lib.Bond:
	"""Create one detached OASA edge from current scalar Qt bond facts."""
	oasa_bond = oasa.bond_lib.Bond(order=bond_model.order, type=bond_model.type)
	oasa_bond.aromatic = bond_model.aromatic
	if bond_model.bond_id:
		oasa_bond.id = bond_model.bond_id
	_display_bond_properties_to_oasa(bond_model, oasa_bond)
	return oasa_bond


#============================================
def materialize_oasa_atom(
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		) -> oasa.atom_lib.Atom:
	"""Create one detached OASA atom from public scalar projection facts.

	The returned atom is bridge-local.  Callers that need connected chemistry
	must add it to a fresh complete molecule before asking OASA for a result.
	"""
	oasa_atom = oasa.atom_lib.Atom(symbol=atom_model.symbol)
	oasa_atom.x, oasa_atom.y, oasa_atom.z = atom_model.get_xyz()
	oasa_atom.charge = atom_model.charge
	oasa_atom.valency = atom_model.valency
	oasa_atom.multiplicity = atom_model.multiplicity
	oasa_atom.free_sites = atom_model.free_sites
	oasa_atom.explicit_hydrogens = atom_model.explicit_hydrogens
	if atom_model.isotope is not None:
		oasa_atom.isotope = atom_model.isotope
	if atom_model.atom_id is not None:
		oasa_atom.id = atom_model.atom_id
	_display_atom_properties_to_oasa(atom_model, oasa_atom)
	return oasa_atom


#============================================
def legacy_atom_render_operations(
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		) -> tuple[oasa.cdml_document.CDMLRenderPrimitive, ...]:
	"""Build portable atom primitives from scalar compatibility display facts.

	Temporary OASA operation classes remain inside this bridge.  The returned
	primitive coordinates are local to an AtomItem whose scene position owns the
	atom's scalar coordinates.
	"""
	atom = materialize_oasa_atom(atom_model)
	atom.x = 0.0
	atom.y = 0.0
	properties = atom.properties_
	if properties.get("show") == "no":
		return ()
	operations = oasa.render_lib.molecule_ops.build_vertex_ops(
		atom,
		transform_xy=None,
		show_hydrogens_on_hetero=atom_model.show_hydrogens,
		color_atoms=True,
		atom_colors={atom.symbol: _compatibility_color(atom_model.line_color)},
		font_name=atom_model.font_family,
		font_size=atom_model.font_size,
		background_color=_BACKEND_DOCUMENT_BACKGROUND,
		show_carbon_symbol=properties.get("show") == "yes",
	)
	return oasa.cdml_document.normalize_render_operations(operations)


#============================================
def legacy_atom_text_bounds(
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		) -> tuple[float, float]:
	"""Return Qt-measured horizontal label bounds from portable primitives."""
	from bkchem_qt.canvas.items import primitive_ops_painter
	operations = legacy_atom_render_operations(atom_model)
	return primitive_ops_painter.text_horizontal_bounds(operations)


#============================================
def legacy_bond_render_operations(
		bond_model: bkchem_qt.models.bond_model.BondModel,
		atom1: bkchem_qt.models.atom_model.AtomModel,
		atom2: bkchem_qt.models.atom_model.AtomModel,
		start: tuple[float, float], end: tuple[float, float],
		) -> tuple[oasa.cdml_document.CDMLRenderPrimitive, ...]:
	"""Build portable bond primitives from scalar endpoint intent.

	This compatibility bridge owns fresh OASA topology materialization, label
	and attach targets, and the render context.  It returns only opaque
	operations; no temporary vertex, edge, or graph escapes to Qt items.
	"""
	if not all(math.isfinite(value) for point in (start, end) for value in point):
		raise ValueError("legacy bond rendering requires finite endpoints")
	molecule_model = atom1.molecule_model
	if (
		molecule_model is not None and molecule_model is atom2.molecule_model
		and any(candidate is bond_model for candidate in molecule_model.bonds)
	):
		materialized = _materialize_oasa_molecule(molecule_model)
		render_molecule = materialized.molecule
		edge = materialized.bonds_by_model_identity[id(bond_model)]
		atom_models = tuple(molecule_model.atoms)
		vertices = tuple(
			materialized.atoms_by_model_identity[id(atom_model)]
			for atom_model in atom_models
		)
	else:
		render_molecule = None
		edge = materialize_oasa_bond(bond_model)
		atom_models = (atom1, atom2)
		vertices = (materialize_oasa_atom(atom1), materialize_oasa_atom(atom2))
		edge.vertices = list(vertices)
	# Preserve the historical theme sentinel as a portable semantic role.  The
	# temporary OASA edge remains bridge-local and is discarded after depiction.
	edge.properties_["line_color"] = _compatibility_color(bond_model.line_color)
	shown_vertices, label_targets, attach_targets = _legacy_bond_label_targets(
		atom_models, vertices,
	)
	render_context = oasa.render_lib.data_types.BondRenderContext(
		molecule=render_molecule,
		line_width=bond_model.line_width,
		bond_width=bond_model.bond_width,
		wedge_width=bond_model.wedge_width,
		bold_line_width_multiplier=1.2,
		bond_second_line_shortening=oasa.cdml_standard.bond_second_line_shortening(
			bond_model.double_length_ratio,
		),
		color_bonds=True,
		atom_colors=None,
		shown_vertices=shown_vertices,
		bond_coords={edge: (start, end)},
		bond_coords_provider={edge: (start, end)}.get,
		point_for_atom=None,
		label_targets=label_targets,
		attach_targets=attach_targets,
		attach_constraints=oasa.render_lib.data_types.make_attach_constraints(),
	)
	operations = oasa.render_lib.bond_ops.build_bond_ops(edge, start, end, render_context)
	return oasa.cdml_document.normalize_render_operations(operations)


#============================================
def _compatibility_color(value: str) -> str:
	"""Map the historical default line sentinel to a frontend-neutral role."""
	if value.lower() == _LEGACY_DEFAULT_LINE_COLOR:
		return _BACKEND_FOREGROUND
	return value


#============================================
def _legacy_bond_label_targets(
		atom_models: tuple[bkchem_qt.models.atom_model.AtomModel, ...],
		vertices: tuple[oasa.atom_lib.Atom, ...],
		) -> tuple[set[object], dict[object, object], dict[object, object]]:
	"""Build OASA clipping targets using each endpoint's own display facts."""
	shown_vertices = set()
	label_targets = {}
	attach_targets = {}
	for atom_model, vertex in zip(atom_models, vertices, strict=True):
		if not atom_model.show:
			continue
		shown, labels, attaches = oasa.render_lib.molecule_ops.build_label_attach_targets(
			vertices=[vertex],
			show_hydrogens_on_hetero=bool(atom_model.show_hydrogens),
			font_name=atom_model.font_family,
			font_size=float(atom_model.font_size),
			show_carbon_symbol=(
				atom_model.show and "show" in atom_model.cdml_display_fields
			),
		)
		shown_vertices.update(shown)
		label_targets.update(labels)
		attach_targets.update(attaches)
	return shown_vertices, label_targets, attach_targets


@dataclasses.dataclass(frozen=True)
class _MaterializedOASAMolecule:
	"""One bridge-local graph plus identity associations to Qt wrappers."""

	molecule: oasa.molecule_lib.Molecule
	atoms_by_model_identity: dict[int, oasa.atom_lib.Atom]
	bonds_by_model_identity: dict[int, oasa.bond_lib.Bond]


#============================================
def qt_mol_to_oasa_mol(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> oasa.molecule_lib.Molecule:
	"""Convert a Qt MoleculeModel back to a pure OASA molecule.

	Creates new OASA atom and bond objects suitable for format export
	through OASA codecs or CDML serialization.

	Args:
		mol_model: MoleculeModel to convert.

	Returns:
		oasa.molecule_lib.Molecule with atoms and bonds.
	"""
	return _materialize_oasa_molecule(mol_model).molecule


#============================================
def _materialize_oasa_molecule(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> _MaterializedOASAMolecule:
	"""Create a complete disposable OASA graph and scalar-wrapper association."""
	oasa_mol = oasa.molecule_lib.Molecule()
	if mol_model.mol_id:
		oasa_mol.id = mol_model.mol_id
	if mol_model.name:
		oasa_mol.name = mol_model.name

	# Build a complete fresh OASA graph.  The Qt projection retains none of it.
	atom_by_model_identity = {}
	for am in mol_model.atoms:
		oasa_atom = materialize_oasa_atom(am)
		oasa_mol.add_vertex(oasa_atom)
		atom_by_model_identity[id(am)] = oasa_atom

	# Create bonds and retain the bridge-local association needed by renderers.
	bond_by_model_identity = {}
	for bm in mol_model.bonds:
		oasa_bond = materialize_oasa_bond(bm)
		a1 = bm.atom1
		a2 = bm.atom2
		if a1 is None or a2 is None:
			continue
		v1 = atom_by_model_identity.get(id(a1))
		v2 = atom_by_model_identity.get(id(a2))
		if v1 is None or v2 is None:
			continue
		oasa_mol.add_edge(v1, v2, e=oasa_bond)
		bond_by_model_identity[id(bm)] = oasa_bond

	return _MaterializedOASAMolecule(
		oasa_mol, atom_by_model_identity, bond_by_model_identity,
	)


#============================================
def standalone_atom_chemistry(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> dict[int, tuple[int, int]]:
	"""Calculate connected-graph compatibility facts in one disposable graph.

	The keys are ephemeral ``id(AtomModel)`` values used only by the caller's
	synchronous loop.  No OASA vertex survives the bridge call.
	"""
	materialized = _materialize_oasa_molecule(mol_model)
	return {
		model_identity: (oasa_atom.free_valency, oasa_atom.oxidation_number)
		for model_identity, oasa_atom in materialized.atoms_by_model_identity.items()
	}


#============================================
def _display_atom_properties_to_oasa(
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		oasa_atom: oasa.atom_lib.Atom,
		) -> None:
	"""Copy explicit Qt atom display edits into OASA's CDML property carrier."""
	properties = oasa_atom.properties_
	fields = atom_model.cdml_display_fields
	if "show" in fields:
		properties["show"] = "yes" if atom_model.show else "no"
	if "show_hydrogens" in fields:
		properties["show_hydrogens"] = "on" if atom_model.show_hydrogens else "off"
	if "font_size" in fields:
		properties["font_size"] = str(atom_model.font_size)
	if "font_family" in fields:
		properties["font_family"] = atom_model.font_family
	if "line_color" in fields:
		properties["line_color"] = atom_model.line_color


#============================================
def _display_bond_properties_to_oasa(
		bond_model: bkchem_qt.models.bond_model.BondModel,
		oasa_bond: oasa.bond_lib.Bond,
		) -> None:
	"""Copy supported Qt depiction fields into OASA/CDML writer fields."""
	oasa_bond.line_color = bond_model.line_color
	oasa_bond.wavy_style = bond_model.wavy_style
	oasa_bond.center = bond_model.center
	oasa_bond.line_width = bond_model.line_width
	oasa_bond.bond_width = bond_model.bond_width
	oasa_bond.wedge_width = bond_model.wedge_width
	oasa_bond.double_length_ratio = bond_model.double_length_ratio
	oasa_bond.auto_bond_sign = bond_model.auto_bond_sign
	oasa_bond.equithick = int(bond_model.equithick)
	oasa_bond.simple_double = int(bond_model.simple_double)
	fields = bond_model.cdml_display_fields
	if "line_width" in fields:
		oasa_bond.properties_["line_width"] = str(bond_model.line_width)
	if "bond_width" in fields:
		oasa_bond.properties_["bond_width"] = str(bond_model.bond_width)
	if "wedge_width" in fields:
		oasa_bond.properties_["wedge_width"] = str(bond_model.wedge_width)
	if "center" in fields and bond_model.center is not None:
		oasa_bond.properties_["center"] = "yes" if bond_model.center else "no"
	if "simple_double" in fields:
		oasa_bond.properties_["simple_double"] = str(int(bond_model.simple_double))
	if "auto_sign" in fields:
		oasa_bond.properties_["auto_sign"] = str(bond_model.auto_bond_sign)
	if "double_ratio" in fields:
		oasa_bond.properties_["double_ratio"] = str(bond_model.double_length_ratio)
	if "equithick" in fields:
		oasa_bond.properties_["equithick"] = str(int(bond_model.equithick))
	if "color" in fields:
		oasa_bond.properties_["line_color"] = bond_model.line_color
	if "wavy_style" in fields and bond_model.wavy_style is not None:
		oasa_bond.properties_["wavy_style"] = bond_model.wavy_style
	if "haworth_position" in fields and bond_model.haworth_position is not None:
		oasa_bond.properties_["haworth_position"] = bond_model.haworth_position
	oasa.cdml_bond_io.set_cdml_bond_explicit_fields(
		oasa_bond, fields,
	)


#============================================
def read_codec_file(
		codec_name: str,
		file_obj: object,
		**kwargs,
		) -> list[bkchem_qt.models.molecule_model.MoleculeModel]:
	"""Read a chemistry file via OASA codec and return MoleculeModel list.

	Uses the OASA codec registry to parse the file into an OASA molecule,
	splits disconnected components into separate MoleculeModel instances,
	and generates 2D coordinates if needed.

	Args:
		codec_name: OASA codec name (e.g. 'molfile', 'smiles', 'cdxml').
		file_obj: Open file object to read from.
		**kwargs: Additional keyword arguments passed to the codec.

	Returns:
		List of MoleculeModel instances, one per connected component.
	"""
	codec = oasa.codec_registry.get_codec(codec_name)
	mol = codec.read_file(file_obj, **kwargs)
	if mol is None:
		return []

	# generate 2D coords if not present
	coords_generator.calculate_coords(mol, bond_length=1.0, force=0)

	# split disconnected components
	if not mol.is_connected():
		parts = mol.get_disconnected_subgraphs()
	else:
		parts = [mol]

	# convert each part to a MoleculeModel
	results = []
	for part in parts:
		mol_model = oasa_mol_to_qt_mol(part)
		results.append(mol_model)
	return results


#============================================
def write_codec_file(
		codec_name: str,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		file_obj: object,
		**kwargs,
		) -> None:
	"""Write a MoleculeModel to a file via OASA codec.

	Converts the MoleculeModel back to a pure OASA molecule and delegates
	serialization to the named OASA codec.

	Args:
		codec_name: OASA codec name (e.g. 'molfile', 'smiles', 'cdxml').
		mol_model: MoleculeModel to export.
		file_obj: Open file object to write to.
		**kwargs: Additional keyword arguments passed to the codec.
	"""
	codec = oasa.codec_registry.get_codec(codec_name)
	oasa_mol = qt_mol_to_oasa_mol(mol_model)
	codec.write_file(oasa_mol, file_obj, **kwargs)
