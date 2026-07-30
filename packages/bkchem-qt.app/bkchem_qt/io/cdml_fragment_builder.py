"""Build bounded selected-object CDML fragments for Clipboard proposals."""

# Standard Library
import xml.dom.minidom as dom

# local repo modules
import oasa.cdml_writer
import oasa.safe_xml
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.models.fragment_model
import bkchem_qt.models.molecule_model

_SUPPORTED_MARK_TYPES = {"plus", "minus", "radical", "electronpair"}
_QT_OWNED_MARK_TYPES = {"atom_number"}

#============================================
def build_top_level_fragment(
		document: bkchem_qt.models.document.Document, objects: list[object],
		) -> str:
	"""Build a selected top-level CDML proposal for backend insertion.

	The result contains only the requested top-level objects. It is not a
	complete document serializer and does not publish files or update a saved
	baseline. The backend validates, allocates durable IDs, and accepts it.
	"""
	result = dom.Document()
	root = result.createElement("cdml")
	root.setAttribute("version", str(oasa.cdml_writer.DEFAULT_CDML_VERSION))
	root.setAttribute("xmlns", str(oasa.cdml_writer.CDML_NAMESPACE))
	result.appendChild(root)
	for object_model in objects:
		root.appendChild(_serialize_object(result, object_model, document))
	_ensure_fragment_ids(root)
	return result.toxml(encoding="utf-8").decode("utf-8")


#============================================
def _ensure_fragment_ids(root: dom.Element) -> None:
	"""Give copied molecule and bond elements source IDs for backend insertion."""
	used_ids = {
		element.getAttribute("id") for element in _elements(root)
		if element.hasAttribute("id") and element.getAttribute("id")
	}
	for element in _elements(root):
		if element.tagName not in {"molecule", "bond"}:
			continue
		if element.hasAttribute("id") and element.getAttribute("id"):
			continue
		candidate = "%s1" % element.tagName
		fresh_id = _fresh_id(candidate, used_ids)
		element.setAttribute("id", fresh_id)
		used_ids.add(fresh_id)


#============================================
def _fresh_id(candidate: str, used_ids: set[str]) -> str:
	"""Return an unused source label for one clipboard fragment object."""
	if candidate not in used_ids:
		return candidate
	index = 2
	while "%s-%d" % (candidate, index) in used_ids:
		index += 1
	return "%s-%d" % (candidate, index)


#============================================
def _elements(element: dom.Element | None) -> list[dom.Element]:
	"""Return one element and all element descendants in document order."""
	if element is None:
		return []
	result = [element]
	for child in element.childNodes:
		if child.nodeType == child.ELEMENT_NODE:
			result.extend(_elements(child))
	return result

#============================================
def _match_elements_by_id(
		generated: list[dom.Element], source: list[dom.Element],
		) -> list[tuple[dom.Element, dom.Element]]:
	"""Pair current elements with source elements by ID, then stable order."""
	by_id = {element.getAttribute("id"): element for element in source
			if element.getAttribute("id")}
	unused = list(source)
	pairs: list[tuple[dom.Element, dom.Element]] = []
	for current in generated:
		current_id = current.getAttribute("id")
		old = by_id.get(current_id) if current_id else None
		if old not in unused:
			old = None
		if old is None and not current_id and unused:
			old = unused[0]
		if old is None:
			continue
		if old in unused:
			unused.remove(old)
		pairs.append((current, old))
	return pairs


#============================================
def _bond_has_only_model_atoms(
		bond_el: dom.Element, source_atom_ids: set[str],
		) -> bool:
	"""Return whether a source bond has two OASA-modelled atom endpoints."""
	has_model_atoms = (
			bond_el.getAttribute("start") in source_atom_ids
			and bond_el.getAttribute("end") in source_atom_ids
		)
	return has_model_atoms


