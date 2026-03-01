"""Qt composition wrapper around an OASA Bond with change signals."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import oasa.bond_lib


#============================================
class BondModel(PySide6.QtCore.QObject):
	"""Composition wrapper that owns an OASA Bond and emits Qt signals on changes.

	Delegates chemistry properties (order, type, aromatic) to an internal
	``oasa.bond_lib.Bond`` instance. Stores endpoint references (AtomModel
	pairs) and display properties (line width, wedge width, centering, etc.)
	locally. Every setter emits ``property_changed(name, new_value)``.

	Args:
		oasa_bond: Existing OASA Bond to wrap. A default single bond is
			created when ``None``.
		parent: Optional parent QObject.
	"""

	# signal emitted whenever a property changes: (property_name, new_value)
	property_changed = PySide6.QtCore.Signal(str, object)

	#============================================
	def __init__(self, oasa_bond: oasa.bond_lib.Bond = None, parent: PySide6.QtCore.QObject = None):
		"""Initialize the bond model.

		Args:
			oasa_bond: Existing OASA Bond to wrap, or None for default single bond.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		# chemistry backend
		self._chem_bond = oasa_bond or oasa.bond_lib.Bond()
		# endpoint AtomModel references (managed by MoleculeModel)
		self._atom1 = None
		self._atom2 = None
		# display properties
		self._line_color = "#000000"
		self._line_width = 2.0
		self._bond_width = 6.0
		self._wedge_width = 9.2
		self._center = None
		self._simple_double = False
		self._auto_bond_sign = 1
		self._double_length_ratio = 0.75

	# ------------------------------------------------------------------
	# Chemistry properties delegated to _chem_bond
	# ------------------------------------------------------------------

	#============================================
	@property
	def order(self) -> int:
		"""Bond order: 1 (single), 2 (double), 3 (triple), 4 (aromatic)."""
		return self._chem_bond.order

	#============================================
	@order.setter
	def order(self, value: int):
		self._chem_bond.order = value
		self.property_changed.emit("order", value)

	#============================================
	@property
	def type(self) -> str:
		"""Bond type character: 'n','w','h','a','b','d','o','s','q'."""
		return self._chem_bond.type

	#============================================
	@type.setter
	def type(self, value: str):
		self._chem_bond.type = value
		self.property_changed.emit("type", value)

	#============================================
	@property
	def aromatic(self):
		"""Aromatic flag: None (not set), True, or False."""
		return self._chem_bond.aromatic

	#============================================
	@aromatic.setter
	def aromatic(self, value):
		self._chem_bond.aromatic = value
		self.property_changed.emit("aromatic", value)

	# ------------------------------------------------------------------
	# Endpoint properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def atom1(self):
		"""First endpoint AtomModel (or None if not yet connected)."""
		return self._atom1

	#============================================
	@atom1.setter
	def atom1(self, value):
		self._atom1 = value
		self.property_changed.emit("atom1", value)

	#============================================
	@property
	def atom2(self):
		"""Second endpoint AtomModel (or None if not yet connected)."""
		return self._atom2

	#============================================
	@atom2.setter
	def atom2(self, value):
		self._atom2 = value
		self.property_changed.emit("atom2", value)

	#============================================
	@property
	def atoms(self) -> list:
		"""Return both endpoint AtomModels as a list.

		Returns:
			List of [atom1, atom2].
		"""
		return [self._atom1, self._atom2]

	# ------------------------------------------------------------------
	# Display properties (local)
	# ------------------------------------------------------------------

	#============================================
	@property
	def line_color(self) -> str:
		"""Color string for bond rendering (e.g. '#000000')."""
		return self._line_color

	#============================================
	@line_color.setter
	def line_color(self, value: str):
		self._line_color = str(value)
		self.property_changed.emit("line_color", self._line_color)

	#============================================
	@property
	def line_width(self) -> float:
		"""Display line width in pixels."""
		return self._line_width

	#============================================
	@line_width.setter
	def line_width(self, value: float):
		self._line_width = float(value)
		self.property_changed.emit("line_width", self._line_width)

	#============================================
	@property
	def bond_width(self) -> float:
		"""Signed display width for double/triple bond offset."""
		return self._bond_width

	#============================================
	@bond_width.setter
	def bond_width(self, value: float):
		self._bond_width = float(value)
		self.property_changed.emit("bond_width", self._bond_width)

	#============================================
	@property
	def wedge_width(self) -> float:
		"""Wedge bond display width."""
		return self._wedge_width

	#============================================
	@wedge_width.setter
	def wedge_width(self, value: float):
		self._wedge_width = float(value)
		self.property_changed.emit("wedge_width", self._wedge_width)

	#============================================
	@property
	def center(self):
		"""Double bond centering: None (auto), True (force centered), False (offset)."""
		return self._center

	#============================================
	@center.setter
	def center(self, value):
		self._center = value
		self.property_changed.emit("center", self._center)

	#============================================
	@property
	def simple_double(self) -> bool:
		"""Non-normal double bond style option."""
		return self._simple_double

	#============================================
	@simple_double.setter
	def simple_double(self, value: bool):
		self._simple_double = bool(value)
		self.property_changed.emit("simple_double", self._simple_double)

	#============================================
	@property
	def auto_bond_sign(self) -> int:
		"""Auto sign for bond placement direction."""
		return self._auto_bond_sign

	#============================================
	@auto_bond_sign.setter
	def auto_bond_sign(self, value: int):
		self._auto_bond_sign = int(value)
		self.property_changed.emit("auto_bond_sign", self._auto_bond_sign)

	#============================================
	@property
	def double_length_ratio(self) -> float:
		"""Second line length ratio for double bonds (0.0 to 1.0)."""
		return self._double_length_ratio

	#============================================
	@double_length_ratio.setter
	def double_length_ratio(self, value: float):
		self._double_length_ratio = float(value)
		self.property_changed.emit("double_length_ratio", self._double_length_ratio)

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		return f"BondModel(order={self.order}, type='{self.type}')"
