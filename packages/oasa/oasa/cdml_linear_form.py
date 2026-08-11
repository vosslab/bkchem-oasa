"""Backend-owned narrow CDML linear-form conversion and validity checks."""

# Standard Library
import dataclasses

# local repo modules
import oasa.cdml_document


_BOND_LENGTH_PT = 10.0
_OWNER_NAME = "linear_form"


@dataclasses.dataclass(frozen=True)
class LinearFormDetails:
	"""Durable identifiers produced or retained by one conversion."""

	fragment_id: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]


#============================================
def convert(document: object, molecule_id: str, atom_ids: tuple[str, ...]) -> LinearFormDetails:
	"""Apply one validated backend-owned linear-form conversion to ``document``.

	The caller supplies a detached :class:`CDMLDocument`.  This helper owns only
	the narrow authored linear-form grammar; it never receives frontend geometry,
	model objects, or rendering information.
	"""
	cdml = oasa.cdml_document
	molecule = cdml._direct_root_molecule(document, molecule_id)
	atoms, bonds = _direct_graph(molecule)
	if not atom_ids or len(set(atom_ids)) != len(atom_ids):
		raise cdml.CDMLLinearFormError("linear form requires unique selected atom IDs")
	if any(type(identifier) is not str or not identifier for identifier in atom_ids):
		raise cdml.CDMLLinearFormError("linear form atom IDs must be durable nonempty strings")
	if any(identifier not in atoms for identifier in atom_ids):
		raise cdml.CDMLLinearFormError("linear form atom target is not a direct durable atom")
	selected = tuple(atoms[identifier] for identifier in atom_ids)
	points = {atom: _atom_point(atom) for atom in selected}
	path, path_bonds = _ordered_path(selected, bonds, points)
	if path is None:
		raise cdml.CDMLLinearFormError("linear form selection must be one unbranched path")
	deltas = _path_deltas(path, points)
	external_deltas = _external_deltas(selected, bonds, deltas)
	for atom in external_deltas:
		_atom_point(atom)
		_validate_marks(atom)
	for atom in selected:
		_validate_marks(atom)
	owned = _matching_owned_fragment(molecule, tuple(atom.getAttribute("id") for atom in path),
		tuple(bond.getAttribute("id") for bond in path_bonds))
	if owned is not None and _matches_owned_state(owned, path, path_bonds):
		return LinearFormDetails(owned.getAttribute("id"), atom_ids_in_order(path), bond_ids_in_order(path_bonds))
	for atom, (dx_pt, dy_pt) in {**deltas, **external_deltas}.items():
		_move_atom_and_marks(atom, dx_pt, dy_pt)
	for atom in path:
		atom.setAttribute("hydrogens", "on")
	if owned is not None:
		_canonicalize_owned_members(document, owned, path, path_bonds)
	remove_invalid_generated_forms(document, (molecule_id,))
	if owned is not None:
		return LinearFormDetails(owned.getAttribute("id"), atom_ids_in_order(path), bond_ids_in_order(path_bonds))
	used_ids = cdml._candidate_durable_ids(document)
	fragment_id = cdml._next_durable_id("fragment", used_ids)
	fragment = cdml._new_core_element(document, molecule, "fragment")
	fragment.setAttribute("id", fragment_id)
	fragment.setAttribute("type", "linear_form")
	name = cdml._new_core_element(document, fragment, "name")
	name.appendChild(document._dom_document.createTextNode(_OWNER_NAME))
	fragment.appendChild(name)
	for bond in path_bonds:
		member = cdml._new_core_element(document, fragment, "bond")
		member.setAttribute("id", bond.getAttribute("id"))
		fragment.appendChild(member)
	for atom in path:
		member = cdml._new_core_element(document, fragment, "vertex")
		member.setAttribute("id", atom.getAttribute("id"))
		fragment.appendChild(member)
	property_element = cdml._new_core_element(document, fragment, "property")
	property_element.setAttribute("name", "bond_length")
	property_element.setAttribute("value", "10")
	property_element.setAttribute("type", "IntType")
	fragment.appendChild(property_element)
	molecule.appendChild(fragment)
	return LinearFormDetails(fragment_id, atom_ids_in_order(path), bond_ids_in_order(path_bonds))