#============================================
def _match_bonds(
		generated: list[dom.Element], source: list[dom.Element],
		) -> list[tuple[dom.Element, dom.Element]]:
	"""Pair regenerated bonds with modelled source bonds without pseudo bonds."""
	by_id = {element.getAttribute("id"): element for element in source
			if element.getAttribute("id")}
	unused = list(source)
	pairs: list[tuple[dom.Element, dom.Element]] = []
	for current in generated:
		current_id = current.getAttribute("id")
		old = by_id.get(current_id) if current_id else None
		if old not in unused:
			old = None
		if old is None and not current_id:
			endpoints = {
					current.getAttribute("start"), current.getAttribute("end"),
					}
			for candidate in unused:
				candidate_endpoints = {
						candidate.getAttribute("start"),
						candidate.getAttribute("end"),
						}
				if candidate_endpoints == endpoints:
					old = candidate
					break
		if old is None and not current_id and unused:
			old = unused[0]
		if old is None:
			continue
		unused.remove(old)
		pairs.append((current, old))
	return pairs


#============================================
def _merge_generated_child(
		result: dom.Document, current: dom.Element, old: dom.Element,
		is_atom: bool,
		) -> None:
	"""Keep source-only display attributes and nested XML on a current node."""
	for name, value in _attributes(old).items():
		if not current.hasAttribute(name):
			current.setAttribute(name, value)
	for old_child in _element_children(old):
		if _local_name(old_child) == "point":
			_merge_point_attributes(current, old_child)
			continue
		if _local_name(old_child) == "font":
			current_font = _first_child(current, "font")
			if current_font is not None:
				for name, value in _attributes(old_child).items():
					current_font.setAttribute(name, value)
				continue
			current.appendChild(result.importNode(old_child, deep=True))
			continue
		if is_atom and _local_name(old_child) == "mark":
			continue
		current.appendChild(result.importNode(old_child, deep=True))


#============================================
def _merge_point_attributes(current: dom.Element, old_point: dom.Element) -> None:
	"""Retain source-only attributes on a regenerated atom point."""
	current_point = _first_child(current, "point")
	if current_point is None:
		return
	for name, value in _attributes(old_point).items():
		if not current_point.hasAttribute(name):
			current_point.setAttribute(name, value)


#============================================
def _serialize_object(
		result: dom.Document, obj: object,
		document: bkchem_qt.models.document.Document,
		) -> dom.Element:
	"""Serialize a molecule or presentation DTO in stack order."""
	if isinstance(obj, bkchem_qt.models.molecule_model.MoleculeModel):
		return _serialize_molecule(result, obj, document)
	presentation = obj
	if not isinstance(presentation, bkchem_qt.models.document_object.PresentationObject):
		raise TypeError("Document object must be a molecule or PresentationObject")
	raw = presentation.raw_xml
	if not presentation.supported:
		return _import_raw(result, raw or "<%s/>" % presentation.kind)
	element = _import_raw(result, raw) if raw else result.createElement(presentation.kind)
	attrs = presentation.attributes
	for name, value in attrs.items():
		element.setAttribute(str(name), str(value))
	object_id = presentation.object_id
	if object_id:
		element.setAttribute("id", str(object_id))
	_points = presentation.points
	if _points:
		_replace_points(result, element, _points)
	bounds = presentation.bounds
	if bounds:
		x1, y1, width, height = bounds
		for name, value in zip(
				("x1", "y1", "x2", "y2"),
				(x1, y1, x1 + width, y1 + height),
				):
			element.setAttribute(name, _px_to_cm_text(value))
	font_attrs = presentation.font_attributes
	if font_attrs:
		font = _first_child(element, "font")
		if font is None:
			font = result.createElement("font")
			element.appendChild(font)
		for name, value in font_attrs.items():
			font.setAttribute(str(name), str(value))
	ftext_xml = presentation.xml_ftext
	if ftext_xml is not None:
		ftext = _first_child(element, "ftext")
		if ftext is None:
			ftext = result.createElement("ftext")
			element.appendChild(ftext)
		_replace_inner_xml(result, ftext, ftext_xml)
	return element


