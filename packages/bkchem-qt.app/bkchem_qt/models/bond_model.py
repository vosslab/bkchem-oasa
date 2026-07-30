"""Qt composition wrapper around an OASA Bond with change signals."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import oasa.bond_lib
import oasa.cdml_bond_io
import oasa.render_lib.data_types


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
	def __init__(
			self, oasa_bond: oasa.bond_lib.Bond | None = None,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the bond model.

		Args:
			oasa_bond: Existing OASA Bond to wrap, or None for default single bond.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		# chemistry backend
		self._chem_bond = oasa_bond or oasa.bond_lib.Bond()
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
		# Effective display values are separate from authoritative lexical
		# presence, so a projection does not author absent CDML attributes.
		self._cdml_display_fields: set[str] = set()

	# ------------------------------------------------------------------
	# Chemistry properties delegated to _chem_bond
	# ------------------------------------------------------------------

	#============================================
	@property
	def bond_id(self) -> str | None:
		"""Return the persisted CDML bond identifier without exposing OASA state."""
		return self._chem_bond.id

	#============================================
	@property
	def backend_durable_id(self) -> str | None:
		"""Return an authoritative bond ID only while local linkage agrees."""
		if self._backend_durable_id and self.bond_id == self._backend_durable_id:
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
		return self._chem_bond.order

	#============================================
	@order.setter
	def order(self, value: int) -> None:
		self._chem_bond.order = value
		self.property_changed.emit("order", value)

	#============================================
	@property
	def type(self) -> str:
		"""Bond type character: 'n','w','h','a','b','d','o','s','q'."""
		return self._chem_bond.type

	#============================================
	@type.setter
	def type(self, value: str) -> None:
		self._chem_bond.type = value
		self.property_changed.emit("type", value)

	#============================================
	@property
	def aromatic(self) -> bool | None:
		"""Aromatic flag: None (not set), True, or False."""
		return self._chem_bond.aromatic

	#============================================
	@aromatic.setter
	def aromatic(self, value: bool | None) -> None:
		self._chem_bond.aromatic = value
		self.property_changed.emit("aromatic", value)

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
			self._sync_chem_bond_depiction()
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
			self._sync_chem_bond_depiction()
		else:
			self._record_cdml_display_field("wavy_style")
		self.property_changed.emit("wavy_style", self._wavy_style)

	#============================================
	def install_projected_depiction(
			self, depiction: oasa.render_lib.data_types.BondDepiction,
			) -> None:
		"""Install one OASA-resolved projection without inventing presence."""
		if depiction.line_width is not None:
			self._line_width = depiction.line_width
		if depiction.bond_width is not None:
			self._bond_width = depiction.bond_width
		if depiction.wedge_width is not None:
			self._wedge_width = depiction.wedge_width
		self._double_length_ratio = depiction.double_ratio
		self._center = depiction.center
		self._auto_bond_sign = depiction.auto_sign
		self._equithick = depiction.equithick
		self._simple_double = depiction.simple_double
		if depiction.color is not None:
			self._line_color = depiction.color
		self._wavy_style = depiction.wavy_style
		self._cdml_display_fields = set(depiction.explicit_fields)
		if depiction.haworth_position is not None:
			self._chem_bond.properties_["haworth_position"] = depiction.haworth_position
		self._sync_chem_bond_depiction()

	#============================================
	def _record_cdml_display_field(self, name: str) -> None:
		"""Mark one explicit Qt depiction edit and synchronize its render edge."""
		self._cdml_display_fields.add(name)
		self._sync_chem_bond_depiction()

	#============================================
	def _sync_chem_bond_depiction(self) -> None:
		"""Copy effective values and explicit presence to the composed OASA edge."""
		edge = self._chem_bond
		edge.line_color = self._line_color
		edge.line_width = self._line_width
		edge.bond_width = self._bond_width
		edge.wedge_width = self._wedge_width
		edge.center = self._center
		edge.simple_double = int(self._simple_double)
		edge.auto_bond_sign = self._auto_bond_sign
		edge.double_length_ratio = self._double_length_ratio
		edge.equithick = int(self._equithick)
		edge.wavy_style = self._wavy_style
		properties = edge.properties_
		for name in (
				"line_width", "bond_width", "wedge_width", "center",
				"simple_double", "auto_sign", "double_ratio", "equithick",
				"line_color", "color", "wavy_style",
				):
			properties.pop(name, None)
		if "line_width" in self._cdml_display_fields:
			properties["line_width"] = str(self._line_width)
		if "bond_width" in self._cdml_display_fields:
			properties["bond_width"] = str(self._bond_width)
		if "wedge_width" in self._cdml_display_fields:
			properties["wedge_width"] = str(self._wedge_width)
		if "center" in self._cdml_display_fields and self._center is not None:
			properties["center"] = "yes" if self._center else "no"
		if "simple_double" in self._cdml_display_fields:
			properties["simple_double"] = str(int(self._simple_double))
		if "auto_sign" in self._cdml_display_fields:
			properties["auto_sign"] = str(self._auto_bond_sign)
		if "double_ratio" in self._cdml_display_fields:
			properties["double_ratio"] = str(self._double_length_ratio)
		if "equithick" in self._cdml_display_fields:
			properties["equithick"] = str(int(self._equithick))
		if "color" in self._cdml_display_fields:
			properties["line_color"] = self._line_color
		if "wavy_style" in self._cdml_display_fields and self._wavy_style is not None:
			properties["wavy_style"] = self._wavy_style
		oasa.cdml_bond_io.set_cdml_bond_explicit_fields(
			edge, self._cdml_display_fields,
		)

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		return f"BondModel(order={self.order}, type='{self.type}')"
