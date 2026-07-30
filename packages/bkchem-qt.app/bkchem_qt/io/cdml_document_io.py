"""Decode backend canonical CDML into disposable Qt projections.

This module accepts complete backend CDML only to rebuild frontend state. OASA
owns complete persistent documents, including paper, presentation objects,
reactions, marks, and unknown XML. Qt publication uses backend snapshots, and
Clipboard proposal construction lives in ``cdml_fragment_builder``.
"""

# Standard Library
import dataclasses
import xml.dom.minidom as dom

# local repo modules
import oasa.cdml_writer
import oasa.cdml_xml
import oasa.safe_xml

import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.models.fragment_model
import bkchem_qt.models.group_model
import bkchem_qt.models.molecule_model
import bkchem_qt.canvas.document_projection


_DRAWING_TAGS = {
	"arrow", "plus", "text", "rect", "oval", "square", "circle",
	"polygon", "polyline",
}
_HEADER_TAGS = {"info", "metadata", "paper", "viewport", "standard"}
_SUPPORTED_MARK_TYPES = {"plus", "minus", "radical", "electronpair"}
_MODELED_PAPER_ATTRIBUTES = {
	"type", "orientation", "size_x", "size_y", "crop_svg",
	"crop_margin", "use_real_minus", "replace_minus",
}
# The legacy Tk frontend projects atom numbers as a generated mark.  The Qt
# model owns that presentation state directly through ``number`` and
# ``show_number`` attributes, so retaining this generated mark would create a
# second stale label after a clear-and-save operation.
_QT_OWNED_MARK_TYPES = {"atom_number"}


#============================================
@dataclasses.dataclass(frozen=True)
class PreparedProjection:
	"""Fresh, detached Qt projection decoded from complete canonical CDML.

	The bundle is deliberately frontend-only: it holds a new Qt ``Document``
	and scene-less graphics wrappers that a document session may install later.
	It neither changes OASA state nor serializes a candidate document.
	"""
	document: bkchem_qt.models.document.Document
	molecule_projections: tuple[tuple[object, tuple[object, ...]], ...]
	presentation_items: tuple[object, ...]
	# Atom-owned marks are declared with their parent wrapper.  They are not
	# scene roots and installation must never infer that ownership from scene().
	mark_parent_items: tuple[tuple[object, tuple[object, ...]], ...]
	mark_items: tuple[object, ...]


#============================================
def prepare_projection_from_cdml(
		complete_cdml: str, retirement_reaper: object | None = None,
		) -> PreparedProjection:
	"""Decode canonical CDML into a complete, scene-less Qt projection.

	The caller owns the returned bundle and must either install it into a
	session or call :func:`dispose_prepared_projection`.  Building completes
	before any live scene is touched, so a decoding or graphics failure cannot
	partially replace the current projection.
	"""
	document = load_cdml_document_string(complete_cdml)
	molecule_projections = []
	presentation_items = []
	mark_items = []
	mark_parent_items = []
	try:
		# Imported locally because file actions retain the transitional decoder
		# as an import compatibility dependency.  The helper itself only creates
		# detached molecule wrappers and does not mutate a scene or document.
		import bkchem_qt.actions.file_actions
		built_molecules = bkchem_qt.actions.file_actions._build_molecule_projections(
			document.molecules,
		)
		for molecule, items in built_molecules:
			molecule_projections.append((molecule, tuple(items)))

		atom_items = {}
		for _molecule, items in molecule_projections:
			for item in items:
				atom_model = getattr(item, "atom_model", None)
				if atom_model is not None:
					atom_items[atom_model] = item

		for model in document.presentation_objects:
			item = bkchem_qt.canvas.document_projection.create_presentation_item(
				model,
			)
			if item is not None:
				presentation_items.append(item)
		for model in document.marks:
			atom_item = atom_items.get(model.atom_model)
			if atom_item is None:
				continue
			item = bkchem_qt.canvas.document_projection.create_mark_item(
				model, atom_item,
			)
			if item is not None:
				mark_items.append(item)
				mark_parent_items.append((atom_item, (item,)))
		return PreparedProjection(
			document=document,
			molecule_projections=tuple(molecule_projections),
			presentation_items=tuple(presentation_items),
			mark_parent_items=tuple(mark_parent_items),
			mark_items=tuple(mark_items),
		)
	except Exception:
		_dispose_projection_parts(
			document, molecule_projections, presentation_items, mark_items,
			retirement_reaper,
		)
		raise


