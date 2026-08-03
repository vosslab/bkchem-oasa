"""Qt-neutral CDML document objects owned by :mod:`document`."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore


#============================================
@dataclasses.dataclass
class ReactionRecord:
	"""Lossless reaction record with its molecule reference attributes."""

	refs: list[tuple[str, str]] = dataclasses.field(default_factory=list)
	raw_xml: str = ""


#============================================
@dataclasses.dataclass
class CdmlEnvelope:
	"""CDML document content that is not represented by drawable objects."""

	root_attributes: dict[str, str] = dataclasses.field(default_factory=dict)
	info_xml: list[str] = dataclasses.field(default_factory=list)
	metadata_xml: list[str] = dataclasses.field(default_factory=list)
	standard_xml: list[str] = dataclasses.field(default_factory=list)
	extra_header_xml: list[str] = dataclasses.field(default_factory=list)
	reactions: list[ReactionRecord] = dataclasses.field(default_factory=list)
	external_data_xml: list[str] = dataclasses.field(default_factory=list)
	trailing_xml: list[str] = dataclasses.field(default_factory=list)


#============================================
@dataclasses.dataclass
class PaperModel:
	"""Paper and viewport state preserved from a CDML document."""

	attributes: dict[str, str] = dataclasses.field(default_factory=dict)
	viewport_attributes: dict[str, str] = dataclasses.field(default_factory=dict)
	raw_xml: str | None = None
	viewport_raw_xml: str | None = None

	#============================================
	def snapshot(self) -> "PaperModel":
		"""Return an independent copy suitable for an undo command."""
		copy = PaperModel(
			attributes=dict(self.attributes),
			viewport_attributes=dict(self.viewport_attributes),
			raw_xml=self.raw_xml,
			viewport_raw_xml=self.viewport_raw_xml,
		)
		return copy

	#============================================
	def replace(self, replacement: "PaperModel") -> None:
		"""Replace modeled state while retaining this document-owned object."""
		self.attributes = dict(replacement.attributes)
		self.viewport_attributes = dict(replacement.viewport_attributes)
		self.raw_xml = replacement.raw_xml
		self.viewport_raw_xml = replacement.viewport_raw_xml


#============================================
@dataclasses.dataclass
class UnsupportedContent:
	"""A plain warning for persistent content not represented by the Qt canvas.

	``raw_xml`` is populated by legacy-isolated and still-transitional decoders.
	A synchronized direct-root presentation diagnostic receives an empty value
	because OASA retains the authoritative content.
	"""

	tag: str
	object_id: str | None
	path: str
	reason: str
	raw_xml: str


#============================================
class PresentationObject(PySide6.QtCore.QObject):
	"""A drawable non-molecule CDML object and its serializable state."""

	changed = PySide6.QtCore.Signal()

	#============================================
	def __init__(
			self,
			kind: str,
			attributes: dict[str, str] | None = None,
			points: list[tuple[float, float, float | None]] | None = None,
			bounds: tuple[float, float, float, float] | None = None,
			xml_ftext: str | None = None,
			formatted_text_runs: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
			display_text: str = "",
			font_attributes: dict[str, str] | None = None,
			raw_xml: str | None = None,
			supported: bool = True,
			parent: PySide6.QtCore.QObject | None = None,
			editable: bool | None = None,
			) -> None:
		"""Initialize a CDML presentation object.

		Args:
			kind: CDML element name such as ``arrow`` or ``text``.
			attributes: Element attributes.
			points: Ordered point coordinates in CDML document units.
			bounds: Optional normalized x, y, width, height bounds.
			xml_ftext: CDML formatted-text fragment.
			formatted_text_runs: Supported authored ftext as immutable plain runs.
			display_text: Always-safe character-data display value.
			font_attributes: Font element attributes.
			raw_xml: Original node XML retained for lossless fallback output.
			supported: Whether the object has a Qt projection.
			parent: Optional QObject owner.
			editable: Whether persistent Qt actions may target the projection.
		"""
		super().__init__(parent)
		self._kind = str(kind)
		self._attributes = dict(attributes or {})
		self._points = list(points or [])
		self._bounds = tuple(bounds) if bounds is not None else None
		self._xml_ftext = xml_ftext
		self._formatted_text_runs = formatted_text_runs
		self._display_text = str(display_text)
		self._font_attributes = dict(font_attributes or {})
		self._raw_xml = raw_xml
		self._supported = bool(supported)
		self._editable = self._supported if editable is None else bool(editable) and self._supported

	#============================================
	@property
	def kind(self) -> str:
		"""Return the CDML element name."""
		return self._kind

	#============================================
	@property
	def object_id(self) -> str | None:
		"""Return the optional CDML ``id`` attribute."""
		return self._attributes.get("id")

	#============================================
	@property
	def attributes(self) -> dict[str, str]:
		"""Return a copy of element attributes."""
		return dict(self._attributes)

	#============================================
	@property
	def points(self) -> list[tuple[float, float, float | None]]:
		"""Return a copy of point coordinates."""
		return list(self._points)

	#============================================
	@property
	def bounds(self) -> tuple[float, float, float, float] | None:
		"""Return optional object bounds."""
		return self._bounds

	#============================================
	@property
	def xml_ftext(self) -> str | None:
		"""Return the optional formatted-text XML fragment."""
		return self._xml_ftext

	#============================================
	@property
	def formatted_text_runs(self) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
		"""Return supported authored ftext runs, or None for preservation content."""
		return self._formatted_text_runs

	#============================================
	@property
	def display_text(self) -> str:
		"""Return plain character data that is safe to display without HTML parsing."""
		return self._display_text

	#============================================
	@property
	def rich_text_editable(self) -> bool:
		"""Whether this projected Text has supported authored ftext run data."""
		return (
			self._editable
			and self._kind == "text"
			and self._formatted_text_runs is not None
		)

	#============================================
	@property
	def font_attributes(self) -> dict[str, str]:
		"""Return a copy of font attributes."""
		return dict(self._font_attributes)

	#============================================
	@property
	def raw_xml(self) -> str | None:
		"""Return original XML retained for lossless fallback output."""
		return self._raw_xml

	#============================================
	@property
	def supported(self) -> bool:
		"""Whether this object has a supported Qt projection."""
		return self._supported

	#============================================
	@property
	def editable(self) -> bool:
		"""Whether persistent frontend actions may target this projection."""
		return self._editable

	#============================================
	def set_points(self, points: list[tuple[float, float, float | None]]) -> None:
		"""Replace point coordinates and notify observers when changed."""
		new_points = list(points)
		if new_points != self._points:
			self._points = new_points
			self.changed.emit()

	#============================================
	def set_bounds(self, bounds: tuple[float, float, float, float] | None) -> None:
		"""Replace bounds and notify observers when changed."""
		new_bounds = tuple(bounds) if bounds is not None else None
		if new_bounds != self._bounds:
			self._bounds = new_bounds
			self.changed.emit()

	#============================================
	def set_xml_ftext(self, xml_ftext: str | None) -> None:
		"""Replace formatted text and notify observers when changed."""
		if xml_ftext != self._xml_ftext:
			self._xml_ftext = xml_ftext
			self.changed.emit()

	#============================================
	def update_attribute(self, name: str, value: str | None) -> None:
		"""Set or remove an attribute and notify observers when changed."""
		if value is None:
			if name not in self._attributes:
				return
			del self._attributes[name]
			self.changed.emit()
			return
		value = str(value)
		if self._attributes.get(name) != value:
			self._attributes[name] = value
			self.changed.emit()


#============================================
class AtomMarkModel(PySide6.QtCore.QObject):
	"""A CDML mark attached to an atom model."""

	changed = PySide6.QtCore.Signal()

	#============================================
	def __init__(
			self,
			atom_model: object,
			attributes: dict[str, str],
			raw_xml: str | None = None,
			supported: bool = True,
			matching_mark_index: int | None = None,
			rendering_facts: tuple[float, float, float, bool, float] | None = None,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize a mark linked to an atom model.

		Args:
			atom_model: AtomModel owning this mark.
			attributes: CDML mark attributes; ``type`` is required.
			raw_xml: Original XML retained for lossless fallback output.
			supported: Whether the mark can be projected by the UI.
			matching_mark_index: Snapshot-derived zero-based ordinal among direct
				core marks of this same type.
			parent: Optional QObject owner.
		"""
		if "type" not in attributes:
			raise ValueError("Atom mark attributes require a 'type' value")
		super().__init__(parent)
		self._atom_model = atom_model
		self._attributes = dict(attributes)
		self._raw_xml = raw_xml
		self._supported = bool(supported)
		if matching_mark_index is not None and (
				type(matching_mark_index) is not int or matching_mark_index < 0
			):
			raise ValueError("Atom mark matching index must be a nonnegative int")
		self._matching_mark_index = matching_mark_index
		self._rendering_facts = rendering_facts

	#============================================
	@property
	def atom_model(self) -> object:
		"""Return the atom model this mark decorates."""
		return self._atom_model

	#============================================
	@property
	def mark_type(self) -> str:
		"""Return the required CDML mark type."""
		return self._attributes["type"]

	#============================================
	@property
	def attributes(self) -> dict[str, str]:
		"""Return a copy of mark attributes."""
		return dict(self._attributes)

	#============================================
	@property
	def raw_xml(self) -> str | None:
		"""Return original XML retained for lossless fallback output."""
		return self._raw_xml

	#============================================
	@property
	def supported(self) -> bool:
		"""Whether this mark has a supported Qt projection."""
		return self._supported

	#============================================
	@property
	def matching_mark_index(self) -> int | None:
		"""Return this direct core mark's same-type CDML child ordinal."""
		return self._matching_mark_index

	#============================================
	@property
	def rendering_facts(self) -> tuple[float, float, float, bool, float] | None:
		"""Return backend-normalized rendering facts for synchronized projections."""
		return self._rendering_facts

	#============================================
	def update_attribute(self, name: str, value: str | None) -> None:
		"""Set or remove a mark attribute and emit only on real change."""
		if name == "type" and value is None:
			raise ValueError("Atom mark type cannot be removed")
		if value is None:
			if name not in self._attributes:
				return
			del self._attributes[name]
			self.changed.emit()
			return
		value = str(value)
		if self._attributes.get(name) != value:
			self._attributes[name] = value
			self.changed.emit()
