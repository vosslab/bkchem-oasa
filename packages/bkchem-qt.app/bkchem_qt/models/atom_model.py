"""Scalar Qt projection of one atom.

``AtomModel`` deliberately contains no OASA object.  Persistent chemistry and
connected-graph facts belong to the backend; compatibility callers materialize
a short-lived OASA graph through :mod:`bkchem_qt.bridge.oasa_bridge`.
"""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore


#============================================
class AtomModel(PySide6.QtCore.QObject):
	"""A disposable scalar atom projection with Qt change notifications."""

	property_changed = PySide6.QtCore.Signal(str, object)

	#============================================
	def __init__(
			self, symbol: str = "C", *, atom_id: str | None = None,
			charge: int = 0, valency: int | None = None,
			authored_valency: int | None = None, isotope: int | None = None,
			multiplicity: int = 1, free_sites: int = 0,
			explicit_hydrogens: int = 0, x: float = 0.0, y: float = 0.0,
			z: float = 0.0, parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Create one scalar atom projection without an OASA carrier."""
		super().__init__(parent)
		self._molecule_model: object | None = None
		self._backend_durable_id: str | None = None
		self._cdml_display_fields: set[str] = set()
		self._number: int | None = None
		self._show_number = True
		self._show = True
		self._show_hydrogens = True
		self._font_size = 12
		self._font_family = "Arial"
		self._line_color = "#000000"
		self._atom_id = self._validated_identifier(atom_id)
		self._symbol, default_valency = self._creation_facts(symbol)
		self._charge = self._validated_int(charge, "charge")
		self._valency = self._validated_int(
			default_valency if valency is None else valency, "valency",
		)
		self._authored_valency = self._validated_optional_int(
			authored_valency, "authored valency",
		)
		self._isotope = self._validated_optional_int(isotope, "isotope")
		self._multiplicity = self._validated_int(multiplicity, "multiplicity")
		self._free_sites = self._validated_int(free_sites, "free sites")
		self._explicit_hydrogens = self._validated_int(
			explicit_hydrogens, "explicit hydrogens",
		)
		self._x = self._validated_coordinate(x, "x")
		self._y = self._validated_coordinate(y, "y")
		self._z = self._validated_coordinate(z, "z")

	#============================================
	@classmethod
	def create(
			cls, symbol: str = "C", parent: PySide6.QtCore.QObject | None = None,
			) -> "AtomModel":
		"""Create one new scalar atom projection."""
		return cls(symbol=symbol, parent=parent)

	#============================================
	@staticmethod
	def _validated_identifier(value: str | None) -> str | None:
		if value is None or value == "":
			return None
		if type(value) is not str:
			raise TypeError("atom ID must be a string or None")
		return value

	#============================================
	@staticmethod
	def _creation_facts(value: str) -> tuple[str, int]:
		"""Resolve supported element defaults without retaining an OASA value."""
		from bkchem_qt.bridge.oasa_bridge import atom_creation_facts
		return atom_creation_facts(value)

	#============================================
	@classmethod
	def _validated_symbol(cls, value: str) -> str:
		return cls._creation_facts(value)[0]

	#============================================
	@staticmethod
	def _validated_int(value: int, name: str) -> int:
		if type(value) is not int:
			raise TypeError(f"{name} must be an integer")
		return value

	#============================================
	@classmethod
	def _validated_optional_int(cls, value: int | None, name: str) -> int | None:
		if value is None:
			return None
		return cls._validated_int(value, name)

	#============================================
	@staticmethod
	def _validated_coordinate(value: float, name: str) -> float:
		if isinstance(value, bool) or not isinstance(value, (int, float)):
			raise TypeError(f"{name} coordinate must be a finite number")
		result = float(value)
		if not math.isfinite(result):
			raise ValueError(f"{name} coordinate must be finite")
		return result

	#============================================
	@property
	def molecule_model(self) -> object | None:
		"""Return the current Qt topology owner, if any."""
		return self._molecule_model

	#============================================
	def set_molecule_model(self, molecule_model: object | None) -> None:
		"""Set the Qt-only topology relationship."""
		self._molecule_model = molecule_model

	#============================================
	@property
	def atom_id(self) -> str | None:
		"""Return the scalar CDML ID, safely including ID-less legacy atoms."""
		return self._atom_id

	#============================================
	@atom_id.setter
	def atom_id(self, value: str | None) -> None:
		self._atom_id = self._validated_identifier(value)
		self.property_changed.emit("atom_id", self._atom_id)

	#============================================
	@property
	def backend_durable_id(self) -> str | None:
		"""Return the backend address only while it agrees with this scalar ID."""
		if self._backend_durable_id == self._atom_id:
			return self._backend_durable_id
		return None

	#============================================
	def bind_backend_durable_id(self, identifier: str | None) -> None:
		"""Bind a backend-issued durable address without changing scalar identity."""
		self._backend_durable_id = self._validated_identifier(identifier)

	#============================================
	@property
	def symbol(self) -> str:
		return self._symbol

	@symbol.setter
	def symbol(self, value: str) -> None:
		self._symbol, self._valency = self._creation_facts(value)
		self._authored_valency = None
		self.property_changed.emit("symbol", self._symbol)
		self.property_changed.emit("valency", self._valency)

	#============================================
	@property
	def charge(self) -> int:
		return self._charge

	@charge.setter
	def charge(self, value: int) -> None:
		self._charge = self._validated_int(value, "charge")
		self.property_changed.emit("charge", self._charge)

	#============================================
	@property
	def valency(self) -> int:
		"""Return the effective valency supplied by the projection boundary."""
		return self._valency

	@valency.setter
	def valency(self, value: int) -> None:
		self._valency = self._validated_int(value, "valency")
		self._authored_valency = self._valency
		self.property_changed.emit("valency", self._valency)

	#============================================
	@property
	def authored_valency(self) -> int | None:
		"""Return authored valency presence separately from effective valency."""
		return self._authored_valency

	#============================================
	@property
	def isotope(self) -> int | None:
		return self._isotope

	@isotope.setter
	def isotope(self, value: int | None) -> None:
		self._isotope = self._validated_optional_int(value, "isotope")
		self.property_changed.emit("isotope", self._isotope)

	#============================================
	@property
	def multiplicity(self) -> int:
		return self._multiplicity

	@multiplicity.setter
	def multiplicity(self, value: int) -> None:
		self._multiplicity = self._validated_int(value, "multiplicity")
		self.property_changed.emit("multiplicity", self._multiplicity)

	#============================================
	@property
	def free_sites(self) -> int:
		return self._free_sites

	@free_sites.setter
	def free_sites(self, value: int) -> None:
		self._free_sites = self._validated_int(value, "free sites")
		self.property_changed.emit("free_sites", self._free_sites)

	#============================================
	@property
	def explicit_hydrogens(self) -> int:
		return self._explicit_hydrogens

	@explicit_hydrogens.setter
	def explicit_hydrogens(self, value: int) -> None:
		self._explicit_hydrogens = self._validated_int(value, "explicit hydrogens")
		self.property_changed.emit("explicit_hydrogens", self._explicit_hydrogens)

	#============================================
	@property
	def x(self) -> float:
		return self._x

	@x.setter
	def x(self, value: float) -> None:
		self._x = self._validated_coordinate(value, "x")
		self.property_changed.emit("x", self._x)

	#============================================
	@property
	def y(self) -> float:
		return self._y

	@y.setter
	def y(self, value: float) -> None:
		self._y = self._validated_coordinate(value, "y")
		self.property_changed.emit("y", self._y)

	#============================================
	@property
	def z(self) -> float:
		return self._z

	@z.setter
	def z(self, value: float) -> None:
		self._z = self._validated_coordinate(value, "z")
		self.property_changed.emit("z", self._z)

	#============================================
	@property
	def show(self) -> bool:
		return self._show

	@show.setter
	def show(self, value: bool) -> None:
		if type(value) is not bool:
			raise TypeError("show must be a bool")
		self._show = value
		self._cdml_display_fields.add("show")
		self.property_changed.emit("show", value)

	#============================================
	@property
	def show_hydrogens(self) -> bool:
		return self._show_hydrogens

	@show_hydrogens.setter
	def show_hydrogens(self, value: bool) -> None:
		if type(value) is not bool:
			raise TypeError("show_hydrogens must be a bool")
		self._show_hydrogens = value
		self._cdml_display_fields.add("show_hydrogens")
		self.property_changed.emit("show_hydrogens", value)

	#============================================
	@property
	def font_size(self) -> int:
		return self._font_size

	@font_size.setter
	def font_size(self, value: int) -> None:
		self._font_size = self._validated_int(value, "font size")
		self._cdml_display_fields.add("font_size")
		self.property_changed.emit("font_size", self._font_size)

	#============================================
	@property
	def font_family(self) -> str:
		return self._font_family

	@font_family.setter
	def font_family(self, value: str) -> None:
		if type(value) is not str:
			raise TypeError("font family must be a string")
		self._font_family = value
		self._cdml_display_fields.add("font_family")
		self.property_changed.emit("font_family", value)

	#============================================
	@property
	def line_color(self) -> str:
		return self._line_color

	@line_color.setter
	def line_color(self, value: str) -> None:
		if type(value) is not str:
			raise TypeError("line color must be a string")
		self._line_color = value
		self._cdml_display_fields.add("line_color")
		self.property_changed.emit("line_color", value)

	#============================================
	@property
	def number(self) -> int | None:
		return self._number

	@number.setter
	def number(self, value: int | None) -> None:
		self._number = self._validated_optional_int(value, "atom number")
		self.property_changed.emit("number", self._number)

	#============================================
	@property
	def show_number(self) -> bool:
		return self._show_number

	@show_number.setter
	def show_number(self, value: bool) -> None:
		if type(value) is not bool:
			raise TypeError("show_number must be a bool")
		self._show_number = value
		self.property_changed.emit("show_number", value)

	#============================================
	@property
	def cdml_display_fields(self) -> frozenset[str]:
		"""Return exact authored display-field presence."""
		return frozenset(self._cdml_display_fields)

	#============================================
	def install_projection(
			self, *, atom_id: str | None, symbol: str, charge: int, valency: int,
			authored_valency: int | None, isotope: int | None, multiplicity: int,
			free_sites: int, explicit_hydrogens: int, x: float, y: float, z: float,
			show: bool = True, show_hydrogens: bool = True, font_size: int = 12,
			font_family: str = "Arial", line_color: str = "#000000",
			number: int | None = None, show_number: bool = True,
			explicit_fields: frozenset[str] = frozenset(),
			) -> None:
		"""Quietly install one accepted scalar observation without emitting signals."""
		if not isinstance(explicit_fields, frozenset) or not all(
			type(field) is str for field in explicit_fields
		):
			raise TypeError("explicit fields must be a frozenset of strings")
		self._atom_id = self._validated_identifier(atom_id)
		self._symbol = self._validated_symbol(symbol)
		self._charge = self._validated_int(charge, "charge")
		self._valency = self._validated_int(valency, "valency")
		self._authored_valency = self._validated_optional_int(authored_valency, "authored valency")
		self._isotope = self._validated_optional_int(isotope, "isotope")
		self._multiplicity = self._validated_int(multiplicity, "multiplicity")
		self._free_sites = self._validated_int(free_sites, "free sites")
		self._explicit_hydrogens = self._validated_int(explicit_hydrogens, "explicit hydrogens")
		self._x = self._validated_coordinate(x, "x")
		self._y = self._validated_coordinate(y, "y")
		self._z = self._validated_coordinate(z, "z")
		if type(show) is not bool or type(show_hydrogens) is not bool or type(show_number) is not bool:
			raise TypeError("display visibility values must be bools")
		self._show = show
		self._show_hydrogens = show_hydrogens
		self._font_size = self._validated_int(font_size, "font size")
		if type(font_family) is not str or type(line_color) is not str:
			raise TypeError("display typography values must be strings")
		self._font_family = font_family
		self._line_color = line_color
		self._number = self._validated_optional_int(number, "atom number")
		self._show_number = show_number
		self._cdml_display_fields = set(explicit_fields)

	#============================================
	def get_xyz(self) -> tuple[float, float, float]:
		return (self._x, self._y, self._z)

	#============================================
	def set_xyz(self, x: float, y: float, z: float = 0.0) -> None:
		self._x = self._validated_coordinate(x, "x")
		self._y = self._validated_coordinate(y, "y")
		self._z = self._validated_coordinate(z, "z")
		self.property_changed.emit("x", self._x)
		self.property_changed.emit("y", self._y)
		self.property_changed.emit("z", self._z)

	#============================================
	def __repr__(self) -> str:
		return f"AtomModel(symbol='{self.symbol}', charge={self.charge})"
