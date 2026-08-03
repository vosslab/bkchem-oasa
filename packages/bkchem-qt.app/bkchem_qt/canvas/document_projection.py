"""Projection of document-owned CDML presentation models into a scene."""

# Standard Library
import dataclasses
import enum
import math
import warnings

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.arrow_item
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.items.graphics_item
import bkchem_qt.canvas.items.mark_item
import bkchem_qt.canvas.items.text_item
import bkchem_qt.canvas.graphics_retirement


#============================================
def _number(value: object, default: float = 0.0) -> float:
	"""Return a CDML numeric value, using the intentional display default."""
	if value is None:
		return default
	result = float(value)
	return result


#============================================
def _coordinate(value: object) -> float:
	"""Return a CDML coordinate as scene-space points."""
	text = str(value)
	if text.endswith("cm"):
		result = float(text[:-2]) * 72.0 / 2.54
		return result
	if text.endswith("px"):
		result = float(text[:-2])
		return result
	result = float(text)
	return result


#============================================
def _color(attributes: dict[str, str]) -> str | None:
	"""Return a legacy CDML line/text color when one is specified."""
	value = attributes.get("line_color")
	if value is None:
		value = attributes.get("color")
	return value


#============================================
def _brush(attributes: dict[str, str]) -> PySide6.QtGui.QBrush:
	"""Build a fill brush from legacy CDML area color attributes."""
	color = attributes.get("area_color")
	if color is None:
		color = attributes.get("background-color")
	if color is None or color == "" or color == "none":
		brush = PySide6.QtGui.QBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		return brush
	brush = PySide6.QtGui.QBrush(PySide6.QtGui.QColor(color))
	return brush


#============================================
def _pen(attributes: dict[str, str]) -> PySide6.QtGui.QPen:
	"""Build a pen from legacy CDML line attributes."""
	color = _color(attributes)
	qt_color = PySide6.QtGui.QColor(color) if color is not None else PySide6.QtGui.QColor("black")
	width = _number(attributes.get("width"), 1.0)
	pen = PySide6.QtGui.QPen(qt_color, width)
	return pen


#============================================
def _points(model: object) -> list[PySide6.QtCore.QPointF]:
	"""Convert document model coordinates to Qt points."""
	converted = []
	for x, y, _z in model.points:
		converted.append(PySide6.QtCore.QPointF(x, y))
	return converted


#============================================
def _bounds(model: object) -> PySide6.QtCore.QRectF:
	"""Return model bounds or compatible legacy x/y/width/height attributes."""
	bounds = model.bounds
	if bounds is not None:
		x, y, width, height = bounds
	else:
		attributes = model.attributes
		x = _number(attributes.get("x"))
		y = _number(attributes.get("y"))
		width = _number(attributes.get("width"), _number(attributes.get("w")))
		height = _number(attributes.get("height"), _number(attributes.get("h")))
	rect = PySide6.QtCore.QRectF(x, y, width, height).normalized()
	return rect


#============================================
def _presentation_text(model: object) -> str:
	"""Return the display text for a projected text-like presentation."""
	if model.kind == "plus":
		return "+"
	text = model.display_text
	return text


#============================================
def _set_item_interaction(item: PySide6.QtWidgets.QGraphicsItem,
		model: object) -> None:
	"""Attach model identity while keeping loaded artwork non-movable."""
	item.document_object_model = model
	item.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
	item.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)


