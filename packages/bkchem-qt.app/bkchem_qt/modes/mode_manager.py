"""Mode manager for switching between interaction modes."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.edit_mode
import bkchem_qt.modes.draw_mode


#============================================
class ModeManager(PySide6.QtCore.QObject):
	"""Manages the current interaction mode and mode switching.

	Registers named modes, handles transitions (deactivate old, activate
	new), and dispatches mouse/keyboard events from ChemView to the
	currently active mode.

	Args:
		view: The ChemView widget whose events are dispatched.
		parent: Optional parent QObject.
	"""

	# emitted when the active mode changes, carries the new mode name
	mode_changed = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, view: object, parent: object = None) -> None:
		"""Initialize the mode manager with built-in modes.

		Registers edit and draw modes and sets edit as the default.

		Args:
			view: The ChemView widget whose events are dispatched.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._view = view
		self._modes = {}
		self._current_mode = None
		self._disposed = False
		# register built-in modes
		self.register_mode(
			"edit",
			bkchem_qt.modes.edit_mode.EditMode(view),
		)
		self.register_mode(
			"draw",
			bkchem_qt.modes.draw_mode.DrawMode(view),
		)
		# set default mode
		self.set_mode("edit")

	# ------------------------------------------------------------------
	# Mode management
	# ------------------------------------------------------------------

	#============================================
	def register_mode(self, name: str, mode: object) -> None:
		"""Register a mode under a given name.

		Args:
			name: Short name for the mode (e.g. 'edit', 'draw').
			mode: BaseMode instance to register.
		"""
		self._modes[name] = mode

	#============================================
	def set_mode(self, name: str) -> None:
		"""Switch to the named mode.

		Deactivates the current mode (if any) and activates the new
		one. Emits ``mode_changed`` with the new mode name.

		Args:
			name: Name of the mode to activate.

		Raises:
			KeyError: If no mode is registered under ``name``.
		"""
		if name not in self._modes:
			raise KeyError(f"Unknown mode: {name!r}")
		# deactivate current mode
		if self._current_mode is not None:
			self._current_mode.deactivate()
		# activate new mode
		self._current_mode = self._modes[name]
		self._current_mode.activate()
		self.mode_changed.emit(name)

	#============================================
	@property
	def current_mode(self) -> object:
		"""Return the currently active BaseMode instance.

		Returns:
			The active BaseMode, or None if no mode is set.
		"""
		return self._current_mode

	#============================================
	def mode_names(self) -> list:
		"""Return a list of all registered mode names.

		Returns:
			List of mode name strings.
		"""
		return list(self._modes.keys())

	#============================================
	def mode(self, name: str) -> object:
		"""Return one registered mode by its stable public name."""
		if name not in self._modes:
			raise KeyError(f"Unknown mode: {name!r}")
		return self._modes[name]

	#============================================
	def dispose(self) -> None:
		"""Deactivate and queue every Python-backed mode independently.

		Deleting a Python ``QObject`` parent can recursively destroy its Python
		children while Shiboken is deallocating the parent's attribute graph.
		Detach the registered modes first and retain their wrappers in
		``_modes`` until the manager's later deferred deletion.
		"""
		if self._disposed:
			return
		self._disposed = True
		if self._current_mode is not None:
			self._current_mode.deactivate()
		self._current_mode = None
		for mode in self._modes.values():
			mode.setParent(None)
			mode.deleteLater()

	#============================================
	def release_python_references(self) -> None:
		"""Break mode-to-view references after an external owner retains roots."""
		for mode in self._modes.values():
			mode._view = None
			environment = getattr(mode, "_env", None)
			if environment is not None:
				environment._view = None
		self._modes.clear()
		self._current_mode = None
		self._view = None

	# ------------------------------------------------------------------
	# Event dispatch
	# ------------------------------------------------------------------

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Dispatch a mouse press event to the active mode.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_mode is not None:
			self._current_mode.mouse_press(scene_pos, event)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Dispatch a mouse release event to the active mode.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_mode is not None:
			self._current_mode.mouse_release(scene_pos, event)

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Dispatch a mouse move event to the active mode.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_mode is not None:
			self._current_mode.mouse_move(scene_pos, event)

	#============================================
	def mouse_press3(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Dispatch a right-click (button-3) press event to the active mode.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_mode is not None:
			self._current_mode.mouse_press3(scene_pos, event)

	#============================================
	def mouse_double_click(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Dispatch a mouse double-click event to the active mode.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_mode is not None:
			self._current_mode.mouse_double_click(scene_pos, event)

	#============================================
	def key_press(self, event: object) -> None:
		"""Dispatch a key press event to the active mode.

		Args:
			event: The QKeyEvent.
		"""
		if self._current_mode is not None:
			self._current_mode.key_press(event)

	#============================================
	def key_release(self, event: object) -> None:
		"""Dispatch a key release event to the active mode.

		Args:
			event: The QKeyEvent.
		"""
		if self._current_mode is not None:
			self._current_mode.key_release(event)
