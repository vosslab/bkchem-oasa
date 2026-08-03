"""Detached coordinate-only CDML geometry repair helpers."""

# Standard Library
import math

# local repo modules
import oasa.cdml_document
import oasa.cdml_writer
import oasa.coords_generator
import oasa.repair_ops


#============================================
def _element_children(node: object) -> list:
	"""Return direct element children in source order."""
	return [
		child for child in node.childNodes
		if child.nodeType == child.ELEMENT_NODE
	]


#============================================
def _local_name(node: object) -> str:
	"""Return one XML local name without changing the compatibility DOM."""
	name = getattr(node, "localName", None) or getattr(node, "tagName", "")
	return str(name).rsplit(":", 1)[-1]


#============================================
def _coordinate_to_points(value: str, attribute: str) -> float:
	"""Parse one finite CDML coordinate into PostScript points."""
	try:
		points = oasa.cdml_writer._cm_to_float_coord(value)
	except (TypeError, ValueError) as exc:
		raise ValueError("atom point %s must be a finite coordinate" % attribute) from exc
	if not math.isfinite(points):
		raise ValueError("atom point %s must be a finite coordinate" % attribute)
	return points


#============================================
def _point_to_cdml(points: float) -> str:
	"""Format one finite point coordinate in the backend CDML unit convention."""
	if not math.isfinite(points):
		raise ValueError("repaired coordinates must be finite")
	return "%.3fcm" % (points / oasa.cdml_writer.POINTS_PER_CM)


#============================================
def _validate_target_molecule(
		molecule: object, allow_foreign_children: bool = False,
		) -> dict[str, object]:
	"""Validate the narrow lossless molecule subset and return direct atom points."""
	children = _element_children(molecule)
	if not allow_foreign_children and any(
			not oasa.cdml_document._is_cdml_element(child) for child in children
		):
		raise ValueError("geometry repair supports only direct atom and bond children")
	core_children = [child for child in children if oasa.cdml_document._is_cdml_element(child)]
	if any(_local_name(child) not in ("atom", "bond") for child in core_children):
		raise ValueError("geometry repair supports only direct core atom and bond children")
	atom_elements = [child for child in core_children if _local_name(child) == "atom"]
	bond_elements = [child for child in core_children if _local_name(child) == "bond"]
	if not atom_elements or not bond_elements:
		raise ValueError("geometry repair requires a bonded direct-atom molecule")
	points_by_atom_id = {}
	for atom in atom_elements:
		atom_id = atom.getAttribute("id")
		if not atom_id or atom_id in points_by_atom_id:
			raise ValueError("geometry repair requires unique durable atom IDs")
		if not atom.getAttribute("name"):
			raise ValueError("geometry repair requires named direct atoms")
		points = [
			child for child in _element_children(atom)
			if (
				oasa.cdml_document._is_cdml_element(child)
				and _local_name(child) == "point"
			)
		]
		if len(points) != 1:
			raise ValueError("geometry repair requires one direct point per atom")
		_coordinate_to_points(points[0].getAttribute("x"), "x")
		_coordinate_to_points(points[0].getAttribute("y"), "y")
		points_by_atom_id[atom_id] = points[0]
	for bond in bond_elements:
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		if start not in points_by_atom_id or end not in points_by_atom_id:
			raise ValueError("geometry repair bond endpoints must name direct atoms")
	return points_by_atom_id


#============================================
def _root_molecules(document: object) -> dict[str, object]:
	"""Return direct-root core molecules keyed by one unambiguous durable ID."""
	root_molecules = {}
	for child in _element_children(document._dom_document.documentElement):
		if (
			not oasa.cdml_document._is_cdml_element(child)
			or _local_name(child) != "molecule"
			):
			continue
		identifier = child.getAttribute("id")
		if identifier:
			if identifier in root_molecules:
				raise ValueError("geometry repair target ID is ambiguous: %s" % identifier)
			root_molecules[identifier] = child
	return root_molecules


#============================================
def _selected_molecules(
		document: object, molecule_ids: tuple[str, ...], allow_foreign_children: bool = False,
		) -> list[tuple[object, dict[str, object], object]]:
	"""Validate every target before any detached coordinate mutation occurs."""
	root_molecules = _root_molecules(document)
	targets = []
	for molecule_id in molecule_ids:
		molecule = root_molecules.get(molecule_id)
		if molecule is None:
			raise ValueError("geometry repair requires a direct-root molecule ID: %s" % molecule_id)
		points_by_atom_id = _validate_target_molecule(molecule, allow_foreign_children)
		oasa_molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(molecule)
		if oasa_molecule is None or len(oasa_molecule.atoms) != len(points_by_atom_id):
			raise ValueError("geometry repair does not support this molecule form")
		atom_ids = [getattr(atom, "id", None) for atom in oasa_molecule.atoms]
		if set(atom_ids) != set(points_by_atom_id) or len(atom_ids) != len(set(atom_ids)):
			raise ValueError("geometry repair could not preserve direct atom identity")
		targets.append((molecule, points_by_atom_id, oasa_molecule))
	return targets