#============================================
def _refresh_presentation(item: PySide6.QtWidgets.QGraphicsItem,
		model: object) -> None:
	"""Refresh an already projected graphics item after model mutation."""
	attributes = model.attributes
	if isinstance(item, bkchem_qt.canvas.items.arrow_item.ArrowItem):
		points = _points(model)
		if len(points) >= 2:
			item.start = points[0]
			item.end = points[-1]
			item.control_points = points[1:-1]
			item.spline = attributes.get("spline", "no") in (
				"yes", "true", "1",
			)
		item.start_head = attributes.get("start", "no") in ("yes", "true", "1", "both")
		item.end_head = attributes.get("end", "yes") not in ("no", "false", "0")
		item.line_width = _number(attributes.get("width"), 1.0)
		item.color = _color(attributes)
		return
	if isinstance(item, bkchem_qt.canvas.items.text_item.TextItem):
		points = _points(model)
		position = points[0] if points else _bounds(model).topLeft()
		item.setPos(position)
		font = item.font()
		font_attributes = model.font_attributes
		family = font_attributes.get("family")
		if family is not None:
			font.setFamily(family)
		size = font_attributes.get("size")
		if size is None:
			size = attributes.get("font_size")
		if size is None and model.kind == "plus":
			size = "14"
		if size is not None:
			if model.kind == "text" and (
				type(size) is not str or not size.isdecimal()
			):
				font.setPointSizeF(12.0)
			else:
				font.setPointSizeF(_number(size, 12.0))
		item.setFont(font)
		if model.kind == "plus" and points:
			bounds = item.boundingRect()
			position = PySide6.QtCore.QPointF(
				points[0].x() - bounds.width() / 2.0,
				points[0].y() - bounds.height() / 2.0,
			)
			item.setPos(position)
		color = font_attributes.get("color")
		if color is None:
			color = _color(attributes)
		if color is None and model.kind == "plus":
			color = "#000000"
		if color is not None:
			item.set_color(color)
		if model.kind == "text" and model.formatted_text_runs is not None:
			item.set_formatted_text_runs(model.formatted_text_runs)
		else:
			item.set_text(_presentation_text(model))
		return
	if isinstance(item, (bkchem_qt.canvas.items.graphics_item.RectItem,
			bkchem_qt.canvas.items.graphics_item.OvalItem)):
		item.setRect(_bounds(model))
		item.setPen(_pen(attributes))
		item.setBrush(_brush(attributes))
		return
	if isinstance(item, bkchem_qt.canvas.items.graphics_item.PolygonItem):
		item.setPolygon(PySide6.QtGui.QPolygonF(_points(model)))
		item.setPen(_pen(attributes))
		item.setBrush(_brush(attributes))
		return
	if isinstance(item, PySide6.QtWidgets.QGraphicsPathItem):
		path = PySide6.QtGui.QPainterPath()
		points = _points(model)
		if points:
			path.moveTo(points[0])
			for point in points[1:]:
				path.lineTo(point)
		item.setPath(path)
		item.setPen(_pen(attributes))
		item.setBrush(_brush(attributes))


#============================================
class _ProjectionBinding(PySide6.QtCore.QObject):
	"""Own a model signal connection for one projected graphics item."""

	#============================================
	def __init__(self, model: object, item: PySide6.QtWidgets.QGraphicsItem,
			refresh_callback: object = None) -> None:
		"""Connect a model's changed signal to its graphics refresh callback."""
		super().__init__()
		self._model = model
		self._item = item
		self._refresh_callback = refresh_callback
		self._connected = True
		model.changed.connect(self.refresh)

	#============================================
	def refresh(self) -> None:
		"""Update the item while it remains owned by a live scene."""
		if self._connected:
			if self._refresh_callback is None:
				_refresh_presentation(self._item, self._model)
			else:
				self._refresh_callback(self._item, self._model)

	#============================================
	def dispose(self) -> None:
		"""Release every strong callback edge exactly once before item deletion."""
		try:
			if self._connected:
				with warnings.catch_warnings():
					warnings.simplefilter("ignore", RuntimeWarning)
					self._model.changed.disconnect(self.refresh)
		except (RuntimeError, TypeError):
			# QObject/model teardown may already have severed this connection.
			pass
		finally:
			self._connected = False
			self._model = None
			self._item = None
			self._refresh_callback = None


#============================================
def is_bound_presentation_projection(
		item: PySide6.QtWidgets.QGraphicsItem, model: object,
		) -> bool:
	"""Return whether ``item`` is this projection's live binding for ``model``.

	A graphics attribute alone is only presentation metadata: an unrelated scene
	item can imitate it.  The binding is created exclusively by
	``_attach_binding`` during projection, so this identity check is the small
	frontend boundary used by persistent presentation actions.  It deliberately
	does not walk parents or touch native-wrapper lifetime APIs.
	"""
	binding = getattr(item, "_projection_binding", None)
	return (
		getattr(item, "document_object_model", None) is model
		and isinstance(binding, _ProjectionBinding)
		and binding._model is model
		and binding._item is item
	)


