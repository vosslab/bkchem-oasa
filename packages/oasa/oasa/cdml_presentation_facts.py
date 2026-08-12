"""Immutable frontend-neutral observations for direct presentation roots."""

# Standard Library
import dataclasses

# local repo modules
import oasa.cdml_projection_plan


@dataclasses.dataclass(frozen=True)
class CDMLPresentationIssue:
	"""Plain diagnostic for a direct root unavailable to the projection."""

	source_position: int
	tag: str
	namespace_uri: str | None
	path: str
	identifier: str | None
	disposition: str
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLPresentationRecord:
	"""Immutable description of one direct-root presentation record."""

	source_position: int
	identifier: str | None
	kind: str
	attributes: tuple[tuple[str, str], ...]
	points: tuple[tuple[float, float, float | None], ...]
	bounds: tuple[float, float, float, float] | None
	font_attributes: tuple[tuple[str, str], ...]
	effective_font_family: str | None
	display_text: str
	ftext_runs: tuple[tuple[str, tuple[str, ...]], ...] | None
	disposition: str
	reason: str | None


@dataclasses.dataclass(frozen=True)
class CDMLPresentationDescription:
	"""Revision-bound plain presentation-stack facts for a disposable projection."""

	revision: int
	records: tuple[CDMLPresentationRecord, ...]
	issues: tuple[CDMLPresentationIssue, ...]
	bracket_pairs: tuple[oasa.cdml_projection_plan.CDMLBracketPairRecord, ...]