#============================================
def normalize_bond_lengths_in_document(
		document: object, molecule_ids: tuple[str, ...], target_bond_length_pt: float,
		) -> None:
	"""Patch selected direct-root molecules in a detached complete CDML document.

	Args:
		document: Detached ``CDMLDocument`` compatibility document.
		molecule_ids: Durable direct-root molecule IDs to repair.
		target_bond_length_pt: Requested scene-space bond length in points.

	Raises:
		ValueError: The requested molecule cannot be losslessly repaired.
	"""
	for _molecule, points_by_atom_id, oasa_molecule in _selected_molecules(document, molecule_ids):
		oasa.repair_ops.normalize_bond_lengths(oasa_molecule, target_bond_length_pt)
		for atom in oasa_molecule.atoms:
			point = points_by_atom_id[atom.id]
			new_x = _point_to_cdml(atom.x)
			new_y = _point_to_cdml(atom.y)
			old_x = _point_to_cdml(_coordinate_to_points(point.getAttribute("x"), "x"))
			old_y = _point_to_cdml(_coordinate_to_points(point.getAttribute("y"), "y"))
			if old_x != new_x:
				point.setAttribute("x", new_x)
			if old_y != new_y:
				point.setAttribute("y", new_y)


#============================================
def normalize_bond_angles_in_document(
		document: object, molecule_ids: tuple[str, ...], target_spacing_pt: float,
		) -> None:
	"""Snap selected non-ring bond angles while preserving complete CDML content.

	The target spacing is used only for degenerate outgoing bond vectors.  All
	targets validate before this detached document has any coordinates patched.
	"""
	targets = _selected_molecules(document, molecule_ids, allow_foreign_children=True)
	for _molecule, _points_by_atom_id, oasa_molecule in targets:
		oasa.repair_ops.validate_bond_angle_normalization_topology(oasa_molecule)
	for _molecule, points_by_atom_id, oasa_molecule in targets:
		oasa.repair_ops.normalize_bond_angles(oasa_molecule, target_spacing_pt)
		if any(
				getattr(atom, "id", None) not in points_by_atom_id
				or not math.isfinite(atom.x) or not math.isfinite(atom.y)
				for atom in oasa_molecule.atoms
			):
			raise ValueError("bond-angle normalization produced invalid direct atom coordinates")
		for atom in oasa_molecule.atoms:
			point = points_by_atom_id[atom.id]
			new_x = _point_to_cdml(atom.x)
			new_y = _point_to_cdml(atom.y)
			old_x = _point_to_cdml(_coordinate_to_points(point.getAttribute("x"), "x"))
			old_y = _point_to_cdml(_coordinate_to_points(point.getAttribute("y"), "y"))
			if old_x != new_x:
				point.setAttribute("x", new_x)
			if old_y != new_y:
				point.setAttribute("y", new_y)


#============================================
def normalize_rings_in_document(
		document: object, molecule_ids: tuple[str, ...], target_spacing_pt: float,
		) -> None:
	"""Regularize one simple ring per selected molecule without losing CDML.

	All target graphs complete bounded-topology validation before the detached
	document receives any coordinate patch.  Ring-free targets intentionally
	remain semantic no-ops.
	"""
	targets = _selected_molecules(document, molecule_ids, allow_foreign_children=True)
	for _molecule, _points_by_atom_id, oasa_molecule in targets:
		oasa.repair_ops.validate_single_ring_normalization_topology(oasa_molecule)
	for _molecule, points_by_atom_id, oasa_molecule in targets:
		oasa.repair_ops.normalize_single_ring(oasa_molecule, target_spacing_pt)
		if any(
				getattr(atom, "id", None) not in points_by_atom_id
				or not math.isfinite(atom.x) or not math.isfinite(atom.y)
				for atom in oasa_molecule.atoms
			):
			raise ValueError("ring normalization produced invalid direct atom coordinates")
		for atom in oasa_molecule.atoms:
			point = points_by_atom_id[atom.id]
			new_x = _point_to_cdml(atom.x)
			new_y = _point_to_cdml(atom.y)
			old_x = _point_to_cdml(_coordinate_to_points(point.getAttribute("x"), "x"))
			old_y = _point_to_cdml(_coordinate_to_points(point.getAttribute("y"), "y"))
			if old_x != new_x:
				point.setAttribute("x", new_x)
			if old_y != new_y:
				point.setAttribute("y", new_y)