#============================================
def selected_presentation_stack_root_ids(document: object,
		scene: PySide6.QtWidgets.QGraphicsScene | None) -> tuple[str, ...]:
	"""Return canonical durable roots only for real selected projections.

	Every selected item must be a direct, supported presentation item bound by
	the current projection.  Canonical document order, rather than Qt selection
	or scene order, determines the submitted IDs.
	"""
	selected_items = bkchem_qt.canvas.graphics_retirement.selected_items_from_captured_scene(
		scene,
	)
	selected_models = []
	for item in selected_items:
		model = getattr(item, "document_object_model", None)
		if (
			not getattr(model, "supported", False)
			or not getattr(model, "editable", False)
			or model not in document.presentation_objects
			or model not in document.objects
			or not isinstance(getattr(model, "object_id", None), str)
			or not model.object_id.strip()
			or not is_bound_presentation_projection(item, model)
		):
			return ()
		selected_models.append(model)
	if not selected_models or len({id(model) for model in selected_models}) != len(selected_models):
		return ()
	selected_ids = {id(model) for model in selected_models}
	root_ids = tuple(
		model.object_id for model in document.objects if id(model) in selected_ids
	)
	if len(root_ids) != len(selected_ids) or len(set(root_ids)) != len(root_ids):
		return ()
	return root_ids


#============================================
def selected_top_level_transform_keys(document: object,
		scene: PySide6.QtWidgets.QGraphicsScene | None,
		) -> tuple[tuple[str, str], ...]:
	"""Return the complete eligible transform selection in document order.

	This bridge resolves selected atom, bond, group, and mark projections to
	their owning direct-root molecule.  Any item outside this exact projection
	invalidates the whole selection rather than silently changing the request.
	"""
	selected_items = bkchem_qt.canvas.graphics_retirement.selected_items_from_captured_scene(
		scene,
	)
	selected_roots = set()
	document_objects = tuple(document.objects)
	for item in selected_items:
		model = getattr(item, "document_object_model", None)
		if model is not None:
			if (
				not getattr(model, "supported", False)
				or not getattr(model, "editable", False)
				or model not in document.presentation_objects
				or model not in document_objects
				or type(getattr(model, "object_id", None)) is not str
				or not model.object_id
				or not is_bound_presentation_projection(item, model)
			):
				return ()
			selected_roots.add(model)
			continue
		molecule = document.molecule_for_current_projection_item(item)
		if (
			molecule is None or molecule not in document.molecules
			or molecule not in document_objects
			or type(getattr(molecule, "mol_id", None)) is not str
			or not molecule.mol_id
		):
			return ()
		selected_roots.add(molecule)
	if not selected_roots:
		return ()
	keys = []
	for root in document_objects:
		if root not in selected_roots:
			continue
		if root in document.molecules:
			keys.append(("molecule", root.mol_id))
		elif root in document.presentation_objects:
			keys.append(("presentation", root.object_id))
		else:
			return ()
	return tuple(keys) if len(keys) == len(selected_roots) else ()


#============================================
def top_level_presentation_keys_for_items(
		document: object, items: tuple[PySide6.QtWidgets.QGraphicsItem, ...],
		) -> tuple[tuple[str, str], ...]:
	"""Return durable presentation roots for one exact current wrapper tuple.

	EditMode captures responsive drag previews as graphics/model state, then uses
	this bridge only at release to obtain the plain direct-root CDML request.  A
	foreign, retired, unsupported, duplicated, or ID-less wrapper invalidates
	the whole selection rather than allowing a local edit to leak into a
	synchronized session.
	"""
	if type(items) is not tuple or not items:
		return ()
	models = []
	for item in items:
		model = getattr(item, "document_object_model", None)
		if (
			not document.is_current_projection_item(item)
			or not getattr(model, "supported", False)
			or not getattr(model, "editable", False)
			or model not in document.presentation_objects
			or model not in document.objects
			or type(getattr(model, "object_id", None)) is not str
			or not model.object_id
			or not is_bound_presentation_projection(item, model)
		):
			return ()
		models.append(model)
	if len({id(model) for model in models}) != len(models):
		return ()
	model_ids = {id(model) for model in models}
	keys = tuple(
		("presentation", model.object_id)
		for model in document.objects
		if id(model) in model_ids
	)
	return keys if len(keys) == len(models) and len({key[1] for key in keys}) == len(keys) else ()


