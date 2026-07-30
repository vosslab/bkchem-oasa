"""Non-mutating Qt export planning and temporary scene projection."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item

# A legacy paper with crop enabled but no explicit margin uses this display
# margin.  It is intentionally kept in one place for SVG and clipboard use.
DEFAULT_CROP_MARGIN = 20.0


#============================================
@dataclasses.dataclass(frozen=True)
class RenderPlan:
	"""Describe one export's source rectangle and decoration policy."""

	source_rect: PySide6.QtCore.QRectF
	include_decorations: bool
	crop_to_content: bool


#============================================
@dataclasses.dataclass
class ExportProjection:
	"""Own temporary supported graphics used for content-only rendering."""

	scene: PySide6.QtWidgets.QGraphicsScene | None
	items: list[PySide6.QtWidgets.QGraphicsItem]
	_disposed: bool = dataclasses.field(default=False, init=False, repr=False)

	#============================================
	def dispose(self) -> None:
		"""Retire the temporary graphics and scene once in callback-safe order."""
		if self._disposed:
			return
		# Mark terminal state before any fallible native work.  The temporary-scene
		# reaper owns the scene through deferred deletion, rather than leaving its
		# wrapper to Python finalization after this projection releases references.
		self._disposed = True
		items = list(self.items)
		self.items.clear()
		scene = self.scene
		self.scene = None
		if scene is None:
			return
		from bkchem_qt.canvas.graphics_retirement import temporary_scene_retirement_reaper
		record = temporary_scene_retirement_reaper.retire(scene, items, [])
		temporary_scene_retirement_reaper.drain()
		if record.diagnostics:
			raise RuntimeError(
				"Export projection was retired after a disposal failure",
			) from record.diagnostics[0]


#============================================
@dataclasses.dataclass
class ExportRenderScope:
	"""End a native painter before retiring an optional temporary projection."""

	projection: ExportProjection | None
	painter: PySide6.QtGui.QPainter

	#============================================
	def __enter__(self) -> "ExportRenderScope":
		"""Enter the scope after its projection has been fully constructed."""
		return self

	#============================================
	def __exit__(self, exception_type: type[BaseException] | None,
			exception: BaseException | None, traceback: object) -> bool:
		"""Finish native rendering, then dispose without replacing a primary error."""
		first_error = None
		try:
			if self.painter.isActive():
				self.painter.end()
		except Exception as exc:
			first_error = exc
		try:
			if self.projection is not None:
				self.projection.dispose()
		except Exception as exc:
			if first_error is None:
				first_error = exc
		if exception_type is None and first_error is not None:
			raise RuntimeError("Export rendering cleanup failed") from first_error
		return False


#============================================
def _is_truthy(value: object) -> bool:
	"""Return whether a CDML integer/bool attribute enables an option."""
	text = str(value).strip().lower()
	result = text in ("1", "true", "yes", "on")
	return result


#============================================
def _crop_margin(attributes: dict[str, str], fallback: float) -> float:
	"""Return the explicit CDML crop margin or the caller's display fallback."""
	value = attributes.get("crop_margin")
	if value is None:
		return fallback
	result = float(value)
	if result < 0.0:
		raise ValueError("paper crop_margin must not be negative")
	return result


#============================================
def _is_decoration(scene: PySide6.QtWidgets.QGraphicsScene,
		item: PySide6.QtWidgets.QGraphicsItem) -> bool:
	"""Return whether an item belongs to the paper/grid rather than content."""
	if item is getattr(scene, "_paper_item", None):
		return True
	return item is getattr(scene, "_grid_overlay", None)


#============================================
def content_rect(scene: PySide6.QtWidgets.QGraphicsScene) -> PySide6.QtCore.QRectF:
	"""Return visible document-content bounds without paper or grid graphics."""
	bounds = PySide6.QtCore.QRectF()
	for item in scene.items():
		if _is_decoration(scene, item) or not item.isVisible():
			continue
		bounds = bounds.united(item.sceneBoundingRect())
	return bounds


#============================================
def build_render_plan(scene: PySide6.QtWidgets.QGraphicsScene,
		format_name: str, margin: float = DEFAULT_CROP_MARGIN,
		force_content_crop: bool = False) -> RenderPlan:
	"""Choose page or content bounds for one format without changing the scene.

	``crop_svg`` is a modeled CDML paper option and applies only to SVG. PNG
	and PDF remain page exports so their paper layout is preserved.
	"""
	attributes = getattr(scene, "_paper_attributes", {})
	crop_svg = format_name.lower() == "svg" and _is_truthy(
		attributes.get("crop_svg", "0")
	)
	crop_to_content = force_content_crop or crop_svg
	if crop_to_content:
		crop_margin = _crop_margin(attributes, margin)
		bounds = content_rect(scene)
		if bounds.isEmpty():
			paper_rect = getattr(scene, "paper_rect", None)
			if paper_rect is not None:
				bounds = paper_rect
			else:
				bounds = scene.sceneRect()
		else:
			bounds = bounds.adjusted(
				-crop_margin, -crop_margin, crop_margin, crop_margin,
			)
		plan = RenderPlan(bounds, False, True)
		return plan
	plan = RenderPlan(scene.paper_rect, True, False)
	return plan


#============================================
def _molecule_for_item(item: PySide6.QtWidgets.QGraphicsItem) -> object | None:
	"""Resolve a molecule model through an item or one of its parents."""
	current = item
	while current is not None:
		molecule = getattr(current, "molecule_model", None)
		if molecule is not None:
			return molecule
		current = current.parentItem()
	return None