#============================================
def remove_invalid_generated_forms(document: object, molecule_ids: tuple[str, ...]) -> bool:
	"""Remove only invalid narrow backend-generated forms from selected roots."""
	changed = False
	for molecule_id in molecule_ids:
		molecule = oasa.cdml_document._direct_root_molecule(document, molecule_id)
		owned_forms = tuple(
			(fragment, members)
			for fragment in oasa.cdml_document._element_children(molecule)
			if (members := _owned_members(fragment)) is not None
		)
		if not owned_forms:
			continue
		atoms = _unique_direct_records(molecule, "atom")
		bonds = _unique_direct_records(molecule, "bond")
		for fragment, members in owned_forms:
			atom_ids, bond_ids = members
			if not _form_is_valid(atoms, bonds, atom_ids, bond_ids):
				molecule.removeChild(fragment)
				changed = True
	return changed


#============================================
def is_exact_generated_form(element: object) -> bool:
	"""Return whether one element is the exact narrow generated grammar."""
	return _owned_members(element) is not None


#============================================
def atom_ids_in_order(atoms: tuple[object, ...]) -> tuple[str, ...]:
	"""Return path vertices in durable path order."""
	return tuple(atom.getAttribute("id") for atom in atoms)


#============================================
def bond_ids_in_order(bonds: tuple[object, ...]) -> tuple[str, ...]:
	"""Return path edges in durable path order."""
	return tuple(bond.getAttribute("id") for bond in bonds)


#============================================
def _direct_graph(molecule: object) -> tuple[dict[str, object], dict[str, object]]:
	"""Read a closed direct atom/bond graph, rejecting opaque ambiguity."""
	cdml = oasa.cdml_document
	atoms = {}
	bonds = {}
	for child in cdml._element_children(molecule):
		if not cdml._is_cdml_element(child):
			continue
		name = cdml._local_name(child)
		if name not in ("atom", "bond"):
			continue
		identifier = child.getAttribute("id")
		if not identifier or identifier in (atoms if name == "atom" else bonds):
			raise cdml.CDMLLinearFormError("linear form molecule has ambiguous durable IDs")
		if name == "atom":
			atoms[identifier] = child
		else:
			bonds[identifier] = child
	for bond in bonds.values():
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		if not start or not end or start == end or start not in atoms or end not in atoms:
			raise cdml.CDMLLinearFormError("linear form bond endpoints are invalid")
	for atom in atoms.values():
		_atom_point(atom)
		_validate_marks(atom)
	return atoms, bonds


#============================================
def _unique_direct_records(molecule: object, record_name: str) -> dict[str, object]:
	"""Index only unambiguous direct records needed by generated metadata."""
	records = {}
	ambiguous_ids = set()
	for child in oasa.cdml_document._element_children(molecule):
		if not oasa.cdml_document._is_cdml_element(child):
			continue
		if oasa.cdml_document._local_name(child) != record_name:
			continue
		identifier = child.getAttribute("id")
		if not identifier or identifier in ambiguous_ids:
			continue
		if identifier in records:
			del records[identifier]
			ambiguous_ids.add(identifier)
			continue
		records[identifier] = child
	return records


#============================================
def _atom_point(atom: object) -> tuple[object, float, float]:
	"""Return one finite direct atom coordinate in PostScript points."""
	cdml = oasa.cdml_document
	points = [
		child for child in cdml._element_children(atom)
		if cdml._is_cdml_element(child) and cdml._local_name(child) == "point"
	]
	if len(points) != 1 or not points[0].hasAttribute("x") or not points[0].hasAttribute("y"):
		raise cdml.CDMLLinearFormError("linear form atom requires one direct point")
	try:
		x_cm = cdml._insertion_coordinate(points[0].getAttribute("x"))
		y_cm = cdml._insertion_coordinate(points[0].getAttribute("y"))
	except cdml.CDMLValidationError as error:
		raise cdml.CDMLLinearFormError("linear form atom has invalid geometry") from error
	return points[0], x_cm / cdml._POINT_CM_PER_POSTSCRIPT_POINT, y_cm / cdml._POINT_CM_PER_POSTSCRIPT_POINT