#============================================
def dispose_prepared_projection(
		prepared: PreparedProjection, retirement_reaper: object | None = None,
		) -> None:
	"""Release a prepared projection that was never installed into a scene."""
	_dispose_projection_parts(
		prepared.document,
		list(prepared.molecule_projections),
		list(prepared.presentation_items),
		list(prepared.mark_items), retirement_reaper,
	)


#============================================
def _dispose_projection_parts(
		document: bkchem_qt.models.document.Document,
		molecule_projections: list, presentation_items: list,
		mark_items: list, retirement_reaper: object | None = None,
		) -> None:
	"""Disconnect detached graphics bindings before releasing their models."""
	items = list(mark_items)
	items.extend(presentation_items)
	for _molecule, molecule_items in molecule_projections:
		items.extend(molecule_items)
	first_error = None
	try:
		bkchem_qt.canvas.document_projection.dispose_detached_items(
			items, reaper=retirement_reaper,
		)
	except Exception as exc:
		first_error = exc
	try:
		document.clear()
	except Exception as exc:
		if first_error is None:
			first_error = exc
	finally:
		# Always sever the prepared Document's QObject ownership after an item
		# cleanup fault.  It must never survive as a hidden owner of detached
		# models or graphics callbacks.
		try:
			document.setParent(None)
		except Exception as exc:
			if first_error is None:
				first_error = exc
		try:
			document.deleteLater()
		except Exception as exc:
			if first_error is None:
				first_error = exc
	if first_error is not None:
		raise RuntimeError(
			"Prepared projection was released after a disposal failure",
		) from first_error


#============================================
def load_cdml_document_file(
		file_path: str, bond_length_pt: float | None = None,
		preserve_coordinates: bool = True,
		) -> bkchem_qt.models.document.Document:
	"""Load a complete CDML drawing from ``file_path``.

	Native CDML defaults to preserving its scene coordinates.  Callers importing
	into a normalized layout can pass ``preserve_coordinates=False`` and a target
	bond length.
	"""
	with open(file_path, "r", encoding="utf-8") as source:
		return load_cdml_document_string(
			source.read(), bond_length_pt=bond_length_pt,
			preserve_coordinates=preserve_coordinates,
		)