#============================================
def selection_translate_targets_for_items(
		document: object, items: tuple[PySide6.QtWidgets.QGraphicsItem, ...],
		) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]] | None:
	"""Resolve one exact mixed atom/presentation selection in source order.

	The returned values contain only durable backend addresses.  Every supplied
	wrapper must belong to the current projection: atom wrappers resolve through
	the document identity bridge and presentation wrappers through their direct
	document binding.  A mixed operation deliberately has no partial selection
	meaning, so duplicate, foreign, retired, unsupported, or extra wrappers make
	the complete observation ineligible.
	"""
	if type(items) is not tuple or not items:
		return None
	if len({id(item) for item in items}) != len(items):
		return None
	atom_models = set()
	presentation_models = set()
	for item in items:
		if not document.is_current_projection_item(item):
			return None
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			molecule = document.molecule_for_current_projection_item(item)
			model = item.atom_model
			atom_id = getattr(model, "backend_durable_id", None)
			molecule_id = getattr(molecule, "mol_id", None)
			if (
				molecule is None or molecule not in document.molecules
				or model not in molecule.atoms or model in atom_models
				or type(atom_id) is not str or not atom_id.strip()
				or type(molecule_id) is not str or not molecule_id.strip()
			):
				return None
			atom_models.add(model)
			continue
		model = getattr(item, "document_object_model", None)
		if (
			not getattr(model, "supported", False)
			or not getattr(model, "editable", False)
			or model not in document.presentation_objects
			or model not in document.objects
			or model in presentation_models
			or type(getattr(model, "object_id", None)) is not str
			or not model.object_id.strip()
			or not is_bound_presentation_projection(item, model)
		):
			return None
		presentation_models.add(model)
	if not atom_models or not presentation_models:
		return None
	atom_targets = []
	for molecule in document.molecules:
		if molecule not in document.objects:
			return None
		for atom in molecule.atoms:
			if atom in atom_models:
				atom_targets.append((molecule.mol_id, atom.backend_durable_id))
	presentation_keys = tuple(
		("presentation", model.object_id)
		for model in document.objects if model in presentation_models
	)
	if (
		len(atom_targets) != len(atom_models)
		or len(presentation_keys) != len(presentation_models)
		or len(set(atom_targets)) != len(atom_targets)
		or len({key[1] for key in presentation_keys}) != len(presentation_keys)
	):
		return None
	return tuple(atom_targets), presentation_keys


#============================================
class StructuralSelectionKind(enum.Enum):
	"""Describe how a selected scene set relates to partial structure actions."""
	EXACT = "exact"
	INVALID = "invalid"
	ROOT_OR_MIXED = "root-or-mixed"


@dataclasses.dataclass(frozen=True)
class StructuralSelectionClassification:
	"""Return only immutable structural targets when the selection is exact."""
	kind: StructuralSelectionKind
	targets: tuple[str, tuple[str, ...], tuple[str, ...]] | None = None


#============================================
def classify_structural_selection(
		document: object, items: tuple[PySide6.QtWidgets.QGraphicsItem, ...],
		) -> StructuralSelectionClassification:
	"""Classify exact structural, invalid structural, and root/mixed selection.

	The returned observation contains only immutable durable backend values.
	Every wrapper must be registered in this exact projection and resolve to one
	document-owned molecule.  Atom and bond identifiers are emitted in molecule
	model source order rather than Qt scene or selection order.  A foreign,
	stale, or ID-less structural wrapper is invalid rather than a whole-root
	fallback.  A legitimate presentation-root or mixed selection remains for the
	existing top-level clipboard route.
	"""
	if type(items) is not tuple or not items:
		return StructuralSelectionClassification(StructuralSelectionKind.ROOT_OR_MIXED)
	if len({id(item) for item in items}) != len(items):
		return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
	structural_items = tuple(
		item for item in items
		if isinstance(item, (
			bkchem_qt.canvas.items.atom_item.AtomItem,
			bkchem_qt.canvas.items.bond_item.BondItem,
		))
	)
	if not structural_items:
		return StructuralSelectionClassification(StructuralSelectionKind.ROOT_OR_MIXED)
	molecule = None
	multiple_molecules = False
	molecules_by_id = {}
	atom_models = set()
	bond_models = set()
	for item in structural_items:
		if not document.is_current_projection_item(item):
			return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
		item_molecule = document.molecule_for_current_projection_item(item)
		if item_molecule is None or item_molecule not in document.molecules:
			return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
		if molecule is None:
			molecule = item_molecule
		elif item_molecule is not molecule:
			multiple_molecules = True
		molecule_id = getattr(item_molecule, "mol_id", None)
		if type(molecule_id) is not str or not molecule_id.strip():
			return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
		if molecule_id in molecules_by_id and molecules_by_id[molecule_id] is not item_molecule:
			return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
		molecules_by_id[molecule_id] = item_molecule
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			model = item.atom_model
			durable_id = getattr(model, "backend_durable_id", None)
			if (
				model not in item_molecule.atoms
				or type(durable_id) is not str
				or not durable_id.strip()
				or model in atom_models
			):
				return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
			atom_models.add(model)
		elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			model = item.bond_model
			durable_id = getattr(model, "backend_durable_id", None)
			if (
				model not in item_molecule.bonds
				or type(durable_id) is not str
				or not durable_id.strip()
				or model in bond_models
			):
				return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
			bond_models.add(model)
	if molecule is None:
		return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
	if multiple_molecules:
		return StructuralSelectionClassification(StructuralSelectionKind.ROOT_OR_MIXED)
	molecule_id = molecule.mol_id
	atom_ids = tuple(
		atom.backend_durable_id for atom in molecule.atoms if atom in atom_models
	)
	bond_ids = tuple(
		bond.backend_durable_id for bond in molecule.bonds if bond in bond_models
	)
	if (
		len(atom_ids) != len(atom_models)
		or len(bond_ids) != len(bond_models)
		or len(set(atom_ids)) != len(atom_ids)
		or len(set(bond_ids)) != len(bond_ids)
		or set(atom_ids).intersection(bond_ids)
	):
		return StructuralSelectionClassification(StructuralSelectionKind.INVALID)
	if len(structural_items) != len(items):
		return StructuralSelectionClassification(StructuralSelectionKind.ROOT_OR_MIXED)
	return StructuralSelectionClassification(
		StructuralSelectionKind.EXACT, (molecule_id, atom_ids, bond_ids),
	)


