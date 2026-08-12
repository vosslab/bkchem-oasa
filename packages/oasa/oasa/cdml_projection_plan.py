"""Frontend-neutral facts for one synchronized CDML projection."""

# Standard Library
import dataclasses


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLBracketPairRecord:
	"""One exact observed top-level bracket-pair relationship."""

	pair_id: str
	member_ids: tuple[str, str]
	style: str
	line_width: float | None
	line_color: str | None

	#============================================
	def __post_init__(self) -> None:
		"""Reject mutable or structurally incomplete pair facts."""
		if type(self.pair_id) is not str or not self.pair_id:
			raise ValueError("bracket pair ID must be a nonblank string")
		if (
			type(self.member_ids) is not tuple or len(self.member_ids) != 2
			or any(type(identifier) is not str or not identifier for identifier in self.member_ids)
			or self.member_ids[0] != self.pair_id or self.member_ids[0] == self.member_ids[1]
		):
			raise ValueError("bracket pair members must be distinct durable left and right IDs")
		if self.style not in {"rectangular", "round"}:
			raise ValueError("bracket pair style must be rectangular or round")
		if self.line_width is not None and type(self.line_width) is not float:
			raise ValueError("bracket pair width must be a float or null")
		if self.line_color is not None and type(self.line_color) is not str:
			raise ValueError("bracket pair color must be a string or null")


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLProjectionRoot:
	"""One ordered direct CDML root and its backend projection disposition."""

	source_position: int
	tag: str
	identifier: str | None
	disposition: str
	reason: str | None

	#============================================
	def __post_init__(self) -> None:
		"""Reject malformed root facts before any frontend creates wrappers."""
		if type(self.source_position) is not int or self.source_position < 1:
			raise ValueError("projection root source position must be a positive integer")
		if type(self.tag) is not str or not self.tag:
			raise ValueError("projection root tag must be a nonblank string")
		if self.identifier is not None and type(self.identifier) is not str:
			raise ValueError("projection root identifier must be a string or null")
		if self.disposition not in {"editable", "display-only", "header"}:
			raise ValueError("projection root has an unknown disposition")
		if self.reason is not None and type(self.reason) is not str:
			raise ValueError("projection root reason must be a string or null")


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLProjectionPlan:
	"""Plain exact-revision facts required to build a disposable projection.

	The fields deliberately carry immutable OASA observation records as objects
	rather than XML.  A frontend associates its wrappers by the source positions
	in these records and never needs to inspect the canonical document tree.
	"""

	revision: int
	roots: tuple[CDMLProjectionRoot, ...]
	presentation_description: object
	paper_layout: object
	fragment_metadata: object
	atom_mark_observation: object
	group_observation: object
	molecule_core_observation: object
	molecule_render_observation: object

	def __post_init__(self) -> None:
		"""Keep every associated fact on the exact snapshot revision."""
		if type(self.revision) is not int:
			raise ValueError("projection plan revision must be an integer")
		if any(type(root) is not CDMLProjectionRoot for root in self.roots):
			raise ValueError("projection plan roots must be exact immutable records")
		positions = tuple(root.source_position for root in self.roots)
		if positions != tuple(range(1, len(positions) + 1)):
			raise ValueError("projection plan roots must be complete ordered direct-root facts")
		# Importing here keeps this frontend-neutral value module free of an import
		# cycle while still rejecting lookalike or mutable observation objects.
		import oasa.cdml_document
		facts = (
			self.presentation_description, self.paper_layout, self.fragment_metadata,
			self.atom_mark_observation, self.group_observation,
			self.molecule_core_observation, self.molecule_render_observation,
		)
		expected_types = (
			oasa.cdml_document.CDMLPresentationDescription,
			oasa.cdml_document.CDMLPaperLayout,
			oasa.cdml_document.CDMLFragmentMetadata,
			oasa.cdml_document.CDMLAtomMarkObservation,
			oasa.cdml_document.CDMLGroupObservation,
			oasa.cdml_document.CDMLMoleculeCoreObservation,
			oasa.cdml_document.CDMLMoleculeRenderObservation,
		)
		if any(type(fact) is not expected for fact, expected in zip(facts, expected_types)):
			raise ValueError("projection plan facts must be exact immutable observations")
		if any(getattr(fact, "revision", None) != self.revision for fact in facts):
			raise ValueError("projection plan facts must match its exact revision")


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLProjectionSnapshot:
	"""One atomic backend projection envelope for one canonical snapshot."""

	snapshot: object
	plan: CDMLProjectionPlan

	def __post_init__(self) -> None:
		"""Keep the plan and canonical snapshot at one exact revision."""
		if getattr(self.snapshot, "revision", None) != self.plan.revision:
			raise ValueError("projection plan must match the backend snapshot revision")