#============================================
def load_cdml_document_string(
		text: str, bond_length_pt: float | None = None,
		preserve_coordinates: bool = True,
		) -> bkchem_qt.models.document.Document:
	"""Load a complete CDML XML string into a document model."""
	dom_doc = oasa.safe_xml.parse_dom_from_string(text)
	root = dom_doc.documentElement
	if root is None or _local_name(root) != "cdml":
		raise ValueError("CDML document must have a <cdml> root element")

	document = bkchem_qt.models.document.Document()
	header_elements = {tag: [] for tag in _HEADER_TAGS}
	envelope = None
	state = {
		"paper": None,
		"reactions": [],
		"external_data": [],
		"unsupported": [],
		"trailing": [],
	}
	atom_lookup: dict[str, object] = {}

	for child_position, child in enumerate(_element_children(root), start=1):
		tag = _local_name(child)
		if tag in _HEADER_TAGS and _is_direct_core_cdml_child(child):
			header = _raw_xml(child)
			header_elements[tag].append(header)
			continue
		if tag == "molecule":
			mol_model = _read_molecule(child, bond_length_pt, preserve_coordinates)
			if mol_model is None:
				unsupported = _unsupported(
						child, "molecule could not be decoded",
						"/cdml/molecule[%d]" % child_position,
					)
				state["unsupported"].append(unsupported)
				document.add_presentation_object(
						_presentation(child, supported=False), mark_dirty=False,
					)
				continue
			# Legacy CDML can omit atom and bond IDs.  Give every loaded
			# model/source pair a shared ID before it is exposed for editing;
			# matching the remaining nodes by position at a later save would
			# attach deleted nodes' display XML to their survivors.
			# Import into a detached DOM so inherited namespace declarations stay
			# on the retained fragment instead of being stripped against ``root``.
			source_el = _import_raw(dom.Document(), _raw_xml(child))
			_normalize_loaded_source_ids(mol_model, source_el)
			_load_atom_number_fields(mol_model, source_el)
			mol_model.cdml_source_xml = _raw_xml(source_el)
			_parse_fragments(mol_model, source_el, state["unsupported"], child_position)
			_parse_groups(mol_model, source_el, state["unsupported"], child_position)
			document.add_molecule(mol_model, mark_dirty=False)
			for atom_el, atom_model in zip(
					_direct_children(source_el, "atom"), mol_model.atoms,
					):
				atom_id = atom_el.getAttribute("id")
				if atom_id:
					atom_lookup[atom_id] = atom_model
			_parse_marks(
					document, source_el, atom_lookup, state["unsupported"], child_position,
					)
			_report_unrendered_molecule_children(
					source_el, state["unsupported"], child_position,
					)
			continue
		if tag in _DRAWING_TAGS:
			document.add_presentation_object(
					_presentation(child, supported=True), mark_dirty=False,
					)
			continue
		if tag == "reaction":
			state["reactions"].append(_reaction(child))
			continue
		if tag == "external-data":
			state["external_data"].append(_raw_xml(child))
			continue
		unsupported = _unsupported(
				child, "unsupported top-level CDML element",
				"/cdml/%s[%d]" % (tag, child_position),
				)
		state["unsupported"].append(unsupported)
		document.add_presentation_object(
				_presentation(child, supported=False), mark_dirty=False,
				)

	info_xml = header_elements["info"]
	metadata_xml = header_elements["metadata"]
	standard_xml = header_elements["standard"]
	paper_xml = header_elements["paper"][0] if header_elements["paper"] else None
	viewport_xml = header_elements["viewport"][0] if header_elements["viewport"] else None
	paper_el = _import_raw(dom_doc, paper_xml) if paper_xml else None
	viewport_el = _import_raw(dom_doc, viewport_xml) if viewport_xml else None
	state["paper"] = bkchem_qt.models.document_object.PaperModel(
		attributes=_attributes(paper_el), viewport_attributes=_attributes(viewport_el),
		raw_xml=paper_xml, viewport_raw_xml=viewport_xml,
	)
	extra_headers = []
	for tag in ("paper", "viewport"):
		extra_headers.extend(header_elements[tag][1:])
	envelope = bkchem_qt.models.document_object.CdmlEnvelope(
		root_attributes=_all_attributes(root),
		info_xml=info_xml, metadata_xml=metadata_xml, standard_xml=standard_xml,
		extra_header_xml=extra_headers, reactions=state["reactions"],
		external_data_xml=state["external_data"], trailing_xml=state["trailing"],
	)
	state["envelope"] = envelope
	document.set_cdml_state(envelope, state["paper"], state["unsupported"])
	document.mark_clean()
	return document


#============================================
#============================================
def _read_molecule(
		element: dom.Element, bond_length_pt: float | None,
		preserve_coordinates: bool,
		) -> bkchem_qt.models.molecule_model.MoleculeModel | None:
	"""Decode one molecule without splitting a native CDML element."""
	oasa_molecule = oasa.cdml_writer.read_cdml_molecule_element(element)
	if oasa_molecule is None:
		return None
	target = None if preserve_coordinates else bond_length_pt
	mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
		oasa_molecule, bond_length_pt=target,
	)
	return mol_model


#============================================
def _presentation(
		element: dom.Element, supported: bool,
		) -> bkchem_qt.models.document_object.PresentationObject:
	"""Create a presentation DTO while retaining every XML attribute/child."""
	attrs = _attributes(element)
	points = [_point_values(point) for point in _direct_children(element, "point")]
	bounds = _bounds_values(element)
	if bounds is None and _local_name(element) in ("text", "plus") and points:
		bounds = (points[0][0], points[0][1], 0.0, 0.0)
	font = _first_child(element, "font")
	ftext = _first_child(element, "ftext")
	return bkchem_qt.models.document_object.PresentationObject(
		kind=_local_name(element),
		attributes=attrs,
		points=points, bounds=bounds,
		font_attributes=_attributes(font) if font is not None else {},
		xml_ftext=_inner_xml(ftext) if ftext is not None else None,
		raw_xml=_raw_xml(element), supported=supported,
	)


#============================================
def _reaction(element: dom.Element) -> bkchem_qt.models.document_object.ReactionRecord:
	"""Read ordered reaction references without changing their XML order."""
	refs: list[tuple[str, str]] = []
	for child in _element_children(element):
		refs.append((_local_name(child), child.getAttribute("idref")))
	return bkchem_qt.models.document_object.ReactionRecord(
		refs=refs, raw_xml=_raw_xml(element),
	)


