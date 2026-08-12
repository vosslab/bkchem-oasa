"""Miscellaneous mode for atom numbering and special annotations."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import oasa.cdml_presentation_insert


_PREVIEW_PEN_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine


#============================================
class MiscMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for miscellaneous operations like atom numbering.

	Provides access to less common drawing operations. The active
	submode determines the operation:
	- numbering: click atoms in sequence to assign numbers
	- clear-numbers: click to clear numbering from atoms
	- wavy: press, drag, and release to add a presentation-only wavy line

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view: object, parent: PySide6.QtCore.QObject | None = None) -> None:
		"""Initialize the miscellaneous mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Misc"
		self._cursor = PySide6.QtCore.Qt.CursorShape.PointingHandCursor
		# active operation (from submode selection)
		self._operation = "number"
		# running counter for atom numbering
		self._next_number = 1
		# Transient scene-only state for an in-progress wavy line.
		self._wavy_start = None
		self._wavy_preview = None
		self._wavy_preview_scene = None
		self._persistent_operation = None
		self._atom_number_context = None
		self._atom_number_revision = None

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Misc persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def set_atom_number_context(self, provider: object | None) -> None:
		"""Install or clear the session-owned atom-number context provider."""
		if provider is not None and not callable(provider):
			raise TypeError("Misc atom-number context provider must be callable")
		self._atom_number_context = provider
		self._atom_number_revision = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return misc mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		if self._operation == "number":
			return f"Click atoms to number them (next: {self._next_number})"
		if self._operation == "clear-numbers":
			return "Click an atom to clear its number"
		if self._operation == "wavy":
			return "Drag to draw a wavy line"
		return "Click to apply operation"

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Switch the active operation when a submode is selected.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		# ``modes.yaml`` is the toolbar's public vocabulary.  Preserve the
		# compact internal operation name used by the original implementation.
		if name == "numbering":
			self._operation = "number"
		else:
			self._operation = name
		self.status_message.emit(self.status_hint)

	#============================================
	def activate(self) -> None:
		"""Start after the highest number already owned by the document."""
		self._refresh_next_number()
		super().activate()

	#============================================
	def _refresh_next_number(self) -> None:
		"""Refresh transient numbering from the authoritative snapshot provider."""
		if self._atom_number_context is None:
			return
		context = self._atom_number_context()
		if (
			not isinstance(context, tuple)
			or len(context) != 2
			or type(context[0]) is not int
		):
			raise ValueError("Atom-number context provider must return revision and candidate")
		revision, next_number = context
		if type(next_number) is not int or next_number <= 0:
			raise ValueError("Atom-number candidate provider must return a positive integer")
		self._atom_number_revision = revision
		self._next_number = next_number

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Apply the active operation at the click position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._operation == "wavy":
			self._wavy_start = PySide6.QtCore.QPointF(scene_pos)
			self.status_message.emit("Drag to set wavy-line endpoint")
			return
		item = self._item_at(scene_pos)
		if self._operation == "number":
			self._number_atom(item, scene_pos)
		elif self._operation == "clear-numbers":
			self._clear_number(item)

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Update the transient wavy-line preview while dragging."""
		if self._operation != "wavy" or self._wavy_start is None:
			return
		self._remove_wavy_preview()
		scene = self._env.scene
		if scene is None:
			return
		try:
			points = oasa.cdml_presentation_insert.wavy_points(
				(self._wavy_start.x(), self._wavy_start.y()),
				(scene_pos.x(), scene_pos.y()),
			)
		except ValueError as error:
			self.status_message.emit(str(error))
			return
		if len(points) < 2:
			return
		path = _path_for_points(_qpoints_for_wavy(points))
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(80, 80, 80, 150))
		pen.setWidthF(1.0)
		pen.setStyle(_PREVIEW_PEN_STYLE)
		self._wavy_preview = scene.addPath(path, pen)
		self._wavy_preview_scene = scene

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Submit one completed normal Wavy drag through backend authority."""
		if self._operation != "wavy":
			return
		start = self._wavy_start
		self._remove_wavy_preview()
		self._wavy_start = None
		if start is None:
			return
		try:
			points = oasa.cdml_presentation_insert.wavy_points(
				(start.x(), start.y()),
				(scene_pos.x(), scene_pos.y()),
			)
		except ValueError as error:
			self.status_message.emit(str(error))
			return
		if len(points) < 2:
			self.status_message.emit(self.status_hint)
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"wavy.add", "Wavy",
			(("start", (start.x(), start.y())), ("end", (scene_pos.x(), scene_pos.y()))),
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)

	#============================================
	def deactivate(self) -> None:
		"""Discard an in-progress preview when this mode loses focus."""
		self._remove_wavy_preview()
		self._wavy_start = None
		super().deactivate()

	#============================================
	def _remove_wavy_preview(self) -> None:
		"""Terminally retire transient feedback without changing document state."""
		wavy_preview = self._wavy_preview
		wavy_preview_scene = self._wavy_preview_scene
		if wavy_preview is None:
			return
		try:
			coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
			if wavy_preview_scene is None:
				coordinator.retire_detached_projection_items(
					[wavy_preview], reaper=self._graphics_retirement_reaper,
				)
			else:
				coordinator.retire_scene_projection_items(
					wavy_preview_scene, [wavy_preview],
					reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Wavy preview retirement failed")
		finally:
			self._wavy_preview = None
			self._wavy_preview_scene = None

	#============================================
	def _number_atom(self, item: object | None, scene_pos: PySide6.QtCore.QPointF) -> None:
		"""Assign a sequential number to the clicked atom.

		If an AtomItem is under the cursor, submits a durable scalar request.

		Args:
			item: The item at the click position (or None).
			scene_pos: The click position in scene coordinates.
		"""
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		self._refresh_next_number()
		atom_model = item.atom_model
		new_number = self._next_number
		molecule = self._env.document.molecule_for_graphics_item(item)
		if molecule is None:
			self.status_message.emit("Atom has no persistent molecule identity")
			return
		molecule_id = molecule.mol_id
		atom_id = atom_model.backend_durable_id
		if not isinstance(molecule_id, str) or not molecule_id:
			self.status_message.emit("Atom has no persistent molecule identity")
			return
		if not isinstance(atom_id, str) or not atom_id:
			self.status_message.emit("Atom has no persistent identity")
			return
		show_number = atom_model.show_number if atom_model.number is not None else True
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"atom.number.set", "Number Atom",
			(
				("expected_revision", self._numbering_revision()),
				("molecule_id", molecule_id), ("atom_id", atom_id),
				("number", new_number), ("show_number", show_number),
			),
			frozenset({("molecule", molecule_id), ("atom", atom_id)}),
		)
		outcome = self._persistent_operation(request)
		self._refresh_next_number()
		self.status_message.emit(outcome.message)

	#============================================
	def _clear_number(self, item: object | None) -> None:
		"""Remove the number label from the clicked atom.

		Args:
			item: The item at the click position (or None).
		"""
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		self._refresh_next_number()
		atom_model = item.atom_model
		if atom_model.number is None:
			self.status_message.emit("No number to clear")
			self._refresh_next_number()
			return
		molecule = self._env.document.molecule_for_graphics_item(item)
		if molecule is None:
			self.status_message.emit("Atom has no persistent molecule identity")
			return
		molecule_id = molecule.mol_id
		atom_id = atom_model.backend_durable_id
		if not isinstance(molecule_id, str) or not molecule_id:
			self.status_message.emit("Atom has no persistent molecule identity")
			return
		if not isinstance(atom_id, str) or not atom_id:
			self.status_message.emit("Atom has no persistent identity")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"atom.number.set", "Clear Atom Number",
			(
				("expected_revision", self._numbering_revision()),
				("molecule_id", molecule_id), ("atom_id", atom_id),
				("number", None), ("show_number", None),
			),
			frozenset({("molecule", molecule_id), ("atom", atom_id)}),
		)
		outcome = self._persistent_operation(request)
		self._refresh_next_number()
		self.status_message.emit(outcome.message)

	#============================================
	def _numbering_revision(self) -> int:
		"""Return the authoritative revision captured with the next candidate."""
		revision = self._atom_number_revision
		if type(revision) is not int:
			raise ValueError("Atom numbering requires a backend snapshot revision")
		return revision


#============================================
def _path_for_points(
		points: tuple[PySide6.QtCore.QPointF, ...],
		) -> PySide6.QtGui.QPainterPath:
	"""Build a scene path from deterministic presentation points."""
	path = PySide6.QtGui.QPainterPath()
	path.moveTo(points[0])
	for point in points[1:]:
		path.lineTo(point)
	return path


#============================================
def _qpoints_for_wavy(
		points: tuple[tuple[float, float], ...],
		) -> tuple[PySide6.QtCore.QPointF, ...]:
	"""Adapt pure Wavy geometry to transient Qt preview points."""
	result = tuple(PySide6.QtCore.QPointF(x, y) for x, y in points)
	return result
