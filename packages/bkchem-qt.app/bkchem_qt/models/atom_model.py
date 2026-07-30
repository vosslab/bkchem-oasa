"""Qt composition wrapper around an OASA Atom with change signals."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import oasa.atom_lib


#============================================
class AtomModel(PySide6.QtCore.QObject):
	"""Composition wrapper that owns an OASA Atom and emits Qt signals on changes.

	Delegates chemistry properties (symbol, charge, valency, etc.) to an
	internal ``oasa.atom_lib.Atom`` instance and stores display properties
	(coordinates, font, visibility) locally. Every setter emits
	``property_changed(name, new_value)`` so the scene can react.

	Args:
		oasa_atom: Existing OASA Atom to wrap. A default Carbon atom is
			created when ``None``.
		parent: Optional parent QObject.
	"""

	# signal emitted whenever a property changes: (property_name, new_value)
	property_changed = PySide6.QtCore.Signal(str, object)

	#============================================
	def __init__(self, oasa_atom: oasa.atom_lib.Atom = None, parent: PySide6.QtCore.QObject = None) -> None:
		"""Initialize the atom model.

		Args:
			oasa_atom: Existing OASA Atom to wrap, or None for default Carbon.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		# chemistry backend
		self._chem_atom = oasa_atom or oasa.atom_lib.Atom()
		# The projection can allocate a private linkage ID for an ID-less legacy
		# atom.  Keep the backend-issued identity separate so a local repair
		# cannot become a target in an authoritative request.
		self._backend_durable_id: str | None = None
		# coordinates (display layer owns these)
		self._x = 0.0
		self._y = 0.0
		self._z = 0.0
		# display properties
		self._show = True
		self._show_hydrogens = True
		self._font_size = 12
		self._font_family = "Arial"
		self._line_color = "#000000"
		# Atom numbering is a frontend projection of backend-owned CDML depiction
		# state. It remains separate from the OASA chemistry atom.
		self._number: int | None = None
		self._show_number = True
		# Fields explicitly supplied by CDML or changed through the Qt model.
		# This avoids writing display defaults merely because a model was created.
		self._cdml_display_fields: set[str] = set()

	# ------------------------------------------------------------------
	# Chemistry properties delegated to _chem_atom
	# ------------------------------------------------------------------

	#============================================
	@property
	def atom_id(self) -> str | None:
		"""Return the persisted CDML atom identifier without exposing OASA state."""
		return self._chem_atom.id

	#============================================
	@property
	def backend_durable_id(self) -> str | None:
		"""Return an authoritative atom ID only while local linkage agrees."""
		if self._backend_durable_id and self.atom_id == self._backend_durable_id:
			return self._backend_durable_id
		return None

	#============================================
	def bind_backend_durable_id(self, identifier: str | None) -> None:
		"""Bind this projection to an ID present in the backend snapshot."""
		self._backend_durable_id = str(identifier) if identifier else None

	#============================================
	@property
	def symbol(self) -> str:
		"""Element symbol, e.g. 'C', 'N', 'O'."""
		return self._chem_atom.symbol

	#============================================
	@symbol.setter
	def symbol(self, value: str) -> None:
		self._chem_atom.symbol = value
		self.property_changed.emit("symbol", value)

	#============================================
	@property
	def charge(self) -> int:
		"""Formal charge on the atom."""
		return self._chem_atom.charge

	#============================================
	@charge.setter
	def charge(self, value: int) -> None:
		self._chem_atom.charge = value
		self.property_changed.emit("charge", value)

	#============================================
	@property
	def valency(self) -> int:
		"""Maximum valency."""
		return self._chem_atom.valency

	#============================================
	@valency.setter
	def valency(self, value: int) -> None:
		self._chem_atom.valency = value
		self.property_changed.emit("valency", value)

	#============================================
	@property
	def isotope(self) -> int | None:
		"""Mass number (int or None)."""
		return self._chem_atom.isotope

	#============================================
	@isotope.setter
	def isotope(self, value: int | None) -> None:
		self._chem_atom.isotope = value
		self.property_changed.emit("isotope", value)

	#============================================
	@property
	def multiplicity(self) -> int:
		"""Spin multiplicity (1 = singlet)."""
		return self._chem_atom.multiplicity

	#============================================
	@multiplicity.setter
	def multiplicity(self, value: int) -> None:
		self._chem_atom.multiplicity = value
		self.property_changed.emit("multiplicity", value)

	#============================================
	@property
	def free_sites(self) -> int:
		"""Coordination sites beyond normal valency."""
		return self._chem_atom.free_sites

	#============================================
	@free_sites.setter
	def free_sites(self, value: int) -> None:
		self._chem_atom.free_sites = value
		self.property_changed.emit("free_sites", value)

	#============================================
	@property
	def explicit_hydrogens(self) -> int:
		"""Explicitly declared hydrogen count."""
		return self._chem_atom.explicit_hydrogens

	#============================================
	@explicit_hydrogens.setter
	def explicit_hydrogens(self, value: int) -> None:
		self._chem_atom.explicit_hydrogens = int(value)
		self.property_changed.emit("explicit_hydrogens", int(value))

	#============================================
	@property
	def free_valency(self) -> int:
		"""Remaining unused valency (read-only, computed by OASA)."""
		return self._chem_atom.free_valency

	#============================================
	@property
	def occupied_valency(self) -> int:
		"""Valency consumed by bonds, charge, and multiplicity (read-only)."""
		return self._chem_atom.occupied_valency

	#============================================
	@property
	def symbol_number(self) -> int:
		"""Atomic number (read-only, set by symbol)."""
		return self._chem_atom.symbol_number

	#============================================
	@property
	def oxidation_number(self) -> int:
		"""Oxidation number computed from electronegativity and bonds (read-only)."""
		return self._chem_atom.oxidation_number

	# ------------------------------------------------------------------
	# Coordinate properties (display layer)
	# ------------------------------------------------------------------

	#============================================
	@property
	def x(self) -> float:
		"""X coordinate in scene units."""
		return self._x

	#============================================
	@x.setter
	def x(self, value: float) -> None:
		self._x = float(value)
		# sync to OASA atom so render ops see correct coordinates
		self._chem_atom.x = self._x
		self.property_changed.emit("x", self._x)

	#============================================
	@property
	def y(self) -> float:
		"""Y coordinate in scene units."""
		return self._y

	#============================================
	@y.setter
	def y(self, value: float) -> None:
		self._y = float(value)
		# sync to OASA atom so render ops see correct coordinates
		self._chem_atom.y = self._y
		self.property_changed.emit("y", self._y)

	#============================================
	@property
	def z(self) -> float:
		"""Z coordinate (used for 3D stereochemistry)."""
		return self._z

	#============================================
	@z.setter
	def z(self, value: float) -> None:
		self._z = float(value)
		# sync to OASA atom so render ops see correct coordinates
		self._chem_atom.z = self._z
		self.property_changed.emit("z", self._z)

	# ------------------------------------------------------------------
	# Display properties (local)
	# ------------------------------------------------------------------

	#============================================
	@property
	def show(self) -> bool:
		"""Whether to display the atom symbol on the canvas."""
		return self._show

	#============================================
	@show.setter
	def show(self, value: bool) -> None:
		self._show = bool(value)
		self._cdml_display_fields.add("show")
		self._chem_atom.properties_["show"] = "yes" if self._show else "no"
		self.property_changed.emit("show", self._show)

	#============================================
	@property
	def show_hydrogens(self) -> bool:
		"""Whether to display hydrogen labels."""
		return self._show_hydrogens

	#============================================
	@show_hydrogens.setter
	def show_hydrogens(self, value: bool) -> None:
		self._show_hydrogens = bool(value)
		self._cdml_display_fields.add("show_hydrogens")
		self._chem_atom.properties_["show_hydrogens"] = "on" if self._show_hydrogens else "off"
		self.property_changed.emit("show_hydrogens", self._show_hydrogens)

	#============================================
	@property
	def font_size(self) -> int:
		"""Font size for the atom label."""
		return self._font_size

	#============================================
	@font_size.setter
	def font_size(self, value: int) -> None:
		self._font_size = int(value)
		self._cdml_display_fields.add("font_size")
		self.property_changed.emit("font_size", self._font_size)

	#============================================
	@property
	def font_family(self) -> str:
		"""Font family for the atom label."""
		return self._font_family

	#============================================
	@font_family.setter
	def font_family(self, value: str) -> None:
		self._font_family = str(value)
		self._cdml_display_fields.add("font_family")
		self.property_changed.emit("font_family", self._font_family)

	#============================================
	@property
	def line_color(self) -> str:
		"""Color string for the atom label (e.g. '#000000')."""
		return self._line_color

	#============================================
	@line_color.setter
	def line_color(self, value: str) -> None:
		self._line_color = str(value)
		self._cdml_display_fields.add("line_color")
		self.property_changed.emit("line_color", self._line_color)

	#============================================
	@property
	def number(self) -> int | None:
		"""Optional persistent atom number shown by the canvas projection."""
		return self._number

	#============================================
	@number.setter
	def number(self, value: int | None) -> None:
		"""Set the optional atom number without changing its visibility policy."""
		if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
			raise TypeError("atom number must be an integer or None")
		self._number = value
		self.property_changed.emit("number", self._number)

	#============================================
	@property
	def show_number(self) -> bool:
		"""Whether an assigned atom number is projected on the canvas."""
		return self._show_number

	#============================================
	@show_number.setter
	def show_number(self, value: bool) -> None:
		"""Set whether the assigned number is visible in the canvas projection."""
		if not isinstance(value, bool):
			raise TypeError("show_number must be a bool")
		self._show_number = value
		self.property_changed.emit("show_number", self._show_number)

	# ------------------------------------------------------------------
	# Methods
	# ------------------------------------------------------------------

	#============================================
	def get_xyz(self) -> tuple:
		"""Return coordinates as a (x, y, z) tuple.

		Returns:
			Tuple of (x, y, z) floats.
		"""
		return (self._x, self._y, self._z)

	#============================================
	def set_xyz(self, x: float, y: float, z: float = 0.0) -> None:
		"""Set all three coordinates at once and emit signals.

		Args:
			x: X coordinate.
			y: Y coordinate.
			z: Z coordinate (default 0.0).
		"""
		self._x = float(x)
		self._y = float(y)
		self._z = float(z)
		# sync to OASA atom so render ops see correct coordinates
		self._chem_atom.x = self._x
		self._chem_atom.y = self._y
		self._chem_atom.z = self._z
		self.property_changed.emit("x", self._x)
		self.property_changed.emit("y", self._y)
		self.property_changed.emit("z", self._z)

	#============================================
	def get_hydrogen_count(self) -> int:
		"""Return total hydrogen count (explicit + implicit free valency).

		Returns:
			Number of hydrogens attached to this atom.
		"""
		return self._chem_atom.get_hydrogen_count()

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		return f"AtomModel(symbol='{self.symbol}', charge={self.charge})"