#============================================
def _ordered_path(selected: tuple[object, ...], bonds: dict[str, object], points: dict[object, tuple[object, float, float]]) -> tuple[tuple[object, ...] | None, tuple[object, ...]]:
	"""Derive one deterministic unbranched induced path from durable CDML."""
	neighbors = {atom: [] for atom in selected}
	edges = {}
	for bond in bonds.values():
		start = next(atom for atom in selected if atom.getAttribute("id") == bond.getAttribute("start")) if bond.getAttribute("start") in {atom.getAttribute("id") for atom in selected} else None
		end = next(atom for atom in selected if atom.getAttribute("id") == bond.getAttribute("end")) if bond.getAttribute("end") in {atom.getAttribute("id") for atom in selected} else None
		if start is not None and end is not None:
			neighbors[start].append(end)
			neighbors[end].append(start)
			edges[frozenset((start, end))] = bond
	if any(len(values) > 2 for values in neighbors.values()):
		return None, ()
	if len(selected) == 1:
		return selected, ()
	ends = [atom for atom, values in neighbors.items() if len(values) == 1]
	if len(ends) != 2:
		return None, ()
	start = min(ends, key=lambda atom: (points[atom][1], points[atom][2], atom.getAttribute("id")))
	path = []
	previous = None
	current = start
	while current is not None:
		path.append(current)
		next_atoms = [atom for atom in neighbors[current] if atom is not previous]
		if len(next_atoms) > 1:
			return None, ()
		previous, current = current, next_atoms[0] if next_atoms else None
	if len(path) != len(selected):
		return None, ()
	return tuple(path), tuple(edges[frozenset((first, second))] for first, second in zip(path, path[1:]))


#============================================
def _path_deltas(path: tuple[object, ...], points: dict[object, tuple[object, float, float]]) -> dict[object, tuple[float, float]]:
	"""Return point-space offsets that preserve the chosen endpoint position."""
	start_x = points[path[0]][1]
	start_y = points[path[0]][2]
	return {
		atom: (start_x + index * _BOND_LENGTH_PT - points[atom][1], start_y - points[atom][2])
		for index, atom in enumerate(path)
	}


#============================================
def _external_deltas(selected: tuple[object, ...], bonds: dict[str, object], deltas: dict[object, tuple[float, float]]) -> dict[object, tuple[float, float]]:
	"""Attach each external component to exactly one selected path vertex."""
	selected_set = set(selected)
	by_atom = {atom: [] for atom in selected}
	for bond in bonds.values():
		start_id, end_id = bond.getAttribute("start"), bond.getAttribute("end")
		for atom in selected:
			if atom.getAttribute("id") == start_id:
				by_atom.setdefault(atom, []).append((bond, end_id))
			if atom.getAttribute("id") == end_id:
				by_atom.setdefault(atom, []).append((bond, start_id))
	atom_by_id = {}
	for bond in bonds.values():
		for identifier in (bond.getAttribute("start"), bond.getAttribute("end")):
			atom_by_id.setdefault(identifier, None)
	for atom in selected:
		atom_by_id[atom.getAttribute("id")] = atom
	# reconstruct unselected direct atoms from endpoints once; their identity is
	# available through bond parent lookup without accepting a frontend graph.
	for bond in bonds.values():
		for candidate in oasa.cdml_document._element_children(bond.parentNode):
			if oasa.cdml_document._is_cdml_element(candidate) and oasa.cdml_document._local_name(candidate) == "atom":
				atom_by_id[candidate.getAttribute("id")] = candidate
	visited = set()
	result = {}
	for anchor in selected:
		for _bond, other_id in by_atom.get(anchor, []):
			other = atom_by_id[other_id]
			if other in selected_set:
				continue
			if other in visited:
				continue
			component = set()
			pending = [other]
			anchors = set()
			while pending:
				current = pending.pop()
				if current in component or current in selected_set:
					continue
				component.add(current)
				for bond in bonds.values():
					start_id, end_id = bond.getAttribute("start"), bond.getAttribute("end")
					if current.getAttribute("id") == start_id:
						neighbor = atom_by_id[end_id]
					elif current.getAttribute("id") == end_id:
						neighbor = atom_by_id[start_id]
					else:
						continue
					if neighbor in selected_set:
						anchors.add(neighbor)
					else:
						pending.append(neighbor)
			if len(anchors) != 1:
				raise oasa.cdml_document.CDMLLinearFormError("linear form external component has multiple selected anchors")
			component_anchor = next(iter(anchors))
			for member in component:
				result[member] = deltas[component_anchor]
			visited.update(component)
	return result


