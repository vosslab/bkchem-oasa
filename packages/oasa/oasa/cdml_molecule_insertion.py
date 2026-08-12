"""Immutable result values for backend-owned molecule insertion."""

# Standard Library
import collections.abc
import dataclasses
import types
import typing


if typing.TYPE_CHECKING:
	import oasa.cdml_document


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeInsertionResult:
	"""Accepted insertion with root-only and declaration-level ID facts."""

	commit: "oasa.cdml_document.CDMLCommit"
	root_id_map: collections.abc.Mapping[str, str]

	#============================================
	def __post_init__(self) -> None:
		"""Keep root correlation facts immutable and nonempty strings."""
		root_id_map = dict(self.root_id_map)
		if any(
			type(provisional_id) is not str or not provisional_id
			or type(durable_id) is not str or not durable_id
			for provisional_id, durable_id in root_id_map.items()
		):
			raise TypeError("molecule insertion root IDs must be nonempty strings")
		object.__setattr__(self, "root_id_map", types.MappingProxyType(root_id_map))

	#============================================
	@property
	def snapshot(self) -> "oasa.cdml_document.CDMLSnapshot":
		"""Return the accepted immutable backend snapshot."""
		return self.commit.snapshot

	#============================================
	@property
	def id_map(self) -> collections.abc.Mapping[str, str]:
		"""Return complete declaration-level provisional-ID allocation facts."""
		return self.commit.id_map

	#============================================
	@property
	def revision(self) -> int:
		"""Return the accepted monotonic backend revision."""
		return self.commit.revision

	#============================================
	@property
	def cdml(self) -> str:
		"""Return the accepted canonical complete CDML document."""
		return self.commit.cdml
