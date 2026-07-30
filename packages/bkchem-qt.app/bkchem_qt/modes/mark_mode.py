"""Mark mode for adding chemical marks to atoms."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.mark_item
import bkchem_qt.models.document_object
import bkchem_qt.undo.commands


#============================================
class MarkMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for adding or removing chemical marks on atoms.

	Click on an atom to add a mark of the current type. If the atom
	already has a mark of the same type, it is removed (toggle behavior).
	The mark type can be changed via ``set_mark_type()``.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(
			self,
			view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the mark mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Mark"
		# default mark type to add
		self._current_mark_type = bkchem_qt.canvas.items.mark_item.MARK_PLUS
		self._cursor = PySide6.QtCore.Qt.CursorShape.PointingHandCursor

	#============================================
	@property
	def current_mark_type(self) -> str:
		"""Return the current mark type that will be applied on click."""
		return self._current_mark_type

	#============================================
	def set_mark_type(self, mark_type: str) -> None:
		"""Set the mark type for subsequent clicks.

		Args:
			mark_type: One of the MARK_* constants from mark_item module.
		"""
		self._current_mark_type = mark_type
		self.status_message.emit(f"Mark mode: {mark_type}")

	#============================================
	def mouse_press(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Add or toggle a mark on the atom under the cursor.

		If the click lands on an AtomItem, checks whether a mark of
		the current type already exists. If so, removes it; otherwise
		adds a new mark at the default angle for that type.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		atom_item = self._item_at(scene_pos)
		if not isinstance(atom_item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		document = self._env.document
		undo_stack = self._env.undo_stack
		if document is None or undo_stack is None:
			return
		legacy_mark_type = _legacy_mark_type(self._current_mark_type)
		if legacy_mark_type is None:
			return
		# Persisted models, rather than transient child item types, define toggle
		# identity. This also handles CDML's electronpair spelling consistently.
		existing_mark = _matching_mark_item(atom_item, legacy_mark_type)
		if existing_mark is not None:
			command = bkchem_qt.undo.commands.RemoveAtomMarkCommand(
				document,
				existing_mark.atom_mark_model,
				existing_mark,
				atom_item,
			)
			undo_stack.push(command)
			self.status_message.emit(f"Removed {self._current_mark_type} mark")
		else:
			# CDML stores mark position in document coordinates. MarkItem uses a
			# 12-point radial display offset, so preserve the same position.
			angle = _default_angle_for_type(self._current_mark_type)
			angle_radians = math.radians(angle)
			atom_model = atom_item.atom_model
			x = atom_model.x + 12.0 * math.cos(angle_radians)
			y = atom_model.y + 12.0 * math.sin(angle_radians)
			attributes = {
				"type": legacy_mark_type,
				"x": f"{x:g}",
				"y": f"{y:g}",
				"auto": "0",
				"size": "4",
				"angle": f"{angle:g}",
			}
			mark_model = bkchem_qt.models.document_object.AtomMarkModel(
				atom_model, attributes,
			)
			mark_item = bkchem_qt.canvas.document_projection.create_mark_item(
				mark_model, atom_item,
			)
			if mark_item is None:
				return
			command = bkchem_qt.undo.commands.AddAtomMarkCommand(
				document, mark_model, mark_item, atom_item,
			)
			undo_stack.push(command)
			self.status_message.emit(f"Added {self._current_mark_type} mark")


#============================================
def _default_angle_for_type(mark_type: str) -> float:
	"""Return a default placement angle for the given mark type.

	Args:
		mark_type: One of the MARK_* constants.

	Returns:
		Angle in degrees.
	"""
	angle_map = {
		bkchem_qt.canvas.items.mark_item.MARK_PLUS: 45.0,
		bkchem_qt.canvas.items.mark_item.MARK_MINUS: 45.0,
		bkchem_qt.canvas.items.mark_item.MARK_RADICAL: 90.0,
		bkchem_qt.canvas.items.mark_item.MARK_ELECTRON_PAIR: 180.0,
		bkchem_qt.canvas.items.mark_item.MARK_LONE_PAIR: 180.0,
	}
	angle = angle_map.get(mark_type, 0.0)
	return angle


#============================================
def _legacy_mark_type(mark_type: str) -> str | None:
	"""Map the Qt display type to the legacy CDML mark spelling.

	Args:
		mark_type: Current MarkItem constant selected by the ribbon.

	Returns:
		CDML mark type, or None when the ribbon supplied an unsupported type.
	"""
	legacy_types = {
		bkchem_qt.canvas.items.mark_item.MARK_PLUS: "plus",
		bkchem_qt.canvas.items.mark_item.MARK_MINUS: "minus",
		bkchem_qt.canvas.items.mark_item.MARK_RADICAL: "radical",
		bkchem_qt.canvas.items.mark_item.MARK_ELECTRON_PAIR: "electronpair",
		bkchem_qt.canvas.items.mark_item.MARK_LONE_PAIR: "electronpair",
	}
	legacy_type = legacy_types.get(mark_type)
	return legacy_type


#============================================
def _matching_mark_item(
		atom_item: bkchem_qt.canvas.items.atom_item.AtomItem,
		legacy_mark_type: str,
		) -> bkchem_qt.canvas.items.mark_item.MarkItem | None:
	"""Return this atom's persistent child mark of the requested CDML type.

	Args:
		atom_item: Atom projection whose child marks are inspected.
		legacy_mark_type: CDML type used to identify a matching mark.

	Returns:
		Matching persistent MarkItem, or None when no model-backed child matches.
	"""
	for child in atom_item.childItems():
		if not isinstance(child, bkchem_qt.canvas.items.mark_item.MarkItem):
			continue
		mark_model = getattr(child, "atom_mark_model", None)
		if mark_model is None:
			continue
		if mark_model.mark_type == legacy_mark_type:
			return child
	return None