#============================================
def structure_delete_targets_for_items(
		document: object, items: tuple[PySide6.QtWidgets.QGraphicsItem, ...],
		) -> tuple[str, tuple[str, ...], tuple[str, ...]] | None:
	"""Return exact structural targets for the existing partial-Delete route."""
	classification = classify_structural_selection(document, items)
	if classification.kind is StructuralSelectionKind.EXACT:
		return classification.targets
	return None


#============================================
def _attach_binding(model: object, item: PySide6.QtWidgets.QGraphicsItem,
		refresh_callback: object = None) -> None:
	"""Associate a projection binding without replacing an item's cleanup hook."""
	item._projection_binding = _ProjectionBinding(model, item, refresh_callback)


#============================================
def dispose_item_callbacks(item: PySide6.QtWidgets.QGraphicsItem) -> None:
	"""Release one item's projection and native callbacks before retirement.

	The item attribute is cleared while its Qt wrapper is still valid.  The
	item-specific ``dispose`` implementation is looked up only for this call, so
	no bound method or closure is retained on the graphics item.
	"""
	first_error = None
	binding = getattr(item, "_projection_binding", None)
	if binding is not None:
		try:
			binding.dispose()
		except Exception as exc:
			first_error = exc
		finally:
			try:
				item._projection_binding = None
			except Exception as exc:
				# An already-retired wrapper cannot accept the attribute update, but
				# its item-specific cleanup must still get a chance to release its
				# own model callbacks before the caller completes retirement.
				if first_error is None:
					first_error = exc
	try:
		dispose = getattr(item, "dispose", None)
		if callable(dispose):
			dispose()
	except Exception as exc:
		if first_error is None:
			first_error = exc
	if first_error is not None:
		raise first_error


#============================================
def create_presentation_item(model: object) -> PySide6.QtWidgets.QGraphicsItem | None:
	"""Create one Qt item for a supported document presentation model."""
	if not model.supported:
		return None
	points = _points(model)
	kind = model.kind
	if kind == "arrow":
		if len(points) < 2:
			return None
		item = bkchem_qt.canvas.items.arrow_item.ArrowItem(points[0], points[-1])
	elif kind in ("text", "plus"):
		text = _presentation_text(model)
		item = bkchem_qt.canvas.items.text_item.TextItem(text)
	elif kind in ("rect", "square"):
		item = bkchem_qt.canvas.items.graphics_item.RectItem(_bounds(model))
	elif kind in ("oval", "circle"):
		item = bkchem_qt.canvas.items.graphics_item.OvalItem(_bounds(model))
	elif kind == "polygon":
		item = bkchem_qt.canvas.items.graphics_item.PolygonItem(points)
	elif kind == "polyline":
		item = PySide6.QtWidgets.QGraphicsPathItem()
	else:
		return None
	_set_item_interaction(item, model)
	_refresh_presentation(item, model)
	_attach_binding(model, item)
	return item


#============================================
def project_presentation_objects(document: object,
		scene: PySide6.QtWidgets.QGraphicsScene) -> dict[object, PySide6.QtWidgets.QGraphicsItem]:
	"""Project all document presentation objects and return their item mapping."""
	projected = {}
	for model in document.presentation_objects:
		item = create_presentation_item(model)
		if item is None:
			continue
		scene.addItem(item)
		projected[model] = item
	return projected


