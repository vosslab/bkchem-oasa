"""Disposable Qt selection behavior for OASA-observed bracket relationships."""

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement


#============================================
def set_facts(document: object, records: tuple[tuple[object, ...], ...]) -> None:
	"""Install plain ``(pair_id, members, style, width, color)`` projection facts."""
	by_member = {}
	by_id = {}
	for record in records:
		if type(record) is not tuple or len(record) != 5:
			raise ValueError("Bracket pair facts must be exact five-tuples")
		pair_id, member_ids, style, width, color = record
		if (
			type(pair_id) is not str or type(member_ids) is not tuple
			or len(member_ids) != 2 or any(type(item) is not str for item in member_ids)
			or type(style) is not str
		):
			raise ValueError("Bracket pair facts must contain plain durable values")
		plain_record = (pair_id, member_ids, style, width, color)
		by_id[pair_id] = plain_record
		for member_id in member_ids:
			by_member[member_id] = plain_record
	document._bracket_pairs_by_member = by_member
	document._bracket_pairs_by_id = by_id


#============================================
def pair_for_presentation(document: object, identifier: str) -> tuple[object, ...] | None:
	"""Return one observed pair fact for a durable presentation root."""
	return getattr(document, "_bracket_pairs_by_member", {}).get(identifier)


#============================================
def selected_pair(document: object) -> tuple[object, ...] | None:
	"""Return the one wholly selected valid pair, otherwise ``None``."""
	if document.selected_atoms or document.selected_bonds:
		return None
	identifiers = document.selected_presentation_stack_root_ids
	if len(identifiers) != 2:
		return None
	pair = pair_for_presentation(document, identifiers[0])
	if pair is None or frozenset(pair[1]) != frozenset(identifiers):
		return None
	return pair


#============================================
def _items_for_ids(document: object, identifiers: tuple[str, ...]) -> tuple[object, ...]:
	"""Resolve current registered graphics wrappers by durable presentation ID."""
	wanted = frozenset(identifiers)
	return tuple(
		item for item in document._projection_item_refs.values()
		if getattr(getattr(item, "document_object_model", None), "object_id", None) in wanted
		and bkchem_qt.canvas.document_projection.persistent_selection_key(item) is not None
	)


#============================================
def expand_selection(document: object) -> None:
	"""Select the companion of every selected observed bracket root."""
	if document._scene is None or getattr(document, "_expanding_bracket_selection", False):
		return
	selected_ids = {
		getattr(getattr(item, "document_object_model", None), "object_id", None)
		for item in bkchem_qt.canvas.graphics_retirement.selected_items_from_captured_scene(
			document._scene,
		)
	}
	selected_ids.discard(None)
	companion_ids = set()
	for identifier in selected_ids:
		pair = pair_for_presentation(document, identifier)
		if pair is not None:
			companion_ids.update(pair[1])
	if companion_ids.issubset(selected_ids):
		return
	document._expanding_bracket_selection = True
	try:
		for item in _items_for_ids(document, tuple(companion_ids)):
			item.setSelected(True)
	finally:
		document._expanding_bracket_selection = False


#============================================
def toggle_selection(document: object, item: object) -> bool:
	"""Toggle an observed pair as one user-level selection unit."""
	identifier = getattr(getattr(item, "document_object_model", None), "object_id", None)
	pair = pair_for_presentation(document, identifier) if type(identifier) is str else None
	if pair is None:
		return False
	items = _items_for_ids(document, pair[1])
	selected = all(current.isSelected() for current in items)
	document._expanding_bracket_selection = True
	try:
		for current in items:
			current.setSelected(not selected)
	finally:
		document._expanding_bracket_selection = False
	return True