#============================================
def _serialize_molecule(
		result: dom.Document,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		document: bkchem_qt.models.document.Document,
		) -> dom.Element:
	"""Write chemistry, then merge the loaded presentation envelope by ID."""
	source = mol_model.cdml_source_xml
	source_el = None
	if source:
		source_el = _import_raw(result, source)
	oasa_molecule = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(mol_model)
	reserved_ids = _serialization_reserved_ids(document, mol_model)
	element = oasa.cdml_writer.write_cdml_molecule_element(
		oasa_molecule, doc=result, coord_to_text=_px_to_cm_text,
		reserved_atom_ids=reserved_ids, reserved_bond_ids=reserved_ids,
	)
	if source_el is not None:
		for name, value in _attributes(source_el).items():
			if not element.hasAttribute(name):
				element.setAttribute(name, value)
		element = _merge_molecule_children(result, element, source_el, mol_model)
	_merge_marks(result, element, mol_model, document)
	_apply_atom_number_attributes(element, mol_model)
	return element


#============================================
def _apply_atom_number_attributes(
		element: dom.Element,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> None:
	"""Write model-owned numbering fields and remove legacy number marks.

	A source molecule can contain unsupported pseudoatoms in addition to the
	editable OASA atom wrappers. Stable IDs select only wrapper-owned atoms,
	which leaves every unsupported source atom unchanged.
	"""
	atom_elements = _direct_children(element, "atom")
	models_by_id = {
			str(atom_model._chem_atom.id): atom_model
			for atom_model in mol_model.atoms
			if getattr(atom_model._chem_atom, "id", None)
		}
	if len(atom_elements) == len(mol_model.atoms):
		atom_pairs = zip(atom_elements, mol_model.atoms)
	else:
		atom_pairs = (
			(atom_el, models_by_id.get(atom_el.getAttribute("id")))
			for atom_el in atom_elements
		)
	for atom_el, atom_model in atom_pairs:
		if atom_model is None:
			continue
		if atom_el.hasAttribute("number"):
			atom_el.removeAttribute("number")
		if atom_el.hasAttribute("show_number"):
			atom_el.removeAttribute("show_number")
		if atom_model.number is None:
			continue
		atom_el.setAttribute("number", str(atom_model.number))
		atom_el.setAttribute(
				"show_number", "yes" if atom_model.show_number else "no",
			)


#============================================
def _serialization_reserved_ids(
		document: bkchem_qt.models.document.Document,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> set[str]:
	"""Collect document-global IDs that output allocation must not reuse.

	The current molecule's live graph IDs are deliberately released after the
	collection step: they remain the identity used to merge source-backed XML.
	Everything else, including deleted source nodes and opaque fragment/group
	references, stays reserved only in this local output calculation.
	"""
	external_ids = _document_cdml_ids(document, exclude_molecule=mol_model)
	reserved = set(external_ids)
	reserved.update(_source_cdml_ids(mol_model.cdml_source_xml))
	reserved.update(_molecule_metadata_ids(mol_model))
	active_ids = {
			str(getattr(atom._chem_atom, "id", "") or "")
			for atom in mol_model.atoms
		}
	active_ids.update(
			str(getattr(bond._chem_bond, "id", "") or "")
			for bond in mol_model.bonds
		)
	active_ids.discard("")
	for identifier in active_ids:
		if identifier not in external_ids:
			reserved.discard(identifier)
	return reserved


#============================================
def _document_cdml_ids(
		document: bkchem_qt.models.document.Document,
		exclude_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		) -> set[str]:
	"""Return identifiers and references retained by the editable document."""
	identifiers = set()
	for molecule in document.molecules:
		if molecule is exclude_molecule:
			continue
		identifiers.update(_molecule_metadata_ids(molecule))
		if molecule.mol_id:
			identifiers.add(molecule.mol_id)
		for atom_model in molecule.atoms:
			atom_id = getattr(atom_model._chem_atom, "id", None)
			if atom_id:
				identifiers.add(str(atom_id))
		for bond_model in molecule.bonds:
			bond_id = getattr(bond_model._chem_bond, "id", None)
			if bond_id:
				identifiers.add(str(bond_id))
	for object_model in document.presentation_objects:
		if object_model.object_id:
			identifiers.add(object_model.object_id)
	for unsupported in document.unsupported_content:
		if unsupported.object_id:
			identifiers.add(unsupported.object_id)
	return {identifier for identifier in identifiers if identifier}


#============================================
def _molecule_metadata_ids(molecule: object) -> set[str]:
	"""Return molecule-owned non-graph IDs and durable references."""
	identifiers = set()
	if getattr(molecule, "mol_id", ""):
		identifiers.add(molecule.mol_id)
	for group_model in molecule.groups:
		identifiers.update(_group_cdml_ids(group_model))
	for fragment in molecule.fragments:
		identifiers.add(fragment.fragment_id)
		identifiers.update(fragment.atom_ids)
		identifiers.update(fragment.bond_ids)
		identifiers.update(_raw_cdml_ids(fragment.raw_xml))
		for raw_xml in fragment.unknown_children_xml:
			identifiers.update(_raw_cdml_ids(raw_xml))
	for raw_xml in molecule.unsupported_fragment_xml:
		identifiers.update(_raw_cdml_ids(raw_xml))
	identifiers.update(_template_marker_ids(molecule))
	return {identifier for identifier in identifiers if identifier}


#============================================
def _group_cdml_ids(group_model: object) -> set[str]:
	"""Return group and retained attachment IDs without modifying the group."""
	identifiers = {str(getattr(group_model, "group_id", "") or "")}
	for attachment in getattr(group_model, "attachments", ()):
		identifiers.update((
			str(getattr(attachment, "bond_id", "") or ""),
			str(getattr(attachment, "start_id", "") or ""),
			str(getattr(attachment, "end_id", "") or ""),
		))
	return {identifier for identifier in identifiers if identifier}


#============================================
def _template_marker_ids(molecule: object) -> set[str]:
	"""Return current template attachment IDs held by the Qt model."""
	identifiers = set()
	for marker in (
			getattr(molecule, "t_atom", None),
			getattr(molecule, "t_bond_first", None),
			getattr(molecule, "t_bond_second", None),
		):
		chemistry = getattr(marker, "_chem_atom", None)
		if chemistry is None:
			chemistry = getattr(marker, "_chem_bond", None)
		identifier = getattr(chemistry, "id", None)
		if identifier:
			identifiers.add(str(identifier))
	return identifiers


#============================================
def _source_cdml_ids(raw_xml: str | None) -> set[str]:
	"""Read ID-bearing source XML attributes without changing the source."""
	return _raw_cdml_ids(raw_xml)


#============================================
def _raw_cdml_ids(raw_xml: str | None) -> set[str]:
	"""Collect CDML IDs and node references from a retained XML fragment."""
	if not raw_xml:
		return set()
	try:
		root = oasa.safe_xml.parse_dom_from_string(raw_xml).documentElement
	except ValueError:
		return set()
	identifiers = set()
	for element in [root, *list(_element_children_recursive(root))]:
		for name in ("id", "start", "end", "idref"):
			value = element.getAttribute(name)
			if value:
				identifiers.add(value)
	return identifiers


#============================================
def _element_children_recursive(element: dom.Element) -> list[dom.Element]:
	"""Return nested element descendants in source order."""
	children = []
	for child in _element_children(element):
		children.append(child)
		children.extend(_element_children_recursive(child))
	return children


#============================================
def _next_free_id(prefix: str, reserved: set[str]) -> str:
	"""Return the next unused stable CDML identifier for an edited object."""
	index = 1
	candidate = "%s%d" % (prefix, index)
	while candidate in reserved:
		index += 1
		candidate = "%s%d" % (prefix, index)
	return candidate


#============================================
def _merge_molecule_children(
		result: dom.Document, generated: dom.Element, source: dom.Element,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> dom.Element:
	"""Merge generated chemistry into source order without losing pseudoatoms.

	OASA deliberately models only ordinary ``atom`` vertices.  Native CDML also
	permits query, group, and text vertices, whose incident bonds must remain
	in the source envelope rather than being mistaken for deleted OASA bonds.
	"""
	source_atoms = _direct_children(source, "atom")
	generated_atoms = _direct_children(generated, "atom")
	atom_pairs = _match_elements_by_id(generated_atoms, source_atoms)
	atom_id_remap: dict[str, str] = {}
	for current, old in atom_pairs:
		old_id = old.getAttribute("id")
		current_id = current.getAttribute("id")
		if old_id:
			if current_id:
				atom_id_remap[current_id] = old_id
			current.setAttribute("id", old_id)
		_merge_generated_child(result, current, old, is_atom=True)

	source_atom_ids = {atom.getAttribute("id") for atom in source_atoms}
	source_bonds = _direct_children(source, "bond")
	model_bonds = [
			bond for bond in source_bonds
			if _bond_has_only_model_atoms(bond, source_atom_ids)
		]
	generated_bonds = _direct_children(generated, "bond")
	for current in generated_bonds:
		for endpoint in ("start", "end"):
			current_id = current.getAttribute(endpoint)
			if current_id in atom_id_remap:
				current.setAttribute(endpoint, atom_id_remap[current_id])
	bond_pairs = _match_bonds(generated_bonds, model_bonds)
	for current, old in bond_pairs:
		old_id = old.getAttribute("id")
		if old_id:
			current.setAttribute("id", old_id)
		_merge_generated_child(result, current, old, is_atom=False)

	merged = result.importNode(source, deep=True)
	atom_replacements = {id(old): current for current, old in atom_pairs}
	bond_replacements = {id(old): current for current, old in bond_pairs}
	matched_source_atoms = set(atom_replacements)
	matched_source_bonds = set(bond_replacements)
	matched_source_atom_ids = {
			old.getAttribute("id") for _current, old in atom_pairs
			if old.getAttribute("id")
		}
	fragments_by_id = {fragment.fragment_id: fragment for fragment in mol_model.fragments}
	source_fragment_ids = {fragment.getAttribute("id")
			for fragment in _direct_children(source, "fragment")
			if fragment.getAttribute("id")}
	unsupported_fragment_ids = _unsupported_fragment_ids(
			mol_model.unsupported_fragment_xml,
		)
	matched_fragment_ids = set()
	for source_child, old_child in zip(
			_element_children(source), list(_element_children(merged)),
			):
		original_id = id(source_child)
		if _local_name(source_child) == "atom":
			if original_id not in matched_source_atoms:
				merged.removeChild(old_child)
				continue
			replacement = atom_replacements[original_id]
			merged.replaceChild(result.importNode(replacement, deep=True), old_child)
			continue
		if _local_name(source_child) == "bond":
			endpoints = {
				source_child.getAttribute("start"), source_child.getAttribute("end"),
				}
			if any(endpoint in source_atom_ids
					and endpoint not in matched_source_atom_ids for endpoint in endpoints):
				merged.removeChild(old_child)
				continue
			if _bond_has_only_model_atoms(source_child, source_atom_ids):
				if original_id not in matched_source_bonds:
					merged.removeChild(old_child)
					continue
				replacement = bond_replacements[original_id]
				merged.replaceChild(result.importNode(replacement, deep=True), old_child)
			continue
		if _local_name(source_child) == "fragment":
			fragment_id = source_child.getAttribute("id")
			fragment = fragments_by_id.get(fragment_id)
			if fragment is not None and fragment_id not in matched_fragment_ids:
				merged.replaceChild(_serialize_fragment(result, fragment), old_child)
				matched_fragment_ids.add(fragment_id)
				continue
			if fragment_id in unsupported_fragment_ids or not fragment_id:
				continue
			merged.removeChild(old_child)

	matched_generated_atoms = {id(current) for current, _old in atom_pairs}
	matched_generated_bonds = {id(current) for current, _old in bond_pairs}
	for current in generated_atoms:
		if id(current) not in matched_generated_atoms:
			merged.appendChild(result.importNode(current, deep=True))
	for current in generated_bonds:
		if id(current) not in matched_generated_bonds:
			merged.appendChild(result.importNode(current, deep=True))
	for fragment in mol_model.fragments:
		if fragment.fragment_id not in matched_fragment_ids:
			merged.appendChild(_serialize_fragment(result, fragment))
	for raw_xml in mol_model.unsupported_fragment_xml:
		fragment_id = _fragment_id_from_raw(raw_xml)
		if fragment_id and fragment_id in source_fragment_ids:
			continue
		merged.appendChild(_import_raw(result, raw_xml))
	return merged


#============================================
def _serialize_fragment(
		result: dom.Document,
		fragment: bkchem_qt.models.fragment_model.FragmentModel,
		) -> dom.Element:
	"""Serialize fragment metadata without interpreting legacy property values."""
	if fragment.raw_xml:
		return _import_raw(result, fragment.raw_xml)
	element = result.createElement("fragment")
	for name, value in fragment.attributes:
		element.setAttribute(name, value)
	element.setAttribute("id", fragment.fragment_id)
	element.setAttribute("type", fragment.fragment_type)
	if fragment.name:
		name_el = result.createElement("name")
		name_el.appendChild(result.createTextNode(fragment.name))
		element.appendChild(name_el)
	for bond_id in fragment.bond_ids:
		bond_el = result.createElement("bond")
		bond_el.setAttribute("id", bond_id)
		element.appendChild(bond_el)
	for atom_id in fragment.atom_ids:
		vertex_el = result.createElement("vertex")
		vertex_el.setAttribute("id", atom_id)
		element.appendChild(vertex_el)
	for property_model in fragment.properties:
		property_el = result.createElement("property")
		for name, value in property_model.attributes:
			property_el.setAttribute(name, value)
		property_el.setAttribute("name", property_model.name)
		property_el.setAttribute("value", property_model.value)
		if property_model.type_name:
			property_el.setAttribute("type", property_model.type_name)
		element.appendChild(property_el)
	for raw_xml in fragment.unknown_children_xml:
		element.appendChild(_import_raw(result, raw_xml))
	return element


#============================================
def _unsupported_fragment_ids(raw_fragments: tuple[str, ...]) -> set[str]:
	"""Return IDs of retained raw fragments that must not be edited or dropped."""
	return {fragment_id for raw_xml in raw_fragments
			if (fragment_id := _fragment_id_from_raw(raw_xml))}


#============================================
def _fragment_id_from_raw(raw_xml: str) -> str:
	"""Read only a raw fragment's identifier for source-aware preservation."""
	parsed = oasa.safe_xml.parse_dom_from_string(raw_xml)
	element = parsed.documentElement
	return element.getAttribute("id")


#============================================
def _merge_marks(
		result: dom.Document, molecule_el: dom.Element,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		document: bkchem_qt.models.document.Document,
		) -> None:
	"""Regenerate supported marks from the model layer by atom wrapper identity."""
	marks = document.marks
	source = mol_model.cdml_source_xml
	source_atoms_by_id: dict[str, dom.Element] = {}
	if source is not None:
		source_atoms = _direct_children(_import_raw(result, source), "atom")
		source_atoms_by_id = {
				atom.getAttribute("id"): atom for atom in source_atoms
				if atom.getAttribute("id")
			}
	for atom_el, atom_model in zip(
			_direct_children(molecule_el, "atom"), mol_model.atoms,
			):
		for mark_el in list(_direct_children(atom_el, "mark")):
			atom_el.removeChild(mark_el)
		source_atom = source_atoms_by_id.get(atom_el.getAttribute("id"))
		if source_atom is not None:
			for source_mark in _direct_children(source_atom, "mark"):
				mark_type = source_mark.getAttribute("type")
				if (
						mark_type not in _SUPPORTED_MARK_TYPES
						and mark_type not in _QT_OWNED_MARK_TYPES
						):
					atom_el.appendChild(result.importNode(source_mark, deep=True))
		for mark in marks:
			if mark.atom_model is not atom_model:
				continue
			raw = mark.raw_xml
			mark_el = _import_raw(result, raw) if raw else result.createElement("mark")
			for name, value in mark.attributes.items():
				mark_el.setAttribute(str(name), str(value))
			atom_el.appendChild(mark_el)


#============================================
def _serialize_reaction(
		result: dom.Document,
		reaction: bkchem_qt.models.document_object.ReactionRecord,
		) -> dom.Element:
	"""Serialize a reaction while preserving the typed reference order."""
	raw = reaction.raw_xml
	element = _import_raw(result, raw) if raw else result.createElement("reaction")
	refs = reaction.refs
	if refs and _reaction_refs(element) != refs:
		for child in list(_element_children(element)):
			element.removeChild(child)
		for tag, idref in refs:
			ref = result.createElement(str(tag))
			if idref:
				ref.setAttribute("idref", str(idref))
			element.appendChild(ref)
	return element


#============================================
def _reaction_refs(element: dom.Element) -> list[tuple[str, str]]:
	"""Return the editable reference identity without flattening raw children."""
	refs = [(_local_name(child), child.getAttribute("idref"))
			for child in _element_children(element)]
	return refs


#============================================
def _replace_points(
		result: dom.Document, element: dom.Element,
		points: list[tuple[float, float, float | None]],
		) -> None:
	"""Mutate direct point children to match editable scene coordinates."""
	existing = _direct_children(element, "point")
	for index, values in enumerate(points):
		point = existing[index] if index < len(existing) else result.createElement("point")
		x, y, z = values
		point.setAttribute("x", _px_to_cm_text(x))
		point.setAttribute("y", _px_to_cm_text(y))
		if z is not None:
			point.setAttribute("z", _px_to_cm_text(z))
		elif point.hasAttribute("z"):
			point.removeAttribute("z")
		if index >= len(existing):
			element.appendChild(point)
	for point in existing[len(points):]:
		element.removeChild(point)


#============================================
def _all_attributes(element: dom.Element | None) -> dict[str, str]:
	"""Return every XML attribute, including namespace declarations."""
	if element is None:
		return {}
	return {element.attributes.item(index).name: element.attributes.item(index).value
			for index in range(element.attributes.length)}


#============================================
def _attributes(element: dom.Element | None) -> dict[str, str]:
	"""Return model attributes without serializer-only namespace declarations."""
	return {name: value for name, value in _all_attributes(element).items()
			if name != "xmlns" and not name.startswith("xmlns:")}


#============================================
def _element_children(element: dom.Element) -> list[dom.Element]:
	"""Return direct element children, excluding whitespace and text nodes."""
	return [child for child in element.childNodes
			if child.nodeType == child.ELEMENT_NODE]


#============================================
def _direct_children(element: dom.Element, tag: str) -> list[dom.Element]:
	"""Return direct element children whose local CDML tag matches."""
	return [child for child in _element_children(element) if _local_name(child) == tag]


#============================================
def _local_name(element: dom.Element) -> str:
	"""Return a CDML element's semantic name independently of its prefix."""
	return element.localName or element.tagName.rsplit(":", maxsplit=1)[-1]


#============================================
def _first_child(element: dom.Element, tag: str) -> dom.Element | None:
	"""Return the first direct matching CDML child, if present."""
	children = _direct_children(element, tag)
	return children[0] if children else None


#============================================
def _element_text(element: dom.Element) -> str:
	"""Return direct text content without interpreting embedded XML."""
	return "".join(child.data for child in element.childNodes
				if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE))


#============================================
def _raw_xml(element: dom.Element) -> str:
	"""Serialize an element with namespace declarations inherited from parents."""
	result = dom.Document()
	copy = result.importNode(element, deep=True)
	for name, value in _in_scope_namespace_attributes(element).items():
		if not copy.hasAttribute(name):
			copy.setAttribute(name, value)
	result.appendChild(copy)
	return copy.toxml()


#============================================
def _inner_xml(element: dom.Element | None) -> str:
	"""Serialize child XML that remains valid outside its original ancestor."""
	if element is None:
		return ""
	return "".join(
			_raw_inner_xml_element(child)
			if child.nodeType == child.ELEMENT_NODE else child.toxml()
			for child in element.childNodes
		)


#============================================
def _raw_inner_xml_element(element: dom.Element) -> str:
	"""Serialize one formatted-text child without adding the CDML default XMLNS."""
	result = dom.Document()
	copy = result.importNode(element, deep=True)
	inherited = _in_scope_namespace_attributes(element)

	# The saved child will be inserted under ``ftext`` in the CDML default
	# namespace.  Adding that inherited declaration to a simple <b> or <i>
	# changes the exposed formatted-text string on every load/save cycle.
	if (copy.hasAttribute("xmlns")
			and copy.getAttribute("xmlns") == inherited.get("xmlns")):
		copy.removeAttribute("xmlns")

	# Prefix declarations remain necessary because the formatted-text fragment is
	# parsed beneath a temporary namespace-free wrapper before it is reinserted.
	for name, value in inherited.items():
		if name == "xmlns" or copy.hasAttribute(name):
			continue
		copy.setAttribute(name, value)
	result.appendChild(copy)
	text = copy.toxml()
	return text


#============================================
def _in_scope_namespace_attributes(element: dom.Element) -> dict[str, str]:
	"""Return the namespace declarations visible from ``element``'s parents."""
	ancestors: list[dom.Element] = []
	parent = element.parentNode
	while isinstance(parent, dom.Element):
		ancestors.append(parent)
		parent = parent.parentNode
	attributes: dict[str, str] = {}
	for ancestor in reversed(ancestors):
		for name, value in _all_attributes(ancestor).items():
			if name == "xmlns" or name.startswith("xmlns:"):
				attributes[name] = value
	return attributes


#============================================
def _import_raw(result: dom.Document, raw: str) -> dom.Element:
	"""Import a raw fragment while removing declarations inherited from output."""
	parsed = oasa.safe_xml.parse_dom_from_string(raw)
	imported = result.importNode(parsed.documentElement, deep=True)
	root = result.documentElement
	root_namespaces = {
			name: value for name, value in _all_attributes(root).items()
			if name == "xmlns" or name.startswith("xmlns:")
		}
	_strip_redundant_namespace_declarations(imported, root_namespaces)
	return imported


#============================================
def _strip_redundant_namespace_declarations(
		element: dom.Element, inherited: dict[str, str],
		) -> None:
	"""Drop synthetic declarations already supplied by the output CDML root."""
	visible = dict(inherited)
	for name, value in list(_all_attributes(element).items()):
		if name != "xmlns" and not name.startswith("xmlns:"):
			continue
		if visible.get(name) == value:
			element.removeAttribute(name)
		else:
			visible[name] = value
	for child in _element_children(element):
		_strip_redundant_namespace_declarations(child, visible)


#============================================
def _replace_inner_xml(result: dom.Document, element: dom.Element, inner: str) -> None:
	"""Replace children from a fragment, retaining only needed namespaces."""
	for child in list(element.childNodes):
		element.removeChild(child)
	if inner:
		wrapper = oasa.safe_xml.parse_dom_from_string("<wrapper>%s</wrapper>" % inner)
		root = result.documentElement
		root_namespaces = {
				name: value for name, value in _all_attributes(root).items()
				if name == "xmlns" or name.startswith("xmlns:")
		}
		for child in wrapper.documentElement.childNodes:
			imported = result.importNode(child, deep=True)
			if isinstance(imported, dom.Element):
				_strip_redundant_namespace_declarations(imported, root_namespaces)
			element.appendChild(imported)


#============================================
def _coord_to_points(value: str | None) -> float:
	"""Convert CDML centimetres to points while retaining raw pixel values."""
	if not value:
		return 0.0
	text = str(value).strip()
	if text.endswith("cm"):
		return float(text[:-2]) * oasa.cdml_writer.POINTS_PER_CM
	if text.endswith("px"):
		text = text[:-2]
	return float(text)


#============================================
def _point_values(element: dom.Element) -> tuple[float, float, float | None]:
	"""Return a CDML point's coordinates converted to scene points."""
	x = _coord_to_points(element.getAttribute("x"))
	y = _coord_to_points(element.getAttribute("y"))
	z_text = element.getAttribute("z")
	return (x, y, _coord_to_points(z_text) if z_text else None)


#============================================
def _bounds_values(
		element: dom.Element,
		) -> tuple[float, float, float, float] | None:
	"""Return CDML bounds as scene x, y, width, and height when complete."""
	if not all(element.hasAttribute(name) for name in ("x1", "y1", "x2", "y2")):
		return None
	x1, y1, x2, y2 = tuple(_coord_to_points(element.getAttribute(name))
			for name in ("x1", "y1", "x2", "y2"))
	return (x1, y1, x2 - x1, y2 - y1)


#============================================
def _px_to_cm_text(value: float | None) -> str:
	"""Convert scene points to canonical CDML centimetre text."""
	points = 0.0 if value is None else float(value)
	return "%.3fcm" % (points / oasa.cdml_writer.POINTS_PER_CM)