#============================================
def _find_atom_item(scene: PySide6.QtWidgets.QGraphicsScene,
		atom_model: object) -> PySide6.QtWidgets.QGraphicsItem | None:
	"""Find the existing AtomItem by exact AtomModel identity."""
	for item in scene.items():
		if getattr(item, "atom_model", None) is atom_model:
			return item
	return None


#============================================
def _refresh_mark(item: PySide6.QtWidgets.QGraphicsItem, model: object) -> None:
	"""Refresh a projected mark from its persisted CDML geometry."""
	facts = model.rendering_facts
	if facts is None:
		angle, offset, size = _mark_geometry(model)
		draw_circle = _mark_draw_circle(model.attributes)
		line_width = _mark_line_width(model.attributes)
	else:
		angle, offset, size, draw_circle, line_width = facts
	item.angle = angle
	item.offset = offset
	item.size = size
	item.draw_circle = draw_circle
	item.line_width = line_width


#============================================
def _default_mark_size(mark_type: str) -> float:
	"""Return the legacy BKChem diameter for an omitted CDML mark size."""
	if mark_type in ("plus", "minus", "electronpair", "electron_pair", "lone_pair"):
		return 10.0
	if mark_type == "pz_orbital":
		return 40.0
	return 4.0


#============================================
def _positive_display_number(value: object, default: float) -> float:
	"""Return a finite positive display scalar without changing CDML data."""
	if value is None:
		return default
	try:
		result = float(value)
	except (TypeError, ValueError):
		return default
	return result if math.isfinite(result) and result > 0.0 else default


#============================================
def _finite_display_number(value: object, default: float) -> float:
	"""Return a finite display scalar while preserving model data verbatim."""
	try:
		result = float(value)
	except (TypeError, ValueError):
		return default
	return result if math.isfinite(result) else default


#============================================
def _mark_coordinate(value: str) -> float | None:
	"""Decode one finite CDML coordinate for frontend placement only."""
	try:
		result = _coordinate(value)
	except ValueError:
		return None
	return result if math.isfinite(result) else None


#============================================
def _mark_draw_circle(attributes: dict[str, str]) -> bool:
	"""Return the explicit CDML charge-circle display setting."""
	return attributes.get("draw_circle", "yes") in ("yes", "true", "1", "on")


#============================================
def _mark_line_width(attributes: dict[str, str]) -> float:
	"""Return a finite positive electron-pair line width for Qt rendering."""
	return _positive_display_number(attributes.get("line_width"), 1.0)


#============================================
def _mark_geometry(model: object) -> tuple[float, float, float]:
	"""Return angle, radial offset, and diameter from an atom-mark model.

	CDML ``x``/``y`` are authoritative persisted coordinates. The angle and
	distance are derived together so importing a legacy mark cannot preserve one
	and silently replace the other with a display default. New marks with no
	explicit position retain the historic 12-point radial placement.
	"""
	attributes = model.attributes
	default_angle = _finite_display_number(attributes.get("angle"), 0.0)
	if "x" in attributes and "y" in attributes:
		x = _mark_coordinate(attributes["x"])
		y = _mark_coordinate(attributes["y"])
		if x is not None and y is not None:
			dx = x - model.atom_model.x
			dy = y - model.atom_model.y
			offset = math.hypot(dx, dy)
			angle = math.degrees(math.atan2(dy, dx)) if offset else default_angle
		else:
			angle = default_angle
			offset = 12.0
	else:
		angle = default_angle
		offset = 12.0
	size = _positive_display_number(
		attributes.get("size"), _default_mark_size(model.mark_type),
	)
	return (angle, offset, size)