#============================================
def _parse_marks(
		document: bkchem_qt.models.document.Document, molecule_el: dom.Element,
		atom_lookup: dict[str, object],
		unsupported: list[bkchem_qt.models.document_object.UnsupportedContent],
		molecule_position: int,
		) -> None:
	"""Read atom marks and keep unsupported mark XML explicitly visible."""
	for atom_position, atom_el in enumerate(_direct_children(molecule_el, "atom"), start=1):
		atom_id = atom_el.getAttribute("id")
		atom_model = atom_lookup.get(atom_id)
		for mark_position, mark_el in enumerate(_direct_children(atom_el, "mark"), start=1):
			attrs = _attributes(mark_el)
			mark_type = attrs.get("type", "")
			if mark_type in _QT_OWNED_MARK_TYPES:
				continue
			if mark_type not in _SUPPORTED_MARK_TYPES:
				unsupported.append(_unsupported(
						mark_el, "unsupported atom mark",
						"/cdml/molecule[%d]/atom[%d]/mark[%d]" % (
								molecule_position, atom_position, mark_position,
								),
						))
				continue
			if atom_model is None:
				unsupported.append(_unsupported(
						mark_el, "unsupported atom mark",
						"/cdml/molecule[%d]/atom[%d]/mark[%d]" % (
								molecule_position, atom_position, mark_position,
								),
						))
				continue
			mark = bkchem_qt.models.document_object.AtomMarkModel(
				atom_model=atom_model, attributes=attrs, raw_xml=_raw_xml(mark_el),
			)
			document.add_mark(mark, mark_dirty=False)


#============================================
def _load_atom_number_fields(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		molecule_el: dom.Element,
		) -> None:
	"""Load legacy atom ``number`` and ``show_number`` presentation fields."""
	for atom_el, atom_model in zip(
			_direct_children(molecule_el, "atom"), mol_model.atoms,
		):
		number_text = atom_el.getAttribute("number")
		if number_text:
			atom_model.number = int(number_text)
		show_number = atom_el.getAttribute("show_number")
		if show_number:
			atom_model.show_number = show_number in ("yes", "true", "1", "on")


#============================================
def _parse_fragments(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		molecule_el: dom.Element,
		unsupported: list[bkchem_qt.models.document_object.UnsupportedContent],
		molecule_position: int,
		) -> None:
	"""Read safely representable fragments without evaluating legacy values."""
	for fragment_position, fragment_el in enumerate(
				_direct_children(molecule_el, "fragment"), start=1,
		):
		fragment = _read_fragment(fragment_el)
		path = "/cdml/molecule[%d]/fragment[%d]" % (
				molecule_position, fragment_position,
		)
		if fragment is None:
			mol_model.retain_unsupported_fragment_xml(_raw_xml(fragment_el))
			unsupported.append(_unsupported(
					fragment_el, "fragment has no stable identifier", path,
					))
			continue
		if mol_model.can_add_fragment(fragment):
			mol_model.add_fragment(fragment)
		else:
			# A dangling or duplicate reference is retained as raw XML so it is
			# visible to callers and never becomes partly editable metadata.
			mol_model.retain_unsupported_fragment_xml(_raw_xml(fragment_el))
			unsupported.append(_unsupported(
					fragment_el, "fragment has unresolved references", path,
					))


#============================================
def _parse_groups(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		molecule_el: dom.Element,
		unsupported: list[bkchem_qt.models.document_object.UnsupportedContent],
		molecule_position: int,
		) -> None:
	"""Load CDML groups structurally while retaining every source XML node.

	The OASA CDML codec omits group vertices.  This frontend layer therefore
	reads only their display/attachment metadata and lets the source-envelope
	merge retain group and incident-bond XML unchanged on save.
	"""
	groups_by_id = {}
	for group_position, group_el in enumerate(_direct_children(molecule_el, "group"), start=1):
		group, reason = _read_group(group_el)
		path = "/cdml/molecule[%d]/group[%d]" % (molecule_position, group_position)
		if group is None:
			unsupported.append(_unsupported(group_el, reason or "invalid group", path))
			continue
		mol_model.add_group(group)
		groups_by_id[group.group_id] = group
		if not group.supported:
			unsupported.append(_unsupported(group_el, group.unsupported_reason or "unsupported group", path))
	attachments = {group_id: [] for group_id in groups_by_id}
	for bond_el in _direct_children(molecule_el, "bond"):
		start_id = bond_el.getAttribute("start")
		end_id = bond_el.getAttribute("end")
		for group_id in (start_id, end_id):
			if group_id not in attachments:
				continue
			attachments[group_id].append(bkchem_qt.models.group_model.GroupAttachment(
					bond_id=bond_el.getAttribute("id"), start_id=start_id, end_id=end_id,
					attributes=tuple(sorted(_attributes(bond_el).items())), raw_xml=_raw_xml(bond_el),
					))
	for group_id, group in groups_by_id.items():
		group.set_attachments(tuple(attachments[group_id]))