#============================================
def straighten_bonds_in_document(
		document: object, molecule_ids: tuple[str, ...], target_spacing_pt: float,
		) -> None:
	"""Straighten selected terminal bonds while preserving complete CDML content.

	``target_spacing_pt`` is the common geometry-repair request envelope.  This
	kind preserves every nondegenerate terminal bond length and therefore does
	not use it.  All direct-root target validation and detached graph repair
	finish before any direct CDML point receives an x/y patch.
	"""
	# Keep the public request envelope uniform while documenting this unused value.
	del target_spacing_pt
	targets = _selected_molecules(document, molecule_ids, allow_foreign_children=True)
	for _molecule, _points_by_atom_id, oasa_molecule in targets:
		oasa.repair_ops.straighten_bonds(oasa_molecule)
	if any(
			getattr(atom, "id", None) not in points_by_atom_id
			or not math.isfinite(atom.x) or not math.isfinite(atom.y)
			for _molecule, points_by_atom_id, oasa_molecule in targets
			for atom in oasa_molecule.atoms
		):
		raise ValueError("straighten bonds produced invalid direct atom coordinates")
	for _molecule, points_by_atom_id, oasa_molecule in targets:
		for atom in oasa_molecule.atoms:
			point = points_by_atom_id[atom.id]
			new_x = _point_to_cdml(atom.x)
			new_y = _point_to_cdml(atom.y)
			old_x = _point_to_cdml(_coordinate_to_points(point.getAttribute("x"), "x"))
			old_y = _point_to_cdml(_coordinate_to_points(point.getAttribute("y"), "y"))
			if old_x != new_x:
				point.setAttribute("x", new_x)
			if old_y != new_y:
				point.setAttribute("y", new_y)


#============================================
def clean_geometry_in_document(
		document: object, molecule_ids: tuple[str, ...], target_bond_length_pt: float,
		) -> None:
	"""Regenerate selected layouts while preserving each source molecule centroid.

	Only detached OASA molecule graphs are used for layout.  Durable atom IDs,
	not graph iteration position, identify the direct CDML points to patch.
	"""
	targets = _selected_molecules(document, molecule_ids, allow_foreign_children=True)
	for _molecule, points_by_atom_id, oasa_molecule in targets:
		source_coordinates = {
			atom_id: (
				_coordinate_to_points(point.getAttribute("x"), "x"),
				_coordinate_to_points(point.getAttribute("y"), "y"),
			)
			for atom_id, point in points_by_atom_id.items()
		}
		oasa.coords_generator.calculate_coords(
			oasa_molecule, bond_length=target_bond_length_pt, force=1,
		)
		if any(
			getattr(atom, "id", None) not in source_coordinates
			or not math.isfinite(atom.x) or not math.isfinite(atom.y)
			for atom in oasa_molecule.atoms
		):
			raise ValueError("clean geometry produced invalid direct atom coordinates")
		source_center_x = sum(value[0] for value in source_coordinates.values()) / len(source_coordinates)
		source_center_y = sum(value[1] for value in source_coordinates.values()) / len(source_coordinates)
		layout_center_x = sum(atom.x for atom in oasa_molecule.atoms) / len(oasa_molecule.atoms)
		layout_center_y = sum(atom.y for atom in oasa_molecule.atoms) / len(oasa_molecule.atoms)
		shift_x = source_center_x - layout_center_x
		shift_y = source_center_y - layout_center_y
		for atom in oasa_molecule.atoms:
			point = points_by_atom_id[atom.id]
			new_x = _point_to_cdml(atom.x + shift_x)
			new_y = _point_to_cdml(atom.y + shift_y)
			old_x = _point_to_cdml(source_coordinates[atom.id][0])
			old_y = _point_to_cdml(source_coordinates[atom.id][1])
			if old_x != new_x:
				point.setAttribute("x", new_x)
			if old_y != new_y:
				point.setAttribute("y", new_y)


#============================================
def snap_to_hex_grid_in_document(
		document: object, molecule_ids: tuple[str, ...], spacing_pt: float,
		) -> None:
	"""Snap selected molecules to the shared displayed hex lattice.

	All eligible targets are validated before the detached candidate changes.
	Durable atom IDs, rather than graph traversal order, map repaired OASA
	coordinates back to their direct CDML points.  Comparison uses canonical
	point spellings so a lexical no-op preserves the source point attributes.

	Args:
		document: Detached ``CDMLDocument`` compatibility document.
		molecule_ids: Durable direct-root molecule IDs to repair.
		spacing_pt: Positive displayed hex-grid spacing in PostScript points.

	Raises:
		ValueError: A selected molecule cannot be losslessly snapped.
	"""
	targets = _selected_molecules(document, molecule_ids, allow_foreign_children=True)
	for _molecule, points_by_atom_id, oasa_molecule in targets:
		oasa.repair_ops.snap_to_hex_grid(oasa_molecule, spacing_pt)
		if any(
				getattr(atom, "id", None) not in points_by_atom_id
				or not math.isfinite(atom.x) or not math.isfinite(atom.y)
				for atom in oasa_molecule.atoms
			):
			raise ValueError("hex-grid snap produced invalid direct atom coordinates")
		for atom in oasa_molecule.atoms:
			point = points_by_atom_id[atom.id]
			new_x = _point_to_cdml(atom.x)
			new_y = _point_to_cdml(atom.y)
			old_x = _point_to_cdml(_coordinate_to_points(point.getAttribute("x"), "x"))
			old_y = _point_to_cdml(_coordinate_to_points(point.getAttribute("y"), "y"))
			if old_x != new_x:
				point.setAttribute("x", new_x)
			if old_y != new_y:
				point.setAttribute("y", new_y)
