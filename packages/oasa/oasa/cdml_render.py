"""Frontend-neutral immutable inputs and outcomes for CDML visual rendering.

The values in this module describe a document snapshot render.  They are not a
renderer and deliberately carry no Qt, filesystem, clipboard, or widget state.
"""

# Standard Library
import dataclasses
import math

# local repo modules
import oasa.cdml_document


_FORMATS = frozenset({"svg", "png", "pdf"})
_SCOPES = frozenset({"page", "content", "selection"})
_SELECTION_KINDS = frozenset({"molecule", "presentation", "atom", "bond", "group"})


@dataclasses.dataclass(frozen=True)
class CDMLRenderSelectionKey:
	"""One durable persistent identity selected for a snapshot render."""

	kind: str
	identifier: str

	#============================================
	def __post_init__(self) -> None:
		"""Require a declared durable identity rather than frontend object state."""
		if self.kind not in _SELECTION_KINDS:
			raise ValueError("Unknown CDML render selection kind: %s" % self.kind)
		if not isinstance(self.identifier, str) or not self.identifier.strip():
			raise ValueError("CDML render selection identifiers must be nonempty strings")


@dataclasses.dataclass(frozen=True)
class CDMLRenderRequest:
	"""One immutable complete-CDML snapshot render request."""

	snapshot: oasa.cdml_document.CDMLSnapshot
	format_name: str
	scope: str = "page"
	selection_keys: tuple[CDMLRenderSelectionKey, ...] = ()
	options: tuple[tuple[str, bool | float | int | str], ...] = ()

	#============================================
	def __post_init__(self) -> None:
		"""Validate the portable request before a frontend allocates graphics."""
		if not isinstance(self.snapshot, oasa.cdml_document.CDMLSnapshot):
			raise TypeError("CDML render requests require an immutable CDML snapshot")
		if self.format_name not in _FORMATS:
			raise ValueError("Unsupported CDML render format: %s" % self.format_name)
		if self.scope not in _SCOPES:
			raise ValueError("Unsupported CDML render scope: %s" % self.scope)
		keys = tuple(self.selection_keys)
		if any(not isinstance(key, CDMLRenderSelectionKey) for key in keys):
			raise TypeError("CDML render selection keys must be immutable durable keys")
		if self.scope != "selection" and keys:
			raise ValueError("Only selection renders may include selection keys")
		options = tuple(self.options)
		seen = set()
		for name, value in options:
			if not isinstance(name, str) or not name:
				raise ValueError("CDML render option names must be nonempty strings")
			if name in seen:
				raise ValueError("CDML render option names must be unique")
			seen.add(name)
			if not isinstance(value, (bool, float, int, str)):
				raise TypeError("CDML render options must contain scalar values")
			if isinstance(value, float) and not math.isfinite(value):
				raise ValueError("CDML render float options must be finite")
		object.__setattr__(self, "selection_keys", keys)
		object.__setattr__(self, "options", options)

	#============================================
	def option(self, name: str, default: object = None) -> object:
		"""Return one declared scalar option without exposing mutable mappings."""
		for option_name, value in self.options:
			if option_name == name:
				return value
		return default


@dataclasses.dataclass(frozen=True)
class CDMLRenderWarning:
	"""One stable warning about incomplete visual coverage of persisted content."""

	code: str
	path: str
	identifier: str | None
	message: str


@dataclasses.dataclass(frozen=True)
class CDMLRenderResult:
	"""A successful visual artifact generated from one named snapshot revision."""

	snapshot_revision: int
	format_name: str
	artifact: bytes | None
	artifact_path: str | None = None
	warnings: tuple[CDMLRenderWarning, ...] = ()


@dataclasses.dataclass(frozen=True)
class CDMLRenderFailure:
	"""A typed non-mutating render failure."""

	code: str
	message: str
	snapshot_revision: int | None = None
	diagnostics: tuple[str, ...] = ()

	#============================================
	def __post_init__(self) -> None:
		"""Retain plain diagnostic detail without exposing frontend exceptions."""
		diagnostics = tuple(self.diagnostics)
		if any(not isinstance(diagnostic, str) for diagnostic in diagnostics):
			raise TypeError("CDML render failure diagnostics must be strings")
		object.__setattr__(self, "diagnostics", diagnostics)
