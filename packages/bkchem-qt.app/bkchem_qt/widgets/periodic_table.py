"""Periodic table popup widget for element selection."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# Element data: (symbol, name, row, col)
# Covers common elements for organic and general chemistry
ELEMENTS = [
	("H", "Hydrogen", 0, 0),
	("He", "Helium", 0, 17),
	("Li", "Lithium", 1, 0),
	("Be", "Beryllium", 1, 1),
	("B", "Boron", 1, 12),
	("C", "Carbon", 1, 13),
	("N", "Nitrogen", 1, 14),
	("O", "Oxygen", 1, 15),
	("F", "Fluorine", 1, 16),
	("Ne", "Neon", 1, 17),
	("Na", "Sodium", 2, 0),
	("Mg", "Magnesium", 2, 1),
	("Al", "Aluminium", 2, 12),
	("Si", "Silicon", 2, 13),
	("P", "Phosphorus", 2, 14),
	("S", "Sulfur", 2, 15),
	("Cl", "Chlorine", 2, 16),
	("Ar", "Argon", 2, 17),
	("K", "Potassium", 3, 0),
	("Ca", "Calcium", 3, 1),
	("Ti", "Titanium", 3, 3),
	("Cr", "Chromium", 3, 5),
	("Mn", "Manganese", 3, 6),
	("Fe", "Iron", 3, 7),
	("Co", "Cobalt", 3, 8),
	("Ni", "Nickel", 3, 9),
	("Cu", "Copper", 3, 10),
	("Zn", "Zinc", 3, 11),
	("Ga", "Gallium", 3, 12),
	("Ge", "Germanium", 3, 13),
	("As", "Arsenic", 3, 14),
	("Se", "Selenium", 3, 15),
	("Br", "Bromine", 3, 16),
	("Kr", "Krypton", 3, 17),
	("Ag", "Silver", 4, 10),
	("Sn", "Tin", 4, 13),
	("I", "Iodine", 4, 16),
	("Xe", "Xenon", 4, 17),
	("Pt", "Platinum", 5, 9),
	("Au", "Gold", 5, 10),
	("Hg", "Mercury", 5, 11),
	("Pb", "Lead", 5, 13),
]

# color coding by element category
_NONMETAL_COLOR = "#a0ffa0"
_METAL_COLOR = "#ffa0a0"
_METALLOID_COLOR = "#ffffa0"
_NOBLE_GAS_COLOR = "#a0e0ff"
_HALOGEN_COLOR = "#ffff80"

# sets for classification
_NONMETALS = {"H", "C", "N", "O", "P", "S", "Se"}
_HALOGENS = {"F", "Cl", "Br", "I"}
_NOBLE_GASES = {"He", "Ne", "Ar", "Kr", "Xe"}
_METALLOIDS = {"B", "Si", "Ge", "As"}

# button size in pixels
_BTN_SIZE = 36


#============================================
def _element_color(symbol: str) -> str:
	"""Return background color hex string for an element category.

	Args:
		symbol: Chemical element symbol.

	Returns:
		Hex color string for the element's category.
	"""
	if symbol in _NONMETALS:
		return _NONMETAL_COLOR
	if symbol in _HALOGENS:
		return _HALOGEN_COLOR
	if symbol in _NOBLE_GASES:
		return _NOBLE_GAS_COLOR
	if symbol in _METALLOIDS:
		return _METALLOID_COLOR
	# default: metals
	return _METAL_COLOR


#============================================
class PeriodicTablePopup(PySide6.QtWidgets.QDialog):
	"""Popup dialog with a grid of element buttons.

	Each button shows an element symbol. Clicking a button emits
	``element_selected`` with the symbol string and closes the dialog.
	Buttons are color-coded by element type.

	Args:
		parent: Optional parent widget.
	"""

	# emitted when the user clicks an element button
	element_selected = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, parent=None):
		"""Initialize the periodic table popup.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self.setWindowTitle(self.tr("Select Element"))
		self._selected_symbol = ""
		self._build_ui()

	#============================================
	def _build_ui(self) -> None:
		"""Build the grid layout of element buttons."""
		layout = PySide6.QtWidgets.QGridLayout(self)
		layout.setSpacing(2)
		for symbol, name, row, col in ELEMENTS:
			btn = PySide6.QtWidgets.QPushButton(symbol)
			btn.setFixedSize(_BTN_SIZE, _BTN_SIZE)
			btn.setToolTip(name)
			# color-code by element type
			bg_color = _element_color(symbol)
			btn.setStyleSheet(
				f"background-color: {bg_color}; "
				"font-weight: bold; "
				"border: 1px solid #888;"
			)
			# connect click to selection handler
			btn.clicked.connect(self._make_handler(symbol))
			layout.addWidget(btn, row, col)

	#============================================
	def _make_handler(self, symbol: str):
		"""Create a click handler that selects the given element.

		Args:
			symbol: Element symbol to select on click.

		Returns:
			A callable that emits the signal and closes the dialog.
		"""
		def handler():
			self._selected_symbol = symbol
			self.element_selected.emit(symbol)
			self.accept()
		return handler

	#============================================
	@staticmethod
	def pick_element(parent=None) -> str:
		"""Show popup, return selected element symbol or empty string.

		Args:
			parent: Optional parent widget.

		Returns:
			The selected element symbol, or empty string if cancelled.
		"""
		dialog = PeriodicTablePopup(parent)
		result = dialog.exec()
		if result == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return dialog._selected_symbol
		return ""
