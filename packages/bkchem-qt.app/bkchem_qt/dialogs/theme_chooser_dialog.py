"""Theme chooser dialog for selecting a color theme."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.themes.theme_loader


#============================================
class ThemeChooserDialog(PySide6.QtWidgets.QDialog):
	"""Dialog with a list of available themes for the user to choose from.

	Displays theme names in a QListWidget with the current theme
	preselected. Returns the selected theme name on accept.

	Args:
		current_theme: Name of the currently active theme.
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(
		self, current_theme: str,
		parent: PySide6.QtWidgets.QWidget = None,
	):
		"""Initialize the theme chooser dialog.

		Args:
			current_theme: Name of the currently active theme.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self.setWindowTitle(self.tr("Choose Theme"))
		self.setMinimumWidth(250)
		self._selected_theme = None
		self._build_ui(current_theme)

	#============================================
	def _build_ui(self, current_theme: str) -> None:
		"""Build the dialog layout with theme list and OK/Cancel buttons.

		Args:
			current_theme: Name of the currently active theme.
		"""
		layout = PySide6.QtWidgets.QVBoxLayout(self)

		# list of available themes
		self._list_widget = PySide6.QtWidgets.QListWidget()
		theme_names = bkchem_qt.themes.theme_loader.get_theme_names()
		for name in theme_names:
			self._list_widget.addItem(name)
		layout.addWidget(self._list_widget)

		# preselect the current theme
		for i in range(self._list_widget.count()):
			item = self._list_widget.item(i)
			if item.text() == current_theme:
				self._list_widget.setCurrentItem(item)
				break

		# allow double-click to accept
		self._list_widget.itemDoubleClicked.connect(self.accept)

		# OK / Cancel buttons
		button_box = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel
		)
		button_box.accepted.connect(self.accept)
		button_box.rejected.connect(self.reject)
		layout.addWidget(button_box)

	#============================================
	def selected_theme(self) -> str:
		"""Return the name of the selected theme.

		Returns:
			Theme name string, or None if nothing is selected.
		"""
		current_item = self._list_widget.currentItem()
		if current_item is None:
			return None
		return current_item.text()

	#============================================
	@staticmethod
	def choose_theme(
		parent: PySide6.QtWidgets.QWidget,
		current_theme: str,
	) -> str:
		"""Show the theme chooser and return the selected theme name.

		Args:
			parent: Parent widget for the dialog.
			current_theme: Name of the currently active theme.

		Returns:
			Selected theme name string, or None if the user cancelled.
		"""
		dialog = ThemeChooserDialog(current_theme, parent)
		result = dialog.exec()
		if result == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return dialog.selected_theme()
		return None