#============================================
def _validate_marks(atom: object) -> None:
	"""Reject malformed explicit direct mark coordinates before all mutation."""
	cdml = oasa.cdml_document
	for mark in cdml._element_children(atom):
		if not cdml._is_cdml_element(mark) or cdml._local_name(mark) != "mark":
			continue
		has_x, has_y = mark.hasAttribute("x"), mark.hasAttribute("y")
		if has_x != has_y:
			raise cdml.CDMLLinearFormError("linear form mark coordinates must be paired")
		if has_x:
			try:
				cdml._insertion_coordinate(mark.getAttribute("x"))
				cdml._insertion_coordinate(mark.getAttribute("y"))
			except cdml.CDMLValidationError as error:
				raise cdml.CDMLLinearFormError("linear form mark has invalid geometry") from error


#============================================
def _move_atom_and_marks(atom: object, dx_pt: float, dy_pt: float) -> None:
	"""Translate one previously validated atom and its explicit mark positions."""
	cdml = oasa.cdml_document
	point, x_pt, y_pt = _atom_point(atom)
	point.setAttribute("x", _point_text(x_pt + dx_pt))
	point.setAttribute("y", _point_text(y_pt + dy_pt))
	for mark in cdml._element_children(atom):
		if not cdml._is_cdml_element(mark) or cdml._local_name(mark) != "mark" or not mark.hasAttribute("x"):
			continue
		mark_x = cdml._insertion_coordinate(mark.getAttribute("x")) / cdml._POINT_CM_PER_POSTSCRIPT_POINT
		mark_y = cdml._insertion_coordinate(mark.getAttribute("y")) / cdml._POINT_CM_PER_POSTSCRIPT_POINT
		mark.setAttribute("x", _point_text(mark_x + dx_pt))
		mark.setAttribute("y", _point_text(mark_y + dy_pt))


#============================================
def _point_text(value: float) -> str:
	"""Write a finite PostScript-point coordinate without an invented unit."""
	if not oasa.cdml_document.math.isfinite(value):
		raise oasa.cdml_document.CDMLLinearFormError("linear form coordinate is nonfinite")
	return format(value, ".15g")


#============================================
def _matching_owned_fragment(molecule: object, atom_ids: tuple[str, ...], bond_ids: tuple[str, ...]) -> object | None:
	"""Return the unique owned fragment for this path, if one already exists."""
	matches = [
		fragment for fragment in oasa.cdml_document._element_children(molecule)
		if _owned_path_matches(_owned_members(fragment), atom_ids, bond_ids)
	]
	if len(matches) > 1:
		raise oasa.cdml_document.CDMLLinearFormError(
			"linear form has ambiguous matching generated metadata",
		)
	return matches[0] if matches else None


