"""Main application toolbar with action buttons."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.widgets.icon_loader


# map action names to icon sources: either a pixmap name (str) or a
# QStyle.StandardPixmap enum value for Qt built-in fallback icons
_ACTION_ICON_MAP = {
	"new": PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileIcon,
	"open": PySide6.QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton,
	"save": PySide6.QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton,
	"undo": "undo",
	"redo": "redo",
	"cut": PySide6.QtWidgets.QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton,
	"copy": PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView,
	"paste": PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogListView,
	"zoom_in": PySide6.QtWidgets.QStyle.StandardPixmap.SP_ArrowUp,
	"zoom_out": PySide6.QtWidgets.QStyle.StandardPixmap.SP_ArrowDown,
	"reset_zoom": PySide6.QtWidgets.QStyle.StandardPixmap.SP_BrowserReload,
	"toggle_grid": PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView,
}


#============================================
def _load_action_icon(name: str) -> PySide6.QtGui.QIcon:
	"""Load the icon for a toolbar action by name.

	Checks the pixmaps directory first, then falls back to Qt built-in
	standard pixmaps.

	Args:
		name: Action name key from _ACTION_ICON_MAP.

	Returns:
		QIcon for the action.
	"""
	source = _ACTION_ICON_MAP.get(name)
	if source is None:
		return PySide6.QtGui.QIcon()
	# string means a pixmap name in bkchem_data/pixmaps/
	if isinstance(source, str):
		icon = bkchem_qt.widgets.icon_loader.get_icon(source)
		if not icon.isNull():
			return icon
	# enum means a Qt built-in standard pixmap
	if isinstance(source, PySide6.QtWidgets.QStyle.StandardPixmap):
		style = PySide6.QtWidgets.QApplication.style()
		return style.standardIcon(source)
	return PySide6.QtGui.QIcon()


#============================================
class MainToolbar(PySide6.QtWidgets.QToolBar):
	"""Main toolbar with file, edit, and view actions.

	Organizes actions into logical sections separated by dividers.
	Each action has a text label, tooltip, icon, and optional keyboard
	shortcut.

	Args:
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, parent=None):
		"""Initialize the main toolbar.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__("Main Toolbar", parent)
		self.setMovable(True)
		self.setIconSize(PySide6.QtCore.QSize(32, 32))
		# store created actions for external access
		self._actions = {}

	#============================================
	def setup_actions(self, main_window) -> None:
		"""Create toolbar actions connected to main window slots.

		Builds three sections separated by dividers:
		- File: New, Open, Save
		- Edit: Undo, Redo, Cut, Copy, Paste
		- View: Zoom In, Zoom Out, Reset Zoom, Toggle Grid

		Args:
			main_window: The MainWindow instance providing slots.
		"""
		# -- File section --
		self._actions["new"] = self._create_action(
			"new",
			self.tr("New"), self.tr("Create a new document"),
			shortcut="Ctrl+N",
			callback=getattr(main_window, "on_new", None),
		)
		self._actions["open"] = self._create_action(
			"open",
			self.tr("Open"), self.tr("Open an existing file"),
			shortcut="Ctrl+O",
			callback=getattr(main_window, "on_open", None),
		)
		self._actions["save"] = self._create_action(
			"save",
			self.tr("Save"), self.tr("Save the current document"),
			shortcut="Ctrl+S",
			callback=getattr(main_window, "on_save", None),
		)

		self.addSeparator()

		# -- Edit section --
		self._actions["undo"] = self._create_action(
			"undo",
			self.tr("Undo"), self.tr("Undo the last action"),
			shortcut="Ctrl+Z",
			callback=getattr(main_window, "on_undo", None),
		)
		self._actions["redo"] = self._create_action(
			"redo",
			self.tr("Redo"), self.tr("Redo the last undone action"),
			shortcut="Ctrl+Shift+Z",
			callback=getattr(main_window, "on_redo", None),
		)

		self.addSeparator()

		self._actions["cut"] = self._create_action(
			"cut",
			self.tr("Cut"), self.tr("Cut selected items"),
			shortcut="Ctrl+X",
			callback=getattr(main_window, "on_cut", None),
		)
		self._actions["copy"] = self._create_action(
			"copy",
			self.tr("Copy"), self.tr("Copy selected items"),
			shortcut="Ctrl+C",
			callback=getattr(main_window, "on_copy", None),
		)
		self._actions["paste"] = self._create_action(
			"paste",
			self.tr("Paste"), self.tr("Paste from clipboard"),
			shortcut="Ctrl+V",
			callback=getattr(main_window, "on_paste", None),
		)

		self.addSeparator()

		# -- View section --
		self._actions["zoom_in"] = self._create_action(
			"zoom_in",
			self.tr("Zoom In"), self.tr("Zoom in on the canvas"),
			shortcut="Ctrl+=",
			callback=getattr(main_window, "on_zoom_in", None),
		)
		self._actions["zoom_out"] = self._create_action(
			"zoom_out",
			self.tr("Zoom Out"), self.tr("Zoom out on the canvas"),
			shortcut="Ctrl+-",
			callback=getattr(main_window, "on_zoom_out", None),
		)
		self._actions["reset_zoom"] = self._create_action(
			"reset_zoom",
			self.tr("Reset Zoom"), self.tr("Reset zoom to 100%"),
			shortcut="Ctrl+0",
			callback=getattr(main_window, "on_reset_zoom", None),
		)

		self.addSeparator()

		self._actions["toggle_grid"] = self._create_action(
			"toggle_grid",
			self.tr("Grid"), self.tr("Toggle grid visibility"),
			shortcut="Ctrl+G",
			callback=getattr(main_window, "on_toggle_grid", None),
		)

	#============================================
	def _create_action(self, name: str, text: str, tooltip: str,
			shortcut: str = None, callback=None) -> PySide6.QtGui.QAction:
		"""Helper to create a QAction with icon and add it to the toolbar.

		Args:
			name: Action key for icon lookup.
			text: Action display text.
			tooltip: Tooltip string shown on hover.
			shortcut: Optional keyboard shortcut string.
			callback: Optional callable connected to triggered signal.

		Returns:
			The created QAction.
		"""
		action = PySide6.QtGui.QAction(text, self)
		action.setToolTip(tooltip)
		# load icon for this action
		icon = _load_action_icon(name)
		if not icon.isNull():
			action.setIcon(icon)
		if shortcut:
			action.setShortcut(PySide6.QtGui.QKeySequence(shortcut))
		if callback is not None:
			action.triggered.connect(callback)
		self.addAction(action)
		return action

	#============================================
	def refresh_icons(self) -> None:
		"""Reload icons for all actions from the current theme.

		Called after a theme switch to update toolbar icons.
		"""
		for name, action in self._actions.items():
			icon = _load_action_icon(name)
			if not icon.isNull():
				action.setIcon(icon)

	#============================================
	def get_action(self, name: str) -> PySide6.QtGui.QAction:
		"""Retrieve a named action.

		Args:
			name: The action key (e.g. "new", "undo", "zoom_in").

		Returns:
			The QAction, or None if not found.
		"""
		return self._actions.get(name)
