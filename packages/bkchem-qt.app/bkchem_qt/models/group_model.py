"""Qt-owned structural model for one native CDML chemical group."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore


_EDITABLE_GROUP_TYPES = frozenset({"builtin", "implicit", "explicit"})


#============================================
@dataclasses.dataclass(frozen=True)
class GroupAttachment:
	"""One retained CDML bond joining a group vertex to another endpoint."""

	bond_id: str
	start_id: str
	end_id: str
	attributes: tuple[tuple[str, str], ...]
	raw_xml: str

	#============================================
	def endpoint_for(self, group_id: str) -> str | None:
		"""Return the non-group endpoint, or ``None`` for a malformed bond."""
		if self.start_id == group_id:
			return self.end_id
		if self.end_id == group_id:
			return self.start_id
		return None


#============================================
class GroupModel(PySide6.QtCore.QObject):
	"""Durable display metadata for a CDML ``<group>`` pseudo-vertex.

	Groups deliberately do not enter the OASA graph until a future explicit
	expansion command.  They retain their native CDML source and attachment
	bonds, so unsupported group chemistry cannot be silently rewritten.
	"""

	changed = PySide6.QtCore.Signal()

	#============================================
	def __init__(
			self, group_id: str, name: str, group_type: str, pos: str,
			x: float, y: float, attributes: tuple[tuple[str, str], ...],
			point_attributes: tuple[tuple[str, str], ...],
			font_attributes: tuple[tuple[str, str], ...], raw_xml: str,
			attachments: tuple[GroupAttachment, ...] = (),
			unsupported_reason: str | None = None,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Create a group model from one local-name-aware CDML element."""
		super().__init__(parent)
		self.group_id = group_id
		self.name = name
		self.group_type = group_type
		self.pos = pos
		self.x = x
		self.y = y
		self.attributes = attributes
		self.point_attributes = point_attributes
		self.font_attributes = font_attributes
		self.raw_xml = raw_xml
		self.attachments = attachments
		self.unsupported_reason = unsupported_reason

	#============================================
	@property
	def supported(self) -> bool:
		"""Whether this group has the narrow structural projection contract."""
		return self.unsupported_reason is None

	#============================================
	@property
	def editable(self) -> bool:
		"""Whether a later group editor may safely offer structural edits."""
		return self.supported and self.group_type in _EDITABLE_GROUP_TYPES

	#============================================
	def set_attachments(self, attachments: tuple[GroupAttachment, ...]) -> None:
		"""Install retained incident-bond metadata after all molecule nodes load."""
		self.attachments = attachments
		self.changed.emit()
