"""Qt scalar projection of one bond with change signals."""

# PIP3 modules
import PySide6.QtCore

#============================================
class BondModel(PySide6.QtCore.QObject):
	"""Qt-only scalar projection of one bond.

	The model owns only scalar chemistry, endpoint, and depiction facts.  The
	bridge materializes a short-lived OASA edge when a legacy calculation needs
	one; no OASA object crosses or remains in this Qt model.
	"""

	# signal emitted whenever a property changes: (property_name, new_value)
	property_changed = PySide6.QtCore.Signal(str, object)

	#============================================
	def __init__(
			self, order: int = 1, bond_type: str = "n",
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize a scalar bond projection."""
		super().__init__(parent)
		self._bond_id: str | None = None
		self._order = int(order)
		self._type = str(bond_type)
		self._aromatic: bool | None = None
		# Local projection linkage for ID-less legacy bonds is intentionally not a
		# backend operation target.  Only a source-snapshot ID is durable.
		self._backend_durable_id: str | None = None
		# endpoint AtomModel references (managed by MoleculeModel)
		self._atom1 = None
		self._atom2 = None
		# display properties
		self._line_color = "#000000"
		self._line_width = 2.0
		self._bond_width = 6.0
		self._wedge_width = 9.2
		self._center = None
		self._simple_double = True
		self._auto_bond_sign = 1
		self._double_length_ratio = 0.75
		self._equithick = False
		self._wavy_style = None
		self._haworth_position: str | None = None
		# Effective display values are separate from authoritative lexical
		# presence, so a projection does not author absent CDML attributes.
		self._cdml_display_fields: set[str] = set()

	#============================================
	@classmethod
	def create(
			cls, order: int = 1, bond_type: str = "n", bond_id: str | None = None,
			parent: PySide6.QtCore.QObject | None = None,
			) -> "BondModel":
		"""Create one new Qt bond wrapper from scalar topology values."""
		bond_model = cls(order=order, bond_type=bond_type, parent=parent)
		bond_model.bond_id = bond_id
		return bond_model

	# ------------------------------------------------------------------
	# Scalar chemistry properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def bond_id(self) -> str | None:
		"""Return this projected CDML bond identifier."""
		return self._bond_id

	#============================================
	@bond_id.setter
	def bond_id(self, value: str | None) -> None:
		"""Set a scalar local identifier used by standalone compatibility paths."""
		self._bond_id = str(value) if value else None
		self.property_changed.emit("bond_id", self._bond_id)

	#============================================
	@property
	def backend_durable_id(self) -> str | None:
		"""Return an authoritative bond ID only while local linkage agrees."""
		if self._backend_durable_id and self._bond_id == self._backend_durable_id:
			return self._backend_durable_id
		return None

	#============================================
	def bind_backend_durable_id(self, identifier: str | None) -> None:
		"""Bind this projection to an ID present in the backend snapshot."""
		self._backend_durable_id = str(identifier) if identifier else None

	#============================================
	@property
	def order(self) -> int:
		"""Bond order: 1 (single), 2 (double), 3 (triple), 4 (aromatic)."""
		return self._order

	#============================================
	@order.setter
	def order(self, value: int) -> None:
		self._order = int(value)
		self.property_changed.emit("order", self._order)

	#============================================
	@property
	def type(self) -> str:
		"""Bond type character: 'n','w','h','a','b','d','o','s','q'."""
		return self._type

	#============================================
	@type.setter
	def type(self, value: str) -> None:
		self._type = str(value)
		self.property_changed.emit("type", self._type)

	#============================================
	@property
	def aromatic(self) -> bool | None:
		"""Aromatic flag: None (not set), True, or False."""
		return self._aromatic

	#============================================
	@aromatic.setter
	def aromatic(self, value: bool | None) -> None:
		self._aromatic = value
		self.property_changed.emit("aromatic", self._aromatic)

	# ------------------------------------------------------------------
	# Endpoint properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def atom1(self) -> object | None:
		"""First endpoint AtomModel (or None if not yet connected)."""
		return self._atom1

	#============================================
	@atom1.setter
	def atom1(self, value: object | None) -> None:
		self._atom1 = value
		self.property_changed.emit("atom1", value)

	#============================================
	@property
	def atom2(self) -> object | None:
		"""Second endpoint AtomModel (or None if not yet connected)."""
		return self._atom2

	#============================================
	@atom2.setter
	def atom2(self, value: object | None) -> None:
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
	def line_color(self, value: str) -> None:
		self._line_color = str(value)
		self._record_cdml_display_field("color")
		self.property_changed.emit("line_color", self._line_color)

	#============================================
	@property
	def line_width(self) -> float:
		"""Display line width in pixels."""
		return self._line_width

	#============================================
	@line_width.setter
	def line_width(self, value: float) -> None:
		self._line_width = float(value)
		self._record_cdml_display_field("line_width")
		self.property_changed.emit("line_width", self._line_width)

	#============================================
	@property
	def bond_width(self) -> float:
		"""Signed display width for double/triple bond offset."""
		return self._bond_width

	#============================================
	@bond_width.setter
	def bond_width(self, value: float) -> None:
		self._bond_width = float(value)
		self._record_cdml_display_field("bond_width")
		self.property_changed.emit("bond_width", self._bond_width)

	#============================================
	@property
	def wedge_width(self) -> float:
		"""Wedge bond display width."""
		return self._wedge_width

	#============================================
	@wedge_width.setter
	def wedge_width(self, value: float) -> None:
		self._wedge_width = float(value)
		self._record_cdml_display_field("wedge_width")
		self.property_changed.emit("wedge_width", self._wedge_width)

	#============================================
	@property
	def center(self) -> bool | None:
		"""Double bond centering: None (auto), True (force centered), False (offset)."""
		return self._center

	#============================================
	@center.setter
	def center(self, value: bool | None) -> None:
		self._center = value
		if value is None:
			self._cdml_display_fields.discard("center")
		else:
			self._record_cdml_display_field("center")
		self.property_changed.emit("center", self._center)

	#============================================
	@property
	def simple_double(self) -> bool:
		"""Non-normal double bond style option."""
		return self._simple_double

	#============================================
	@simple_double.setter
	def simple_double(self, value: bool) -> None:
		self._simple_double = bool(value)
		self._record_cdml_display_field("simple_double")
		self.property_changed.emit("simple_double", self._simple_double)

	#============================================
	@property
	def auto_bond_sign(self) -> int:
		"""Auto sign for bond placement direction."""
		return self._auto_bond_sign

	#============================================
	@auto_bond_sign.setter
	def auto_bond_sign(self, value: int) -> None:
		self._auto_bond_sign = int(value)
		self._record_cdml_display_field("auto_sign")
		self.property_changed.emit("auto_bond_sign", self._auto_bond_sign)

	#============================================
	@property
	def double_length_ratio(self) -> float:
		"""Second line length ratio for double bonds (0.0 to 1.0)."""
		return self._double_length_ratio

	#============================================
	@double_length_ratio.setter
	def double_length_ratio(self, value: float) -> None:
		self._double_length_ratio = float(value)
		self._record_cdml_display_field("double_ratio")
		self.property_changed.emit("double_length_ratio", self._double_length_ratio)

	#============================================
	@property
	def equithick(self) -> bool:
		"""Whether all lines in a multi-line bond have equal thickness."""
		return self._equithick

	#============================================
	@equithick.setter
	def equithick(self, value: bool) -> None:
		self._equithick = bool(value)
		self._record_cdml_display_field("equithick")
		self.property_changed.emit("equithick", self._equithick)

	#============================================
	@property
	def wavy_style(self) -> str | None:
		"""Optional geometry style for wavy bonds."""
		return self._wavy_style

	#============================================
	@wavy_style.setter
	def wavy_style(self, value: str | None) -> None:
		self._wavy_style = value
		if value is None:
			self._cdml_display_fields.discard("wavy_style")
		else:
			self._record_cdml_display_field("wavy_style")
		self.property_changed.emit("wavy_style", self._wavy_style)

	#============================================
	@property
	def haworth_position(self) -> str | None:
		"""Return the optional scalar Haworth position metadata."""
		return self._haworth_position

	#============================================
	@haworth_position.setter
	def haworth_position(self, value: str | None) -> None:
		"""Set optional Haworth metadata and retain its authored presence."""
		self._haworth_position = str(value) if value is not None else None
		if value is None:
			self._cdml_display_fields.discard("haworth_position")
		else:
			self._record_cdml_display_field("haworth_position")
		self.property_changed.emit("haworth_position", self._haworth_position)

	#============================================
	@property
	def cdml_display_fields(self) -> frozenset[str]:
		"""Return the exact authored depiction-field presence."""
		return frozenset(self._cdml_display_fields)

	#============================================
	def install_projection(
			self, *, bond_id: str | None, order: int, bond_type: str,
			aromatic: bool | None, line_width: float | None,
			bond_width: float | None, wedge_width: float | None,
			double_ratio: float | None, center: bool | None,
			auto_sign: int | None, equithick: bool | None,
			simple_double: bool | None, line_color: str | None,
			wavy_style: str | None, haworth_position: str | None,
			explicit_fields: frozenset[str] | set[str],
			) -> None:
		"""Install backend/bridge scalar facts without inventing XML presence."""
		self._bond_id = str(bond_id) if bond_id else None
		self._order = int(order)
		self._type = str(bond_type)
		self._aromatic = aromatic
		if line_width is not None:
			self._line_width = float(line_width)
		if bond_width is not None:
			self._bond_width = float(bond_width)
		if wedge_width is not None:
			self._wedge_width = float(wedge_width)
		if double_ratio is not None:
			self._double_length_ratio = float(double_ratio)
		self._center = center
		if auto_sign is not None:
			self._auto_bond_sign = int(auto_sign)
		if equithick is not None:
			self._equithick = bool(equithick)
		if simple_double is not None:
			self._simple_double = bool(simple_double)
		if line_color is not None:
			self._line_color = str(line_color)
		self._wavy_style = wavy_style
		self._haworth_position = haworth_position
		self._cdml_display_fields = set(explicit_fields)

	#============================================
	def _record_cdml_display_field(self, name: str) -> None:
		"""Mark one explicit Qt depiction edit for later bridge materialization."""
		self._cdml_display_fields.add(name)

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		return f"BondModel(order={self.order}, type='{self.type}')"
