"""File actions mode for BKChem-Qt.

Provides New, Open, Save, and Save As as submode buttons in the
mode toolbar. Selecting a submode triggers the corresponding file
operation on the main window.
"""

# local repo modules
import bkchem_qt.modes.base_mode


# maps submode keys to MainWindow method names
_FILE_ACTION_METHODS = {
	'new': '_on_new',
	'open': '_on_open',
	'save': '_on_save',
	'save_as': '_on_save_as',
}


#============================================
class FileActionsMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode that exposes file operations as submode buttons.

	Each submode button (New, Open, Save, Save As) dispatches to the
	corresponding file handler on the main window.

	Args:
		view: The ChemView widget that dispatches events.
		main_window: The MainWindow instance for file handler access.
	"""

	#============================================
	def __init__(self, view, main_window=None):
		"""Initialize the file actions mode.

		Args:
			view: The ChemView widget that dispatches events.
			main_window: The MainWindow instance for file handler access.
		"""
		super().__init__(view)
		self._name = "file"
		self._main_window = main_window

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Dispatch to the appropriate file handler.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		if self._main_window is None:
			return
		method_name = _FILE_ACTION_METHODS.get(name)
		if method_name is None:
			return
		# handle save_as specially since MainWindow may not have it
		handler = getattr(self._main_window, method_name, None)
		if handler is not None:
			handler()