#============================================
def _read_group(
		element: dom.Element,
		) -> tuple[bkchem_qt.models.group_model.GroupModel | None, str | None]:
	"""Decode the narrow native-group projection without interpreting chemistry."""
	group_id = element.getAttribute("id")
	if not group_id:
		return None, "group has no stable identifier"
	points = _direct_children(element, "point")
	if len(points) != 1:
		return None, "group must have exactly one point"
	point = points[0]
	try:
		x = _coord_to_points(point.getAttribute("x"))
		y = _coord_to_points(point.getAttribute("y"))
	except ValueError:
		return None, "group point has invalid coordinates"
	group_type = element.getAttribute("group-type")
	unsupported_reason = None
	if group_type not in {"builtin", "implicit", "explicit"}:
		unsupported_reason = "unsupported group-type %r" % (group_type or "missing")
	allowed_children = {"point", "font"}
	if any(_local_name(child) not in allowed_children for child in _element_children(element)):
		unsupported_reason = "group has retained child content not editable by PySide6"
	font = _first_child(element, "font")
	group = bkchem_qt.models.group_model.GroupModel(
			group_id=group_id, name=element.getAttribute("name"), group_type=group_type,
			pos=element.getAttribute("pos") or "center-first", x=x, y=y,
			attributes=tuple(sorted(_attributes(element).items())),
			point_attributes=tuple(sorted(_attributes(point).items())),
			font_attributes=tuple(sorted(_attributes(font).items())) if font is not None else (),
			raw_xml=_raw_xml(element), unsupported_reason=unsupported_reason,
			)
	return group, None


#============================================
def _read_fragment(element: dom.Element) -> bkchem_qt.models.fragment_model.FragmentModel | None:
	"""Decode one CDML fragment into stable, text-only metadata."""
	fragment_id = element.getAttribute("id")
	if not fragment_id:
		return None
	properties = []
	for property_el in _direct_children(element, "property"):
		properties.append(bkchem_qt.models.fragment_model.FragmentProperty(
				name=property_el.getAttribute("name"),
				value=property_el.getAttribute("value"),
				type_name=property_el.getAttribute("type"),
				attributes=tuple(sorted(_attributes(property_el).items())),
				raw_xml=_raw_xml(property_el),
				))
	known_children = {"name", "bond", "vertex", "property"}
	unknown = tuple(_raw_xml(child) for child in _element_children(element)
					if _local_name(child) not in known_children)
	name_el = _first_child(element, "name")
	name = _element_text(name_el) if name_el is not None else ""
	return bkchem_qt.models.fragment_model.FragmentModel(
			fragment_id=fragment_id,
			fragment_type=element.getAttribute("type") or "explicit",
			name=name,
			atom_ids=tuple(vertex.getAttribute("id")
						for vertex in _direct_children(element, "vertex")),
			bond_ids=tuple(bond.getAttribute("id")
						for bond in _direct_children(element, "bond")),
			properties=tuple(properties),
			attributes=tuple(sorted(_attributes(element).items())),
			unknown_children_xml=unknown,
			raw_xml=_raw_xml(element),
			)