#============================================
def create_mark_item(
		model: object, atom_item: PySide6.QtWidgets.QGraphicsItem,
		) -> PySide6.QtWidgets.QGraphicsItem | None:
	"""Create one supported atom-mark projection under an AtomItem."""
	if not model.supported:
		return None
	projection_mark_types = {
		"plus": bkchem_qt.canvas.items.mark_item.MARK_PLUS,
		"minus": bkchem_qt.canvas.items.mark_item.MARK_MINUS,
		"radical": bkchem_qt.canvas.items.mark_item.MARK_RADICAL,
		"biradical": bkchem_qt.canvas.items.mark_item.MARK_BIRADICAL,
		"electronpair": bkchem_qt.canvas.items.mark_item.MARK_ELECTRONPAIR,
		"dotted_electronpair": bkchem_qt.canvas.items.mark_item.MARK_DOTTED_ELECTRONPAIR,
		"pz_orbital": bkchem_qt.canvas.items.mark_item.MARK_PZ_ORBITAL,
		# Earlier Qt-only values remain import-compatible with transient callers.
		"electron_pair": bkchem_qt.canvas.items.mark_item.MARK_ELECTRON_PAIR,
		"lone_pair": bkchem_qt.canvas.items.mark_item.MARK_LONE_PAIR,
	}
	if model.mark_type not in projection_mark_types:
		return None
	facts = model.rendering_facts
	if facts is None:
		angle, offset, size = _mark_geometry(model)
		draw_circle = _mark_draw_circle(model.attributes)
		line_width = _mark_line_width(model.attributes)
	else:
		angle, offset, size, draw_circle, line_width = facts
	mark_type = projection_mark_types[model.mark_type]
	item = bkchem_qt.canvas.items.mark_item.MarkItem(
		atom_item, mark_type, angle, offset, size,
		draw_circle=draw_circle, line_width=line_width,
	)
	item.atom_mark_model = model
	item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
		True,
	)
	item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
		False,
	)
	_attach_binding(model, item, _refresh_mark)
	return item


#============================================
def dispose_detached_items(
		items: list[PySide6.QtWidgets.QGraphicsItem],
		reaper: object | None = None,
		) -> None:
	"""Terminally retire detached projection graphics through the shared reaper.

	Prepared projections create marks below detached atom items.  Disconnecting
	and explicitly deleting those children before their atom wrappers makes
	construction-failure cleanup deterministic without touching a retained live
	scene.  A failed native delete remains owned by the frontend reaper rather
	than by an unreferenced local coordinator.
	"""
	from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
	coordinator = GraphicsRetirementCoordinator()
	coordinator.retire_detached_projection_items(items, reaper=reaper)
	coordinator.raise_if_callback_failed(
		"Detached graphics were released after a disposal failure",
	)