#============================================
def _owned_path_matches(
		members: tuple[tuple[str, ...], tuple[str, ...]] | None,
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> bool:
	"""Match one exact narrow record to a path independent of old direction."""
	if members is None:
		return False
	member_atom_ids, member_bond_ids = members
	forward = member_atom_ids == atom_ids and member_bond_ids == bond_ids
	reverse = (
		member_atom_ids == tuple(reversed(atom_ids))
		and member_bond_ids == tuple(reversed(bond_ids))
	)
	return forward or reverse


#============================================
def _canonicalize_owned_members(
		document: object, fragment: object,
		path: tuple[object, ...], path_bonds: tuple[object, ...],
		) -> None:
	"""Repair one exact narrow record in place while retaining its durable ID."""
	children = oasa.cdml_document._element_children(fragment)
	property_element = children[-1]
	for child in children[1:-1]:
		fragment.removeChild(child)
	for bond in path_bonds:
		member = oasa.cdml_document._new_core_element(document, fragment, "bond")
		member.setAttribute("id", bond.getAttribute("id"))
		fragment.insertBefore(member, property_element)
	for atom in path:
		member = oasa.cdml_document._new_core_element(document, fragment, "vertex")
		member.setAttribute("id", atom.getAttribute("id"))
		fragment.insertBefore(member, property_element)


#============================================
def _owned_members(fragment: object) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	"""Recognize only the exact narrow grammar authored by this helper."""
	cdml = oasa.cdml_document
	if not cdml._is_cdml_element(fragment) or cdml._local_name(fragment) != "fragment":
		return None
	if {fragment.attributes.item(index).name for index in range(fragment.attributes.length)} != {"id", "type"} or fragment.getAttribute("type") != "linear_form" or not fragment.getAttribute("id"):
		return None
	if not _whitespace_text_only(fragment):
		return None
	children = cdml._element_children(fragment)
	if len(children) < 3 or cdml._local_name(children[0]) != "name" or cdml._local_name(children[-1]) != "property":
		return None
	name = children[0]
	if not cdml._is_cdml_element(name) or name.attributes.length or cdml._element_children(name) or not _text_only(name, _OWNER_NAME):
		return None
	property_element = children[-1]
	if not cdml._is_cdml_element(property_element) or {property_element.attributes.item(index).name for index in range(property_element.attributes.length)} != {"name", "value", "type"} or property_element.getAttribute("name") != "bond_length" or property_element.getAttribute("value") != "10" or property_element.getAttribute("type") != "IntType" or cdml._element_children(property_element) or not _whitespace_text_only(property_element):
		return None
	bond_ids = []
	atom_ids = []
	seen_vertex = False
	for child in children[1:-1]:
		if not cdml._is_cdml_element(child) or cdml._element_children(child) or not _whitespace_text_only(child):
			return None
		if {child.attributes.item(index).name for index in range(child.attributes.length)} != {"id"} or not child.getAttribute("id"):
			return None
		if cdml._local_name(child) == "bond" and not seen_vertex:
			bond_ids.append(child.getAttribute("id"))
		elif cdml._local_name(child) == "vertex":
			seen_vertex = True
			atom_ids.append(child.getAttribute("id"))
		else:
			return None
	if not atom_ids or len(set(atom_ids)) != len(atom_ids) or len(set(bond_ids)) != len(bond_ids):
		return None
	return tuple(atom_ids), tuple(bond_ids)


#============================================
def _whitespace_text_only(element: object) -> bool:
	"""Return whether a node has only whitespace character-data children."""
	for node in element.childNodes:
		if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
			if node.data.strip():
				return False
		elif node.nodeType != node.ELEMENT_NODE:
			return False
	return True


#============================================
def _text_only(element: object, expected: str) -> bool:
	"""Return whether a node has only the exact authored character data."""
	values = []
	for node in element.childNodes:
		if node.nodeType not in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
			return False
		values.append(node.data)
	return "".join(values) == expected


#============================================
def _matches_owned_state(fragment: object, path: tuple[object, ...], path_bonds: tuple[object, ...]) -> bool:
	"""Return whether the exact owned metadata and all owned state are canonical."""
	atoms, bonds = _direct_graph(path[0].parentNode)
	canonical_members = (atom_ids_in_order(path), bond_ids_in_order(path_bonds))
	return _owned_members(fragment) == canonical_members and _form_is_valid(
		atoms, bonds,
		canonical_members[0], canonical_members[1],
	) and all(atom.getAttribute("hydrogens") == "on" for atom in path)


#============================================
def _form_is_valid(atoms: dict[str, object], bonds: dict[str, object], atom_ids: tuple[str, ...], bond_ids: tuple[str, ...]) -> bool:
	"""Return whether a narrow owned form still represents its path exactly."""
	if len(bond_ids) != max(0, len(atom_ids) - 1) or any(identifier not in atoms for identifier in atom_ids) or any(identifier not in bonds for identifier in bond_ids):
		return False
	selected_ids = set(atom_ids)
	induced_bond_ids = {
		identifier for identifier, bond in bonds.items()
		if bond.getAttribute("start") in selected_ids and bond.getAttribute("end") in selected_ids
	}
	if induced_bond_ids != set(bond_ids):
		return False
	try:
		points = [_atom_point(atoms[identifier]) for identifier in atom_ids]
	except oasa.cdml_document.CDMLLinearFormError:
		return False
	for index, bond_id in enumerate(bond_ids):
		bond = bonds[bond_id]
		if {bond.getAttribute("start"), bond.getAttribute("end")} != {atom_ids[index], atom_ids[index + 1]}:
			return False
	first_x, first_y = points[0][1], points[0][2]
	return all(
		abs(y - first_y) < 1e-9 and abs(x - (first_x + index * _BOND_LENGTH_PT)) < 1e-9
		for index, (_point, x, y) in enumerate(points)
	)