#============================================
def _report_unrendered_molecule_children(
		molecule_el: dom.Element,
		unsupported: list[bkchem_qt.models.document_object.UnsupportedContent],
		molecule_position: int,
		) -> None:
	"""Report preserved molecule vertices PySide6 cannot yet project."""
	for child_position, child in enumerate(_element_children(molecule_el), start=1):
		if _local_name(child) in {"atom", "bond", "fragment", "group"}:
			continue
		unsupported.append(_unsupported(
				child, "molecule child retained but not rendered by PySide6",
				"/cdml/molecule[%d]/%s[%d]" % (
				molecule_position, _local_name(child), child_position,
						),
				))


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
def _normalize_loaded_source_ids(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		source: dom.Element,
		) -> None:
	"""Assign local linkage IDs while loading an ID-less legacy molecule.

	Legacy CDML is allowed to omit atom and bond IDs.  Qt needs private IDs to
	link the decoded models with retained source XML, but those IDs are not
	issued by the authoritative backend and therefore cannot name a persistent
	operation target.  Serialization itself is read-only and must instead
	allocate output-only IDs.
	"""
	atom_ids = {child.getAttribute("id") for child in _element_children(source)
				if child.getAttribute("id")}
	bond_ids = {child.getAttribute("id") for child in _direct_children(source, "bond")
				if child.getAttribute("id")}
	source_atoms = _direct_children(source, "atom")
	source_atoms_by_id = {
			atom.getAttribute("id"): atom for atom in source_atoms
			if atom.getAttribute("id")
	}
	for atom_model in mol_model.atoms:
		atom_id = getattr(atom_model._chem_atom, "id", None)
		source_atom = source_atoms_by_id.get(str(atom_id)) if atom_id else None
		atom_model.bind_backend_durable_id(
			source_atom.getAttribute("id") if source_atom is not None else None,
		)
	for atom_model in mol_model.atoms:
		atom_id = getattr(atom_model._chem_atom, "id", None)
		source_atom = source_atoms_by_id.get(str(atom_id)) if atom_id else None
		if source_atom is None:
			continue
		atom_ids.add(str(atom_id))

	# Pair only genuinely ID-less loaded atoms by position.  Never zip a newly
	# created atom onto an unmatched, deleted source atom with a real ID.
	idless_source_atoms = [atom for atom in source_atoms
			if not atom.getAttribute("id")]
	idless_current_atoms = [atom for atom in mol_model.atoms
			if not getattr(atom._chem_atom, "id", None)]
	for atom_model, source_atom in zip(idless_current_atoms, idless_source_atoms):
		fresh_id = _next_free_id("atom", atom_ids)
		atom_model._chem_atom.id = fresh_id
		source_atom.setAttribute("id", fresh_id)
		atom_ids.add(fresh_id)
	for atom_model in mol_model.atoms:
		if getattr(atom_model._chem_atom, "id", None):
			continue
		fresh_id = _next_free_id("atom", atom_ids)
		atom_model._chem_atom.id = fresh_id
		atom_ids.add(fresh_id)

	source_atom_ids = {atom.getAttribute("id") for atom in source_atoms}
	source_bonds = [
			bond for bond in _direct_children(source, "bond")
			if _bond_has_only_model_atoms(bond, source_atom_ids)
		]
	source_bonds_by_id = {
			bond.getAttribute("id"): bond for bond in source_bonds
			if bond.getAttribute("id")
	}
	for bond_model in mol_model.bonds:
		bond_id = getattr(bond_model._chem_bond, "id", None)
		source_bond = source_bonds_by_id.get(str(bond_id)) if bond_id else None
		bond_model.bind_backend_durable_id(
			source_bond.getAttribute("id") if source_bond is not None else None,
		)
	for bond_model in mol_model.bonds:
		bond_id = getattr(bond_model._chem_bond, "id", None)
		if bond_id and str(bond_id) in source_bonds_by_id:
			bond_ids.add(str(bond_id))
	idless_source_bonds = [bond for bond in source_bonds
			if not bond.getAttribute("id")]
	idless_current_bonds = [bond for bond in mol_model.bonds
			if not getattr(bond._chem_bond, "id", None)]
	for bond_model, source_bond in zip(idless_current_bonds, idless_source_bonds):
		fresh_id = _next_free_id("bond", bond_ids)
		bond_model._chem_bond.id = fresh_id
		source_bond.setAttribute("id", fresh_id)
		bond_ids.add(fresh_id)
	for bond_model in mol_model.bonds:
		if getattr(bond_model._chem_bond, "id", None):
			continue
		fresh_id = _next_free_id("bond", bond_ids)
		bond_model._chem_bond.id = fresh_id
		bond_ids.add(fresh_id)


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
def _unsupported(
		element: dom.Element, reason: str, path: str,
		) -> bkchem_qt.models.document_object.UnsupportedContent:
	"""Create an explicit warning that retains the unsupported XML exactly."""
	attrs = _attributes(element)
	return bkchem_qt.models.document_object.UnsupportedContent(
		path=path, tag=_local_name(element),
		object_id=attrs.get("id"), reason=reason,
		raw_xml=_raw_xml(element),
	)


#============================================
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
def _is_direct_core_cdml_child(element: dom.Element) -> bool:
	"""Return whether one direct root child is editable CDML, not foreign XML."""
	return (
		element.namespaceURI in (None, "", oasa.cdml_document.CDML_NAMESPACE_URI)
		and _local_name(element) in oasa.cdml_xml.CDML_CORE_ELEMENT_NAMES
	)


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