#============================================
def persistent_selection_key(
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> tuple[str, str] | None:
	"""Return the durable CDML identity represented by an item or its parent.

	Selection is presentation state, so a replacement may carry it forward only
	when the item has an identifier that is already persisted in CDML.  Generated
	labels, marks, handles, and anonymous graphics intentionally return ``None``.
	"""
	current = item
	while bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(current):
		model = getattr(current, "document_object_model", None)
		object_id = getattr(model, "object_id", None)
		if object_id:
			return ("presentation", str(object_id))
		atom_model = getattr(current, "atom_model", None)
		if atom_model is not None:
			atom_id = getattr(atom_model, "backend_durable_id", None)
			return ("atom", str(atom_id)) if atom_id else None
		bond_model = getattr(current, "bond_model", None)
		if bond_model is not None:
			bond_id = getattr(bond_model, "backend_durable_id", None)
			return ("bond", str(bond_id)) if bond_id else None
		mark_model = getattr(current, "atom_mark_model", None)
		if mark_model is not None:
			atom_id = getattr(mark_model.atom_model, "backend_durable_id", None)
			return ("atom", str(atom_id)) if atom_id else None
		group_model = getattr(current, "group_model", None)
		group_id = getattr(group_model, "group_id", None)
		if group_id:
			return ("group", str(group_id))
		molecule = getattr(current, "molecule_model", None)
		molecule_id = getattr(molecule, "mol_id", None)
		if molecule_id:
			return ("molecule", str(molecule_id))
		current = bkchem_qt.canvas.graphics_retirement.native_parent_for_item(current)
	return None


#============================================
def atom_mark_delete_target_for_items(
		document: object, items: tuple[PySide6.QtWidgets.QGraphicsItem, ...],
		) -> tuple[str, str, str, int] | None:
	"""Return plain exact-mark deletion intent for one current supported MarkItem."""
	if len(items) != 1:
		return None
	item = items[0]
	if not isinstance(item, bkchem_qt.canvas.items.mark_item.MarkItem):
		return None
	if not document.is_current_projection_item(item):
		return None
	mark_model = getattr(item, "atom_mark_model", None)
	if mark_model is None or not mark_model.supported or mark_model not in document.marks:
		return None
	atom_item = bkchem_qt.canvas.graphics_retirement.native_parent_for_item(item)
	if not isinstance(atom_item, bkchem_qt.canvas.items.atom_item.AtomItem):
		return None
	if getattr(atom_item, "atom_model", None) is not mark_model.atom_model:
		return None
	molecule = document.molecule_for_graphics_item(atom_item)
	molecule_id = getattr(molecule, "mol_id", None)
	atom_id = getattr(mark_model.atom_model, "backend_durable_id", None)
	mark_type = mark_model.mark_type
	matching_mark_index = mark_model.matching_mark_index
	if (
		type(molecule_id) is not str or not molecule_id
		or type(atom_id) is not str or not atom_id
		or type(mark_type) is not str or not mark_type
		or type(matching_mark_index) is not int or matching_mark_index < 0
		):
		return None
	return molecule_id, atom_id, mark_type, matching_mark_index


#============================================
def select_projected_persistent_keys(
		scene: PySide6.QtWidgets.QGraphicsScene,
		keys: frozenset[tuple[str, str]],
		) -> None:
	"""Restore durable selections only to their canonical projection owners.

	An anonymous MarkItem inherits its atom's durable selection key for ordinary
	interactive correlation, but it is not a durable selection owner.  Selecting
	it here would make one backend atom selection reappear as two Qt selections
	after canonical reprojection.
	"""
	for item in scene.items():
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(item):
			continue
		if getattr(item, "atom_mark_model", None) is not None:
			continue
		molecule = getattr(item, "molecule_model", None)
		molecule_id = getattr(molecule, "mol_id", None)
		molecule_key = ("molecule", str(molecule_id)) if molecule_id else None
		if persistent_selection_key(item) in keys or molecule_key in keys:
			item.setSelected(True)


#============================================
def project_marks(document: object,
		scene: PySide6.QtWidgets.QGraphicsScene) -> dict[object, PySide6.QtWidgets.QGraphicsItem]:
	"""Project document atom marks beneath their matching AtomItem parents."""
	projected = {}
	for model in document.marks:
		atom_item = _find_atom_item(scene, model.atom_model)
		if atom_item is None:
			continue
		item = create_mark_item(model, atom_item)
		if item is None:
			continue
		projected[model] = item
	return projected


#============================================
def project_document_presentation(document: object,
		scene: PySide6.QtWidgets.QGraphicsScene) -> dict:
	"""Apply paper state and project all non-molecule document artwork."""
	if document.paper.attributes and hasattr(scene, "apply_paper_model"):
		scene.apply_paper_model(document.paper)
	presentation = project_presentation_objects(document, scene)
	marks = project_marks(document, scene)
	synchronize_document_stack_z_order(document, scene)
	projected = {"presentation": presentation, "marks": marks}
	return projected


#============================================
def _molecule_for_item(document: object,
		item: PySide6.QtWidgets.QGraphicsItem) -> object | None:
	"""Resolve one molecule graphics item through its model identity."""
	molecule = getattr(item, "molecule_model", None)
	if molecule in document.molecules:
		return molecule
	atom_model = getattr(item, "atom_model", None)
	if atom_model is not None:
		return document._find_molecule_for_atom(atom_model)
	bond_model = getattr(item, "bond_model", None)
	if bond_model is not None:
		return document._find_molecule_for_bond(bond_model)
	parent = bkchem_qt.canvas.graphics_retirement.native_parent_for_item(item)
	if parent is not None:
		return _molecule_for_item(document, parent)
	return None


#============================================
def synchronize_document_stack_z_order(
		document: object, scene: PySide6.QtWidgets.QGraphicsScene,
		) -> None:
	"""Apply ``Document.objects`` order to every projected top-level object.

	Molecules occupy a small z band so bonds remain below their atoms while the
	whole molecule still follows document order relative to presentation
	objects.  Model identities on graphics items, never scene enumeration, are
	the authority for this synchronization.
	"""
	stack_indices = {
		id(object_model): index
		for index, object_model in enumerate(document.objects)
	}
	for item in scene.items():
		object_model = getattr(item, "document_object_model", None)
		if object_model is not None and id(object_model) in stack_indices:
			item.setZValue(float(stack_indices[id(object_model)] * 100 + 20))
			continue
		molecule = _molecule_for_item(document, item)
		if molecule is None:
			continue
		stack_index = stack_indices.get(id(molecule))
		if stack_index is None:
			continue
		if getattr(item, "atom_model", None) is not None:
			layer = 10
		elif getattr(item, "bond_model", None) is not None:
			layer = 5
		else:
			layer = 11
		item.setZValue(float(stack_index * 100 + layer))