#============================================
def _selected_models(
		scene: PySide6.QtWidgets.QGraphicsScene,
		selected_items: list[PySide6.QtWidgets.QGraphicsItem] | None,
		) -> tuple[list[object], list[object]]:
	"""Resolve supported molecule and presentation models in a stable order."""
	items = scene.items() if selected_items is None else selected_items
	molecules = []
	presentations = []
	seen_molecules = set()
	seen_presentations = set()
	for item in items:
		molecule = _molecule_for_item(item)
		if molecule is not None and id(molecule) not in seen_molecules:
			seen_molecules.add(id(molecule))
			molecules.append(molecule)
		presentation = getattr(item, "document_object_model", None)
		if presentation is not None and getattr(presentation, "supported", False):
			if id(presentation) not in seen_presentations:
				seen_presentations.add(id(presentation))
				presentations.append(presentation)
	return molecules, presentations


#============================================
def _source_z_values(scene: PySide6.QtWidgets.QGraphicsScene) -> dict[int, float]:
	"""Map projected model identity to its current document stacking value."""
	values = {}
	for item in scene.items():
		for attribute in ("atom_model", "bond_model", "atom_mark_model",
				"document_object_model"):
			model = getattr(item, attribute, None)
			if model is not None:
				values[id(model)] = item.zValue()
	return values


#============================================
def _project_marks(
		source_scene: PySide6.QtWidgets.QGraphicsScene,
		target_scene: PySide6.QtWidgets.QGraphicsScene,
		molecules: list[object], atom_items: dict[int, PySide6.QtWidgets.QGraphicsItem],
		z_values: dict[int, float], items: list[PySide6.QtWidgets.QGraphicsItem],
		) -> None:
	"""Project marks attached to included molecules beneath their cloned atoms."""
	included_atoms = {
		id(atom_model) for molecule in molecules for atom_model in molecule.atoms
	}
	seen_marks = set()
	for source_item in source_scene.items():
		mark_model = getattr(source_item, "atom_mark_model", None)
		if mark_model is None or id(mark_model) in seen_marks:
			continue
		if id(mark_model.atom_model) not in included_atoms:
			continue
		parent = atom_items[id(mark_model.atom_model)]
		item = bkchem_qt.canvas.document_projection.create_mark_item(mark_model, parent)
		if item is None:
			continue
		# Retain the child before later setup can fail, so transaction cleanup
		# releases its callback before its parent atom or temporary scene retires.
		items.append(item)
		seen_marks.add(id(mark_model))
		item.setZValue(z_values.get(id(mark_model), source_item.zValue()))


#============================================
def _add_temporary_item(
		scene: PySide6.QtWidgets.QGraphicsScene,
		item: PySide6.QtWidgets.QGraphicsItem,
		items: list[PySide6.QtWidgets.QGraphicsItem],
		detached_items: list[PySide6.QtWidgets.QGraphicsItem],
		) -> None:
	"""Transfer a newly constructed item into the temporary scene explicitly."""
	scene.addItem(item)
	detached_items.remove(item)
	items.append(item)


#============================================
def project_supported_items(scene: PySide6.QtWidgets.QGraphicsScene,
		selected_items: list[PySide6.QtWidgets.QGraphicsItem] | None = None,
		) -> ExportProjection:
	"""Clone supported selected content into a temporary render-only scene.

	The live scene, selection, visibility, and persistent document models remain
	untouched. Molecule selection expands to its atom-attached supported marks.
	Unsupported retained CDML has no graphics projection and is not rendered.
	"""
	molecules, presentations = _selected_models(scene, selected_items)
	temporary = PySide6.QtWidgets.QGraphicsScene()
	items = []
	detached_items = []
	atom_items = {}
	z_values = _source_z_values(scene)
	try:
		for molecule in molecules:
			for bond_model in molecule.bonds:
				item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
				detached_items.append(item)
				item.molecule_model = molecule
				item.setZValue(z_values.get(id(bond_model), item.zValue()))
				_add_temporary_item(temporary, item, items, detached_items)
			for atom_model in molecule.atoms:
				item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
				detached_items.append(item)
				item.molecule_model = molecule
				item.setZValue(z_values.get(id(atom_model), item.zValue()))
				_add_temporary_item(temporary, item, items, detached_items)
				atom_items[id(atom_model)] = item
		_project_marks(scene, temporary, molecules, atom_items, z_values, items)
		for presentation in presentations:
			item = bkchem_qt.canvas.document_projection.create_presentation_item(presentation)
			if item is None:
				continue
			detached_items.append(item)
			item.setZValue(z_values.get(id(presentation), item.zValue()))
			_add_temporary_item(temporary, item, items, detached_items)
	except Exception as exc:
		# Keep the construction failure primary while the reaper retains all
		# native wrappers until its ordered scene/deferred-delete transition ends.
		# Snapshot both ownership domains before clearing construction-local lists:
		# items already adopted by the temporary scene need the same callback and
		# explicit-retirement path as a completed projection.
		scene_items = list(items)
		detached_roots = list(detached_items)
		items.clear()
		detached_items.clear()
		from bkchem_qt.canvas.graphics_retirement import temporary_scene_retirement_reaper
		record = temporary_scene_retirement_reaper.retire(
			temporary, scene_items, detached_roots,
		)
		temporary_scene_retirement_reaper.drain()
		if record.diagnostics:
			exc.add_note(
				"Temporary export projection retirement remains owned by the Qt reaper: "
				f"{record.diagnostics[0]!r}",
			)
		raise
	projection = ExportProjection(temporary, items)
	return projection
