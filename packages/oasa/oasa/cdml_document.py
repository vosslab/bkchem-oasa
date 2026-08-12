"""Authoritative complete-CDML document storage and revision transactions.

This module deliberately keeps a complete XML DOM as the persistent source of
truth.  The molecule codec may provide a chemistry view elsewhere, but it must
never be used to reconstruct this document because CDML also contains arrows,
text, reactions, paper data, and extension XML.
"""

# Standard Library
import collections.abc
import dataclasses
import hashlib
import math
import numbers
import re
import types

# local repo modules
import oasa.bond_semantics
import oasa.cdml_bond_io
import oasa.cdml_bracket_pair
import oasa.cdml_ftext
import oasa.cdml_molecule_summary
import oasa.cdml_presentation_facts
import oasa.cdml_projection_plan
import oasa.cdml_standard
import oasa.cdml_writer
import oasa.cdml_xml
import oasa.coords_generator
import oasa.codecs.rdkit_formats
import oasa.group_expansion
import oasa.molecule_lib
import oasa.periodic_table
import oasa.render_ops
import oasa.render_lib.bond_ops
import oasa.render_lib.data_types
import oasa.render_lib.molecule_ops


_PROVISIONAL_ID_PREFIX = "__bkchem_new__"
_PROVISIONAL_ID_PATTERN = re.compile(
	r"^__bkchem_new__[A-Za-z][A-Za-z0-9_-]{0,63}$",
)
CDML_NAMESPACE_URI = oasa.cdml_xml.CDML_NAMESPACE_URI
_ID_DECLARATION_ELEMENT_NAMES = frozenset({
	"arrow", "atom", "bond", "circle", "fragment",
	"group", "molecule", "oval", "paper", "plus", "polygon", "polyline", "reaction",
	"query", "rect", "square", "text", "viewport",
})
_TOP_LEVEL_INSERTION_NAMES = frozenset({
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline", "reaction",
})
_TOP_LEVEL_DELETE_NAMES = frozenset({
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline",
})
_MOLECULE_VERTEX_NAMES = frozenset({"atom", "group", "text", "query"})
_MOLECULE_CHILD_NAMES = _MOLECULE_VERTEX_NAMES | frozenset({"bond", "template", "fragment"})
_REACTION_ROLE_NAMES = frozenset({"arrow", "condition", "plus", "product", "reactant"})
_POINT_CM_PER_POSTSCRIPT_POINT = 2.54 / 72.0
_COORDINATE_PATTERN = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?(?:cm)?$")
_SUPPORTED_FTEXT_MARKUP_PATTERN = re.compile(
	r"<(?:(?:sub|sup|b|i)\s*/?|/(?:sub|sup|b|i)\s*)>",
)
_EMPTY_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'version="26.07"></cdml>'
)
_CDML_PAPER_PROPERTY_FIELDS = frozenset({
	"type", "orientation", "crop_svg", "crop_margin", "use_real_minus",
	"replace_minus", "dimensions",
})
_ATOM_MARK_TYPES = frozenset({
	"plus", "minus", "radical", "biradical", "electronpair",
	"dotted_electronpair", "pz_orbital",
})
_ATOM_MARK_SCALAR_DELTAS = {
	"plus": ("charge", 1),
	"minus": ("charge", -1),
	"radical": ("multiplicity", 1),
	"biradical": ("multiplicity", 2),
}


paper_catalog = oasa.cdml_standard.paper_catalog
class CDMLDocumentError(ValueError):
	"""Base error for a complete CDML document operation."""


class CDMLParseError(CDMLDocumentError):
	"""Raised when text is not a parseable CDML document."""


class CDMLValidationError(CDMLDocumentError):
	"""Raised when a complete CDML document violates backend invariants."""


class CDMLAtomNumberCompatibilityError(CDMLValidationError):
	"""Raised when a direct legacy atom-number mark prevents a number edit."""


class CDMLMoleculeNameEditError(CDMLValidationError):
	"""Raised when a direct-root molecule display-name edit is invalid."""


class CDMLMoleculeSmilesUnavailableError(CDMLDocumentError):
	"""Raised when one direct-root molecule cannot produce a SMILES value."""


class CDMLPaperPropertiesError(CDMLValidationError):
	"""Raised when one revision-bound paper-properties patch is invalid."""


class CDMLBondPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound bond-properties patch is invalid."""


class CDMLAtomPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound atom-properties patch is invalid."""


class CDMLTextPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound plain Text-properties patch is invalid."""


class CDMLRichTextPatchError(CDMLValidationError):
	"""Raised when one revision-bound rich Text patch is invalid."""


class CDMLPlusPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound plain Plus-properties patch is invalid."""


class CDMLWavyPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound plain Wavy-properties patch is invalid."""


class CDMLFragmentOperationError(CDMLValidationError):
	"""Raised when one revision-bound ordinary fragment operation is invalid."""


class CDMLImplicitGroupExpandError(CDMLValidationError):
	"""Raised when one narrow implicit-group expansion is unavailable."""


class CDMLStructureFragmentExtractionError(CDMLValidationError):
	"""Raised when one structural clipboard extraction is unavailable."""


class CDMLTopLevelFragmentExtractionError(CDMLValidationError):
	"""Raised when one direct-root clipboard extraction is unavailable."""


class CDMLPresentationDescriptionError(CDMLValidationError):
	"""Raised when a revision-bound presentation observation is invalid."""


class CDMLPaperLayoutError(CDMLValidationError):
	"""Raised when a revision-bound paper/layout observation is invalid."""


class CDMLFragmentMetadataError(CDMLValidationError):
	"""Raised when a revision-bound fragment metadata observation is invalid."""


class CDMLAtomMarkObservationError(CDMLValidationError):
	"""Raised when a revision-bound atom-mark observation is invalid."""


class CDMLGroupObservationError(CDMLValidationError):
	"""Raised when a revision-bound group observation is invalid."""


class CDMLMoleculeCoreObservationError(CDMLValidationError):
	"""Raised when a revision-bound molecule-core observation is invalid."""


class CDMLMoleculeRenderObservationError(CDMLValidationError):
	"""Raised when a revision-bound molecule render observation is invalid."""


class CDMLAtomChemistryFactsError(CDMLValidationError):
	"""Raised when a revision-bound atom-chemistry observation is invalid."""


class CDMLLinearFormError(CDMLValidationError):
	"""Raised when one revision-bound linear-form conversion is invalid."""


class CDMLAtomMarkOperationError(CDMLValidationError):
	"""Raised when one revision-bound direct atom-mark operation is invalid."""


class CDMLSelectionTranslateError(CDMLValidationError):
	"""Raised when one revision-bound mixed selection translation is invalid."""


class CDMLTopLevelTransformError(CDMLValidationError):
	"""Raised when one revision-bound top-level transform is invalid."""


class CDMLUserTemplateInsertionError(CDMLValidationError):
	"""Raised when one serialized saved-template insertion is invalid."""


@dataclasses.dataclass(frozen=True)
class CDMLUserTemplateInspection:
	"""Immutable frontend-neutral admission facts for one saved CDML template."""

	display_name: str | None


class CDMLRevisionConflictError(CDMLDocumentError):
	"""Raised when a transaction was built from an obsolete revision."""


class CDMLRevisionUnavailableError(CDMLDocumentError):
	"""Raised when a bounded session no longer retains a requested revision."""


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeInsertionRequest:
	"""One detached molecule-only proposal for an optimistic backend insertion."""

	expected_revision: int
	proposal_cdml: str
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLUserTemplateInsertionRequest:
	"""One exact serialized saved template and finite scene-point insertion intent."""

	expected_revision: int
	template_cdml: str
	anchor: tuple[float, float]
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelInsertionRequest:
	"""One detached, translated, top-level CDML composition request."""

	expected_revision: int
	fragment_cdml: str
	translation: tuple[float, float]
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLGeometryRepairRequest:
	"""One revision-bound, direct-root geometry repair request."""

	expected_revision: int
	molecule_ids: tuple[str, ...]
	kind: str
	target_spacing_pt: float


@dataclasses.dataclass(frozen=True)
class CDMLAtomAlignRequest:
	"""One revision-bound direct-core atom alignment request."""

	expected_revision: int
	axis: str
	targets: tuple[tuple[str, str], ...]


@dataclasses.dataclass(frozen=True)
class CDMLAtomTranslateRequest:
	"""One revision-bound translation of selected direct-core atoms in points."""

	expected_revision: int
	targets: tuple[tuple[str, str], ...]
	delta: tuple[float, float]


@dataclasses.dataclass(frozen=True)
class CDMLSelectionTranslateRequest:
	"""One revision-bound mixed atom and presentation selection translation."""

	expected_revision: int
	atom_targets: tuple[tuple[str, str], ...]
	presentation_root_ids: tuple[str, ...]
	delta: tuple[float, float]


@dataclasses.dataclass(frozen=True)
class CDMLAtomRotateRequest:
	"""One revision-bound 2D rotation of selected direct-core atoms."""

	expected_revision: int
	targets: tuple[tuple[str, str], ...]
	center: tuple[float, float]
	angle_radians: float


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelTransformRequest:
	"""One revision-bound affine transform of durable direct-root records."""

	expected_revision: int
	mode: str
	root_ids: tuple[str, ...]
	scale_x: float | None = None
	scale_y: float | None = None
	delta: tuple[float, float] | None = None


@dataclasses.dataclass(frozen=True)
class CDMLBondOrderEditRequest:
	"""One revision-bound exact order edit for a direct core bond."""

	expected_revision: int
	molecule_id: str
	bond_id: str
	order: int


@dataclasses.dataclass(frozen=True)
class CDMLBondTypeEditRequest:
	"""One revision-bound exact type edit for a direct core bond."""

	expected_revision: int
	molecule_id: str
	bond_id: str
	bond_type: str


@dataclasses.dataclass(frozen=True)
class CDMLBondPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct core bond."""

	expected_revision: int
	molecule_id: str
	bond_id: str
	changes: tuple[tuple[str, object], ...] = ()


@dataclasses.dataclass(frozen=True)
class CDMLAtomPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct core atom."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLTextPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct-root plain Text."""

	expected_revision: int
	text_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLRichTextPatch:
	"""One revision-bound formatted-run and root-font patch for one direct-root Text."""

	expected_revision: int
	text_id: str
	runs: tuple[oasa.cdml_ftext.CDMLFTextRun, ...]
	changes: tuple[tuple[str, object], ...] = ()


@dataclasses.dataclass(frozen=True)
class CDMLPlusPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct-root plain Plus."""

	expected_revision: int
	plus_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLWavyPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct-root Wavy."""

	expected_revision: int
	wavy_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLFragmentCreateRequest:
	"""One revision-bound creation of ordinary molecule fragment metadata."""

	expected_revision: int
	molecule_id: str
	name: str
	fragment_type: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLFragmentDeleteRequest:
	"""One revision-bound removal of an ordinary molecule fragment."""

	expected_revision: int
	molecule_id: str
	fragment_id: str


@dataclasses.dataclass(frozen=True)
class CDMLImplicitGroupExpandRequest:
	"""One revision-bound expansion of a direct implicit group with one bond."""

	expected_revision: int
	molecule_id: str
	group_id: str


@dataclasses.dataclass(frozen=True)
class CDMLLinearFormConvertRequest:
	"""One revision-bound conversion of a direct atom path to linear form."""

	expected_revision: int
	molecule_id: str
	atom_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLAtomMarkOperationRequest:
	"""One revision-bound add or removal of one direct atom mark."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	action: str
	mark_type: str
	matching_mark_index: int | None = None


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelDeleteRequest:
	"""One revision-bound request to remove durable direct-root records."""

	expected_revision: int
	root_ids: tuple[str, ...]
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLStructureDeleteRequest:
	"""One revision-bound removal of direct atoms and bonds in one molecule."""

	expected_revision: int
	molecule_id: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLStructureFragmentExtractionQuery:
	"""One revision-bound, nonmutating extraction of a structural clipboard fragment."""

	expected_revision: int
	molecule_id: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelFragmentExtractionQuery:
	"""One revision-bound extraction of durable direct-root clipboard content."""

	expected_revision: int
	root_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLPresentationDescriptionQuery:
	"""One read-only observation of direct-root presentation at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLPaperLayoutQuery:
	"""One read-only observation of direct-core paper/layout at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLFragmentMetadataQuery:
	"""One read-only observation of molecule fragment metadata at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLAtomMarkObservationQuery:
	"""One read-only direct atom-mark observation at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLGroupObservationQuery:
	"""One read-only direct group observation at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeCoreObservationQuery:
	"""One read-only molecule/atom/bond observation at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeRenderObservationQuery:
	"""One read-only complete molecule paint observation at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLAtomChemistryFactsQuery:
	"""One read-only complete direct-graph chemistry observation at one revision."""

	expected_revision: int


@dataclasses.dataclass(frozen=True)
class CDMLPaperLayout:
	"""Revision-bound plain paper/viewport facts for a frontend projection.

	Only the first direct core ``paper`` and ``viewport`` are projected.  All
	other header and lookalike XML stays in the backend-owned CDML snapshot.
	"""

	revision: int
	paper_present: bool
	paper_attributes: tuple[tuple[str, str], ...]
	effective_paper_attributes: tuple[tuple[str, str], ...]
	viewport_attributes: tuple[tuple[str, str], ...]
	default_type: str
	default_orientation: str


@dataclasses.dataclass(frozen=True)
class CDMLFragmentMetadataIssue:
	"""Plain diagnostic for one fragment unavailable for ordinary editing."""

	path: str
	tag: str
	namespace_uri: str | None
	identifier: str | None
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLFragmentMetadataRecord:
	"""Qt-free facts and eligibility for one direct molecule fragment."""

	molecule_id: str | None
	molecule_source_position: int
	source_position: int
	fragment_id: str | None
	display_name: str | None
	fragment_type: str | None
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]
	disposition: str
	reason: str | None


@dataclasses.dataclass(frozen=True)
class CDMLFragmentMetadata:
	"""Revision-bound plain fragment facts for a disposable frontend projection."""

	revision: int
	records: tuple[CDMLFragmentMetadataRecord, ...]
	issues: tuple[CDMLFragmentMetadataIssue, ...]


@dataclasses.dataclass(frozen=True)
class CDMLAtomMarkObservationIssue:
	"""Plain diagnostic for one atom mark that cannot be edited."""

	molecule_source_position: int
	atom_source_position: int
	mark_source_position: int
	mark_type: str | None
	disposition: str
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLAtomMarkObservationRecord:
	"""Qt-free projection and deletion facts for one direct local-name mark."""

	molecule_id: str | None
	atom_id: str | None
	molecule_source_position: int
	atom_source_position: int
	mark_source_position: int
	mark_type: str | None
	same_type_ordinal: int | None
	disposition: str
	reason: str | None
	angle_degrees: float
	radial_offset_pt: float
	size_pt: float
	draw_circle: bool
	line_width_pt: float


@dataclasses.dataclass(frozen=True)
class CDMLAtomMarkObservation:
	"""Revision-bound normalized direct atom-mark projection facts."""

	revision: int
	records: tuple[CDMLAtomMarkObservationRecord, ...]
	issues: tuple[CDMLAtomMarkObservationIssue, ...]


@dataclasses.dataclass(frozen=True)
class CDMLGroupObservationIssue:
	"""Plain diagnostic for one group unavailable to persistent actions."""

	molecule_source_position: int
	group_source_position: int
	disposition: str
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLGroupObservationRecord:
	"""Qt-free visible facts and authority eligibility for one direct group."""

	molecule_id: str | None
	group_id: str | None
	molecule_source_position: int
	group_source_position: int
	group_type: str | None
	name: str | None
	pos: str | None
	x_pt: float | None
	y_pt: float | None
	font_family: str | None
	font_size_pt: float | None
	disposition: str
	reason: str | None
	implicit_expandable: bool


@dataclasses.dataclass(frozen=True)
class CDMLGroupObservation:
	"""Revision-bound plain group facts for a disposable frontend projection."""

	revision: int
	records: tuple[CDMLGroupObservationRecord, ...]
	issues: tuple[CDMLGroupObservationIssue, ...]


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeCoreObservationIssue:
	"""Plain diagnostic for an inert molecule-core record."""

	molecule_source_position: int
	source_position: int
	kind: str
	disposition: str
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLAtomCoreObservationRecord:
	"""Plain atom facts for one disposable molecule-core projection."""
	identifier: str | None
	source_position: int
	symbol: str | None
	x_pt: float | None
	y_pt: float | None
	z_pt: float | None
	charge: int | None
	valency: int | None
	isotope: int | None
	multiplicity: int | None
	free_sites: int | None
	explicit_hydrogens: int | None
	show: bool | None
	show_hydrogens: bool | None
	font_family: str | None
	font_size: int | None
	line_color: str | None
	number: int | None
	show_number: bool | None
	explicit_fields: tuple[str, ...]
	disposition: str
	renderable: bool
	addressable: bool
	reason: str | None


@dataclasses.dataclass(frozen=True)
class CDMLBondCoreObservationRecord:
	"""Plain directed bond and effective depiction facts."""
	identifier: str | None
	source_position: int
	start_id: str | None
	end_id: str | None
	bond_type: str | None
	order: int | None
	line_width: float | None
	bond_width: float | None
	wedge_width: float | None
	double_ratio: float | None
	center: bool | None
	auto_sign: int | None
	equithick: bool | None
	simple_double: bool | None
	line_color: str | None
	wavy_style: str | None
	haworth_position: str | None
	explicit_fields: tuple[str, ...]
	disposition: str
	renderable: bool
	addressable: bool
	reason: str | None


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeCoreObservationRecord:
	"""One molecule and the atom/bond graph projected from one snapshot."""
	identifier: str | None
	source_position: int
	name: str | None
	atoms: tuple[CDMLAtomCoreObservationRecord, ...]
	bonds: tuple[CDMLBondCoreObservationRecord, ...]
	disposition: str
	renderable: bool
	addressable: bool
	reason: str | None


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeCoreObservation:
	"""Revision-bound complete direct molecule-core projection facts."""
	revision: int
	records: tuple[CDMLMoleculeCoreObservationRecord, ...]
	issues: tuple[CDMLMoleculeCoreObservationIssue, ...]


@dataclasses.dataclass(frozen=True)
class CDMLRenderPrimitive:
	"""One frontend-neutral paint primitive in the closed molecule grammar.

	``kind`` is one of ``line``, ``polygon``, ``circle``, ``path``, or ``text``.
	All fields are scalar, tuple, string, boolean, or null facts; color roles
	let a frontend resolve its own canvas theme without accepting a toolkit value.
	"""

	kind: str
	points: tuple[tuple[float, float], ...]
	commands: tuple[tuple[str, tuple[float, ...] | None], ...]
	text_runs: tuple[tuple[str, str], ...]
	radius: float | None
	fill: str | None
	fill_role: str | None
	stroke: str | None
	stroke_role: str | None
	stroke_width: float | None
	font_family: str | None
	font_size: float | None
	anchor: str | None
	weight: str | None
	cap: str | None
	join: str | None
	z: int


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeRenderBatch:
	"""One durable atom or bond paint batch from a shared canonical snapshot."""

	kind: str
	molecule_source_position: int
	identifier: str | None
	source_position: int
	actionable: bool
	anchor: tuple[float, float] | None
	endpoint_positions: tuple[tuple[float, float], tuple[float, float]] | None
	operations: tuple[CDMLRenderPrimitive, ...]


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeRenderObservationIssue:
	"""Plain diagnostic for molecule content unavailable to synchronized paint."""

	molecule_source_position: int
	source_position: int
	kind: str
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeRenderObservation:
	"""Exact-revision immutable atom and bond paint batches."""

	revision: int
	batches: tuple[CDMLMoleculeRenderBatch, ...]
	issues: tuple[CDMLMoleculeRenderObservationIssue, ...]


@dataclasses.dataclass(frozen=True)
class CDMLAtomChemistryFactsIssue:
	"""Plain diagnostic for chemistry that cannot be safely observed."""

	molecule_source_position: int
	atom_source_position: int | None
	disposition: str
	reason: str


@dataclasses.dataclass(frozen=True)
class CDMLAtomChemistryFactRecord:
	"""Qt-free chemistry facts associated by durable IDs and source positions.

	``oxidation_number`` is OASA's electronegativity-derived result.  It is a
	useful connected-graph observation, not a universal formal-chemistry claim
	for every resonance or organometallic representation.
	"""

	molecule_id: str | None
	atom_id: str | None
	symbol: str | None
	charge: int | None
	molecule_source_position: int
	atom_source_position: int
	disposition: str
	effective_valency: int | None
	occupied_valency: int | None
	free_valency: int | None
	hydrogen_count: int | None
	oxidation_number: int | None
	atomic_number: int | None
	reason: str | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomChemistryFactsObservation:
	"""Exact-revision, immutable plain atom chemistry facts."""

	revision: int
	records: tuple[CDMLAtomChemistryFactRecord, ...]
	issues: tuple[CDMLAtomChemistryFactsIssue, ...]


@dataclasses.dataclass(frozen=True)
class CDMLStructuralEditRequest:
	"""One revision-bound persistent Draw-mode topology operation.

	All positions are PostScript scene points.  The operation grammar is
	deliberately narrow: it represents completed Draw-mode gestures without
	exposing a mutable XML or chemistry graph to a frontend.
	"""

	expected_revision: int
	kind: str
	molecule_id: str | None = None
	source_atom_id: str | None = None
	target_atom_id: str | None = None
	bond_id: str | None = None
	source_position: tuple[float, float] | None = None
	target_position: tuple[float, float] | None = None
	element: str | None = None
	bond_type: str | None = None
	bond_order: int | None = None
	simple_double: bool | None = None


@dataclasses.dataclass(frozen=True)
class CDMLAtomElementEditRequest:
	"""One revision-bound replacement of a direct core atom element."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	element: str


@dataclasses.dataclass(frozen=True)
class CDMLAtomNumberEditRequest:
	"""One revision-bound assignment or clearing of a direct atom number."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	number: int | None
	show_number: bool | None


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeNameEditRequest:
	"""One revision-bound replacement or clear of a direct-root molecule name."""

	expected_revision: int
	molecule_id: str
	name: str


@dataclasses.dataclass(frozen=True)
class CDMLPaperPropertiesPatch:
	"""One revision-bound patch containing only explicit paper-field intent.

	``changes`` is an ordered tuple of exact two-value tuples.  Keeping this
	immutable request representation permits the backend to reject duplicate
	field declarations instead of silently choosing a frontend-side winner.
	"""

	expected_revision: int
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSmilesQuery:
	"""One revision-bound, nonmutating direct-root molecule SMILES query."""

	expected_revision: int
	molecule_id: str


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSmilesResult:
	"""One immutable SMILES observation from an authoritative snapshot."""

	revision: int
	molecule_id: str
	smiles: str


@dataclasses.dataclass(frozen=True)
class CDMLIssue:
	"""One strict-validation finding with a stable document location hint."""

	code: str
	message: str
	path: str


@dataclasses.dataclass(frozen=True)
class CDMLObjectRecord:
	"""An immutable persistent-element view with stable preorder metadata."""

	position: int
	path: str
	local_name: str
	identifier: str | None
	raw_xml: str
	opaque: bool


@dataclasses.dataclass(frozen=True)
class CDMLReactionRoleRecord:
	"""An immutable recognized reaction-role reference in document order."""

	reaction_path: str
	path: str
	role_name: str
	target_identifier: str | None


@dataclasses.dataclass(frozen=True)
class CDMLSnapshot:
	"""One immutable view of a backend-owned revision."""

	revision: int
	cdml: str
	is_dirty: bool


CDMLProjectionPlan = oasa.cdml_projection_plan.CDMLProjectionPlan
CDMLProjectionRoot = oasa.cdml_projection_plan.CDMLProjectionRoot
CDMLProjectionSnapshot = oasa.cdml_projection_plan.CDMLProjectionSnapshot
CDMLBracketPairRecord = oasa.cdml_projection_plan.CDMLBracketPairRecord
CDMLPresentationDescription = oasa.cdml_presentation_facts.CDMLPresentationDescription
CDMLPresentationIssue = oasa.cdml_presentation_facts.CDMLPresentationIssue
CDMLPresentationRecord = oasa.cdml_presentation_facts.CDMLPresentationRecord


@dataclasses.dataclass(frozen=True)
class CDMLCommit:
	"""The accepted backend result for a commit or restore transaction."""

	snapshot: CDMLSnapshot
	id_map: collections.abc.Mapping[str, str]

	@property
	def revision(self) -> int:
		"""Return the newly accepted monotonic backend revision."""
		return self.snapshot.revision

	@property
	def cdml(self) -> str:
		"""Return canonical complete CDML from the accepted backend snapshot."""
		return self.snapshot.cdml


@dataclasses.dataclass(frozen=True)
class CDMLGeometryRepairResult:
	"""Immutable result of one geometry repair observation or accepted commit."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomAlignResult:
	"""Immutable result of one backend-authoritative atom alignment."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomTranslateResult:
	"""Immutable result of one backend-authoritative atom translation."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLSelectionTranslateResult:
	"""Immutable result of one backend-authoritative mixed selection translation."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomRotateResult:
	"""Immutable result of one backend-authoritative atom rotation."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelTransformResult:
	"""Immutable result of one backend-authoritative top-level transform."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLBondOrderEditResult:
	"""Immutable result of one exact backend-authoritative bond-order edit."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLBondTypeEditResult:
	"""Immutable result of one exact backend-authoritative bond-type edit."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLBondPropertiesPatchResult:
	"""Immutable result of one backend-authoritative bond-properties patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomPropertiesPatchResult:
	"""Immutable result of one backend-authoritative atom-properties patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLTextPropertiesPatchResult:
	"""Immutable result of one backend-authoritative plain Text patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLRichTextPatchResult:
	"""Immutable result of one backend-authoritative rich Text patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLPlusPropertiesPatchResult:
	"""Immutable result of one backend-authoritative plain Plus patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLWavyPropertiesPatchResult:
	"""Immutable result of one backend-authoritative plain Wavy patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLFragmentCreateResult:
	"""Immutable result of one accepted ordinary fragment creation."""

	snapshot: CDMLSnapshot
	commit: CDMLCommit
	fragment_id: str


@dataclasses.dataclass(frozen=True)
class CDMLFragmentDeleteResult:
	"""Immutable result of one accepted ordinary fragment deletion."""

	snapshot: CDMLSnapshot
	commit: CDMLCommit
	fragment_id: str


@dataclasses.dataclass(frozen=True)
class CDMLLinearFormConvertResult:
	"""Immutable result of one backend-owned linear-form conversion."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None
	fragment_id: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLImplicitGroupExpandResult:
	"""Immutable result of one accepted implicit-group expansion."""

	commit: CDMLCommit
	replacement_atom_id: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]

	@property
	def snapshot(self) -> CDMLSnapshot:
		"""Return the accepted authoritative snapshot."""
		return self.commit.snapshot


@dataclasses.dataclass(frozen=True)
class CDMLAtomMarkOperationResult:
	"""Immutable result of one backend-authoritative atom-mark operation."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None
	action_result: str


@dataclasses.dataclass(frozen=True)
class CDMLStructuralEditResult:
	"""Immutable authoritative result of one accepted structural operation."""

	commit: CDMLCommit
	created_molecule_id: str | None = None
	created_atom_ids: tuple[str, ...] = ()
	created_bond_ids: tuple[str, ...] = ()
	updated_bond_ids: tuple[str, ...] = ()

	@property
	def snapshot(self) -> CDMLSnapshot:
		"""Return the accepted canonical snapshot without exposing mutable DOM."""
		return self.commit.snapshot


@dataclasses.dataclass(frozen=True)
class CDMLStructureDeleteComponent:
	"""One surviving direct-core molecule component in canonical source order."""

	molecule_id: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLStructureDeleteResult:
	"""Immutable accepted result of one bounded structural deletion."""

	commit: CDMLCommit
	removed_atom_ids: tuple[str, ...]
	removed_bond_ids: tuple[str, ...]
	components: tuple[CDMLStructureDeleteComponent, ...]

	@property
	def snapshot(self) -> CDMLSnapshot:
		"""Return the accepted canonical snapshot without exposing mutable DOM."""
		return self.commit.snapshot


@dataclasses.dataclass(frozen=True)
class CDMLStructureFragmentExtractionResult:
	"""One detached structural clipboard fragment from an exact source revision."""

	revision: int
	fragment_cdml: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelFragmentExtractionResult:
	"""One detached direct-root clipboard fragment from an exact source revision."""

	revision: int
	fragment_cdml: str
	root_ids: tuple[str, ...]

#============================================
def _local_name(node: object) -> str:
	"""Return an XML local name without changing the stored node."""
	name = getattr(node, "localName", None) or getattr(node, "tagName", "")
	if ":" in name:
		name = name.rsplit(":", 1)[1]
	return str(name)


#============================================
def _is_core_cdml_element(element: object) -> bool:
	"""Return whether one element itself has a recognized CDML name and namespace."""
	namespace_uri = getattr(element, "namespaceURI", None)
	is_core_element = (
		_local_name(element) in oasa.cdml_xml.CDML_CORE_ELEMENT_NAMES
		and namespace_uri in (None, "", CDML_NAMESPACE_URI)
	)
	return is_core_element


#============================================
def _is_cdml_element(element: object) -> bool:
	"""Return whether an element is editable core CDML in its document context.

	Standalone legacy CDML has no namespace.  Prefix-qualified CDML must use
	the canonical namespace URI.  Every element ancestor must also be core CDML:
	an unknown wrapper owns its complete subtree, even when a descendant uses a
	known CDML local name and namespace.
	"""
	if oasa.cdml_xml.has_preservation_only_ancestor(element):
		return False
	current = element
	while current is not None and getattr(current, "nodeType", None) == current.ELEMENT_NODE:
		if not _is_core_cdml_element(current):
			return False
		parent = current.parentNode
		if parent is None or getattr(parent, "nodeType", None) != parent.ELEMENT_NODE:
			break
		current = parent
	return True


#============================================
def _element_children(node: object) -> list:
	"""Return direct element children in their existing document order."""
	children = []
	for child in node.childNodes:
		if child.nodeType == child.ELEMENT_NODE:
			children.append(child)
	return children


#============================================
def _descendant_elements(node: object) -> list:
	"""Return descendants in depth-first source order, including ``node``."""
	elements = [node]
	for child in _element_children(node):
		elements.extend(_descendant_elements(child))
	return elements


#============================================
def _node_path(node: object) -> str:
	"""Return a compact location hint for diagnostics without modifying XML."""
	parts = []
	current = node
	while current is not None and getattr(current, "nodeType", None) == current.ELEMENT_NODE:
		parts.append(_local_name(current))
		parent = current.parentNode
		if parent is None or getattr(parent, "nodeType", None) != parent.ELEMENT_NODE:
			break
		current = parent
	path = "/" + "/".join(reversed(parts))
	return path


#============================================
def _is_provisional_id(value: str) -> bool:
	"""Return whether ``value`` is a transaction-only frontend correlation ID."""
	return bool(_PROVISIONAL_ID_PATTERN.fullmatch(value))


#============================================
def _has_provisional_id_prefix(value: str) -> bool:
	"""Return whether a value claims the reserved provisional-ID namespace."""
	return value.startswith(_PROVISIONAL_ID_PREFIX)


#============================================
def _durable_prefix(local_name: str) -> str:
	"""Return a readable durable-ID prefix for a recognized CDML object."""
	prefixes = {
		"atom": "a",
		"bond": "b",
		"molecule": "m",
	}
	prefix = prefixes.get(local_name, local_name[:1] or "o")
	return prefix


#============================================
def _next_durable_id(local_name: str, used_ids: set[str]) -> str:
	"""Allocate one collision-free backend durable ID without mutating callers."""
	prefix = _durable_prefix(local_name)
	serial = 1
	identifier = f"{prefix}{serial}"
	while identifier in used_ids:
		serial += 1
		identifier = f"{prefix}{serial}"
	return identifier


#============================================
def _known_reference_attributes(element: object) -> tuple[str, ...]:
	"""Return schema-supported reference attributes for one recognized element."""
	if not _is_cdml_element(element):
		return ()
	local_name = _local_name(element)
	if local_name == "bond":
		return ("start", "end")
	if local_name == "template":
		return ("atom", "bond_first", "bond_second")
	if _fragment_member_reference(element):
		return ("id",)
	parent = element.parentNode
	if (
		parent is not None
		and _is_cdml_element(parent)
		and _local_name(parent) == "reaction"
		and local_name in ("arrow", "condition", "plus", "product", "reactant")
	):
		return ("idref",)
	return ()


#============================================
def _is_id_declaration(element: object) -> bool:
	"""Return whether an element may declare a provisional backend ID.

	This is deliberately narrower than ``_is_id_definition``.  Known editable
	CDML declarations participate in frontend provisional-ID allocation, while
	opaque extension XML owns literal IDs without receiving any provisional-ID
	interpretation.
	"""
	return (
		_is_cdml_element(element)
		and _local_name(element) in _ID_DECLARATION_ELEMENT_NAMES
		and not oasa.cdml_xml.is_preservation_only_container(element)
		and not _fragment_member_reference(element)
	)


#============================================
def _is_id_definition(element: object) -> bool:
	"""Return whether an ``id`` is a lookup definition, including opaque XML.

	Opaque IDs are indexed for whole-document lookup but never inspected for
	provisional-token validation or backend allocation unless their element is a
	recognized editable declaration.
	"""
	return not _fragment_member_reference(element)


#============================================
def _element_locations(root: object) -> tuple[tuple[int, object], ...]:
	"""Return all persistent elements in stable depth-first preorder."""
	elements = _descendant_elements(root)[1:]
	locations = tuple(enumerate(elements))
	return locations


#============================================
def _presentation_attributes(element: object) -> tuple[tuple[str, str], ...]:
	"""Return stable non-namespace attributes for a public projection value."""
	return tuple(
		(element.attributes.item(index).name, element.attributes.item(index).value)
		for index in range(element.attributes.length)
		if element.attributes.item(index).name != "xmlns"
		and not element.attributes.item(index).name.startswith("xmlns:")
	)


#============================================
def _presentation_character_data(element: object) -> str:
	"""Return safe display character data without giving child markup meaning."""
	parts = []
	for child in element.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			parts.append(child.data)
		elif child.hasChildNodes():
			parts.append(_presentation_character_data(child))
	return "".join(parts)


#============================================
def _presentation_scene_coordinate(value: str) -> float:
	"""Convert one finite authored CDML coordinate to PostScript scene points."""
	match = re.fullmatch(
		r"([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)(cm|px)?",
		value.strip(),
	)
	if match is None:
		raise ValueError("presentation coordinate is malformed")
	points = float(match.group(1))
	if match.group(2) == "cm":
		points /= _POINT_CM_PER_POSTSCRIPT_POINT
	if not math.isfinite(points):
		raise ValueError("presentation coordinate is not finite")
	return points


#============================================
def _presentation_description(
		document: "CDMLDocument", revision: int,
		) -> CDMLPresentationDescription:
	"""Describe direct-root presentation without exposing the compatibility DOM."""
	records = []
	issues = []
	presentation_names = frozenset({
		"arrow", "plus", "text", "rect", "square", "oval", "circle",
		"polygon", "polyline",
	})
	ignored_names = frozenset({
		"info", "metadata", "paper", "viewport", "standard", "molecule",
		"reaction", "external-data",
	})
	allowed_children = {
		"arrow": frozenset({"point"}),
		"plus": frozenset({"point", "font"}),
		"text": frozenset({"point", "font", "ftext"}),
		"rect": frozenset(),
		"square": frozenset(),
		"oval": frozenset(),
		"circle": frozenset(),
		"polygon": frozenset({"point"}),
		"polyline": frozenset({"point"}),
	}
	opaque_child_names = frozenset({"rect", "square", "oval", "circle", "polygon", "polyline"})
	root = document._dom_document.documentElement
	standard = oasa.cdml_standard.observe(root, revision)
	for source_position, element in enumerate(_element_children(root), 1):
		name = _local_name(element)
		identifier = element.getAttribute("id") or None
		path = "/cdml/%s[%d]" % (name, source_position)
		if not _is_cdml_element(element):
			issues.append(CDMLPresentationIssue(
				source_position, name, getattr(element, "namespaceURI", None), path, identifier,
				"opaque", "direct root is preservation-only or uses an unsupported namespace",
			))
			continue
		if name not in presentation_names:
			if name not in ignored_names:
				issues.append(CDMLPresentationIssue(
					source_position, name, getattr(element, "namespaceURI", None), path, identifier,
					"unsupported", "direct root is not a supported presentation kind",
				))
			continue
		try:
			compatibility_reason = None
			direct_children = _element_children(element)
			# Geometric scalar edits preserve foreign direct children as opaque data.
			if any(
				(_local_name(child) not in allowed_children[name]
				if _is_cdml_element(child) else name not in opaque_child_names)
				for child in direct_children
			):
				compatibility_reason = (
					"presentation contains preservation-only or unexpected direct child content"
				)
			points = []
			for point in direct_children:
				if _is_cdml_element(point) and _local_name(point) == "point":
					x = _presentation_scene_coordinate(point.getAttribute("x"))
					y = _presentation_scene_coordinate(point.getAttribute("y"))
					z_text = point.getAttribute("z")
					z = _presentation_scene_coordinate(z_text) if z_text else None
					points.append((x, y, z))
			bounds = None
			if all(element.hasAttribute(attribute) for attribute in ("x1", "y1", "x2", "y2")):
				x1, y1, x2, y2 = tuple(_presentation_scene_coordinate(element.getAttribute(attribute))
					for attribute in ("x1", "y1", "x2", "y2"))
				bounds = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
			if bounds is None and name in ("text", "plus") and points:
				bounds = (points[0][0], points[0][1], 0.0, 0.0)
			minimum_points = {"arrow": 2, "polygon": 3, "polyline": 2}
			if name in minimum_points and len(points) < minimum_points[name]:
				raise ValueError("presentation geometry has too few points")
			if name in {"plus", "text"} and len(points) != 1:
				raise ValueError("presentation geometry requires exactly one point")
			if name in {"rect", "square", "oval", "circle"} and bounds is None:
				raise ValueError("presentation geometry has incomplete bounds")
			fonts = tuple(child for child in direct_children
				if _is_cdml_element(child) and _local_name(child) == "font")
			ftexts = tuple(child for child in direct_children
				if _is_cdml_element(child) and _local_name(child) == "ftext")
			if len(fonts) > 1 or len(ftexts) > 1:
				raise ValueError("presentation has duplicate direct font or ftext content")
			if name == "text" and not ftexts:
				raise ValueError("Text presentation requires one direct ftext")
			font = fonts[0] if fonts else None
			ftext = ftexts[0] if ftexts else None
			display_text = (
				element.getAttribute("text")
				if ftext is None else _presentation_character_data(ftext)
			)
			runs = None
			if ftext is not None and not ftext.hasAttributes() and all(
				child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE) for child in ftext.childNodes
			):
				try:
					decoded = oasa.cdml_ftext.decode(_presentation_character_data(ftext))
					runs = tuple((run.text, run.styles) for run in decoded)
					display_text = "".join(run.text for run in decoded)
				except oasa.cdml_ftext.CDMLFTextCodecError as error:
					compatibility_reason = str(error)
			elif ftext is not None:
				compatibility_reason = "ftext contains preservation-only direct markup"
			effective_family = None
			if name in {"plus", "text"}:
				effective_family = (
					(font.getAttribute("family").strip() if font else None) or standard.font_family
				)
			if compatibility_reason is not None:
				issues.append(CDMLPresentationIssue(
					source_position, name, getattr(element, "namespaceURI", None), path, identifier,
					"unsupported", compatibility_reason,
				))
			records.append(CDMLPresentationRecord(
				source_position, identifier, name, _presentation_attributes(element), tuple(points), bounds,
				_presentation_attributes(font) if font is not None else (),
				effective_family, display_text, runs,
				"editable" if identifier is not None and compatibility_reason is None else "display-only",
				compatibility_reason,
			))
		except (ValueError, oasa.cdml_ftext.CDMLFTextCodecError) as error:
			issues.append(CDMLPresentationIssue(
				source_position, name, getattr(element, "namespaceURI", None), path, identifier,
				"unsupported", str(error),
			))
	bracket_pairs = oasa.cdml_bracket_pair.observe_bracket_pairs(
		tuple(_element_children(root)), _is_cdml_element, _local_name,
	)
	return CDMLPresentationDescription(revision, tuple(records), tuple(issues), bracket_pairs)


#============================================
def _paper_layout(document: "CDMLDocument", revision: int) -> CDMLPaperLayout:
	"""Describe direct-core paper facts without exposing header XML or a DOM."""
	paper = _first_direct_core_child(document, "paper")
	viewport = _first_direct_core_child(document, "viewport")
	default_type, default_orientation = _new_paper_defaults(document)
	paper_attributes = () if paper is None else _presentation_attributes(paper)
	return CDMLPaperLayout(
		revision=revision,
		paper_present=paper is not None,
		paper_attributes=paper_attributes,
		effective_paper_attributes=(
			paper_attributes if paper is not None else (
				("type", default_type), ("orientation", default_orientation),
			)
		),
		viewport_attributes=() if viewport is None else _presentation_attributes(viewport),
		default_type=default_type,
		default_orientation=default_orientation,
	)


#============================================
def _plain_fragment_name(fragment: object) -> str | None:
	"""Return one safe direct name value without interpreting fragment markup."""
	names = [
		child for child in _element_children(fragment)
		if _local_name(child) == "name"
	]
	if len(names) != 1:
		return None
	name = names[0]
	if name.attributes.length or _element_children(name):
		return None
	if any(
			node.nodeType not in (node.TEXT_NODE, node.CDATA_SECTION_NODE)
			for node in name.childNodes
		):
		return None
	value = "".join(node.data for node in name.childNodes)
	return value.strip() or None


#============================================
def _fragment_member_ids(fragment: object, local_name: str) -> tuple[str, ...]:
	"""Return readable direct member IDs without treating them as editable facts."""
	return tuple(
		child.getAttribute("id")
		for child in _element_children(fragment)
		if _local_name(child) == local_name and child.getAttribute("id")
	)


#============================================
def _fragment_metadata(
		document: "CDMLDocument", revision: int,
		) -> CDMLFragmentMetadata:
	"""Describe direct molecule fragments without exposing retained XML to Qt."""
	records = []
	issues = []
	root = document._dom_document.documentElement
	identifier_counts = collections.Counter(
		element.getAttribute("id")
		for element in _descendant_elements(root)
		if _is_id_definition(element) and element.getAttribute("id")
	)
	for molecule_position, molecule in enumerate(_element_children(root), 1):
		if _local_name(molecule) != "molecule":
			continue
		molecule_id = molecule.getAttribute("id") or None
		is_direct_root_molecule = False
		if _is_cdml_element(molecule) and molecule_id is not None:
			try:
				is_direct_root_molecule = _direct_root_molecule(document, molecule_id) is molecule
			except CDMLValidationError:
				pass
		fragment_occurrence = 0
		for source_position, fragment in enumerate(_element_children(molecule), 1):
			if _local_name(fragment) != "fragment":
				continue
			fragment_occurrence += 1
			identifier = fragment.getAttribute("id") or None
			fragment_type = fragment.getAttribute("type") or None
			atom_ids = _fragment_member_ids(fragment, "vertex")
			bond_ids = _fragment_member_ids(fragment, "bond")
			path = "/cdml/molecule[%d]/fragment[%d]" % (
				molecule_position, fragment_occurrence,
			)
			reason = None
			if not _is_cdml_element(fragment):
				reason = "fragment is preservation-only or uses an unsupported namespace"
			elif not is_direct_root_molecule:
				reason = "fragment does not belong to one durable direct-root molecule"
			elif identifier is not None and identifier_counts[identifier] != 1:
				reason = "fragment durable ID is ambiguous in the document"
			elif fragment_type == "linear_form":
				reason = "linear-form metadata is backend-generated and read-only"
			else:
				try:
					_observed_id, observed_atoms, observed_bonds = _ordinary_fragment_members(fragment)
					_validate_fragment_members(molecule, observed_atoms, observed_bonds)
				except CDMLFragmentOperationError as error:
					reason = str(error)
			if reason is not None:
				issues.append(CDMLFragmentMetadataIssue(
					path, _local_name(fragment), getattr(fragment, "namespaceURI", None),
					identifier, reason,
				))
			records.append(CDMLFragmentMetadataRecord(
				molecule_id if is_direct_root_molecule else None,
				molecule_position, source_position, identifier,
				_plain_fragment_name(fragment), fragment_type, atom_ids, bond_ids,
				"editable" if reason is None else "display-only", reason,
			))
	return CDMLFragmentMetadata(revision, tuple(records), tuple(issues))


#============================================
def _atom_mark_observation(
		document: "CDMLDocument", revision: int,
		) -> CDMLAtomMarkObservation:
	"""Describe every direct atom local-name mark without exposing XML to Qt."""
	records = []
	issues = []
	root = document._dom_document.documentElement
	identifier_counts = collections.Counter(
		element.getAttribute("id") for element in _descendant_elements(root)
		if _is_id_definition(element) and element.getAttribute("id")
	)
	for molecule_position, molecule in enumerate(_element_children(root), 1):
		if _local_name(molecule) != "molecule":
			continue
		molecule_id = molecule.getAttribute("id") or None
		molecule_addressable = (
			_is_cdml_element(molecule) and molecule_id is not None
			and identifier_counts[molecule_id] == 1
		)
		for atom_position, atom in enumerate(_element_children(molecule), 1):
			if _local_name(atom) != "atom":
				continue
			atom_id = atom.getAttribute("id") or None
			atom_addressable = (
				molecule_addressable and _is_cdml_element(atom) and atom_id is not None
				and identifier_counts[atom_id] == 1
			)
			ordinals: dict[str, int] = {}
			for mark_position, mark in enumerate(_element_children(atom), 1):
				if _local_name(mark) != "mark":
					continue
				mark_type = mark.getAttribute("type") or None
				ordinal = ordinals.get(mark_type or "", 0)
				if _is_cdml_element(mark):
					ordinals[mark_type or ""] = ordinal + 1
				angle, offset, size, circle, width = _normalized_atom_mark_facts(atom, mark, mark_type)
				reason = None
				if not _is_cdml_element(mark):
					reason = "mark is preservation-only or uses an unsupported namespace"
				elif mark_type == "atom_number":
					reason = "legacy atom_number mark is a numbering compatibility diagnostic"
				elif mark_type not in _ATOM_MARK_TYPES:
					reason = "mark type is unsupported"
				elif not atom_addressable:
					reason = "mark does not belong to one uniquely addressed direct atom"
				record = CDMLAtomMarkObservationRecord(
					molecule_id if atom_addressable else None,
					atom_id if atom_addressable else None,
					molecule_position, atom_position, mark_position, mark_type,
					ordinal if reason is None else None,
					"editable" if reason is None else "display-only", reason,
					angle, offset, size, circle, width,
				)
				records.append(record)
				if reason is not None:
					issues.append(CDMLAtomMarkObservationIssue(
						molecule_position, atom_position, mark_position, mark_type,
						"display-only", reason,
					))
	return CDMLAtomMarkObservation(revision, tuple(records), tuple(issues))


#============================================
def _group_observation(document: "CDMLDocument", revision: int) -> CDMLGroupObservation:
	"""Describe direct local-name groups without exposing retained XML to Qt."""
	records = []
	issues = []
	root = document._dom_document.documentElement
	identifier_counts = collections.Counter(
		element.getAttribute("id") for element in _descendant_elements(root)
		if _is_id_definition(element) and element.getAttribute("id")
	)
	for molecule_position, molecule in enumerate(_element_children(root), 1):
		if _local_name(molecule) != "molecule":
			continue
		molecule_id = molecule.getAttribute("id") or None
		molecule_ok = (_is_cdml_element(molecule) and molecule_id is not None
			and identifier_counts[molecule_id] == 1)
		for group_position, group in enumerate(_element_children(molecule), 1):
			if _local_name(group) != "group":
				continue
			group_id = group.getAttribute("id") or None
			group_type = group.getAttribute("group-type") or None
			name = group.getAttribute("name") or None
			pos = group.getAttribute("pos") or "center-first"
			points = [child for child in _element_children(group)
				if _is_cdml_element(child) and _local_name(child) == "point"]
			fonts = [child for child in _element_children(group)
				if _is_cdml_element(child) and _local_name(child) == "font"]
			x = y = None
			if len(points) == 1:
				try:
					x = _presentation_scene_coordinate(points[0].getAttribute("x"))
					y = _presentation_scene_coordinate(points[0].getAttribute("y"))
				except ValueError:
					pass
			family = None
			size = None
			if len(fonts) == 1:
				family = fonts[0].getAttribute("family").strip() or None
				try:
					candidate = float(fonts[0].getAttribute("size"))
					size = candidate if math.isfinite(candidate) and candidate > 0 else None
				except ValueError:
					pass
			reason = None
			if not _is_cdml_element(group):
				reason = "group is preservation-only or uses an unsupported namespace"
			elif not molecule_ok or group_id is None or identifier_counts[group_id] != 1:
				reason = "group does not have one unique direct durable address"
			elif group_type not in {"builtin", "implicit", "explicit"}:
				reason = "group type is unsupported"
			elif x is None or y is None:
				reason = "group lacks one valid visible point"
			elif len(points) != 1 or len(fonts) > 1 or any(
				_local_name(child) not in {"point", "font"} or not _is_cdml_element(child)
				for child in _element_children(group)
			):
				reason = "group has richer or malformed child content"
			elif len(fonts) == 1 and (
				fonts[0].hasAttribute("family") and family is None
				or fonts[0].hasAttribute("size") and size is None
			):
				reason = "group font is malformed"
			implicit_expandable = False
			if reason is None and group_type == "implicit":
				try:
					_implicit_group_source(molecule, group)
					implicit_expandable = True
				except CDMLImplicitGroupExpandError:
					pass
			record = CDMLGroupObservationRecord(
				molecule_id if reason is None else None, group_id if reason is None else None,
				molecule_position, group_position, group_type, name, pos, x, y, family, size,
				"selectable" if reason is None else "display-only", reason, implicit_expandable,
			)
			records.append(record)
			if reason is not None:
				issues.append(CDMLGroupObservationIssue(
					molecule_position, group_position, "display-only", reason,
				))
	return CDMLGroupObservation(revision, tuple(records), tuple(issues))


#============================================
def _molecule_core_observation(
		document: "CDMLDocument", revision: int,
		) -> CDMLMoleculeCoreObservation:
	"""Describe direct molecule chemistry as one coherent plain snapshot."""
	records = []
	issues = []
	root = document._dom_document.documentElement
	standard = oasa.cdml_standard.observe(root, revision)
	identifier_counts = collections.Counter(
		element.getAttribute("id") for element in _descendant_elements(root)
		if _is_id_definition(element) and element.getAttribute("id")
	)
	for molecule_position, molecule in enumerate(_element_children(root), 1):
		if _local_name(molecule) != "molecule":
			continue
		molecule_id = molecule.getAttribute("id") or None
		molecule_reason = None
		if not _is_cdml_element(molecule):
			molecule_reason = "molecule is preservation-only or uses an unsupported namespace"
		elif molecule_id is None or identifier_counts[molecule_id] != 1:
			molecule_reason = "molecule does not have one unique durable ID"
		molecule_renderable = _is_cdml_element(molecule)
		molecule_addressable = molecule_reason is None
		if molecule_reason is not None:
			issues.append(CDMLMoleculeCoreObservationIssue(
				molecule_position, molecule_position, "molecule", "display-only", molecule_reason,
			))
		atoms = []
		atom_ids = set()
		atom_id_counts = collections.Counter()
		for source_position, atom in enumerate(_element_children(molecule), 1):
			if _local_name(atom) != "atom":
				continue
			identifier = atom.getAttribute("id") or None
			reason = None
			if reason is None and not _is_cdml_element(atom):
				reason = "atom is preservation-only or uses an unsupported namespace"
			symbol = atom.getAttribute("name") or None
			if reason is None and symbol not in oasa.periodic_table.periodic_table:
				reason = "atom has an unsupported vertex form for this projection"
			points = [child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"]
			x = y = z = None
			if reason is None and len(points) != 1:
				reason = "atom requires exactly one direct core point"
			if reason is None:
				try:
					x = _presentation_scene_coordinate(points[0].getAttribute("x"))
					y = _presentation_scene_coordinate(points[0].getAttribute("y"))
					z_text = points[0].getAttribute("z")
					z = _presentation_scene_coordinate(z_text) if z_text else None
				except ValueError:
					reason = "atom point coordinates are malformed or non-finite"
			fonts = [child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "font"]
			font = fonts[0] if len(fonts) == 1 else None
			if reason is None and len(fonts) > 1:
				reason = "atom has duplicate direct fonts"
			def integer(name: str) -> int | None:
				value = atom.getAttribute(name)
				if not value:
					return None
				try:
					return int(value)
				except ValueError:
					return None
			integer_names = (
				"charge", "valency", "isotope", "multiplicity", "free_sites",
				"explicit_hydrogens", "number",
			)
			if reason is None and any(
				atom.hasAttribute(name) and integer(name) is None for name in integer_names
			):
				reason = "atom has a malformed integer chemistry or display field"
			show_value = atom.getAttribute("show")
			hydrogen_value = atom.getAttribute("hydrogens")
			if reason is None and (
				(show_value and show_value not in {"yes", "no"})
				or (hydrogen_value and hydrogen_value not in {"on", "off"})
				or (atom.hasAttribute("show_number") and atom.getAttribute("show_number") not in {
					"yes", "true", "1", "on", "no", "false", "0", "off",
				})
			):
				reason = "atom has a malformed display boolean"
			font_size = None
			if font is not None and font.hasAttribute("size"):
				font_size_text = font.getAttribute("size")
				if re.fullmatch(r"[0-9]+", font_size_text) is not None:
					candidate = int(font_size_text)
					font_size = candidate if candidate > 0 else None
			if reason is None and font is not None and (
				(font.hasAttribute("family") and not font.getAttribute("family").strip())
				or
				(font.hasAttribute("size") and font_size is None)
				or (font.hasAttribute("color") and re.fullmatch(
					r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?", font.getAttribute("color"),
				) is None)
			):
				reason = "atom has a malformed font field"
			renderable = reason is None and molecule_renderable
			addressable = (
				molecule_addressable and renderable and identifier is not None
				and identifier_counts[identifier] == 1
			)
			address_reason = None if addressable else "atom has no unique durable ID"
			explicit_fields = tuple(name for name, present in (
				("show", bool(show_value)), ("show_hydrogens", bool(hydrogen_value)),
				("font_family", font is not None and font.hasAttribute("family")),
				("font_size", font is not None and font.hasAttribute("size")),
				("line_color", font is not None and font.hasAttribute("color")),
			) if present)
			effective_hydrogens = {"on": True, "off": False}.get(hydrogen_value)
			effective_family = font.getAttribute("family") or None if font else None
			effective_color = font.getAttribute("color") or None if font else None
			effective_hydrogens, effective_family, font_size, effective_color = (
				oasa.cdml_standard.resolve_atom_values(
					standard, effective_hydrogens, effective_family, font_size, effective_color,
				)
			)
			atoms.append(CDMLAtomCoreObservationRecord(
				identifier, source_position, symbol, x, y, z, integer("charge"),
				integer("valency"), integer("isotope"), integer("multiplicity"),
				integer("free_sites"), integer("explicit_hydrogens"),
				{"yes": True, "no": False}.get(show_value),
				effective_hydrogens, effective_family, font_size, effective_color,
				integer("number"), {"yes": True, "true": True, "1": True, "on": True,
					"no": False, "false": False, "0": False, "off": False}.get(atom.getAttribute("show_number")),
				explicit_fields,
				"actionable" if addressable else "display-only", renderable, addressable,
				reason or molecule_reason or address_reason,
			))
			if reason is None and identifier is not None:
				atom_ids.add(identifier)
				atom_id_counts[identifier] += 1
			if reason is not None:
				issues.append(CDMLMoleculeCoreObservationIssue(
					molecule_position, source_position, "atom", "display-only", reason,
				))
		bonds = []
		for source_position, bond in enumerate(_element_children(molecule), 1):
			if _local_name(bond) != "bond":
				continue
			identifier = bond.getAttribute("id") or None
			start = bond.getAttribute("start") or None
			end = bond.getAttribute("end") or None
			reason = None
			if reason is None and not _is_cdml_element(bond):
				reason = "bond is preservation-only or uses an unsupported namespace"
			bond_type, order, _legacy = oasa.bond_semantics.parse_cdml_bond_type(
				bond.getAttribute("type"),
			)
			if reason is None and (
				bond_type not in oasa.bond_semantics.BOND_TYPE_SEMANTICS
				or not oasa.bond_semantics.is_authored_bond_order(bond_type, order)
			):
				reason = "bond type or order is unsupported"
			if reason is None and (
				start not in atom_ids or end not in atom_ids or start == end
				or atom_id_counts[start] != 1 or atom_id_counts[end] != 1
			):
				reason = "bond endpoints do not name two observed direct atoms"
			def finite_attr(name: str) -> float | None:
				if not bond.hasAttribute(name):
					return None
				try:
					value = float(bond.getAttribute(name))
				except ValueError:
					return None
				return value if math.isfinite(value) else None
			numeric_fields = ("line_width", "bond_width", "wedge_width", "double_ratio")
			if reason is None and any(
				bond.hasAttribute(name) and finite_attr(name) is None for name in numeric_fields
			):
				reason = "bond has a malformed numeric depiction field"
			if reason is None and any(
				finite_attr(name) is not None and finite_attr(name) <= 0
				for name in numeric_fields
			):
				reason = "bond has a nonpositive numeric depiction field"
			if reason is None and (
				(bond.hasAttribute("center") and bond.getAttribute("center") not in {"yes", "no"})
				or (bond.hasAttribute("auto_sign") and not bond.getAttribute("auto_sign").lstrip("+-").isdigit())
				or (bond.hasAttribute("equithick") and bond.getAttribute("equithick") not in {"0", "1"})
				or (bond.hasAttribute("simple_double") and bond.getAttribute("simple_double") not in {"0", "1"})
				or (bond.hasAttribute("haworth_position") and bond.getAttribute("haworth_position") not in {"front", "back"})
			):
				reason = "bond has a malformed depiction enum"
			explicit = tuple(sorted([
				name for name in oasa.cdml_bond_io.CDML_META_ATTRS if bond.hasAttribute(name)
			]))
			renderable = reason is None and molecule_renderable
			addressable = (
				molecule_addressable and renderable and identifier is not None
				and identifier_counts[identifier] == 1
			)
			address_reason = None if addressable else "bond has no unique durable ID"
			line_width = finite_attr("line_width")
			bond_width = finite_attr("bond_width")
			wedge_width = finite_attr("wedge_width")
			double_ratio = finite_attr("double_ratio")
			line_color = bond.getAttribute("color") or None
			line_width, bond_width, wedge_width, double_ratio, line_color = (
				oasa.cdml_standard.resolve_bond_values(
					standard, line_width, bond_width, wedge_width, double_ratio, line_color,
				)
			)
			bonds.append(CDMLBondCoreObservationRecord(
				identifier, source_position, start, end, bond_type, order or None,
				line_width, bond_width, wedge_width, double_ratio,
				True if bond.getAttribute("center") == "yes" else (False if bond.hasAttribute("center") else None),
				int(bond.getAttribute("auto_sign")) if bond.getAttribute("auto_sign").lstrip("+-").isdigit() else None,
				bool(int(bond.getAttribute("equithick"))) if bond.getAttribute("equithick") in ("0", "1") else None,
				bool(int(bond.getAttribute("simple_double"))) if bond.getAttribute("simple_double") in ("0", "1") else None,
				line_color, bond.getAttribute("wavy_style") or None,
				bond.getAttribute("haworth_position") or None, explicit,
				"actionable" if addressable else "display-only", renderable, addressable,
				reason or molecule_reason or address_reason,
			))
			if reason is not None:
				issues.append(CDMLMoleculeCoreObservationIssue(
					molecule_position, source_position, "bond", "display-only", reason,
				))
		records.append(CDMLMoleculeCoreObservationRecord(
			molecule_id, molecule_position, molecule.getAttribute("name") or None,
			tuple(atoms), tuple(bonds), "actionable" if molecule_reason is None else "display-only",
			molecule_renderable,
			molecule_addressable,
			molecule_reason,
		))
	return CDMLMoleculeCoreObservation(revision, tuple(records), tuple(issues))


#============================================
def _render_text_runs(text: str) -> tuple[tuple[str, str], ...]:
	"""Normalize OASA label markup into the portable text-run grammar."""
	return tuple(
		(chunk, oasa.render_ops._segment_baseline_state(tags))
		for chunk, tags in oasa.render_ops._text_segments(text)
	)


#============================================
def _render_primitive(op: object, offset: tuple[float, float] = (0.0, 0.0)) -> CDMLRenderPrimitive:
	"""Convert one internal OASA render operation to finite portable facts."""
	x_offset, y_offset = offset
	def point(point: tuple[float, float]) -> tuple[float, float]:
		if not isinstance(point, tuple) or len(point) != 2:
			raise CDMLMoleculeRenderObservationError("render operation point must contain two coordinates")
		x = _render_number(point[0], "render operation coordinate") - x_offset
		y = _render_number(point[1], "render operation coordinate") - y_offset
		return x, y
	def number(value: object, description: str) -> float:
		return _render_number(value, description)
	def z_order(value: object) -> int:
		if type(value) is not int:
			raise CDMLMoleculeRenderObservationError("render operation z order must be an int")
		return value
	def color(value: object) -> str | None:
		if isinstance(value, str) and value.strip().lower() == "none":
			return None
		converted = oasa.render_ops.color_to_hex(value)
		if converted is not None and re.fullmatch(r"#[0-9a-f]{6}", converted) is None:
			raise CDMLMoleculeRenderObservationError("render operation color is unsupported")
		return converted
	def role(value: object) -> str | None:
		# This is the one renderer-private paper token, not a convention for
		# arbitrary strings.  Qt resolves the resulting semantic role locally.
		if value == "__backend_document_background__":
			return "document-background"
		if value == "__backend_foreground__":
			return "foreground"
		return None
	if isinstance(op, oasa.render_ops.LineOp):
		color_role = role(op.color)
		primitive = CDMLRenderPrimitive("line", (point(op.p1), point(op.p2)), (), (), None,
			None, None, None if color_role else color(op.color), color_role,
			number(op.width, "render operation width"), None, None, None, None,
			op.cap or None, op.join or None, z_order(op.z))
		return _validated_render_primitive(primitive)
	if isinstance(op, oasa.render_ops.PolygonOp):
		fill_role = role(op.fill)
		stroke_role = role(op.stroke)
		primitive = CDMLRenderPrimitive("polygon", tuple(point(value) for value in op.points), (), (), None,
			None if fill_role else color(op.fill), fill_role, None if stroke_role else color(op.stroke),
			stroke_role, number(op.stroke_width, "render operation stroke width"),
			None, None, None, None, None, None, z_order(op.z))
		return _validated_render_primitive(primitive)
	if isinstance(op, oasa.render_ops.CircleOp):
		radius = number(op.radius, "render operation radius")
		fill_role = role(op.fill)
		stroke_role = role(op.stroke)
		primitive = CDMLRenderPrimitive("circle", (point(op.center),), (), (), radius, None if fill_role else color(op.fill), fill_role,
			None if stroke_role else color(op.stroke), stroke_role,
			number(op.stroke_width, "render operation stroke width"), None, None,
			None, None, None, None, z_order(op.z))
		return _validated_render_primitive(primitive)
	if isinstance(op, oasa.render_ops.PathOp):
		commands = []
		if not isinstance(op.commands, tuple):
			raise CDMLMoleculeRenderObservationError("render path commands must be a tuple")
		for entry in op.commands:
			if not isinstance(entry, tuple) or len(entry) != 2:
				raise CDMLMoleculeRenderObservationError("render path command is malformed")
			command, payload = entry
			if command == "Z":
				if payload is not None:
					raise CDMLMoleculeRenderObservationError("render close path command has payload")
				commands.append((command, None))
				continue
			if command not in {"M", "L", "ARC"}:
				raise CDMLMoleculeRenderObservationError("render path command is unsupported")
			expected_length = 5 if command == "ARC" else 2
			if not isinstance(payload, tuple) or len(payload) != expected_length:
				raise CDMLMoleculeRenderObservationError("render path command payload is malformed")
			values = tuple(number(value, "render path coordinate") for value in payload)
			if command in {"M", "L"}:
				values = (values[0] - x_offset, values[1] - y_offset)
			elif command == "ARC":
				values = (values[0] - x_offset, values[1] - y_offset, *values[2:])
			commands.append((command, values))
		fill_role = role(op.fill)
		stroke_role = role(op.stroke)
		primitive = CDMLRenderPrimitive("path", (), tuple(commands), (), None, None if fill_role else color(op.fill), fill_role,
			None if stroke_role else color(op.stroke), stroke_role,
			number(op.stroke_width, "render operation stroke width"), None, None, None, None,
			op.cap or None, op.join or None, z_order(op.z))
		return _validated_render_primitive(primitive)
	if isinstance(op, oasa.render_ops.TextOp):
		if not isinstance(op.text, str):
			raise CDMLMoleculeRenderObservationError("render text must be a string")
		color_role = role(op.color) or ("foreground" if op.color is None else None)
		primitive = CDMLRenderPrimitive("text", (point((op.x, op.y)),), (), _render_text_runs(op.text), None,
			None if color_role else color(op.color), color_role, None, None, None,
			str(op.font_name), number(op.font_size, "render text font size"),
			str(op.anchor), str(op.weight), None, None, z_order(op.z))
		return _validated_render_primitive(primitive)
	raise CDMLMoleculeRenderObservationError("unsupported internal render primitive")


#============================================
def normalize_render_operations(
		operations: collections.abc.Iterable[object],
		offset: tuple[float, float] = (0.0, 0.0),
		) -> tuple[CDMLRenderPrimitive, ...]:
	"""Return validated portable primitives for one transient OASA render batch.

	This is the public rendering boundary for callers that use an OASA
	compatibility depiction calculation without owning persistent CDML.  It
	accepts internal operation values only at the backend edge and returns the
	closed, frontend-neutral grammar used by authoritative snapshot observations.
	The optional offset converts scene-space operations into the receiving
	frontend's local coordinate frame.
	"""
	if not isinstance(offset, tuple) or len(offset) != 2:
		raise CDMLMoleculeRenderObservationError("render operation offset must be a point")
	if any(isinstance(value, bool) or not isinstance(value, numbers.Real) for value in offset):
		raise CDMLMoleculeRenderObservationError("render operation offset must be numeric")
	normalized_offset = float(offset[0]), float(offset[1])
	if not all(math.isfinite(value) for value in normalized_offset):
		raise CDMLMoleculeRenderObservationError("render operation offset must be finite")
	if not isinstance(operations, collections.abc.Iterable):
		raise CDMLMoleculeRenderObservationError("render operations must be iterable")
	result = tuple(_render_primitive(operation, normalized_offset) for operation in operations)
	return result


#============================================
def _render_number(value: object, description: str) -> float:
	"""Return one finite render scalar without admitting bool as geometry."""
	if isinstance(value, bool) or not isinstance(value, numbers.Real):
		raise CDMLMoleculeRenderObservationError(f"{description} must be numeric")
	converted = float(value)
	if not math.isfinite(converted):
		raise CDMLMoleculeRenderObservationError(f"{description} must be finite")
	return converted


#============================================
def _validated_render_primitive(primitive: CDMLRenderPrimitive) -> CDMLRenderPrimitive:
	"""Reject an invalid portable primitive before it crosses the backend seam."""
	if primitive.kind not in {"line", "polygon", "circle", "path", "text"}:
		raise CDMLMoleculeRenderObservationError("render primitive kind is unsupported")
	if type(primitive.z) is not int:
		raise CDMLMoleculeRenderObservationError("render primitive z order must be an int")
	for point in primitive.points:
		if (
			not isinstance(point, tuple) or len(point) != 2
			or any(
				isinstance(value, bool) or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in point
			)
		):
			raise CDMLMoleculeRenderObservationError("render primitive point is not finite")
	if primitive.stroke_width is not None and (
		isinstance(primitive.stroke_width, bool)
		or not isinstance(primitive.stroke_width, numbers.Real)
		or not math.isfinite(primitive.stroke_width) or primitive.stroke_width < 0
	):
		raise CDMLMoleculeRenderObservationError("render primitive stroke width is invalid")
	if primitive.kind == "line" and (
		len(primitive.points) != 2 or primitive.stroke_width is None or primitive.stroke_width <= 0
	):
		raise CDMLMoleculeRenderObservationError("render line primitive is invalid")
	if primitive.kind == "polygon" and len(primitive.points) < 3:
		raise CDMLMoleculeRenderObservationError("render polygon primitive is invalid")
	if primitive.kind == "circle" and (
		len(primitive.points) != 1 or primitive.radius is None
		or isinstance(primitive.radius, bool) or not isinstance(primitive.radius, numbers.Real)
		or not math.isfinite(primitive.radius) or primitive.radius <= 0
	):
		raise CDMLMoleculeRenderObservationError("render circle primitive is invalid")
	if primitive.kind == "path":
		if not primitive.commands or primitive.commands[0][0] != "M":
			raise CDMLMoleculeRenderObservationError("render path primitive must begin with move")
		closed = False
		for command, payload in primitive.commands:
			if closed:
				raise CDMLMoleculeRenderObservationError("render path command follows close")
			if command == "Z" and payload is None:
				closed = True
				continue
			if command in {"M", "L"} and payload is not None and len(payload) == 2:
				pass
			elif command == "ARC" and payload is not None and len(payload) == 5 and payload[2] > 0:
				pass
			else:
				raise CDMLMoleculeRenderObservationError("render path command is unsupported")
			if any(
				isinstance(value, bool) or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in payload
			):
				raise CDMLMoleculeRenderObservationError("render path command is not finite")
	if primitive.kind == "text" and (
		len(primitive.points) != 1 or primitive.font_size is None
		or isinstance(primitive.font_size, bool) or not isinstance(primitive.font_size, numbers.Real)
		or not math.isfinite(primitive.font_size) or primitive.font_size <= 0
		or primitive.anchor not in {"start", "middle", "end"}
		or primitive.weight not in {"normal", "bold"}
		or any(baseline not in {"base", "sub", "sup"} for _text, baseline in primitive.text_runs)
	):
		raise CDMLMoleculeRenderObservationError("render text primitive is invalid")
	for value, role in ((primitive.fill, primitive.fill_role), (primitive.stroke, primitive.stroke_role)):
		if value is not None and re.fullmatch(r"#[0-9a-f]{6}", value) is None:
			raise CDMLMoleculeRenderObservationError("render primitive color is invalid")
		if role not in {None, "foreground", "document-background"}:
			raise CDMLMoleculeRenderObservationError("render primitive color role is invalid")
	if primitive.cap not in {None, "", "butt", "round", "square"}:
		raise CDMLMoleculeRenderObservationError("render primitive cap is invalid")
	if primitive.join not in {None, "", "miter", "round", "bevel"}:
		raise CDMLMoleculeRenderObservationError("render primitive join is invalid")
	return primitive


#============================================
def _molecule_render_observation(document: "CDMLDocument", revision: int) -> CDMLMoleculeRenderObservation:
	"""Build atom and bond paint batches from one canonical CDML snapshot."""
	core = _molecule_core_observation(document, revision)
	batches = []
	issues = []
	root = document._dom_document.documentElement
	standard = oasa.cdml_standard.observe(root, revision)
	for core_record in core.records:
		if not core_record.renderable:
			continue
		molecule = next((child for position, child in enumerate(_element_children(root), 1)
			if position == core_record.source_position), None)
		try:
			chem_molecule, atom_by_source, bond_by_source = _decode_renderable_molecule_core(
				molecule, core_record,
			)
			atom_entries = [
				(atom_record, atom_by_source[atom_record.source_position])
				for atom_record in core_record.atoms if atom_record.renderable
			]
			for atom_record, atom in atom_entries:
				if atom_record.show is False:
					ops = ()
				else:
					marks = atom.properties_.pop("marks", None)
					color = atom_record.line_color or "__backend_foreground__"
					ops = oasa.render_lib.molecule_ops.build_vertex_ops(
						atom, transform_xy=None, show_hydrogens_on_hetero=bool(atom_record.show_hydrogens),
						color_atoms=True, atom_colors={atom.symbol: color},
						font_name=atom_record.font_family or "Arial", font_size=atom_record.font_size or 12.0,
						background_color=standard.area_color or "__backend_document_background__",
						show_carbon_symbol=atom_record.show is True,
					)
					if marks is not None:
						atom.properties_["marks"] = marks
				anchor = (float(atom_record.x_pt), float(atom_record.y_pt))
				batches.append(CDMLMoleculeRenderBatch("atom", core_record.source_position, atom_record.identifier,
					atom_record.source_position, atom_record.addressable, anchor, None,
					tuple(_render_primitive(op, anchor) for op in ops)))
			shown, labels, attaches = set(), {}, {}
			for atom_record, atom in atom_entries:
				if atom_record.show is False:
					continue
				entry_shown, entry_labels, entry_attaches = oasa.render_lib.molecule_ops.build_label_attach_targets(
					[atom], show_hydrogens_on_hetero=bool(atom_record.show_hydrogens),
					font_name=atom_record.font_family or "Arial", font_size=atom_record.font_size or 12.0,
					show_carbon_symbol=atom_record.show is True,
				)
				shown.update(entry_shown); labels.update(entry_labels); attaches.update(entry_attaches)
			bond_entries = [
				(bond_record, bond_by_source[bond_record.source_position])
				for bond_record in core_record.bonds if bond_record.renderable
			]
			for bond_record, bond in bond_entries:
				start_atom, end_atom = bond.get_vertices()
				start, end = (float(start_atom.x), float(start_atom.y)), (float(end_atom.x), float(end_atom.y))
				context = oasa.render_lib.data_types.BondRenderContext(
					None, bond_record.line_width if bond_record.line_width is not None else 2.0,
					bond_record.bond_width if bond_record.bond_width is not None else 6.0,
					bond_record.wedge_width if bond_record.wedge_width is not None else 9.2,
					1.2, bond_second_line_shortening=(
						oasa.cdml_standard.bond_second_line_shortening(bond_record.double_ratio)
					),
					shown_vertices=shown,
					bond_coords={bond: (start, end)}, bond_coords_provider={bond: (start, end)}.get,
					label_targets=labels, attach_targets=attaches,
					attach_constraints=oasa.render_lib.data_types.make_attach_constraints(),
				)
				previous = oasa.cdml_standard.install_bond_render_values(
					bond, bond_record.double_ratio, bond_record.line_color,
				)
				try:
					ops = oasa.render_lib.bond_ops.build_bond_ops(bond, start, end, context)
				finally:
					oasa.cdml_standard.restore_bond_render_values(bond, previous)
				batches.append(CDMLMoleculeRenderBatch("bond", core_record.source_position, bond_record.identifier,
					bond_record.source_position, bond_record.addressable, None, (start, end),
					tuple(_render_primitive(op) for op in ops)))
		except CDMLMoleculeRenderObservationError:
			raise
		except Exception as exc:
			raise CDMLMoleculeRenderObservationError(
				"could not prepare molecule render observation: %s" % exc,
			) from exc
	for issue in core.issues:
		issues.append(CDMLMoleculeRenderObservationIssue(
			issue.molecule_source_position, issue.source_position, issue.kind, issue.reason,
		))
	return CDMLMoleculeRenderObservation(revision, tuple(batches), tuple(issues))


#============================================
def _decode_renderable_molecule_core(
		molecule: object, core_record: CDMLMoleculeCoreObservationRecord,
		) -> tuple[object, dict[int, object], dict[int, object]]:
	"""Decode exactly accepted direct core records and retain source associations.

	The codec is allowed to make temporary chemistry objects but must never be
	matched back by an ID or by a graph enumeration.  Filtering occurs before
	decode, so an inert middle record or a known-group expansion cannot shift a
	later authored record's association.
	"""
	renderable_atoms = [record for record in core_record.atoms if record.renderable]
	renderable_bonds = [record for record in core_record.bonds if record.renderable]
	by_source = {
		position: child for position, child in enumerate(_element_children(molecule), 1)
	}
	clone = molecule.cloneNode(False)
	temporary_atom_ids = {}
	atom_sources_by_identifier = {}
	for record in renderable_atoms:
		atom_clone = by_source[record.source_position].cloneNode(True)
		temporary_identifier = "__render_atom_%d" % record.source_position
		atom_clone.setAttribute("id", temporary_identifier)
		temporary_atom_ids[record.source_position] = temporary_identifier
		if record.identifier is not None:
			atom_sources_by_identifier[record.identifier] = temporary_identifier
		clone.appendChild(atom_clone)
	for record in renderable_bonds:
		bond_clone = by_source[record.source_position].cloneNode(True)
		bond_clone.setAttribute("id", "__render_bond_%d" % record.source_position)
		bond_clone.setAttribute("start", atom_sources_by_identifier[record.start_id])
		bond_clone.setAttribute("end", atom_sources_by_identifier[record.end_id])
		clone.appendChild(bond_clone)
	chem_molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(clone)
	if chem_molecule is None:
		raise CDMLMoleculeRenderObservationError("renderable direct molecule core could not be decoded")
	if len(chem_molecule.atoms) != len(renderable_atoms) or len(chem_molecule.bonds) != len(renderable_bonds):
		raise CDMLMoleculeRenderObservationError("direct molecule codec changed authored core association")
	atom_by_source = {
		record.source_position: chem_molecule.atoms[index]
		for index, record in enumerate(renderable_atoms)
	}
	bond_by_temporary_id = {bond.id: bond for bond in chem_molecule.bonds}
	bond_by_source = {
		record.source_position: bond_by_temporary_id["__render_bond_%d" % record.source_position]
		for record in renderable_bonds
	}
	return chem_molecule, atom_by_source, bond_by_source


#============================================
def _atom_chemistry_facts_observation(
		document: "CDMLDocument", revision: int,
		) -> CDMLAtomChemistryFactsObservation:
	"""Observe complete direct-core chemistry without retaining graph objects."""
	core = _molecule_core_observation(document, revision)
	records = []
	issues = []
	root = document._dom_document.documentElement
	molecules_by_source_position = {
		source_position: molecule
		for source_position, molecule in enumerate(_element_children(root), 1)
		if _local_name(molecule) == "molecule"
	}
	for core_record in core.records:
		molecule = molecules_by_source_position.get(core_record.source_position)
		if molecule is None:
			issues.append(CDMLAtomChemistryFactsIssue(
				core_record.source_position, None, "display-only",
				"molecule source position is unavailable for chemistry observation",
			))
			continue
		reason = core_record.reason
		if reason is None and (
			not core_record.renderable or not core_record.addressable
			or any(not atom.renderable or not atom.addressable for atom in core_record.atoms)
			or any(not bond.renderable or not bond.addressable for bond in core_record.bonds)
		):
			reason = "molecule core is incomplete or lacks unique durable addresses"
		atom_by_source = {}
		if reason is None:
			try:
				_unused_molecule, atom_by_source, _unused_bonds = _decode_renderable_molecule_core(
					molecule, core_record,
				)
			except (
					AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError,
				) as error:
				reason = "direct molecule chemistry could not be decoded: %s" % error
		for atom_record in core_record.atoms:
			atom = atom_by_source.get(atom_record.source_position)
			if atom is None:
				records.append(CDMLAtomChemistryFactRecord(
					core_record.identifier, atom_record.identifier, atom_record.symbol,
					atom_record.charge, core_record.source_position,
					atom_record.source_position, "display-only", None, None, None, None,
					None, None, reason or atom_record.reason or "atom chemistry is unavailable",
				))
				continue
			try:
				records.append(CDMLAtomChemistryFactRecord(
					core_record.identifier, atom_record.identifier, atom_record.symbol,
					atom_record.charge, core_record.source_position,
					atom_record.source_position, "usable", atom.valency,
					atom.occupied_valency, atom.free_valency, atom.get_hydrogen_count(),
					atom.oxidation_number, oasa.periodic_table.periodic_table[atom.symbol]["ord"], None,
				))
			except (AttributeError, RuntimeError, TypeError, ValueError) as error:
				records.append(CDMLAtomChemistryFactRecord(
					core_record.identifier, atom_record.identifier, atom_record.symbol,
					atom_record.charge, core_record.source_position,
					atom_record.source_position, "display-only", None, None, None, None,
					None, None, "atom chemistry could not be observed: %s" % error,
				))
		if reason is not None:
			issues.append(CDMLAtomChemistryFactsIssue(
				core_record.source_position, None, "display-only", reason,
			))
	return CDMLAtomChemistryFactsObservation(revision, tuple(records), tuple(issues))


#============================================
def _normalized_atom_mark_facts(
		atom: object, mark: object, mark_type: str | None,
		) -> tuple[float, float, float, bool, float]:
	"""Return finite final Qt rendering facts without repairing source XML."""
	angle = _finite_atom_mark_number(mark.getAttribute("angle"), 0.0)
	offset = 12.0
	point = next((child for child in _element_children(atom)
		if _is_cdml_element(child) and _local_name(child) == "point"), None)
	if point is not None and mark.hasAttribute("x") and mark.hasAttribute("y"):
		atom_x = _atom_mark_coordinate(point.getAttribute("x"))
		atom_y = _atom_mark_coordinate(point.getAttribute("y"))
		mark_x = _atom_mark_coordinate(mark.getAttribute("x"))
		mark_y = _atom_mark_coordinate(mark.getAttribute("y"))
		if None not in (atom_x, atom_y, mark_x, mark_y):
			dx = mark_x - atom_x
			dy = mark_y - atom_y
			offset = math.hypot(dx, dy)
			if offset:
				angle = math.degrees(math.atan2(dy, dx))
	defaults = {"plus": 10.0, "minus": 10.0, "electronpair": 10.0,
		"pz_orbital": 40.0}
	size = _positive_atom_mark_number(mark.getAttribute("size"), defaults.get(mark_type, 4.0))
	circle = mark.getAttribute("draw_circle") in ("yes", "true", "1", "on") if mark.hasAttribute("draw_circle") else True
	width = _positive_atom_mark_number(mark.getAttribute("line_width"), 1.0)
	return angle, offset, size, circle, width


#============================================
def _atom_mark_coordinate(value: str) -> float | None:
	"""Decode one finite authored coordinate into PostScript points."""
	try:
		if value.endswith("cm"):
			result = float(value[:-2]) / _POINT_CM_PER_POSTSCRIPT_POINT
		elif value.endswith("px"):
			result = float(value[:-2])
		else:
			result = float(value)
	except ValueError:
		return None
	return result if math.isfinite(result) else None


#============================================
def _finite_atom_mark_number(value: str, default: float) -> float:
	"""Return a finite display scalar or its compatibility fallback."""
	try:
		result = float(value)
	except ValueError:
		return default
	return result if math.isfinite(result) else default


#============================================
def _positive_atom_mark_number(value: str, default: float) -> float:
	"""Return a finite positive display scalar or its compatibility fallback."""
	result = _finite_atom_mark_number(value, default)
	return result if result > 0.0 else default


#============================================
def _record_for_element(position: int, element: object) -> CDMLObjectRecord:
	"""Build a node-free immutable record from one persistent XML element."""
	local_name = _local_name(element)
	identifier = element.getAttribute("id") or None
	record = CDMLObjectRecord(
		position=position,
		path=_node_path(element),
		local_name=local_name,
		identifier=identifier,
		raw_xml=element.toxml(),
		opaque=not _is_cdml_element(element),
	)
	return record


#============================================
def _fragment_member_reference(element: object) -> bool:
	"""Return whether an ``id`` attribute is a documented fragment member ref."""
	parent = element.parentNode
	if (
		parent is None
		or not _is_cdml_element(element)
		or not _is_cdml_element(parent)
		or _local_name(parent) != "fragment"
	):
		return False
	return _local_name(element) in ("vertex", "bond")


#============================================
def _copy_proposal_namespace_declarations(proposal_root: object, molecule: object) -> None:
	"""Keep proposal-root namespace bindings available on one imported molecule."""
	for index in range(proposal_root.attributes.length):
		attribute = proposal_root.attributes.item(index)
		if not attribute.name.startswith("xmlns"):
			continue
		if not molecule.hasAttribute(attribute.name):
			molecule.setAttribute(attribute.name, attribute.value)


#============================================
def _insertion_coordinate(value: str) -> float:
	"""Convert one accepted CDML scene coordinate to centimeters."""
	if not isinstance(value, str) or not _COORDINATE_PATTERN.fullmatch(value):
		raise CDMLValidationError(f"invalid insertion coordinate: {value!r}")
	is_centimeters = value.endswith("cm")
	number_text = value[:-2] if is_centimeters else value
	number = float(number_text)
	if not math.isfinite(number):
		raise CDMLValidationError(f"nonfinite insertion coordinate: {value!r}")
	coordinate = number if is_centimeters else number * _POINT_CM_PER_POSTSCRIPT_POINT
	if not math.isfinite(coordinate):
		raise CDMLValidationError(f"overflow insertion coordinate: {value!r}")
	return coordinate


#============================================
def _translated_coordinate(value: str, offset: float) -> str:
	"""Return one translated, canonical centimeter coordinate."""
	coordinate = _insertion_coordinate(value) + offset
	if not math.isfinite(coordinate):
		raise CDMLValidationError("translated insertion coordinate is nonfinite")
	result = f"{coordinate:.3f}cm"
	return result


#============================================
def _canonical_authored_coordinate(coordinate: float) -> str:
	"""Return one 0.001 cm canonical coordinate without a signed zero.

	Persistent coordinate operations compare authored values at the precision
	that they can write.  This keeps a geometrically real but sub-resolution
	motion from creating a meaningless revision, while retaining a source's
	lexical spelling whenever that axis is unchanged.
	"""
	rounded = round(coordinate, 3)
	if rounded == 0.0:
		rounded = 0.0
	return f"{rounded:.3f}cm"


#============================================
def _translate_point(point: object, dx: float, dy: float) -> None:
	"""Validate and translate one established CDML point in detached state."""
	if _has_direct_core_children(point):
		raise CDMLValidationError("insertion point may not contain element children")
	if not point.hasAttribute("x") or not point.hasAttribute("y"):
		raise CDMLValidationError("insertion point requires x and y")
	if point.hasAttribute("z"):
		_insertion_coordinate(point.getAttribute("z"))
	point.setAttribute("x", _translated_coordinate(point.getAttribute("x"), dx))
	point.setAttribute("y", _translated_coordinate(point.getAttribute("y"), dy))


#============================================
def _has_direct_core_children(element: object) -> bool:
	"""Return whether a CDML element contains known direct CDML grammar.

	Foreign children are opaque extension payload. Insertion keeps them literal
	and translates only the surrounding recognized CDML geometry.
	"""
	return any(_is_cdml_element(child) for child in _element_children(element))


#============================================
def _translate_mark(mark: object, dx: float, dy: float) -> None:
	"""Translate an explicit mark position while retaining all mark semantics."""
	if _has_direct_core_children(mark):
		raise CDMLValidationError("insertion mark may not contain element children")
	has_x = mark.hasAttribute("x")
	has_y = mark.hasAttribute("y")
	if has_x != has_y:
		raise CDMLValidationError("insertion mark x and y must be present together")
	if has_x:
		mark.setAttribute("x", _translated_coordinate(mark.getAttribute("x"), dx))
		mark.setAttribute("y", _translated_coordinate(mark.getAttribute("y"), dy))


#============================================
def _validate_vertex_geometry(vertex: object, dx: float, dy: float) -> None:
	"""Validate and translate one complete established molecular vertex."""
	name = _local_name(vertex)
	allowed_children = {
		"atom": frozenset({"point", "font", "ftext", "mark"}),
		"group": frozenset({"point", "font", "mark"}),
		"text": frozenset({"point", "font", "ftext", "mark"}),
		"query": frozenset({"point", "font", "mark"}),
	}[name]
	points = []
	for child in _element_children(vertex):
		if not _is_cdml_element(child):
			continue
		child_name = _local_name(child)
		if child_name not in allowed_children:
			raise CDMLValidationError(f"unsupported {name} child: {child_name}")
		if child_name == "point":
			points.append(child)
		elif child_name == "font" and _has_direct_core_children(child):
			raise CDMLValidationError(f"insertion {name} font may not contain element children")
		elif child_name == "mark":
			_translate_mark(child, dx, dy)
	if len(points) != 1:
		raise CDMLValidationError(f"insertion {name} requires exactly one direct point")
	_translate_point(points[0], dx, dy)


#============================================
def _validate_molecule_fragment(molecule: object, dx: float, dy: float) -> None:
	"""Validate the closed molecular insertion subset and translate its geometry."""
	for child in _element_children(molecule):
		name = _local_name(child)
		if not _is_cdml_element(child):
			# A foreign child is persistent opaque molecule content.  Its geometry
			# is outside this operation's grammar, so preserve it literally while
			# translating only the recognized CDML molecular records.
			continue
		if name not in _MOLECULE_CHILD_NAMES:
			raise CDMLValidationError(f"unsupported molecule child: {name}")
		if name in _MOLECULE_VERTEX_NAMES:
			_validate_vertex_geometry(child, dx, dy)
		elif name in ("bond", "template") and _has_direct_core_children(child):
			raise CDMLValidationError(f"insertion {name} may not contain element children")
		elif name == "fragment":
			for member in _element_children(child):
				if not _is_cdml_element(member):
					continue
				member_name = _local_name(member)
				if member_name not in (
						"name", "bond", "vertex", "property",
				):
					raise CDMLValidationError(f"unsupported fragment child: {member_name}")
				if _has_direct_core_children(member):
					raise CDMLValidationError(f"insertion fragment {member_name} may not contain children")


#============================================
def _translate_top_level_geometry(element: object, dx: float, dy: float) -> None:
	"""Validate and translate the allowlisted top-level presentation grammar."""
	name = _local_name(element)
	children = _element_children(element)
	if name == "molecule":
		_validate_molecule_fragment(element, dx, dy)
		return
	if name == "arrow":
		if len(children) < 2 or any(
				not _is_cdml_element(child) or _local_name(child) != "point" for child in children
		):
			raise CDMLValidationError("insertion arrow requires at least two direct points")
		for point in children:
			_translate_point(point, dx, dy)
		return
	if name == "plus":
		if sum(_local_name(child) == "point" for child in children) != 1 or sum(
				_local_name(child) == "font" for child in children
		) > 1 or any(
				not _is_cdml_element(child) or _local_name(child) not in ("point", "font") for child in children
			):
			raise CDMLValidationError("insertion plus requires one point and optional font")
		for child in children:
			if _local_name(child) == "font" and _element_children(child):
				raise CDMLValidationError("insertion plus font may not contain element children")
		_translate_point(next(child for child in children if _local_name(child) == "point"), dx, dy)
		return
	if name == "text":
		if sum(_local_name(child) == "point" for child in children) != 1 or sum(
				_local_name(child) == "ftext" for child in children
		) != 1 or sum(_local_name(child) == "font" for child in children) > 1 or any(
				not _is_cdml_element(child) or _local_name(child) not in ("point", "font", "ftext")
				for child in children
		):
			raise CDMLValidationError("insertion text requires one point, one ftext, and optional font")
		for child in children:
			if _local_name(child) == "font" and _element_children(child):
				raise CDMLValidationError("insertion text font may not contain element children")
		_translate_point(next(child for child in children if _local_name(child) == "point"), dx, dy)
		return
	if name in ("rect", "square", "oval", "circle"):
		if children:
			raise CDMLValidationError(f"insertion {name} may not contain element children")
		for attribute in ("x1", "y1", "x2", "y2"):
			if not element.hasAttribute(attribute):
				raise CDMLValidationError(f"insertion {name} requires {attribute}")
			offset = dx if attribute.startswith("x") else dy
			element.setAttribute(attribute, _translated_coordinate(element.getAttribute(attribute), offset))
		return
	if name in ("polygon", "polyline"):
		minimum = 3 if name == "polygon" else 2
		if len(children) < minimum or any(
				not _is_cdml_element(child) or _local_name(child) != "point" for child in children
		):
			raise CDMLValidationError(f"insertion {name} requires direct points")
		for point in children:
			_translate_point(point, dx, dy)
		return
	if name == "reaction":
		if any(
			not _is_cdml_element(child)
			or _local_name(child) not in _REACTION_ROLE_NAMES
			or _element_children(child)
			or child.attributes.length != 1
			or not child.hasAttribute("idref")
			or not child.getAttribute("idref")
			for child in children
		):
			raise CDMLValidationError("insertion reaction has unsupported children")
		return
	raise CDMLValidationError(f"unsupported insertion root: {name}")


#============================================
def _validate_insertion_translation(translation: object) -> tuple[float, float]:
	"""Return finite PostScript point offsets from one plain-data request value."""
	if type(translation) is not tuple or len(translation) != 2:
		raise CDMLValidationError("insertion translation requires exactly two numeric values")
	values = []
	for value in translation:
		if type(value) not in (int, float):
			raise CDMLValidationError("insertion translation requires finite plain numeric values")
		try:
			numeric_value = float(value)
		except OverflowError as error:
			raise CDMLValidationError("insertion translation requires finite plain numeric values") from error
		if not math.isfinite(numeric_value):
			raise CDMLValidationError("insertion translation requires finite plain numeric values")
		offset = numeric_value * _POINT_CM_PER_POSTSCRIPT_POINT
		if not math.isfinite(offset):
			raise CDMLValidationError("insertion translation requires finite plain numeric values")
		values.append(offset)
	return values[0], values[1]


#============================================
def _is_insertion_definition(element: object) -> bool:
	"""Return whether one allowlisted-fragment element owns a durable ID."""
	if not _is_cdml_element(element) or _fragment_member_reference(element):
		return False
	parent = element.parentNode
	if parent is not None and _is_cdml_element(parent) and _local_name(parent) == "reaction":
		return False
	name = _local_name(element)
	if parent is not None and _is_cdml_element(parent) and _local_name(parent) == "molecule":
		return name in _MOLECULE_VERTEX_NAMES or name in ("bond", "fragment")
	if parent is not None and _is_cdml_element(parent) and _local_name(parent) == "cdml":
		return name in _TOP_LEVEL_INSERTION_NAMES
	return False


#============================================
def _insertion_references(element: object) -> tuple[str, ...]:
	"""Return the closed-fragment reference fields for one recognized element."""
	parent = element.parentNode
	parent_name = _local_name(parent) if parent is not None else ""
	name = _local_name(element)
	if parent_name == "molecule" and name == "bond":
		return ("start", "end")
	if parent_name == "molecule" and name == "template":
		references = ["atom"]
		for attribute in ("bond_first", "bond_second"):
			if element.hasAttribute(attribute):
				references.append(attribute)
		return tuple(references)
	if _fragment_member_reference(element):
		return ("id",)
	if parent_name == "reaction" and name in _REACTION_ROLE_NAMES:
		return ("idref",)
	return ()


#============================================
def _prepare_top_level_fragment(
		fragment: "CDMLDocument",
		destination_cdml: str,
		consumed_tokens: set[str],
		dx: float,
		dy: float,
		) -> tuple:
	"""Validate, privately tokenise, and translate one detached insertion fragment."""
	roots = _validate_top_level_fragment(fragment)
	bracket_members = oasa.cdml_bracket_pair.valid_bracket_members(
		tuple(roots), _is_cdml_element, _local_name,
	)
	for element in roots:
		_translate_top_level_geometry(element, dx, dy)
	definitions = []
	by_source_id = {}
	for root_element in roots:
		for element in _descendant_elements(root_element):
			if not _is_insertion_definition(element):
				continue
			source_id = element.getAttribute("id")
			if source_id:
				if source_id in by_source_id:
					raise CDMLValidationError(f"duplicate insertion source id: {source_id}")
				by_source_id[source_id] = element
			definitions.append((source_id, element))
	for root_element in roots:
		for element in _descendant_elements(root_element):
			for attribute in _insertion_references(element):
				reference = element.getAttribute(attribute)
				if not reference or reference not in by_source_id:
					raise CDMLValidationError(
						f"insertion {attribute} reference must resolve inside the fragment: {reference}",
					)
	reserved_text = destination_cdml + fragment.serialize()
	reserved_tokens = set(consumed_tokens)
	token_by_source_id = {}
	serial = 1
	for source_id, element in definitions:
		while True:
			token = f"__bkchem_new__insert_{serial}"
			serial += 1
			if token not in reserved_tokens and token not in reserved_text:
				break
		reserved_tokens.add(token)
		if source_id:
			token_by_source_id[source_id] = token
		element.setAttribute("id", token)
	for left, right in bracket_members:
		pair_token = token_by_source_id[left.getAttribute("bracket_pair")]
		left.setAttribute("bracket_pair", pair_token)
		right.setAttribute("bracket_pair", pair_token)
	for root_element in roots:
		for element in _descendant_elements(root_element):
			for attribute in _insertion_references(element):
				reference = element.getAttribute(attribute)
				if reference:
					element.setAttribute(attribute, token_by_source_id[reference])
	return roots


#============================================
def _validate_top_level_fragment(fragment: "CDMLDocument") -> tuple:
	"""Require the shared detached grammar accepted by top-level insertion."""
	root = fragment._dom_document.documentElement
	roots = tuple(_element_children(root))
	if not roots:
		raise CDMLValidationError("top-level insertion fragment requires an element child")
	for element in roots:
		if not _is_cdml_element(element) or _local_name(element) not in _TOP_LEVEL_INSERTION_NAMES:
			raise CDMLValidationError(f"unsupported insertion root: {_local_name(element)}")
	definitions = {}
	for root_element in roots:
		for element in _descendant_elements(root_element):
			if not _is_insertion_definition(element):
				continue
			source_id = element.getAttribute("id")
			if source_id:
				if source_id in definitions:
					raise CDMLValidationError(f"duplicate insertion source id: {source_id}")
				definitions[source_id] = element
	for root_element in roots:
		for element in _descendant_elements(root_element):
			for attribute in _insertion_references(element):
				reference = element.getAttribute(attribute)
				if not reference or reference not in definitions:
					raise CDMLValidationError(
						f"insertion {attribute} reference must resolve inside the fragment: {reference}",
					)
	return roots


#============================================
def _proposal_molecules(proposal: "CDMLDocument") -> tuple:
	"""Return the bounded top-level molecule payload from one proposal document."""
	root = proposal._dom_document.documentElement
	molecules = tuple(_element_children(root))
	if not molecules:
		raise CDMLValidationError("molecule insertion proposal must contain a molecule")
	for element in molecules:
		if not _is_cdml_element(element) or _local_name(element) != "molecule":
			raise CDMLValidationError(
			"molecule insertion proposal may contain only top-level molecules",
		)
		for descendant in _descendant_elements(element):
			if not _is_id_declaration(descendant):
				continue
			identifier = descendant.getAttribute("id")
			if not _is_provisional_id(identifier):
				raise CDMLValidationError(
					"molecule insertion declarations require valid provisional IDs",
				)
	return molecules


#============================================
def _validate_user_template_request(
		request: object,
		) -> tuple[str, tuple[float, float], str | None]:
	"""Validate one immutable saved-template request before XML parsing."""
	if type(request) is not CDMLUserTemplateInsertionRequest:
		raise CDMLUserTemplateInsertionError(
			"user template insertion requires an exact request",
		)
	if type(request.expected_revision) is not int:
		raise CDMLUserTemplateInsertionError(
			"user template insertion expected_revision must be an int",
		)
	if type(request.template_cdml) is not str:
		raise CDMLUserTemplateInsertionError(
			"user template insertion template_cdml must be a string",
		)
	if request.label is not None and type(request.label) is not str:
		raise CDMLUserTemplateInsertionError(
			"user template insertion label must be a string or None",
		)
	try:
		anchor_cm = _validate_insertion_translation(request.anchor)
	except CDMLValidationError as error:
		raise CDMLUserTemplateInsertionError(
			"user template insertion anchor must be two finite non-bool scene points",
		) from error
	return request.template_cdml, anchor_cm, request.label


#============================================
def inspect_user_template(template_cdml: str) -> CDMLUserTemplateInspection:
	"""Inspect one exact saved template without mutating durable backend state.

	The result is intentionally limited to catalog-display data.  It validates
	the same M0 saved-template eligibility grammar used by insertion, but never
	allocates IDs, translates geometry, or touches a session.
	"""
	if type(template_cdml) is not str:
		raise CDMLUserTemplateInsertionError("user template CDML must be a string")
	template = CDMLDocument.parse(template_cdml, validation="compat")
	inspection = _inspect_user_template_document(template)
	return inspection


#============================================
def _user_template_molecule(template: "CDMLDocument") -> object:
	"""Return the sole template molecule while ignoring standard/paper context."""
	root = template._dom_document.documentElement
	molecules = []
	seen_envelopes = set()
	for child in _element_children(root):
		if not _is_cdml_element(child):
			raise CDMLUserTemplateInsertionError(
				"user template has an unsupported direct persistent root",
			)
		name = _local_name(child)
		if name == "molecule":
			molecules.append(child)
		elif name in ("standard", "paper"):
			if name in seen_envelopes:
				raise CDMLUserTemplateInsertionError(
					"user template has repeated %s envelope" % name,
				)
			seen_envelopes.add(name)
		else:
			raise CDMLUserTemplateInsertionError(
				"user template has an unsupported direct persistent root",
			)
	if len(molecules) != 1:
		raise CDMLUserTemplateInsertionError(
			"user template requires exactly one direct molecule",
		)
	molecule = molecules[0]
	if any(
			_is_cdml_element(child) and _local_name(child) == "template"
			for child in _element_children(molecule)
	):
		raise CDMLUserTemplateInsertionError(
			"user template molecule may not contain a legacy template attachment marker",
		)
	return molecule


#============================================
def _user_template_atom_geometry(molecule: object) -> tuple[tuple[object, float, float], ...]:
	"""Return finite direct atom points used for authored-scale centroid placement."""
	atom_points = []
	for child in _element_children(molecule):
		if not _is_cdml_element(child) or _local_name(child) != "atom":
			continue
		points = [
			point for point in _element_children(child)
			if _is_cdml_element(point) and _local_name(point) == "point"
		]
		if len(points) != 1:
			raise CDMLUserTemplateInsertionError(
				"user template atom requires exactly one direct core point",
			)
		try:
			x = _insertion_coordinate(points[0].getAttribute("x"))
			y = _insertion_coordinate(points[0].getAttribute("y"))
		except CDMLValidationError as error:
			raise CDMLUserTemplateInsertionError(
				"user template atom point must have finite x and y coordinates",
			) from error
		atom_points.append((points[0], x, y))
	if not atom_points:
		raise CDMLUserTemplateInsertionError("user template molecule requires one direct atom")
	return tuple(atom_points)


#============================================
def _validate_user_template_geometry(molecule: object) -> None:
	"""Validate every recognized translated coordinate without rewriting it."""
	for vertex in _element_children(molecule):
		if not _is_cdml_element(vertex) or _local_name(vertex) not in _MOLECULE_VERTEX_NAMES:
			continue
		points = [
			point for point in _element_children(vertex)
			if _is_cdml_element(point) and _local_name(point) == "point"
		]
		if len(points) != 1:
			raise CDMLUserTemplateInsertionError(
				"user template vertex requires exactly one direct core point",
			)
		point = points[0]
		try:
			if _element_children(point) or not point.hasAttribute("x") or not point.hasAttribute("y"):
				raise CDMLValidationError("user template vertex has unsupported point geometry")
			_insertion_coordinate(point.getAttribute("x"))
			_insertion_coordinate(point.getAttribute("y"))
			if point.hasAttribute("z"):
				_insertion_coordinate(point.getAttribute("z"))
			for mark in _element_children(vertex):
				if not _is_cdml_element(mark) or _local_name(mark) != "mark":
					continue
				has_x = mark.hasAttribute("x")
				has_y = mark.hasAttribute("y")
				if _element_children(mark) or has_x != has_y:
					raise CDMLValidationError("user template mark has unsupported geometry")
				if has_x:
					_insertion_coordinate(mark.getAttribute("x"))
					_insertion_coordinate(mark.getAttribute("y"))
		except CDMLValidationError as error:
			raise CDMLUserTemplateInsertionError(
				"user template has unsupported recognized coordinate geometry",
			) from error


#============================================
def _validate_user_template_identifiers(template: "CDMLDocument", molecule: object) -> None:
	"""Validate source-local recognized links and literal template ID uniqueness."""
	by_source_id = {}
	for element in _descendant_elements(molecule):
		if not _is_id_declaration(element):
			continue
		source_id = element.getAttribute("id")
		if not source_id:
			continue
		if source_id in by_source_id:
			raise CDMLUserTemplateInsertionError(
				"user template has duplicate recognized source id: %s" % source_id,
			)
		by_source_id[source_id] = element
	for element in _descendant_elements(molecule):
		for attribute in _known_reference_attributes(element):
			reference = element.getAttribute(attribute)
			if not reference or reference not in by_source_id:
				raise CDMLUserTemplateInsertionError(
					"user template %s reference must resolve inside its molecule" % attribute,
				)
	seen_literal_ids = set()
	root = template._dom_document.documentElement
	for element in _descendant_elements(root):
		if not _is_id_definition(element) or not element.hasAttribute("id"):
			continue
		identifier = element.getAttribute("id")
		if not identifier:
			continue
		if identifier in seen_literal_ids:
			raise CDMLUserTemplateInsertionError(
				"user template has duplicate literal id: %s" % identifier,
			)
		seen_literal_ids.add(identifier)


#============================================
def _inspect_user_template_document(template: "CDMLDocument") -> CDMLUserTemplateInspection:
	"""Validate one parsed template and return only immutable catalog facts."""
	molecule = _user_template_molecule(template)
	_user_template_atom_geometry(molecule)
	_validate_user_template_geometry(molecule)
	_validate_user_template_identifiers(template, molecule)
	display_name = molecule.getAttribute("name").strip() or None
	inspection = CDMLUserTemplateInspection(display_name=display_name)
	return inspection


#============================================
def _translate_user_template_geometry(molecule: object, dx: float, dy: float) -> None:
	"""Translate recognized molecule geometry while preserving unknown subtrees."""
	for vertex in _element_children(molecule):
		if not _is_cdml_element(vertex) or _local_name(vertex) not in _MOLECULE_VERTEX_NAMES:
			continue
		points = [
			point for point in _element_children(vertex)
			if _is_cdml_element(point) and _local_name(point) == "point"
		]
		if len(points) != 1:
			raise CDMLUserTemplateInsertionError(
				"user template vertex requires exactly one direct core point",
			)
		try:
			_translate_point(points[0], dx, dy)
			for mark in _element_children(vertex):
				if _is_cdml_element(mark) and _local_name(mark) == "mark":
					_translate_mark(mark, dx, dy)
		except CDMLValidationError as error:
			raise CDMLUserTemplateInsertionError(
				"user template has unsupported recognized coordinate geometry",
			) from error


#============================================
def _prepare_user_template_molecule(
		template: "CDMLDocument", destination_cdml: str, consumed_tokens: set[str],
		anchor_cm: tuple[float, float],
		) -> object:
	"""Return one detached translated molecule with fresh known IDs and references."""
	molecule = _user_template_molecule(template)
	atom_points = _user_template_atom_geometry(molecule)
	centroid_x = math.fsum(point[1] for point in atom_points) / len(atom_points)
	centroid_y = math.fsum(point[2] for point in atom_points) / len(atom_points)
	dx = anchor_cm[0] - centroid_x
	dy = anchor_cm[1] - centroid_y
	_translate_user_template_geometry(molecule, dx, dy)

	definitions = []
	for element in _descendant_elements(molecule):
		if not _is_id_declaration(element):
			continue
		source_id = element.getAttribute("id")
		definitions.append((source_id, element))
	reserved_text = destination_cdml + template.serialize()
	reserved_tokens = set(consumed_tokens)
	token_by_source_id = {}
	serial = 1
	for source_id, element in definitions:
		while True:
			token = "__bkchem_new__user_template_%s" % serial
			serial += 1
			if token not in reserved_tokens and token not in reserved_text:
				break
		reserved_tokens.add(token)
		if source_id:
			token_by_source_id[source_id] = token
		element.setAttribute("id", token)
	for element in _descendant_elements(molecule):
		for attribute in _known_reference_attributes(element):
			element.setAttribute(attribute, token_by_source_id[element.getAttribute(attribute)])
	destination = CDMLDocument.parse(destination_cdml, validation="compat")
	destination_ids = _candidate_durable_ids(destination)
	for element in _descendant_elements(molecule):
		if not _is_id_definition(element) or not element.hasAttribute("id"):
			continue
		identifier = element.getAttribute("id")
		if identifier and identifier in destination_ids:
			raise CDMLUserTemplateInsertionError(
				"user template has an unsafe literal id collision",
			)
	return molecule


#============================================
def _direct_core_child_by_id(parent: object, identifier: str, local_name: str) -> object:
	"""Return one direct editable core child or reject a non-core target."""
	for child in _element_children(parent):
		if (
			_is_cdml_element(child)
			and _local_name(child) == local_name
			and child.getAttribute("id") == identifier
		):
			return child
	raise CDMLValidationError(
		f"structural edit target is not a direct editable {local_name}: {identifier}",
	)


#============================================
def _direct_root_molecule(document: "CDMLDocument", identifier: str) -> object:
	"""Return a direct-root core molecule without traversing opaque wrappers."""
	root = document._dom_document.documentElement
	return _direct_core_child_by_id(root, identifier, "molecule")


#============================================
def _first_direct_core_child(document: "CDMLDocument", local_name: str) -> object | None:
	"""Return the first direct core root of one local name in source order."""
	root = document._dom_document.documentElement
	for child in _element_children(root):
		if _is_cdml_element(child) and _local_name(child) == local_name:
			return child
	return None


#============================================
def _new_paper_defaults(document: "CDMLDocument") -> tuple[str, str]:
	"""Read valid direct standard defaults or return the authored fallback."""
	return oasa.cdml_standard.paper_defaults(document._dom_document.documentElement)


#============================================
def _paper_dimension_text(value: float) -> str:
	"""Return one finite positive paper dimension in stable CDML text."""
	return "%g" % value


#============================================
def _direct_molecule_atom(molecule: object, identifier: str) -> object:
	"""Return one direct atom in the named editable molecule."""
	return _direct_core_child_by_id(molecule, identifier, "atom")


#============================================
def _direct_molecule_bond(molecule: object, identifier: str) -> object:
	"""Return one direct bond in the named editable molecule."""
	return _direct_core_child_by_id(molecule, identifier, "bond")


#============================================
def _require_plain_implicit_group_child(child: object, child_name: str) -> None:
	"""Require one supported group child to contain only whitespace text nodes."""
	for node in child.childNodes:
		if node.nodeType == node.TEXT_NODE:
			if node.data.strip():
				raise CDMLImplicitGroupExpandError(
					"implicit group %s has non-whitespace text" % child_name,
				)
			continue
		if node.nodeType == node.CDATA_SECTION_NODE:
			raise CDMLImplicitGroupExpandError(
				"implicit group %s has CDATA content" % child_name,
			)
		raise CDMLImplicitGroupExpandError(
			"implicit group %s has unsupported child content" % child_name,
		)


#============================================
def _implicit_group_source(
		molecule: object, group: object,
		) -> tuple[str, float, float, object, tuple[float, float], int]:
	"""Validate and return one minimal implicit-group source envelope."""
	allowed_attributes = frozenset(("id", "name", "group-type", "pos"))
	attributes = {
		group.attributes.item(index).name
		for index in range(group.attributes.length)
	}
	if not attributes.issubset(allowed_attributes):
		raise CDMLImplicitGroupExpandError("implicit group has unsupported attributes")
	if group.getAttribute("group-type") != "implicit":
		raise CDMLImplicitGroupExpandError("group must have group-type implicit")
	name = group.getAttribute("name")
	if not name.strip():
		raise CDMLImplicitGroupExpandError("implicit group name is required")
	points = [child for child in _element_children(group)
		if _is_cdml_element(child) and _local_name(child) == "point"]
	fonts = [child for child in _element_children(group)
		if _is_cdml_element(child) and _local_name(child) == "font"]
	if len(points) != 1 or len(fonts) > 1 or len(_element_children(group)) != len(points) + len(fonts):
		raise CDMLImplicitGroupExpandError("implicit group has unsupported child content")
	for child in group.childNodes:
		if child.nodeType == child.TEXT_NODE and child.data.strip():
			raise CDMLImplicitGroupExpandError("implicit group has non-whitespace text")
		if child.nodeType == child.CDATA_SECTION_NODE:
			raise CDMLImplicitGroupExpandError("implicit group has CDATA content")
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE):
			raise CDMLImplicitGroupExpandError("implicit group has preservation-only content")
	point = points[0]
	if point.attributes.length != 2 or not point.hasAttribute("x") or not point.hasAttribute("y"):
		raise CDMLImplicitGroupExpandError("implicit group point must contain only x and y")
	_require_plain_implicit_group_child(point, "point")
	if fonts and any(
		fonts[0].attributes.item(index).name not in ("family", "size", "color")
		for index in range(fonts[0].attributes.length)
	):
		raise CDMLImplicitGroupExpandError("implicit group font has unsupported attributes")
	if fonts:
		_require_plain_implicit_group_child(fonts[0], "font")
	anchor_x = _insertion_coordinate(point.getAttribute("x"))
	anchor_y = _insertion_coordinate(point.getAttribute("y"))
	group_id = group.getAttribute("id")
	incident = [bond for bond in _element_children(molecule)
		if _is_cdml_element(bond) and _local_name(bond) == "bond"
		and group_id in (bond.getAttribute("start"), bond.getAttribute("end"))]
	if len(incident) != 1:
		raise CDMLImplicitGroupExpandError("implicit group requires exactly one exterior bond")
	bond = incident[0]
	if not bond.getAttribute("id"):
		raise CDMLImplicitGroupExpandError("implicit group exterior bond needs an id")
	if bond.hasAttribute("order"):
		raise CDMLImplicitGroupExpandError("implicit group exterior bond has independent order")
	try:
		_bond_type, bond_order = _editable_bond_type(bond.getAttribute("type"))
	except CDMLValidationError as exc:
		raise CDMLImplicitGroupExpandError("implicit group exterior bond type is invalid") from exc
	start = bond.getAttribute("start")
	end = bond.getAttribute("end")
	exterior_id = end if start == group_id else start
	if not exterior_id or exterior_id == group_id:
		raise CDMLImplicitGroupExpandError("implicit group exterior endpoint is invalid")
	exterior = _direct_molecule_atom(molecule, exterior_id)
	exterior_points = [child for child in _element_children(exterior)
		if _is_cdml_element(child) and _local_name(child) == "point"]
	if len(exterior_points) != 1:
		raise CDMLImplicitGroupExpandError("implicit group exterior atom needs one point")
	exterior_point = exterior_points[0]
	exterior_x = _insertion_coordinate(exterior_point.getAttribute("x"))
	exterior_y = _insertion_coordinate(exterior_point.getAttribute("y"))
	return name, anchor_x, anchor_y, bond, (exterior_x, exterior_y), bond_order


#============================================
def _align_group_graph(
		graph: object, replacement: object, anchor_x: float, anchor_y: float,
		direction_x: float, direction_y: float, alignment_neighbor: object,
		) -> None:
	"""Pin detached geometry using a temporary exterior attachment neighbor."""
	neighbor = alignment_neighbor
	origin_x = replacement.x
	origin_y = replacement.y
	local_x = neighbor.x - replacement.x
	local_y = neighbor.y - replacement.y
	local_length = math.hypot(local_x, local_y)
	target_length = math.hypot(direction_x, direction_y)
	if local_length <= 0 or target_length <= 0:
		raise CDMLImplicitGroupExpandError("implicit replacement has invalid local geometry")
	cosine = (local_x * direction_x + local_y * direction_y) / (local_length * target_length)
	sine = (local_x * direction_y - local_y * direction_x) / (local_length * target_length)
	for vertex in graph.vertices:
		x = vertex.x - origin_x
		y = vertex.y - origin_y
		vertex.x = anchor_x + x * cosine - y * sine
		vertex.y = anchor_y + x * sine + y * cosine


#============================================
def _fragment_request_identifiers(value: object, field_name: str) -> tuple[str, ...]:
	"""Require one ordered immutable, duplicate-free durable-ID sequence."""
	if type(value) is not tuple:
		raise CDMLFragmentOperationError(f"fragment {field_name} must be an immutable tuple")
	if any(type(identifier) is not str or not identifier for identifier in value):
		raise CDMLFragmentOperationError(f"fragment {field_name} must contain nonempty IDs")
	if len(set(value)) != len(value):
		raise CDMLFragmentOperationError(f"fragment {field_name} must not contain duplicates")
	return value


#============================================
def _validate_fragment_create_request(
		request: object,
		) -> tuple[str, str, str, tuple[str, ...], tuple[str, ...]]:
	"""Validate the scalar envelope for one ordinary fragment creation."""
	if type(request) is not CDMLFragmentCreateRequest:
		raise CDMLFragmentOperationError("fragment creation requires an exact request")
	if type(request.expected_revision) is not int:
		raise CDMLFragmentOperationError("fragment creation expected_revision must be an int")
	if type(request.molecule_id) is not str or not request.molecule_id:
		raise CDMLFragmentOperationError("fragment creation molecule_id must be a nonempty string")
	if type(request.name) is not str or not request.name.strip():
		raise CDMLFragmentOperationError("fragment creation name must contain non-whitespace")
	if type(request.fragment_type) is not str or request.fragment_type not in ("explicit", "implicit"):
		raise CDMLFragmentOperationError("fragment creation type must be explicit or implicit")
	atom_ids = _fragment_request_identifiers(request.atom_ids, "atom_ids")
	bond_ids = _fragment_request_identifiers(request.bond_ids, "bond_ids")
	if not atom_ids and not bond_ids:
		raise CDMLFragmentOperationError("fragment creation requires one member")
	return request.molecule_id, request.name, request.fragment_type, atom_ids, bond_ids


#============================================
def _validate_linear_form_convert_request(
		request: object,
		) -> tuple[str, tuple[str, ...]]:
	"""Validate the frontend-neutral linear-form conversion envelope."""
	if type(request) is not CDMLLinearFormConvertRequest:
		raise CDMLLinearFormError("linear form conversion requires an exact request")
	if type(request.expected_revision) is not int:
		raise CDMLLinearFormError("linear form conversion expected_revision must be an int")
	if type(request.molecule_id) is not str or not request.molecule_id:
		raise CDMLLinearFormError("linear form conversion molecule_id must be a nonempty string")
	if type(request.atom_ids) is not tuple or not request.atom_ids:
		raise CDMLLinearFormError("linear form conversion atom_ids must be a nonempty tuple")
	if any(type(identifier) is not str or not identifier for identifier in request.atom_ids):
		raise CDMLLinearFormError("linear form conversion atom_ids must be durable nonempty strings")
	if len(set(request.atom_ids)) != len(request.atom_ids):
		raise CDMLLinearFormError("linear form conversion atom_ids must be unique")
	return request.molecule_id, request.atom_ids


#============================================
def _ordinary_fragment_members(fragment: object) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
	"""Read one narrow editable fragment or classify it as preservation-only.

	The compatibility parser deliberately accepts richer historical fragment XML.
	This operation treats only the small grammar it can edit as ordinary metadata;
	every other accepted form stays preserved but is not an operation target.
	"""
	if not _is_cdml_element(fragment) or _local_name(fragment) != "fragment":
		raise CDMLFragmentOperationError("fragment target is not direct core fragment metadata")
	if fragment.getAttribute("type") not in ("explicit", "implicit"):
		raise CDMLFragmentOperationError("fragment target has unsupported type")
	identifier = fragment.getAttribute("id")
	if not identifier:
		raise CDMLFragmentOperationError("fragment target has no durable ID")
	allowed_attributes = {"id", "type"}
	attributes = {
		fragment.attributes.item(index).name
		for index in range(fragment.attributes.length)
	}
	if attributes != allowed_attributes:
		raise CDMLFragmentOperationError("fragment target has unsupported attributes")
	names = []
	atom_ids = []
	bond_ids = []
	for node in fragment.childNodes:
		if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
			if not node.data.strip():
				continue
			raise CDMLFragmentOperationError("fragment target has unsupported text content")
		if node.nodeType != node.ELEMENT_NODE:
			raise CDMLFragmentOperationError("fragment target has unsupported child")
		child = node
		if not _is_cdml_element(child):
			raise CDMLFragmentOperationError("fragment target has unsupported child")
		local_name = _local_name(child)
		if local_name == "name":
			if child.attributes.length or _element_children(child):
				raise CDMLFragmentOperationError("fragment target has unsupported name")
			if any(node.nodeType not in (node.TEXT_NODE, node.CDATA_SECTION_NODE) for node in child.childNodes):
				raise CDMLFragmentOperationError("fragment target has unsupported name")
			names.append("".join(node.data for node in child.childNodes if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE)))
		elif local_name in ("vertex", "bond"):
			attributes = {child.attributes.item(index).name for index in range(child.attributes.length)}
			member_id = child.getAttribute("id")
			if attributes != {"id"} or not member_id or _element_children(child):
				raise CDMLFragmentOperationError("fragment target has unsupported member")
			if any(
				node.nodeType not in (node.TEXT_NODE, node.CDATA_SECTION_NODE)
				or node.data.strip()
				for node in child.childNodes
			):
				raise CDMLFragmentOperationError("fragment target has unsupported member")
			(atom_ids if local_name == "vertex" else bond_ids).append(member_id)
		else:
			raise CDMLFragmentOperationError("fragment target has unsupported child")
	if len(names) != 1 or not names[0].strip():
		raise CDMLFragmentOperationError("fragment target must have one nonblank direct name")
	if len(set(atom_ids)) != len(atom_ids) or len(set(bond_ids)) != len(bond_ids):
		raise CDMLFragmentOperationError("fragment target has duplicate members")
	if not atom_ids and not bond_ids:
		raise CDMLFragmentOperationError("fragment target has no members")
	return identifier, tuple(atom_ids), tuple(bond_ids)


#============================================
def _validate_fragment_members(
		molecule: object, atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> None:
	"""Require every ordinary fragment reference to stay inside one molecule."""
	try:
		for atom_id in atom_ids:
			_direct_molecule_atom(molecule, atom_id)
		for bond_id in bond_ids:
			bond = _direct_molecule_bond(molecule, bond_id)
			start, end = _require_editable_bond_endpoints(molecule, bond)
			if start not in atom_ids or end not in atom_ids:
				raise CDMLFragmentOperationError(
					"fragment bond endpoints must both occur in atom_ids",
				)
	except CDMLFragmentOperationError:
		raise
	except CDMLValidationError as exc:
		raise CDMLFragmentOperationError("fragment member target is invalid") from exc


#============================================
def _validate_structure_delete_request(
		request: object,
		) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
	"""Validate one exact structural-delete envelope before target lookup."""
	if type(request) is not CDMLStructureDeleteRequest:
		raise CDMLValidationError("structure deletion requires an exact deletion request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("structure deletion expected_revision must be an int")
	if type(request.molecule_id) is not str or not request.molecule_id.strip():
		raise CDMLValidationError(
			"structure deletion molecule_id must contain a non-whitespace character",
		)
	if request.label is not None and type(request.label) is not str:
		raise CDMLValidationError("structure deletion label must be a string or None")
	for name, identifiers in (("atom_ids", request.atom_ids), ("bond_ids", request.bond_ids)):
		if (
			type(identifiers) is not tuple
			or any(
				type(identifier) is not str or not identifier.strip()
				for identifier in identifiers
			)
			or len(set(identifiers)) != len(identifiers)
		):
			raise CDMLValidationError(
				"structure deletion %s must be unique durable strings" % name,
			)
	if not request.atom_ids and not request.bond_ids:
		raise CDMLValidationError("structure deletion requires at least one target")
	return request.molecule_id, request.atom_ids, request.bond_ids


#============================================
def _validate_structure_fragment_extraction_query(
		query: object,
		) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
	"""Validate one exact read-only structural clipboard extraction envelope."""
	if type(query) is not CDMLStructureFragmentExtractionQuery:
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction requires an exact extraction query",
		)
	if type(query.expected_revision) is not int:
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction expected_revision must be an int",
		)
	if type(query.molecule_id) is not str or not query.molecule_id.strip():
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction molecule_id must be a durable ID",
		)
	for name, identifiers in (("atom_ids", query.atom_ids), ("bond_ids", query.bond_ids)):
		if (
			type(identifiers) is not tuple
			or any(type(identifier) is not str or not identifier.strip() for identifier in identifiers)
			or len(set(identifiers)) != len(identifiers)
		):
			raise CDMLStructureFragmentExtractionError(
				"structure fragment extraction %s must be unique durable strings" % name,
			)
	if not query.atom_ids and not query.bond_ids:
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction requires at least one target",
		)
	if set(query.atom_ids).intersection(query.bond_ids):
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction atom and bond IDs must be distinct",
		)
	return query.molecule_id, query.atom_ids, query.bond_ids


#============================================
def _validate_top_level_fragment_extraction_query(
		query: object,
		) -> tuple[str, ...]:
	"""Validate one exact read-only direct-root clipboard extraction envelope."""
	if type(query) is not CDMLTopLevelFragmentExtractionQuery:
		raise CDMLTopLevelFragmentExtractionError(
			"top-level fragment extraction requires an exact extraction query",
		)
	if type(query.expected_revision) is not int:
		raise CDMLTopLevelFragmentExtractionError(
			"top-level fragment extraction expected_revision must be an int",
		)
	if (
		type(query.root_ids) is not tuple
		or not query.root_ids
		or any(type(identifier) is not str or not identifier.strip() for identifier in query.root_ids)
		or len(set(query.root_ids)) != len(query.root_ids)
	):
		raise CDMLTopLevelFragmentExtractionError(
			"top-level fragment extraction root_ids must be unique durable strings",
		)
	return query.root_ids


#============================================
def _top_level_fragment_document(selected_roots: tuple[object, ...]) -> "CDMLDocument":
	"""Clone direct roots into a detached document with their namespace context."""
	fragment = CDMLDocument.parse(_EMPTY_CDML, validation="compat")
	root = fragment._dom_document.documentElement
	source_root = selected_roots[0].ownerDocument.documentElement
	for index in range(source_root.attributes.length):
		attribute = source_root.attributes.item(index)
		root.setAttribute(attribute.name, attribute.value)
	for selected_root in selected_roots:
		copy = fragment._dom_document.importNode(selected_root, deep=True)
		root.appendChild(copy)
	return fragment


#============================================
def _top_level_fragment_selection(
		document: "CDMLDocument", root_ids: tuple[str, ...],
		) -> tuple[object, ...]:
	"""Resolve durable direct insertion roots exactly once in source order."""
	root = document._dom_document.documentElement
	eligible_by_id = {}
	for child in _element_children(root):
		if not _is_cdml_element(child) or _local_name(child) not in _TOP_LEVEL_INSERTION_NAMES:
			continue
		identifier = child.getAttribute("id")
		if not identifier:
			continue
		eligible_by_id.setdefault(identifier, []).append(child)
	selected = []
	requested_ids = frozenset(root_ids)
	for identifier in root_ids:
		matches = eligible_by_id.get(identifier, [])
		if len(matches) != 1:
			raise CDMLTopLevelFragmentExtractionError(
				"top-level fragment extraction target is not one supported durable root: %s" % identifier,
			)
	for child in _element_children(root):
		if child.getAttribute("id") in requested_ids:
			if not _is_cdml_element(child) or _local_name(child) not in _TOP_LEVEL_INSERTION_NAMES:
				raise CDMLTopLevelFragmentExtractionError(
					"top-level fragment extraction target is not an insertion root",
				)
			selected.append(child)
	return tuple(selected)


#============================================
def _validate_top_level_fragment_insertion_path(fragment: "CDMLDocument") -> None:
	"""Prove one extracted root fragment enters the existing insertion path."""
	destination = CDMLDocumentSession.load(_EMPTY_CDML)
	destination.insert_top_level(CDMLTopLevelInsertionRequest(
		destination.revision, fragment.serialize(), (0.0, 0.0), "Validate fragment",
	))


#============================================
def _structure_fragment_selection(
		atoms: dict[str, object], bonds: dict[str, object],
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> tuple[tuple[str, ...], tuple[str, ...]]:
	"""Close selected bonds over endpoints and require one selected graph."""
	if any(identifier not in atoms for identifier in atom_ids):
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction atom target is not a direct durable atom",
		)
	if any(identifier not in bonds for identifier in bond_ids):
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction bond target is not a direct durable bond",
		)
	selected_atoms = set(atom_ids)
	selected_bonds = set(bond_ids)
	for identifier in bond_ids:
		bond = bonds[identifier]
		selected_atoms.add(bond.getAttribute("start"))
		selected_atoms.add(bond.getAttribute("end"))
	ordered_atoms = tuple(identifier for identifier in atoms if identifier in selected_atoms)
	ordered_bonds = tuple(identifier for identifier in bonds if identifier in selected_bonds)
	adjacency = {identifier: set() for identifier in ordered_atoms}
	for identifier in ordered_bonds:
		bond = bonds[identifier]
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		adjacency[start].add(end)
		adjacency[end].add(start)
	pending = [ordered_atoms[0]]
	visited = set()
	while pending:
		current = pending.pop()
		if current not in visited:
			visited.add(current)
			pending.extend(adjacency[current] - visited)
	if len(visited) != len(ordered_atoms):
		raise CDMLStructureFragmentExtractionError(
			"structure fragment extraction selection must be connected",
		)
	return ordered_atoms, ordered_bonds


#============================================
def _structure_fragment_document(
		molecule: object, atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> "CDMLDocument":
	"""Create one detached molecule-only clipboard document in source order."""
	fragment = CDMLDocument.parse(_EMPTY_CDML, validation="compat")
	root = fragment._dom_document.documentElement
	source_root = molecule.ownerDocument.documentElement
	for index in range(source_root.attributes.length):
		attribute = source_root.attributes.item(index)
		if attribute.name == "xmlns" or attribute.name.startswith("xmlns:"):
			root.setAttribute(attribute.name, attribute.value)
	copy = fragment._dom_document.importNode(molecule.cloneNode(deep=False), deep=True)
	selected_ids = set(atom_ids) | set(bond_ids)
	for child in _element_children(molecule):
		if child.getAttribute("id") in selected_ids:
			copy.appendChild(fragment._dom_document.importNode(child, deep=True))
	root.appendChild(copy)
	return fragment


#============================================
def _validate_structure_fragment_insertion_path(fragment: "CDMLDocument") -> None:
	"""Prove a returned structural fragment can enter the Paste preparation path.

	Extraction must return the original source-order CDML unchanged.  Run the
	shared insertion preparation only on a fresh detached clone, which exercises
	the exact root, geometry, definition, reference, and complete-document
	commit grammar that Paste uses.
	"""
	destination = CDMLDocumentSession.load(_EMPTY_CDML)
	destination.insert_top_level(CDMLTopLevelInsertionRequest(
		destination.revision, fragment.serialize(), (0.0, 0.0), "Validate fragment",
	))


#============================================
def _structure_delete_direct_nodes(molecule: object) -> tuple[dict[str, object], dict[str, object]]:
	"""Validate the narrow molecule grammar and return direct atoms and bonds."""
	import oasa.cdml_linear_form
	atoms = {}
	bonds = {}
	for child in molecule.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			if child.data.strip():
				raise CDMLValidationError(
					"structure deletion molecule has non-whitespace character data",
				)
			continue
		if child.nodeType == child.ELEMENT_NODE:
			if oasa.cdml_linear_form.is_exact_generated_form(child):
				continue
		if child.nodeType != child.ELEMENT_NODE or not _is_cdml_element(child):
			raise CDMLValidationError("structure deletion molecule has unsupported direct content")
		if _local_name(child) not in ("atom", "bond"):
			raise CDMLValidationError("structure deletion molecule has unsupported direct content")
		identifier = child.getAttribute("id")
		if not identifier.strip():
			raise CDMLValidationError(
				"structure deletion direct molecule child requires a durable id",
			)
		if _local_name(child) == "atom":
			if identifier in atoms:
				raise CDMLValidationError("structure deletion molecule has duplicate direct atom id")
			atoms[identifier] = child
		else:
			if identifier in bonds:
				raise CDMLValidationError("structure deletion molecule has duplicate direct bond id")
			bonds[identifier] = child
	for bond in bonds.values():
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		if not start or not end or start == end or start not in atoms or end not in atoms:
			raise CDMLValidationError("structure deletion bond endpoints must be distinct direct atoms")
	return atoms, bonds


#============================================
def _validate_structure_delete_molecule(molecule: object) -> None:
	"""Require an eligible direct-root molecule without editing opaque child XML."""
	for index in range(molecule.attributes.length):
		attribute = molecule.attributes.item(index)
		if (
			attribute.name in ("id", "name", "xmlns")
			or attribute.name.startswith("xmlns:")
		):
			continue
		raise CDMLValidationError("structure deletion molecule has unsupported attribute")
	if not molecule.getAttribute("id").strip():
		raise CDMLValidationError("structure deletion molecule requires a durable id")


#============================================
def _structure_delete_components(
		atoms: dict[str, object], bonds: dict[str, object],
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]]:
	"""Return canonical removals and surviving graph components in direct source order."""
	selected_atoms = set(atom_ids)
	selected_bonds = set(bond_ids)
	removed_atom_ids = tuple(identifier for identifier in atoms if identifier in selected_atoms)
	removed_bond_ids = tuple(
		identifier for identifier, bond in bonds.items()
		if (
			identifier in selected_bonds
			or bond.getAttribute("start") in selected_atoms
			or bond.getAttribute("end") in selected_atoms
		)
	)
	surviving_atoms = tuple(identifier for identifier in atoms if identifier not in selected_atoms)
	surviving_bonds = tuple(identifier for identifier in bonds if identifier not in removed_bond_ids)
	adjacency = {identifier: set() for identifier in surviving_atoms}
	for identifier in surviving_bonds:
		bond = bonds[identifier]
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		adjacency[start].add(end)
		adjacency[end].add(start)
	components = []
	visited = set()
	for atom_id in surviving_atoms:
		if atom_id in visited:
			continue
		pending = [atom_id]
		component_atoms = set()
		while pending:
			current = pending.pop()
			if current in visited:
				continue
			visited.add(current)
			component_atoms.add(current)
			pending.extend(adjacency[current] - visited)
		ordered_atoms = tuple(identifier for identifier in surviving_atoms if identifier in component_atoms)
		ordered_bonds = tuple(
			identifier for identifier in surviving_bonds
			if bonds[identifier].getAttribute("start") in component_atoms
		)
		components.append((ordered_atoms, ordered_bonds))
	return removed_atom_ids, removed_bond_ids, tuple(components)


#============================================
def _remove_structure_delete_children(
		molecule: object, atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> None:
	"""Remove direct children outside one retained component without reordering it."""
	retained_ids = set(atom_ids) | set(bond_ids)
	for child in tuple(_element_children(molecule)):
		if (
			_is_cdml_element(child) and _local_name(child) in ("atom", "bond")
			and child.getAttribute("id") not in retained_ids
		):
			molecule.removeChild(child)


#============================================
def _structure_delete_component_root(
		candidate: "CDMLDocument", source_molecule: object, molecule_id: str,
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> object:
	"""Build one shallow-cloned component root retaining node-owned descendants."""
	import oasa.cdml_linear_form
	component = source_molecule.cloneNode(deep=False)
	component.setAttribute("id", molecule_id)
	if component.hasAttribute("name"):
		component.removeAttribute("name")
	selected_ids = set(atom_ids) | set(bond_ids)
	for child in _element_children(source_molecule):
		if (
			child.getAttribute("id") in selected_ids
			or oasa.cdml_linear_form.is_exact_generated_form(child)
		):
			component.appendChild(child.cloneNode(deep=True))
	return component


#============================================
def _new_core_element(document: "CDMLDocument", parent: object, local_name: str) -> object:
	"""Create a core element that retains the target document's namespace style."""
	prefix = getattr(parent, "prefix", None)
	namespace_uri = getattr(parent, "namespaceURI", None)
	if namespace_uri == CDML_NAMESPACE_URI:
		qualified_name = f"{prefix}:{local_name}" if prefix else local_name
		return document._dom_document.createElementNS(namespace_uri, qualified_name)
	return document._dom_document.createElement(local_name)


#============================================
def _point_text(position: tuple[float, float]) -> tuple[str, str]:
	"""Convert a validated scene point to the established CDML centimeter text."""
	x, y = position
	return (
		"%.3fcm" % (x * _POINT_CM_PER_POSTSCRIPT_POINT),
		"%.3fcm" % (y * _POINT_CM_PER_POSTSCRIPT_POINT),
	)


#============================================
def _append_atom(
		document: "CDMLDocument", molecule: object, identifier: str,
		element: str, position: tuple[float, float],
		) -> object:
	"""Append one direct atom and its point in the established CDML grammar."""
	atom = _new_core_element(document, molecule, "atom")
	atom.setAttribute("id", identifier)
	atom.setAttribute("name", element)
	point = _new_core_element(document, atom, "point")
	x_text, y_text = _point_text(position)
	point.setAttribute("x", x_text)
	point.setAttribute("y", y_text)
	atom.appendChild(point)
	molecule.appendChild(atom)
	return atom


#============================================
def _append_bond(
		document: "CDMLDocument", molecule: object, identifier: str,
		start: str, end: str, bond_type: str, bond_order: int,
		simple_double: bool,
		) -> object:
	"""Append one direct bond with selected Draw-mode semantics."""
	bond = _new_core_element(document, molecule, "bond")
	bond.setAttribute("id", identifier)
	bond.setAttribute("start", start)
	bond.setAttribute("end", end)
	bond.setAttribute("type", f"{bond_type}{bond_order}")
	_apply_simple_double_policy(bond, bond_type, bond_order, simple_double)
	molecule.appendChild(bond)
	return bond


#============================================
def _apply_simple_double_policy(
		bond: object, bond_type: str, bond_order: int, simple_double: bool,
		) -> None:
	"""Write the selected added-lane style where the CDML grammar uses it."""
	styled_triple = bond_type in ("a", "d", "o") and bond_order == 3
	if bond_order == 2 or styled_triple:
		bond.setAttribute("simple_double", str(int(simple_double)))
	elif bond.hasAttribute("simple_double"):
		bond.removeAttribute("simple_double")


#============================================
def _finite_bond_attribute(bond: object, name: str, default: float) -> float:
	"""Read one finite numeric depiction field before a bond-tool transition."""
	if not bond.hasAttribute(name):
		return default
	try:
		value = float(bond.getAttribute(name))
	except ValueError as error:
		raise CDMLValidationError(f"bond {name} is not numeric") from error
	if not math.isfinite(value):
		raise CDMLValidationError(f"bond {name} is not finite")
	return value


#============================================
def _bond_centered(bond: object) -> bool:
	"""Return the established CDML interpretation of a centered double bond."""
	return bond.getAttribute("center") == "yes"


#============================================
def _set_bond_number(bond: object, name: str, value: float) -> None:
	"""Store a finite depiction value without changing unrelated attributes."""
	if not math.isfinite(value):
		raise CDMLValidationError(f"bond {name} transition is not finite")
	bond.setAttribute(name, "%g" % value)


#============================================
def _apply_bond_tool_transition(
		bond: object, bond_type: str, bond_order: int, simple_double: bool,
		) -> None:
	"""Apply the established Draw-mode type/order/depiction transition in CDML."""
	current_type, current_order, _legacy = oasa.bond_semantics.parse_cdml_bond_type(
		bond.getAttribute("type"),
	)
	if current_type not in oasa.bond_semantics.BOND_TYPES or current_order < 1:
		raise CDMLValidationError("bond has unsupported current type or order")
	if bond_type != current_type:
		bond.setAttribute("type", f"{bond_type}{bond_order}")
	elif bond_order == 1 and bond_type in ("n", "d"):
		bond.setAttribute("type", f"{bond_type}{(current_order % 3) + 1}")
	elif bond_order != current_order:
		bond.setAttribute("type", f"{bond_type}{bond_order}")
	else:
		if bond_type in ("w", "h"):
			start = bond.getAttribute("start")
			bond.setAttribute("start", bond.getAttribute("end"))
			bond.setAttribute("end", start)
		elif bond_order == 2:
			bond_width = _finite_bond_attribute(bond, "bond_width", 6.0)
			auto_sign = _finite_bond_attribute(bond, "auto_sign", 1.0)
			if _bond_centered(bond):
				_set_bond_number(bond, "bond_width", -bond_width)
				_set_bond_number(bond, "auto_sign", -auto_sign)
				bond.setAttribute("center", "no")
			elif bond_width > 0:
				_set_bond_number(bond, "bond_width", -bond_width)
				_set_bond_number(bond, "auto_sign", -auto_sign)
			else:
				bond.setAttribute("center", "yes")
	updated_type, updated_order, _legacy = oasa.bond_semantics.parse_cdml_bond_type(
		bond.getAttribute("type"),
	)
	_apply_simple_double_policy(bond, updated_type or "n", updated_order, simple_double)


#============================================
def _required_structural_identifier(value: object, name: str) -> str:
	"""Return one plain durable identifier or raise a stable validation error."""
	if not isinstance(value, str) or not value:
		raise CDMLValidationError(f"structural edit {name} must be a nonempty string")
	return value


#============================================
def _required_structural_position(value: object, name: str) -> tuple[float, float]:
	"""Return one finite scene point expressed as a two-value plain tuple."""
	if type(value) is not tuple or len(value) != 2:
		raise CDMLValidationError(f"structural edit {name} must be a two-value tuple")
	coordinates = []
	for coordinate in value:
		if type(coordinate) not in (int, float) or not math.isfinite(coordinate):
			raise CDMLValidationError(
				f"structural edit {name} must contain finite plain numeric values",
			)
		coordinates.append(float(coordinate))
	return coordinates[0], coordinates[1]


#============================================
def _required_structural_element(value: object) -> str:
	"""Return an OASA-supported atom symbol for a created atom."""
	if not isinstance(value, str) or value not in oasa.periodic_table.periodic_table:
		raise CDMLValidationError("structural edit element must be a supported atom symbol")
	return value


#============================================
def _required_structural_bond_settings(request: CDMLStructuralEditRequest) -> tuple[str, int, bool]:
	"""Validate the selected Draw-mode bond settings without frontend coupling."""
	if request.bond_type not in oasa.bond_semantics.BOND_TYPES:
		raise CDMLValidationError("structural edit bond_type is unsupported")
	if type(request.bond_order) is not int:
		raise CDMLValidationError("structural edit bond_order must be an int")
	if not oasa.bond_semantics.is_authored_bond_order(request.bond_type, request.bond_order):
		raise CDMLValidationError("structural edit bond_type/order is unsupported")
	if type(request.simple_double) is not bool:
		raise CDMLValidationError("structural edit simple_double must be a bool")
	return request.bond_type, request.bond_order, request.simple_double


#============================================
def _validate_structural_request(request: object) -> tuple:
	"""Validate one exact structural grammar production before candidate mutation."""
	if not isinstance(request, CDMLStructuralEditRequest):
		raise CDMLValidationError("structural edit requires a structural edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("structural edit expected_revision must be an int")
	bond_type, bond_order, simple_double = _required_structural_bond_settings(request)
	if request.kind == "create-bonded-pair":
		if any(value is not None for value in (
				request.molecule_id, request.source_atom_id, request.target_atom_id, request.bond_id,
		)):
			raise CDMLValidationError("create-bonded-pair accepts no existing durable IDs")
		return (
			request.kind,
			_required_structural_position(request.source_position, "source_position"),
			_required_structural_position(request.target_position, "target_position"),
			_required_structural_element(request.element),
			bond_type,
			bond_order,
			simple_double,
		)
	if request.kind == "extend-atom":
		if any(value is not None for value in (
				request.target_atom_id, request.bond_id, request.source_position,
		)):
			raise CDMLValidationError("extend-atom accepts one source atom and endpoint only")
		return (
			request.kind,
			_required_structural_identifier(request.molecule_id, "molecule_id"),
			_required_structural_identifier(request.source_atom_id, "source_atom_id"),
			_required_structural_position(request.target_position, "target_position"),
			_required_structural_element(request.element),
			bond_type,
			bond_order,
			simple_double,
		)
	if request.kind == "join-atoms":
		if any(value is not None for value in (
				request.bond_id, request.source_position, request.target_position, request.element,
		)):
			raise CDMLValidationError("join-atoms accepts two existing atoms and bond settings only")
		return (
			request.kind,
			_required_structural_identifier(request.molecule_id, "molecule_id"),
			_required_structural_identifier(request.source_atom_id, "source_atom_id"),
			_required_structural_identifier(request.target_atom_id, "target_atom_id"),
			bond_type,
			bond_order,
			simple_double,
		)
	if request.kind == "apply-bond-tool":
		if any(value is not None for value in (
				request.source_atom_id, request.target_atom_id, request.source_position,
				request.target_position, request.element,
		)):
			raise CDMLValidationError("apply-bond-tool accepts one existing bond and settings only")
		return (
			request.kind,
			_required_structural_identifier(request.molecule_id, "molecule_id"),
			_required_structural_identifier(request.bond_id, "bond_id"),
			bond_type,
			bond_order,
			simple_double,
		)
	raise CDMLValidationError(f"unsupported structural edit kind: {request.kind}")


#============================================
def _validate_atom_element_request(request: object) -> tuple[str, str, str]:
	"""Validate one plain atom-element substitution request before mutation."""
	if not isinstance(request, CDMLAtomElementEditRequest):
		raise CDMLValidationError("atom element edit requires an atom element edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom element edit expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLValidationError("atom element edit molecule_id must be a nonempty string")
	if not isinstance(request.atom_id, str) or not request.atom_id:
		raise CDMLValidationError("atom element edit atom_id must be a nonempty string")
	if not isinstance(request.element, str) or request.element not in oasa.periodic_table.periodic_table:
		raise CDMLValidationError("atom element edit element must be a supported atom symbol")
	return request.molecule_id, request.atom_id, request.element


#============================================
def _validate_atom_properties_patch(
		request: object,
		) -> tuple[str, str, tuple[tuple[str, object], ...]]:
	"""Validate explicit atom intent before resolving or changing a target."""
	if type(request) is not CDMLAtomPropertiesPatch:
		raise CDMLAtomPropertiesPatchError("atom properties requires an atom properties patch")
	if type(request.expected_revision) is not int:
		raise CDMLAtomPropertiesPatchError("atom properties expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("atom_id", request.atom_id)):
		if not isinstance(value, str) or not value:
			raise CDMLAtomPropertiesPatchError(
				"atom properties %s must be a nonempty string" % name,
			)
	if type(request.changes) is not tuple:
		raise CDMLAtomPropertiesPatchError("atom properties changes must be an immutable tuple")
	validated = []
	seen = set()
	fields = (
		"element", "charge", "valency", "isotope", "multiplicity", "show",
		"show_hydrogens", "font_size", "line_color",
	)
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLAtomPropertiesPatchError("atom properties changes must be field/value pairs")
		field_name, value = change
		if type(field_name) is not str or field_name not in fields:
			raise CDMLAtomPropertiesPatchError(
				"atom properties field must be a supported string",
			)
		if field_name in seen:
			raise CDMLAtomPropertiesPatchError("atom properties fields must be unique")
		seen.add(field_name)
		if field_name == "element":
			if type(value) is not str or value not in oasa.periodic_table.periodic_table:
				raise CDMLAtomPropertiesPatchError(
					"atom properties element must be a supported atom symbol",
				)
		elif field_name == "charge":
			if type(value) is not int or not -9 <= value <= 9:
				raise CDMLAtomPropertiesPatchError("atom properties charge must be an int from -9 to 9")
		elif field_name == "valency":
			if type(value) is not int or not 0 <= value <= 10:
				raise CDMLAtomPropertiesPatchError("atom properties valency must be an int from 0 to 10")
		elif field_name == "isotope":
			if value is not None and (type(value) is not int or not 1 <= value <= 300):
				raise CDMLAtomPropertiesPatchError(
					"atom properties isotope must be null or an int from 1 to 300",
				)
		elif field_name == "multiplicity":
			if type(value) is not int or value not in (1, 2, 3):
				raise CDMLAtomPropertiesPatchError(
					"atom properties multiplicity must be an int from 1 to 3",
				)
		elif field_name in ("show", "show_hydrogens"):
			if type(value) is not bool:
				raise CDMLAtomPropertiesPatchError("atom properties %s must be a bool" % field_name)
		elif field_name == "font_size":
			if type(value) is not int or not 4 <= value <= 72:
				raise CDMLAtomPropertiesPatchError(
					"atom properties font_size must be an int from 4 to 72",
				)
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLAtomPropertiesPatchError(
					"atom properties line_color must be a six-digit hex color",
				)
			value = value.lower()
		validated.append((field_name, value))
	return request.molecule_id, request.atom_id, tuple(validated)


#============================================
def _validate_text_properties_patch(
		request: object,
		) -> tuple[str, tuple[tuple[str, object], ...]]:
	"""Validate one immutable plain Text intent before authoritative lookup."""
	if type(request) is not CDMLTextPropertiesPatch:
		raise CDMLTextPropertiesPatchError("Text properties requires an exact patch")
	if type(request.expected_revision) is not int:
		raise CDMLTextPropertiesPatchError("Text expected_revision must be an int")
	if type(request.text_id) is not str or not request.text_id.strip():
		raise CDMLTextPropertiesPatchError("Text text_id must be nonblank")
	if type(request.changes) is not tuple:
		raise CDMLTextPropertiesPatchError("Text changes must be an immutable tuple")
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLTextPropertiesPatchError("Text changes must be field/value pairs")
		field_name, value = change
		if type(field_name) is not str or field_name not in (
				"text", "font_family", "font_size", "font_color", "background_color",
			):
			raise CDMLTextPropertiesPatchError("Text properties field is unsupported")
		if field_name in seen:
			raise CDMLTextPropertiesPatchError("Text properties fields must be unique")
		seen.add(field_name)
		if field_name in ("text", "font_family"):
			if type(value) is not str or not value.strip():
				raise CDMLTextPropertiesPatchError(f"Text {field_name} must be nonblank")
			if field_name == "font_family":
				value = value.strip()
		elif field_name == "font_size":
			if type(value) is not int or not 4 <= value <= 144:
				raise CDMLTextPropertiesPatchError("Text font_size must be 4 through 144")
		elif field_name == "background_color" and value is None:
			pass
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLTextPropertiesPatchError("Text colors require six hex digits")
			value = value.lower()
		validated.append((field_name, value))
	return request.text_id, tuple(validated)


#============================================
def _validate_rich_text_patch(
		request: object,
		) -> tuple[str, tuple[oasa.cdml_ftext.CDMLFTextRun, ...], tuple[tuple[str, object], ...]]:
	"""Validate immutable rich Text intent before authoritative lookup."""
	if type(request) is not CDMLRichTextPatch:
		raise CDMLRichTextPatchError("rich Text requires an exact rich Text patch")
	if type(request.expected_revision) is not int:
		raise CDMLRichTextPatchError("rich Text expected_revision must be an int")
	if type(request.text_id) is not str or not request.text_id.strip():
		raise CDMLRichTextPatchError(
			"rich Text text_id must contain a non-whitespace character",
		)
	try:
		runs = oasa.cdml_ftext.normalize(request.runs)
	except oasa.cdml_ftext.CDMLFTextCodecError as error:
		raise CDMLRichTextPatchError("rich Text runs are invalid: %s" % error) from error
	if not any(run.text.strip() for run in runs):
		raise CDMLRichTextPatchError("rich Text requires nonblank rendered content")
	if type(request.changes) is not tuple:
		raise CDMLRichTextPatchError("rich Text changes must be an immutable tuple")
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLRichTextPatchError("rich Text changes must contain field/value pairs")
		field_name, value = change
		if type(field_name) is not str or field_name not in (
				"font_family", "font_size", "font_color",
			):
			raise CDMLRichTextPatchError("rich Text change field is unsupported")
		if field_name in seen:
			raise CDMLRichTextPatchError("rich Text changes must not repeat a field")
		seen.add(field_name)
		if field_name == "font_family":
			if type(value) is not str or not value.strip():
				raise CDMLRichTextPatchError("rich Text font_family must be nonblank")
			value = value.strip()
		elif field_name == "font_size":
			if type(value) is not int or not 4 <= value <= 144:
				raise CDMLRichTextPatchError(
					"rich Text font_size must be an int from 4 to 144",
				)
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLRichTextPatchError(
					"rich Text font_color must be a six-digit hex color",
				)
			value = value.lower()
		validated.append((field_name, value))
	return request.text_id, runs, tuple(validated)


#============================================
def _direct_root_text(document: "CDMLDocument", identifier: str) -> object:
	"""Return one direct-root core Text without traversing opaque wrappers."""
	root = document._dom_document.documentElement
	for child in _element_children(root):
		if (
			_is_cdml_element(child)
			and _local_name(child) == "text"
			and child.getAttribute("id") == identifier
		):
			return child
	raise CDMLTextPropertiesPatchError(
		"Text properties target is not a direct editable Text: %s" % identifier,
	)


#============================================
def _direct_root_rich_text(document: "CDMLDocument", identifier: str) -> object:
	"""Return one direct-root core Text for the rich-text operation."""
	root = document._dom_document.documentElement
	matches = []
	for child in _element_children(root):
		if (
			_is_cdml_element(child)
			and _local_name(child) == "text"
			and child.getAttribute("id") == identifier
		):
			matches.append(child)
	if len(matches) == 1:
		return matches[0]
	if len(matches) > 1:
		raise CDMLRichTextPatchError(
			"rich Text target has an ambiguous direct durable ID: %s" % identifier,
		)
	raise CDMLRichTextPatchError(
		"rich Text target is not a direct editable Text: %s" % identifier,
	)


#============================================
def _editable_text_children(text: object) -> tuple[object | None, object]:
	"""Require the established direct-root Text grammar and return font/ftext."""
	points = []
	fonts = []
	ftexts = []
	for child in text.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			if child.data.strip():
				raise CDMLTextPropertiesPatchError(
					"Text properties target has non-whitespace direct character data",
				)
			continue
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE):
			continue
		if child.nodeType != child.ELEMENT_NODE:
			raise CDMLTextPropertiesPatchError(
				"Text properties target has unsupported direct content",
			)
		# Namespace-owned extension children remain opaque preservation content.
		if not _is_cdml_element(child):
			continue
		child_name = _local_name(child)
		if child_name == "point":
			points.append(child)
		elif child_name == "font":
			fonts.append(child)
		elif child_name == "ftext":
			ftexts.append(child)
		else:
			raise CDMLTextPropertiesPatchError(
				"Text properties target has unsupported direct core content",
			)
	if len(points) != 1:
		raise CDMLTextPropertiesPatchError(
			"Text properties target requires exactly one direct core point",
		)
	if len(fonts) > 1:
		raise CDMLTextPropertiesPatchError(
			"Text properties target has multiple direct core fonts",
		)
	if len(ftexts) != 1:
		raise CDMLTextPropertiesPatchError(
			"Text properties target requires exactly one direct core ftext",
		)
	if fonts and _element_children(fonts[0]):
		raise CDMLTextPropertiesPatchError(
			"Text properties target font may not contain element children",
		)
	if _element_children(ftexts[0]):
		raise CDMLTextPropertiesPatchError(
			"Text properties does not support rich ftext element children",
		)
	ftext_character_data = "".join(
		child.data for child in ftexts[0].childNodes
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE)
	)
	if _SUPPORTED_FTEXT_MARKUP_PATTERN.search(ftext_character_data) is not None:
		raise CDMLTextPropertiesPatchError(
			"Text properties does not support escaped rich ftext markup",
		)
	font = fonts[0] if fonts else None
	return font, ftexts[0]


#============================================
def _editable_rich_text_children(text: object) -> tuple[object | None, object]:
	"""Require the M1 direct-root grammar and return its simple font and ftext."""
	points = []
	fonts = []
	ftexts = []
	for child in text.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			if child.data.strip():
				raise CDMLRichTextPatchError(
					"rich Text target has non-whitespace direct character data",
				)
			continue
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE):
			continue
		if child.nodeType != child.ELEMENT_NODE:
			raise CDMLRichTextPatchError("rich Text target has unsupported direct content")
		if not _is_cdml_element(child):
			continue
		child_name = _local_name(child)
		if child_name == "point":
			points.append(child)
		elif child_name == "font":
			fonts.append(child)
		elif child_name == "ftext":
			ftexts.append(child)
		else:
			raise CDMLRichTextPatchError("rich Text target has unsupported direct core content")
	if len(points) != 1:
		raise CDMLRichTextPatchError("rich Text target requires exactly one direct core point")
	if len(fonts) > 1:
		raise CDMLRichTextPatchError("rich Text target has multiple direct core fonts")
	if len(ftexts) != 1:
		raise CDMLRichTextPatchError("rich Text target requires exactly one direct core ftext")
	if fonts:
		for child in fonts[0].childNodes:
			if child.nodeType not in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
				raise CDMLRichTextPatchError("rich Text target font must be simple")
			if child.data.strip():
				raise CDMLRichTextPatchError(
					"rich Text target font must not contain character data",
				)
	ftext = ftexts[0]
	if ftext.attributes.length:
		raise CDMLRichTextPatchError("rich Text target ftext must not have attributes")
	if any(
		child.nodeType not in (child.TEXT_NODE, child.CDATA_SECTION_NODE)
		for child in ftext.childNodes
	):
		raise CDMLRichTextPatchError(
			"rich Text target ftext must contain only character data",
		)
	font = fonts[0] if fonts else None
	return font, ftext


#============================================
def _validate_plus_properties_patch(
		request: object,
		) -> tuple[str, tuple[tuple[str, object], ...]]:
	"""Validate one immutable plain Plus intent before authoritative lookup."""
	if type(request) is not CDMLPlusPropertiesPatch:
		raise CDMLPlusPropertiesPatchError("Plus properties requires an exact patch")
	if type(request.expected_revision) is not int:
		raise CDMLPlusPropertiesPatchError("Plus expected_revision must be an int")
	if type(request.plus_id) is not str or not request.plus_id.strip():
		raise CDMLPlusPropertiesPatchError("Plus plus_id must be nonblank")
	if type(request.changes) is not tuple:
		raise CDMLPlusPropertiesPatchError("Plus changes must be an immutable tuple")
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLPlusPropertiesPatchError("Plus changes must be field/value pairs")
		field_name, value = change
		if type(field_name) is not str or field_name not in (
			"font_family", "font_size", "color", "background_color",
		):
			raise CDMLPlusPropertiesPatchError("Plus properties field is unsupported")
		if field_name in seen:
			raise CDMLPlusPropertiesPatchError("Plus properties fields must be unique")
		seen.add(field_name)
		if field_name == "font_family":
			if type(value) is not str or not value.strip():
				raise CDMLPlusPropertiesPatchError("Plus font_family must be nonblank")
			value = value.strip()
		elif field_name == "font_size":
			if type(value) is not int or not 4 <= value <= 144:
				raise CDMLPlusPropertiesPatchError("Plus font_size must be 4 through 144")
		elif field_name == "background_color" and value is None:
			pass
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLPlusPropertiesPatchError(
					"Plus properties colors must use six hexadecimal digits",
				)
			value = value.lower()
		validated.append((field_name, value))
	return request.plus_id, tuple(validated)


#============================================
def _direct_root_plus(document: "CDMLDocument", identifier: str) -> object:
	"""Return one unique direct-root core Plus without opaque traversal."""
	root = document._dom_document.documentElement
	matches = tuple(
		child for child in _element_children(root)
		if child.getAttribute("id") == identifier
	)
	if (
		len(matches) != 1 or not _is_cdml_element(matches[0])
		or _local_name(matches[0]) != "plus"
	):
		raise CDMLPlusPropertiesPatchError(
			"Plus properties target is not one unique direct editable Plus: %s" % identifier,
		)
	return matches[0]


#============================================
def _editable_plus_children(plus: object) -> object | None:
	"""Require the narrow direct-root Plus grammar and return its optional font."""
	points = []
	fonts = []
	for child in plus.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			if child.data.strip():
				raise CDMLPlusPropertiesPatchError(
					"Plus properties target has non-whitespace direct character data",
				)
			continue
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE):
			continue
		if child.nodeType != child.ELEMENT_NODE:
			raise CDMLPlusPropertiesPatchError("Plus target has unsupported direct content")
		# Namespace-owned extension children remain opaque preservation content.
		if not _is_cdml_element(child):
			continue
		child_name = _local_name(child)
		if child_name == "point":
			points.append(child)
		elif child_name == "font":
			fonts.append(child)
		else:
			raise CDMLPlusPropertiesPatchError("Plus target has unsupported core content")
	if len(points) != 1:
		raise CDMLPlusPropertiesPatchError("Plus target requires one direct core point")
	if len(fonts) > 1:
		raise CDMLPlusPropertiesPatchError("Plus target has multiple direct core fonts")
	return fonts[0] if fonts else None


#============================================
def _optional_background_color(
		element: object, error_type: type[CDMLValidationError], description: str,
		) -> str | None:
	"""Return compatible optional root background semantics."""
	if not element.hasAttribute("background-color") or not element.getAttribute("background-color"):
		return None
	value = element.getAttribute("background-color")
	if re.fullmatch(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?", value) is None:
		raise error_type(f"{description} background color must be hexadecimal")
	digits = value[1:]
	if len(digits) == 3:
		digits = "".join(character * 2 for character in digits)
	return "#" + digits.lower()


#============================================
def _plus_property_values(
		plus: object, font: object | None,
		) -> tuple[str | None, int, str, str | None]:
	"""Return authored family plus semantic root size, foreground, and background."""
	font_family = None
	if font is not None and font.hasAttribute("family"):
		font_family = font.getAttribute("family").strip() or None
	font_size = 14
	if plus.hasAttribute("font_size"):
		font_size_text = plus.getAttribute("font_size")
		if re.fullmatch(r"[0-9]+", font_size_text) is None:
			raise CDMLPlusPropertiesPatchError(
				"Plus properties target font_size must be an integer",
			)
		font_size = int(font_size_text)
		if not 4 <= font_size <= 144:
			raise CDMLPlusPropertiesPatchError(
				"Plus properties target font_size must be from 4 to 144",
			)
	color = "#000000"
	if plus.hasAttribute("color"):
		color = plus.getAttribute("color")
		if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
			raise CDMLPlusPropertiesPatchError(
				"Plus properties target color must be a six-digit hex color",
			)
		color = color.lower()
	background_color = _optional_background_color(plus, CDMLPlusPropertiesPatchError, "Plus target")
	return font_family, font_size, color, background_color


#============================================
def _validate_wavy_properties_patch(
		request: object,
		) -> tuple[str, tuple[tuple[str, object], ...]]:
	"""Validate one immutable Wavy root-property intent before lookup."""
	if type(request) is not CDMLWavyPropertiesPatch:
		raise CDMLWavyPropertiesPatchError("Wavy properties requires an exact patch")
	if type(request.expected_revision) is not int:
		raise CDMLWavyPropertiesPatchError("Wavy expected_revision must be an int")
	if type(request.wavy_id) is not str or not request.wavy_id.strip():
		raise CDMLWavyPropertiesPatchError("Wavy wavy_id must be nonblank")
	if type(request.changes) is not tuple:
		raise CDMLWavyPropertiesPatchError("Wavy changes must be an immutable tuple")
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLWavyPropertiesPatchError("Wavy changes must be field/value pairs")
		field_name, value = change
		if type(field_name) is not str or field_name not in ("width", "line_color"):
			raise CDMLWavyPropertiesPatchError("Wavy field must be width or line_color")
		if field_name in seen:
			raise CDMLWavyPropertiesPatchError("Wavy properties fields must be unique")
		seen.add(field_name)
		if field_name == "width":
			if (
				type(value) is bool or not isinstance(value, numbers.Real)
				or not math.isfinite(value) or not 0.1 <= value <= 20
			):
				raise CDMLWavyPropertiesPatchError("Wavy width must be finite from 0.1 to 20")
			value = float(value)
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLWavyPropertiesPatchError("Wavy line_color must be six-digit hex")
			value = value.lower()
		validated.append((field_name, value))
	return request.wavy_id, tuple(validated)


#============================================
def _direct_root_wavy(document: "CDMLDocument", identifier: str) -> object:
	"""Return one unique direct-root core polyline whose style is exactly Wavy."""
	root = document._dom_document.documentElement
	matches = tuple(
		child for child in _element_children(root)
		if child.getAttribute("id") == identifier
	)
	if (
		len(matches) != 1 or not _is_cdml_element(matches[0])
		or _local_name(matches[0]) != "polyline"
		or matches[0].getAttribute("style") != "wavy"
	):
		raise CDMLWavyPropertiesPatchError(
			"Wavy properties target is not one unique direct editable Wavy: %s" % identifier,
		)
	return matches[0]


#============================================
def _wavy_property_values(wavy: object) -> tuple[float, str]:
	"""Validate Wavy geometry and return visible root width and color semantics."""
	points = []
	for child in wavy.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			if child.data.strip():
				raise CDMLWavyPropertiesPatchError(
					"Wavy properties target has non-whitespace direct character data",
				)
			continue
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE):
			continue
		if child.nodeType != child.ELEMENT_NODE:
			raise CDMLWavyPropertiesPatchError(
				"Wavy properties target has unsupported direct content",
			)
		# Namespace-owned extension children and their complete subtrees are opaque.
		if not _is_cdml_element(child):
			continue
		if _local_name(child) != "point":
			raise CDMLWavyPropertiesPatchError(
				"Wavy properties target has unsupported direct core content",
			)
		points.append(child)
	if len(points) < 2:
		raise CDMLWavyPropertiesPatchError(
			"Wavy properties target requires at least two direct core points",
		)
	for point in points:
		for child in point.childNodes:
			if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
				if child.data.strip():
					raise CDMLWavyPropertiesPatchError(
						"Wavy properties target point has non-whitespace character data",
					)
				continue
			if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE):
				continue
			if child.nodeType == child.ELEMENT_NODE:
				raise CDMLWavyPropertiesPatchError(
					"Wavy properties target point has element children",
				)
			raise CDMLWavyPropertiesPatchError(
				"Wavy properties target point has unsupported content",
			)
		try:
			_top_level_transform_point_pair(point)
		except CDMLTopLevelTransformError as error:
			raise CDMLWavyPropertiesPatchError(
				"Wavy properties target has malformed core point geometry",
			) from error
	width = 1.0
	if wavy.hasAttribute("width"):
		try:
			width = float(wavy.getAttribute("width"))
		except ValueError as error:
			raise CDMLWavyPropertiesPatchError(
				"Wavy properties target width must be a finite number",
			) from error
		if not math.isfinite(width) or not 0.1 <= width <= 20:
			raise CDMLWavyPropertiesPatchError(
				"Wavy properties target width must be a finite number from 0.1 to 20",
			)
	color = wavy.getAttribute("line_color") if wavy.hasAttribute("line_color") else (
		wavy.getAttribute("color") if wavy.hasAttribute("color") else "#000000"
	)
	if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
		raise CDMLWavyPropertiesPatchError(
			"Wavy properties target color must be a six-digit hex color",
		)
	return width, color.lower()


#============================================
def _validate_atom_mark_request(request: object) -> tuple[str, str, str, str, int | None]:
	"""Validate one immutable atom-mark operation before detached mutation."""
	if type(request) is not CDMLAtomMarkOperationRequest:
		raise CDMLAtomMarkOperationError("atom mark operation requires an exact request")
	if type(request.expected_revision) is not int:
		raise CDMLAtomMarkOperationError("atom mark expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("atom_id", request.atom_id)):
		if type(value) is not str or not value:
			raise CDMLAtomMarkOperationError("atom mark %s must be a nonempty string" % name)
	if type(request.action) is not str or request.action not in ("add", "remove"):
		raise CDMLAtomMarkOperationError("atom mark action must be add or remove")
	if type(request.mark_type) is not str or request.mark_type not in _ATOM_MARK_TYPES:
		raise CDMLAtomMarkOperationError("atom mark type is unsupported")
	matching_mark_index = request.matching_mark_index
	if request.action == "add" and matching_mark_index is not None:
		raise CDMLAtomMarkOperationError("atom mark add does not accept a matching mark index")
	if matching_mark_index is not None and (
			type(matching_mark_index) is not int or matching_mark_index < 0
		):
		raise CDMLAtomMarkOperationError(
			"atom mark matching mark index must be a nonnegative int",
		)
	return (
		request.molecule_id, request.atom_id, request.action, request.mark_type,
		matching_mark_index,
	)


#============================================
def _atom_mark_scalar_value(atom: object, attribute: str, default: int) -> int:
	"""Read one atom scalar required for a mark delta without normalizing it."""
	if not atom.hasAttribute(attribute):
		return default
	value_text = atom.getAttribute(attribute)
	try:
		value = int(value_text)
	except ValueError as error:
		raise CDMLAtomMarkOperationError(
			"atom mark target has an invalid %s value" % attribute,
		) from error
	if str(value) != value_text:
		raise CDMLAtomMarkOperationError(
			"atom mark target has an invalid %s value" % attribute,
		)
	return value


#============================================
def _atom_mark_geometry(atom: object) -> tuple[float, float]:
	"""Read one unambiguous direct atom point for authored mark geometry."""
	points = [
		child for child in _element_children(atom)
		if _is_cdml_element(child) and _local_name(child) == "point"
	]
	if len(points) != 1:
		raise CDMLAtomMarkOperationError("atom mark target requires one direct core point")
	point = points[0]
	if _element_children(point) or not point.hasAttribute("x") or not point.hasAttribute("y"):
		raise CDMLAtomMarkOperationError("atom mark target point has unsupported geometry")
	try:
		x = _insertion_coordinate(point.getAttribute("x"))
		y = _insertion_coordinate(point.getAttribute("y"))
		if point.hasAttribute("z"):
			_insertion_coordinate(point.getAttribute("z"))
	except CDMLValidationError as error:
		raise CDMLAtomMarkOperationError("atom mark target point has unsupported geometry") from error
	return x, y


#============================================
def _authored_atom_mark_attributes(atom: object, mark_type: str) -> dict[str, str]:
	"""Return authoritative, portable attributes for one newly authored mark."""
	x_cm, y_cm = _atom_mark_geometry(atom)
	angle_degrees = {
		"plus": 45.0, "minus": 45.0, "radical": 90.0, "biradical": 90.0,
		"electronpair": 180.0, "dotted_electronpair": 180.0,
	}.get(mark_type)
	if angle_degrees is None:
		x_text = _canonical_authored_coordinate(x_cm)
		y_text = _canonical_authored_coordinate(y_cm)
	else:
		offset_cm = 12.0 * _POINT_CM_PER_POSTSCRIPT_POINT
		angle_radians = math.radians(angle_degrees)
		x_text = _canonical_authored_coordinate(x_cm + offset_cm * math.cos(angle_radians))
		y_text = _canonical_authored_coordinate(y_cm + offset_cm * math.sin(angle_radians))
	attributes = {
		"type": mark_type,
		"x": x_text,
		"y": y_text,
		"auto": "0",
		"size": "40" if mark_type == "pz_orbital" else (
			"4" if mark_type in ("radical", "biradical", "dotted_electronpair") else "10"
		),
	}
	if mark_type in ("plus", "minus"):
		attributes["draw_circle"] = "yes"
	if mark_type == "electronpair":
		attributes["line_width"] = "2"
	return attributes


#============================================
def _first_direct_atom_mark(atom: object, mark_type: str) -> object | None:
	"""Return the first matching direct core mark in persistent child order."""
	for child in _element_children(atom):
		if (
			_is_cdml_element(child)
			and _local_name(child) == "mark"
			and child.getAttribute("type") == mark_type
		):
			return child
	return None


#============================================
def _direct_atom_marks(atom: object, mark_type: str) -> tuple[object, ...]:
	"""Return matching direct core marks in persistent child order."""
	return tuple(
		child for child in _element_children(atom)
		if (
			_is_cdml_element(child)
			and _local_name(child) == "mark"
			and child.getAttribute("type") == mark_type
		)
	)


#============================================
def _apply_atom_mark_scalar_delta(atom: object, mark_type: str, action: str) -> None:
	"""Apply one delta after validating only its addressed scalar state."""
	delta_spec = _ATOM_MARK_SCALAR_DELTAS.get(mark_type)
	if delta_spec is None:
		return
	attribute, delta = delta_spec
	default = 0 if attribute == "charge" else 1
	minimum, maximum = (-9, 9) if attribute == "charge" else (1, 3)
	current_value = _atom_mark_scalar_value(atom, attribute, default)
	if not minimum <= current_value <= maximum:
		raise CDMLAtomMarkOperationError(
			"atom mark %s must already be from %s to %s" % (
				attribute, minimum, maximum,
			),
		)
	if action == "remove":
		delta = -delta
	value = current_value + delta
	if not minimum <= value <= maximum:
		raise CDMLAtomMarkOperationError(
			"atom mark %s result must be from %s to %s" % (attribute, minimum, maximum),
		)
	if value == default:
		atom.removeAttribute(attribute)
	else:
		atom.setAttribute(attribute, str(value))


#============================================
def _validate_atom_translate_request(
		request: object,
		) -> tuple[tuple[tuple[str, str], ...], tuple[float, float]]:
	"""Validate one immutable direct-atom translation before candidate mutation."""
	if type(request) is not CDMLAtomTranslateRequest:
		raise CDMLValidationError("atom translation requires an atom translation request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom translation expected_revision must be an int")
	if not isinstance(request.targets, tuple) or not request.targets:
		raise CDMLValidationError("atom translation targets must be a nonempty immutable tuple")
	if any(
			not isinstance(target, tuple) or len(target) != 2
			or any(not isinstance(identifier, str) or not identifier for identifier in target)
			for target in request.targets
		):
		raise CDMLValidationError("atom translation targets must contain nonempty ID pairs")
	if len(set(request.targets)) != len(request.targets):
		raise CDMLValidationError("atom translation targets must be unique")
	delta_cm = _validate_insertion_translation(request.delta)
	return request.targets, delta_cm


#============================================
def _validate_selection_translate_request(
		request: object,
		) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...], tuple[float, float]]:
	"""Validate one immutable mixed selection request before document lookup."""
	if type(request) is not CDMLSelectionTranslateRequest:
		raise CDMLSelectionTranslateError("selection translation requires an exact request")
	if type(request.expected_revision) is not int:
		raise CDMLSelectionTranslateError("selection translation expected_revision must be an int")
	if type(request.atom_targets) is not tuple or not request.atom_targets:
		raise CDMLSelectionTranslateError(
			"selection translation atom_targets must be nonempty immutable tuple",
		)
	if type(request.presentation_root_ids) is not tuple or not request.presentation_root_ids:
		raise CDMLSelectionTranslateError(
			"selection translation presentation_root_ids must be nonempty immutable tuple",
		)
	if any(
			type(target) is not tuple or len(target) != 2
			or any(type(identifier) is not str or not identifier for identifier in target)
			for target in request.atom_targets
		):
		raise CDMLSelectionTranslateError(
			"selection translation atom_targets must contain nonempty ID pairs",
		)
	if any(
			type(identifier) is not str or not identifier
			for identifier in request.presentation_root_ids
		):
		raise CDMLSelectionTranslateError(
			"selection translation presentation_root_ids must contain nonempty strings",
		)
	if len(set(request.atom_targets)) != len(request.atom_targets):
		raise CDMLSelectionTranslateError("selection translation atom_targets must be unique")
	if len(set(request.presentation_root_ids)) != len(request.presentation_root_ids):
		raise CDMLSelectionTranslateError(
			"selection translation presentation_root_ids must be unique",
		)
	atom_identifiers = {
		identifier
		for target in request.atom_targets
		for identifier in target
	}
	if atom_identifiers.intersection(request.presentation_root_ids):
		raise CDMLSelectionTranslateError(
			"selection translation atom and presentation IDs must be unambiguous",
		)
	try:
		delta_cm = _validate_insertion_translation(request.delta)
	except CDMLValidationError as error:
		raise CDMLSelectionTranslateError(
			"selection translation delta must be two finite non-bool point values",
		) from error
	return request.atom_targets, request.presentation_root_ids, delta_cm


#============================================
def _atom_translation_point(
		atom: object, *, error_type: type[CDMLValidationError],
		) -> tuple[object, float, float]:
	"""Return one validated direct atom point without normalizing its spelling."""
	atom_points = [
		child for child in _element_children(atom)
		if _is_cdml_element(child) and _local_name(child) == "point"
	]
	if len(atom_points) != 1:
		raise error_type("atom translation atom requires one direct core point")
	point = atom_points[0]
	if not point.hasAttribute("x") or not point.hasAttribute("y"):
		raise error_type("atom translation point requires x and y")
	try:
		x = _insertion_coordinate(point.getAttribute("x"))
		y = _insertion_coordinate(point.getAttribute("y"))
	except CDMLValidationError as error:
		raise error_type("atom translation point has invalid geometry") from error
	return point, x, y


#============================================
def _atom_translation_result(
		x: float, y: float, dx_cm: float, dy_cm: float,
		*, error_type: type[CDMLValidationError], canonical_noop: bool,
		) -> tuple[str | None, str | None]:
	"""Return translated axes while retaining unchanged authored spelling."""
	x_coordinate = x + dx_cm
	y_coordinate = y + dy_cm
	if not math.isfinite(x_coordinate) or not math.isfinite(y_coordinate):
		raise error_type("atom translation coordinate is nonfinite")
	if canonical_noop:
		new_x = _canonical_authored_coordinate(x_coordinate)
		new_y = _canonical_authored_coordinate(y_coordinate)
		return (
			new_x if _canonical_authored_coordinate(x) != new_x else None,
			new_y if _canonical_authored_coordinate(y) != new_y else None,
		)
	return (
		f"{x_coordinate:.3f}cm" if dx_cm != 0.0 else None,
		f"{y_coordinate:.3f}cm" if dy_cm != 0.0 else None,
	)


#============================================
@dataclasses.dataclass(frozen=True)
class _SelectionTranslateCoordinate:
	"""One validated coordinate pair and its prospective canonical mutation."""

	element: object
	new_x: str | None
	new_y: str | None


@dataclasses.dataclass(frozen=True)
class _SelectionTranslateAtomGeometry:
	"""One atom point plus every explicit direct core mark coordinate pair."""

	coordinates: tuple[_SelectionTranslateCoordinate, ...]


#============================================
def _selection_translate_atom_geometry(
		atom: object, dx_cm: float, dy_cm: float,
		) -> _SelectionTranslateAtomGeometry:
	"""Validate one atom and its explicit direct mark geometry for translation."""
	point, x, y = _atom_translation_point(atom, error_type=CDMLSelectionTranslateError)
	coordinates = [
		_SelectionTranslateCoordinate(
			point,
			*_atom_translation_result(
				x, y, dx_cm, dy_cm,
				error_type=CDMLSelectionTranslateError, canonical_noop=True,
			),
		),
	]
	for mark in _element_children(atom):
		if not _is_cdml_element(mark) or _local_name(mark) != "mark":
			continue
		has_x = mark.hasAttribute("x")
		has_y = mark.hasAttribute("y")
		if has_x != has_y:
			raise CDMLSelectionTranslateError(
				"selection translation direct atom mark requires x and y together",
			)
		if not has_x:
			continue
		try:
			mark_x = _insertion_coordinate(mark.getAttribute("x"))
			mark_y = _insertion_coordinate(mark.getAttribute("y"))
		except CDMLValidationError as error:
			raise CDMLSelectionTranslateError(
				"selection translation direct atom mark has invalid geometry",
			) from error
		coordinates.append(
			_SelectionTranslateCoordinate(
				mark,
				*_atom_translation_result(
					mark_x, mark_y, dx_cm, dy_cm,
					error_type=CDMLSelectionTranslateError, canonical_noop=True,
				),
			),
		)
	return _SelectionTranslateAtomGeometry(tuple(coordinates))


#============================================
def _apply_selection_translate_atom_geometry(
		geometry: _SelectionTranslateAtomGeometry,
		) -> None:
	"""Apply one already-validated atom/mark coordinate mutation to a candidate."""
	for coordinate in geometry.coordinates:
		if coordinate.new_x is not None:
			coordinate.element.setAttribute("x", coordinate.new_x)
		if coordinate.new_y is not None:
			coordinate.element.setAttribute("y", coordinate.new_y)


#============================================
def _validate_atom_rotate_request(
		request: object,
		) -> tuple[tuple[tuple[str, str], ...], tuple[float, float], float]:
	"""Validate one immutable direct-atom rotation before candidate mutation."""
	if type(request) is not CDMLAtomRotateRequest:
		raise CDMLValidationError("atom rotation requires an atom rotation request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom rotation expected_revision must be an int")
	if type(request.targets) is not tuple or not request.targets:
		raise CDMLValidationError("atom rotation targets must be a nonempty immutable tuple")
	if any(
			type(target) is not tuple or len(target) != 2
			or any(type(identifier) is not str or not identifier for identifier in target)
			for target in request.targets
		):
		raise CDMLValidationError("atom rotation targets must contain nonempty ID pairs")
	if len(set(request.targets)) != len(request.targets):
		raise CDMLValidationError("atom rotation targets must be unique")
	center_cm = _validate_insertion_translation(request.center)
	if type(request.angle_radians) not in (int, float):
		raise CDMLValidationError("atom rotation angle must be a finite plain numeric value")
	try:
		angle = float(request.angle_radians)
	except OverflowError as error:
		raise CDMLValidationError("atom rotation angle must be a finite plain numeric value") from error
	if not math.isfinite(angle):
		raise CDMLValidationError("atom rotation angle must be a finite plain numeric value")
	return request.targets, center_cm, angle


#============================================
def _validate_bond_order_edit_request(request: object) -> tuple[str, str, int]:
	"""Validate one exact direct-core bond-order request before mutation."""
	if type(request) is not CDMLBondOrderEditRequest:
		raise CDMLValidationError("bond order edit requires a bond order edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("bond order edit expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("bond_id", request.bond_id)):
		if not isinstance(value, str) or not value:
			raise CDMLValidationError("bond order edit %s must be a nonempty string" % name)
	if type(request.order) is not int or request.order not in (1, 2, 3):
		raise CDMLValidationError("bond order edit order must be 1, 2, or 3")
	return request.molecule_id, request.bond_id, request.order


#============================================
def _validate_bond_type_edit_request(request: object) -> tuple[str, str, str]:
	"""Validate one exact direct-core ordinary bond-type request."""
	if type(request) is not CDMLBondTypeEditRequest:
		raise CDMLValidationError("bond type edit requires a bond type edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("bond type edit expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("bond_id", request.bond_id)):
		if not isinstance(value, str) or not value:
			raise CDMLValidationError("bond type edit %s must be a nonempty string" % name)
	if request.bond_type not in ("n", "w", "h", "a", "b", "d", "o", "s"):
		raise CDMLValidationError("bond type edit requested type must be an ordinary type character")
	return request.molecule_id, request.bond_id, request.bond_type


#============================================
def _bond_patch_number(value: object, field_name: str, minimum: float, maximum: float) -> float:
	"""Validate one finite authored depiction number within its CDML range."""
	if type(value) not in (int, float) or not math.isfinite(value):
		raise CDMLBondPropertiesPatchError(
			"bond properties %s must be a finite number" % field_name,
		)
	number = float(value)
	if not minimum <= number <= maximum:
		raise CDMLBondPropertiesPatchError(
			"bond properties %s is outside its supported range" % field_name,
		)
	return number


#============================================
def _bond_patch_color(value: object) -> str:
	"""Validate and normalize one frontend-neutral six-digit CDML color."""
	if not isinstance(value, str) or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
		raise CDMLBondPropertiesPatchError(
			"bond properties color must be a six-digit hex color",
		)
	return value.lower()


#============================================
def _validate_bond_properties_patch(
		request: object,
		) -> tuple[str, str, tuple[tuple[str, object], ...]]:
	"""Validate immutable explicit intent before reading or mutating a target."""
	if type(request) is not CDMLBondPropertiesPatch:
		raise CDMLBondPropertiesPatchError(
			"bond properties requires a bond properties patch",
		)
	if type(request.expected_revision) is not int:
		raise CDMLBondPropertiesPatchError(
			"bond properties expected_revision must be an int",
		)
	for name, value in (("molecule_id", request.molecule_id), ("bond_id", request.bond_id)):
		if not isinstance(value, str) or not value:
			raise CDMLBondPropertiesPatchError(
				"bond properties %s must be a nonempty string" % name,
			)
	if type(request.changes) is not tuple:
		raise CDMLBondPropertiesPatchError("bond properties changes must be an immutable tuple")
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLBondPropertiesPatchError("bond properties changes must be field/value pairs")
		field_name, value = change
		if not isinstance(field_name, str) or field_name not in (
				"order", "type", "center", "line_width", "bond_width",
				"wedge_width", "color",
				):
			raise CDMLBondPropertiesPatchError(
				"bond properties field must be a supported string",
			)
		if field_name in seen:
			raise CDMLBondPropertiesPatchError("bond properties fields must be unique")
		seen.add(field_name)
		if field_name == "order":
			if type(value) is not int or value not in (1, 2, 3):
				raise CDMLBondPropertiesPatchError("bond properties order must be 1, 2, or 3")
		elif field_name == "type":
			if type(value) is not str or value not in ("n", "w", "h", "a", "b", "d", "o", "s"):
				raise CDMLBondPropertiesPatchError(
					"bond properties type must be an ordinary type character",
				)
		elif field_name == "center":
			if type(value) is not bool:
				raise CDMLBondPropertiesPatchError("bond properties center must be a bool")
		elif field_name == "line_width":
			value = _bond_patch_number(value, field_name, 0.1, 20.0)
		elif field_name in ("bond_width", "wedge_width"):
			value = _bond_patch_number(value, field_name, 0.1, 40.0)
		elif field_name == "color":
			value = _bond_patch_color(value)
		validated.append((field_name, value))
	return request.molecule_id, request.bond_id, tuple(validated)


#============================================
def _editable_bond_type(value: str) -> tuple[str, int]:
	"""Return an exact supported CDML bond spelling for the order-edit boundary."""
	if not isinstance(value, str) or len(value) != 2:
		raise CDMLValidationError("bond order edit target has no supported bond type")
	type_char, order_text = value
	if type_char not in oasa.bond_semantics.BOND_TYPES or order_text not in ("1", "2", "3"):
		raise CDMLValidationError("bond order edit target has an ambiguous bond type")
	order = int(order_text)
	if not oasa.bond_semantics.is_authored_bond_order(type_char, order):
		raise CDMLValidationError("bond order edit target has an unsupported bond type/order")
	return type_char, order


#============================================
def _editable_bond_type_for_type_edit(value: str) -> tuple[str, int]:
	"""Return the exact current spelling accepted by the type-edit boundary."""
	if not isinstance(value, str) or len(value) != 2:
		raise CDMLValidationError("bond type edit target has no supported bond type")
	type_char, order_text = value
	if order_text not in ("1", "2", "3"):
		raise CDMLValidationError("bond type edit target has an ambiguous bond type")
	order = int(order_text)
	if type_char in ("l", "r"):
		if order != 1:
			raise CDMLValidationError("bond type edit target has an unsupported bond type/order")
		return type_char, order
	if type_char == "q":
		if order != 1:
			raise CDMLValidationError("bond type edit target has an unsupported bond type/order")
		return type_char, order
	if type_char not in ("n", "w", "h", "a", "b", "d", "o", "s"):
		raise CDMLValidationError("bond type edit target has an ambiguous bond type")
	if not oasa.bond_semantics.is_authored_bond_order(type_char, order):
		raise CDMLValidationError("bond type edit target has an unsupported bond type/order")
	return type_char, order


#============================================
def _validate_atom_number_request(
		request: object,
		) -> tuple[str, str, int | None, bool | None]:
	"""Validate one plain direct-atom number request before candidate work."""
	if type(request) is not CDMLAtomNumberEditRequest:
		raise CDMLValidationError("atom number edit requires an atom number edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom number edit expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLValidationError("atom number edit molecule_id must be a nonempty string")
	if not isinstance(request.atom_id, str) or not request.atom_id:
		raise CDMLValidationError("atom number edit atom_id must be a nonempty string")
	if request.number is None and request.show_number is None:
		return request.molecule_id, request.atom_id, None, None
	if type(request.number) is not int or request.number <= 0 or type(request.show_number) is not bool:
		raise CDMLValidationError(
			"atom number edit requires a positive integer number and boolean visibility",
		)
	return request.molecule_id, request.atom_id, request.number, request.show_number


#============================================
def _validate_molecule_smiles_query(request: object) -> str:
	"""Validate one exact immutable molecule-SMILES query grammar."""
	if type(request) is not CDMLMoleculeSmilesQuery:
		raise CDMLValidationError("molecule SMILES query requires a molecule SMILES query")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("molecule SMILES query expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLValidationError("molecule SMILES query molecule_id must be a nonempty string")
	return request.molecule_id


#============================================
def _validate_molecule_name_request(request: object) -> tuple[str, str]:
	"""Validate one exact direct-root molecule display-name request."""
	if type(request) is not CDMLMoleculeNameEditRequest:
		raise CDMLMoleculeNameEditError("molecule name edit requires a molecule name edit request")
	if type(request.expected_revision) is not int:
		raise CDMLMoleculeNameEditError("molecule name edit expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLMoleculeNameEditError("molecule name edit molecule_id must be a nonempty string")
	if not isinstance(request.name, str):
		raise CDMLMoleculeNameEditError("molecule name edit name must be a string")
	return request.molecule_id, request.name


#============================================
def _validate_paper_properties_patch(request: object) -> dict[str, object]:
	"""Validate one explicit-field paper patch before candidate mutation."""
	if type(request) is not CDMLPaperPropertiesPatch:
		raise CDMLPaperPropertiesError(
			"paper properties require a paper properties patch request",
		)
	if type(request.expected_revision) is not int:
		raise CDMLPaperPropertiesError(
			"paper properties expected_revision must be an int",
		)
	if type(request.changes) is not tuple:
		raise CDMLPaperPropertiesError("paper properties changes must be a tuple")
	changes = {}
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLPaperPropertiesError(
				"paper properties changes must contain exact field/value pairs",
			)
		name, value = change
		if type(name) is not str or name not in _CDML_PAPER_PROPERTY_FIELDS:
			raise CDMLPaperPropertiesError("paper properties field is unsupported")
		if name in changes:
			raise CDMLPaperPropertiesError(
				f"paper properties field is repeated: {name}",
			)
		changes[name] = value
	if "type" in changes:
		paper_type = changes["type"]
		if type(paper_type) is not str or paper_type not in oasa.cdml_standard.PAPER_SIZES_MM:
			raise CDMLPaperPropertiesError("paper properties type is unsupported")
	if "orientation" in changes:
		orientation = changes["orientation"]
		if type(orientation) is not str or orientation not in ("portrait", "landscape"):
			raise CDMLPaperPropertiesError(
				"paper properties orientation must be portrait or landscape",
			)
	for name in ("crop_svg", "use_real_minus", "replace_minus"):
		if name in changes and type(changes[name]) is not bool:
			raise CDMLPaperPropertiesError(
				f"paper properties {name} must be a bool",
			)
	if "crop_margin" in changes:
		margin = changes["crop_margin"]
		if type(margin) is not int or margin < 0:
			raise CDMLPaperPropertiesError(
				"paper properties crop_margin must be a nonnegative int",
			)
	if "dimensions" in changes:
		dimensions = changes["dimensions"]
		if type(dimensions) is not tuple or len(dimensions) != 2:
			raise CDMLPaperPropertiesError(
				"paper properties dimensions must be an exact two-value tuple",
			)
		for dimension in dimensions:
			if type(dimension) not in (int, float) or not math.isfinite(dimension) or dimension <= 0:
				raise CDMLPaperPropertiesError(
					"paper properties dimensions must be finite positive plain numbers",
				)
		changes["dimensions"] = (float(dimensions[0]), float(dimensions[1]))
	if changes.get("type") == "custom" and "dimensions" not in changes:
		raise CDMLPaperPropertiesError(
			"paper properties custom type requires dimensions",
		)
	if "type" in changes and changes["type"] != "custom" and "dimensions" in changes:
		raise CDMLPaperPropertiesError(
			"paper properties dimensions apply only to custom paper",
		)
	return changes


#============================================
def _candidate_durable_ids(candidate: "CDMLDocument") -> set[str]:
	"""Return every current durable identifier, including opaque reservations."""
	used_ids = set()
	for element in _descendant_elements(candidate._dom_document.documentElement):
		if not _is_id_definition(element):
			continue
		identifier = element.getAttribute("id")
		if identifier:
			used_ids.add(identifier)
	return used_ids


#============================================
def _molecule_atom_ids(molecule: object) -> set[str]:
	"""Return direct editable atom IDs in one direct-root molecule."""
	return {
		atom.getAttribute("id")
		for atom in _element_children(molecule)
		if _is_cdml_element(atom) and _local_name(atom) == "atom" and atom.getAttribute("id")
	}


#============================================
def _require_editable_bond_endpoints(molecule: object, bond: object) -> tuple[str, str]:
	"""Require a direct bond to connect two direct atoms in the same molecule."""
	start = bond.getAttribute("start")
	end = bond.getAttribute("end")
	atom_ids = _molecule_atom_ids(molecule)
	if not start or not end or start == end or start not in atom_ids or end not in atom_ids:
		raise CDMLValidationError("structural edit bond has invalid direct-molecule endpoints")
	return start, end


#============================================
def _has_direct_bond(molecule: object, first_atom_id: str, second_atom_id: str) -> bool:
	"""Return whether a direct editable molecule already has the undirected edge."""
	requested = frozenset((first_atom_id, second_atom_id))
	for bond in _element_children(molecule):
		if not _is_cdml_element(bond) or _local_name(bond) != "bond":
			continue
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		if frozenset((start, end)) != requested:
			continue
		if start in _molecule_atom_ids(molecule) and end in _molecule_atom_ids(molecule):
			return True
	return False

def _projection_plan(document: "CDMLDocument", revision: int) -> CDMLProjectionPlan:
	"""Collect synchronized facts from one backend DOM revision."""
	presentation = _presentation_description(document, revision)
	paper = _paper_layout(document, revision)
	fragments = _fragment_metadata(document, revision)
	marks = _atom_mark_observation(document, revision)
	groups = _group_observation(document, revision)
	molecule_core = _molecule_core_observation(document, revision)
	molecule_render = _molecule_render_observation(document, revision)
	presentation_by_position = {record.source_position: record for record in presentation.records}
	presentation_issues = {issue.source_position: issue for issue in presentation.issues}
	molecules_by_position = {record.source_position: record for record in molecule_core.records}
	roots = []
	root = document._dom_document.documentElement
	for source_position, element in enumerate(_element_children(root), 1):
		tag = _local_name(element)
		identifier = element.getAttribute("id") or None
		record = presentation_by_position.get(source_position)
		issue = presentation_issues.get(source_position)
		molecule = molecules_by_position.get(source_position)
		if record is not None:
			roots.append(CDMLProjectionRoot(source_position, tag, identifier, record.disposition, record.reason))
		elif molecule is not None:
			roots.append(CDMLProjectionRoot(source_position, tag, identifier, "editable" if molecule.addressable else "display-only", molecule.reason))
		elif tag in {"paper", "viewport", "info", "metadata", "standard"}:
			roots.append(CDMLProjectionRoot(source_position, tag, identifier, "header", None))
		else:
			reason = issue.reason if issue is not None else "direct root is not projected"
			roots.append(CDMLProjectionRoot(source_position, tag, identifier, "display-only", reason))
	plan = CDMLProjectionPlan(
		revision, tuple(roots), presentation, paper, fragments, marks, groups,
		molecule_core, molecule_render,
	)
	return plan
class CDMLDocument:
	"""A complete, DOM-backed CDML document with ordered opaque preservation."""

	#============================================
	def __init__(self, dom_document: object) -> None:
		"""Store a validated detached XML DOM owned solely by this document."""
		self._dom_document = dom_document

	#============================================
	@classmethod
	def parse(cls, text: str, *, validation: str = "compat") -> "CDMLDocument":
		"""Parse complete CDML text and optionally apply strict backend checks."""
		try:
			source = text.encode("utf-8")
			dom_document = oasa.cdml_xml.parse_cdml_dom(source)
		except (UnicodeError, oasa.cdml_xml.CDMLXMLParseError) as error:
			raise CDMLParseError(f"CDML XML parse failed: {error}") from error
		root = dom_document.documentElement
		if root is None or not _is_cdml_element(root) or _local_name(root) != "cdml":
			raise CDMLParseError("CDML root element must be <cdml>")
		document = cls(dom_document)
		if validation == "strict":
			document.validate(validation="strict")
		elif validation != "compat":
			raise CDMLValidationError(f"unknown CDML validation mode: {validation}")
		return document

	#============================================
	@classmethod
	def projection_snapshot(cls, snapshot: CDMLSnapshot) -> CDMLProjectionSnapshot:
		"""Derive one complete projection envelope from an immutable snapshot."""
		if type(snapshot) is not CDMLSnapshot:
			raise CDMLValidationError("projection snapshot requires an exact backend snapshot")
		document = cls.parse(snapshot.cdml, validation="compat")
		plan = _projection_plan(document, snapshot.revision)
		return CDMLProjectionSnapshot(snapshot, plan)

	#============================================
	def serialize(self, *, mode: str = "preserve") -> str:
		"""Return backend-owned complete CDML without ID allocation or reordering."""
		if mode != "preserve":
			raise CDMLValidationError(f"unknown CDML serialization mode: {mode}")
		text = self._dom_document.toxml(encoding="utf-8").decode("utf-8")
		return text

	#============================================
	def presentation_description(self, revision: int) -> CDMLPresentationDescription:
		"""Return direct-root presentation facts tagged with one plain revision."""
		if type(revision) is not int:
			raise CDMLPresentationDescriptionError("presentation revision must be an int")
		return _presentation_description(self, revision)

	#============================================
	def paper_layout(self, revision: int) -> CDMLPaperLayout:
		"""Return direct-core paper facts tagged with one plain revision."""
		if type(revision) is not int:
			raise CDMLPaperLayoutError("paper layout revision must be an int")
		return _paper_layout(self, revision)

	#============================================
	def fragment_metadata(self, revision: int) -> CDMLFragmentMetadata:
		"""Return direct-molecule fragment facts tagged with one plain revision."""
		if type(revision) is not int:
			raise CDMLFragmentMetadataError("fragment metadata revision must be an int")
		return _fragment_metadata(self, revision)

	#============================================
	def atom_mark_observation(self, revision: int) -> CDMLAtomMarkObservation:
		"""Return normalized direct atom-mark facts tagged with one revision."""
		if type(revision) is not int:
			raise CDMLAtomMarkObservationError("atom-mark observation revision must be an int")
		return _atom_mark_observation(self, revision)

	#============================================
	def group_observation(self, revision: int) -> CDMLGroupObservation:
		"""Return normalized direct-group facts tagged with one revision."""
		if type(revision) is not int:
			raise CDMLGroupObservationError("group observation revision must be an int")
		return _group_observation(self, revision)

	#============================================
	def molecule_core_observation(self, revision: int) -> CDMLMoleculeCoreObservation:
		"""Return direct molecule, atom, and bond facts for one revision."""
		if type(revision) is not int:
			raise CDMLMoleculeCoreObservationError("molecule-core observation revision must be an int")
		return _molecule_core_observation(self, revision)

	#============================================
	def molecule_render_observation(self, revision: int) -> CDMLMoleculeRenderObservation:
		"""Return complete portable molecule paint batches for one revision."""
		if type(revision) is not int:
			raise CDMLMoleculeRenderObservationError("molecule render observation revision must be an int")
		return _molecule_render_observation(self, revision)

	#============================================
	def atom_chemistry_facts(
			self, revision: int,
			) -> CDMLAtomChemistryFactsObservation:
		"""Return complete direct-graph chemistry facts for one revision."""
		if type(revision) is not int:
			raise CDMLAtomChemistryFactsError("atom chemistry facts revision must be an int")
		return _atom_chemistry_facts_observation(self, revision)

	#============================================
	def objects(self) -> tuple[CDMLObjectRecord, ...]:
		"""Return direct document-child records in document order.

		The ``position`` and ``path`` metadata use full-document preorder so they
		remain comparable with the broader definition lookup in ``find_by_id``.
		"""
		records = []
		root = self._dom_document.documentElement
		for position, element in _element_locations(self._dom_document.documentElement):
			if element.parentNode is root:
				records.append(_record_for_element(position, element))
		return tuple(records)

	#============================================
	def find_by_id(self, identifier: str) -> CDMLObjectRecord | None:
		"""Find a declaration ID anywhere in the document by stable preorder.

		Unlike ``objects()``, this broader lookup includes known nested durable
		definitions such as atoms and bonds; fragment member references are never
		considered definitions.
		"""
		for position, element in _element_locations(self._dom_document.documentElement):
			if not _is_id_definition(element):
				continue
			if element.getAttribute("id") != identifier:
				continue
			record = _record_for_element(position, element)
			return record
		return None

	#============================================
	def reaction_roles(self) -> tuple[CDMLReactionRoleRecord, ...]:
		"""Return recognized role references from core direct-child reactions.

		The records expose persistent reaction semantics without giving callers
		mutable DOM nodes. Compatibility validation remains responsible for
		reference resolution; profile validators can apply narrower authored
		semantics to these immutable records.
		"""
		records = []
		root = self._dom_document.documentElement
		for reaction in _element_children(root):
			if not _is_cdml_element(reaction) or _local_name(reaction) != "reaction":
				continue
			for child in _element_children(reaction):
				if not _is_cdml_element(child):
					continue
				role_name = _local_name(child)
				if role_name not in _REACTION_ROLE_NAMES:
					continue
				target_identifier = child.getAttribute("idref") or None
				records.append(CDMLReactionRoleRecord(
					reaction_path=_node_path(reaction),
					path=_node_path(child),
					role_name=role_name,
					target_identifier=target_identifier,
				))
		return tuple(records)

	#============================================
	def validation_issues(self, *, validation: str = "strict") -> tuple[CDMLIssue, ...]:
		"""Return durable-ID and known-reference findings without changing this document.

		The public issue value lets pure conformance clients share the backend's
		strict identity/reference rules without duplicating session behavior.  It
		deliberately does not allocate identifiers, normalize XML, or inspect
		opaque extension content beyond its literal document-wide ``id`` value.
		"""
		if validation == "compat":
			return ()
		if validation != "strict":
			raise CDMLValidationError(f"unknown CDML validation mode: {validation}")
		issues = []
		seen_ids = {}
		elements = _descendant_elements(self._dom_document.documentElement)
		for element in elements:
			if not _is_id_definition(element):
				continue
			identifier = element.getAttribute("id")
			if not identifier:
				continue
			if _is_id_declaration(element) and _has_provisional_id_prefix(identifier):
				code = "provisional_id" if _is_provisional_id(identifier) else "malformed_provisional_id"
				message = "provisional IDs are valid only during commit"
				issues.append(CDMLIssue(
					code, message, _node_path(element),
				))
			elif identifier in seen_ids:
				issues.append(CDMLIssue(
					"duplicate_id", f"duplicate CDML id: {identifier}", _node_path(element),
				))
			else:
				seen_ids[identifier] = element
		for element in elements:
			for attribute_name in _known_reference_attributes(element):
				reference = element.getAttribute(attribute_name)
				if not reference:
					continue
				if _has_provisional_id_prefix(reference):
					code = "provisional_reference" if _is_provisional_id(reference) else "malformed_provisional_reference"
					issues.append(CDMLIssue(
						code, "provisional reference escaped commit", _node_path(element),
					))
				elif reference not in seen_ids:
					issues.append(CDMLIssue(
						"unresolved_reference",
						f"unresolved {attribute_name} reference: {reference}", _node_path(element),
					))
			if _fragment_member_reference(element):
				reference = element.getAttribute("id")
				if _has_provisional_id_prefix(reference):
					code = "provisional_reference" if _is_provisional_id(reference) else "malformed_provisional_reference"
					issues.append(CDMLIssue(
						code, "provisional reference escaped commit", _node_path(element),
					))
				elif reference and reference not in seen_ids:
					issues.append(CDMLIssue(
						"unresolved_fragment_member",
						f"unresolved fragment member: {reference}", _node_path(element),
					))
		return tuple(issues)

	#============================================
	def validate(self, *, validation: str = "strict") -> tuple[CDMLIssue, ...]:
		"""Raise for strict findings while preserving the established API behavior."""
		issues = self.validation_issues(validation=validation)
		if issues:
			messages = "; ".join(issue.message for issue in issues)
			raise CDMLValidationError(messages)
		return issues

	#============================================
	def _commit_candidate_ids(self) -> dict[str, str]:
		"""Replace valid transaction-only IDs and known refs in this detached DOM."""
		root = self._dom_document.documentElement
		bracket_members = oasa.cdml_bracket_pair.valid_bracket_members(
			tuple(_element_children(root)), _is_cdml_element, _local_name,
		)
		elements = _descendant_elements(root)
		used_ids = set()
		seen_source_ids = set()
		provisional_nodes = []
		for element in elements:
			if not _is_id_definition(element):
				continue
			identifier = element.getAttribute("id")
			if not identifier:
				continue
			if identifier in seen_source_ids:
				raise CDMLValidationError(f"duplicate CDML id: {identifier}")
			seen_source_ids.add(identifier)
			if _is_id_declaration(element) and _has_provisional_id_prefix(identifier):
				if not _is_provisional_id(identifier):
					raise CDMLValidationError(f"malformed provisional CDML id: {identifier}")
				provisional_nodes.append((identifier, element))
			else:
				used_ids.add(identifier)
		id_map = {}
		for token, element in provisional_nodes:
			if token in id_map:
				raise CDMLValidationError(f"duplicate provisional CDML id: {token}")
			assigned_id = _next_durable_id(_local_name(element), used_ids)
			used_ids.add(assigned_id)
			id_map[token] = assigned_id
		for token, element in provisional_nodes:
			element.setAttribute("id", id_map[token])
		for left, right in bracket_members:
			pair_reference = left.getAttribute("bracket_pair")
			if pair_reference not in id_map:
				continue
			pair_id = id_map[pair_reference]
			left.setAttribute("bracket_pair", pair_id)
			right.setAttribute("bracket_pair", pair_id)
		for element in elements:
			for attribute_name in _known_reference_attributes(element):
				reference = element.getAttribute(attribute_name)
				if not _has_provisional_id_prefix(reference):
					continue
				if not _is_provisional_id(reference):
					raise CDMLValidationError(
						f"malformed provisional {attribute_name} reference: {reference}",
					)
				if reference not in id_map:
					raise CDMLValidationError(
					f"dangling provisional {attribute_name} reference: {reference}",
				)
				element.setAttribute(attribute_name, id_map[reference])
			if _fragment_member_reference(element):
				reference = element.getAttribute("id")
				if not _has_provisional_id_prefix(reference):
					continue
				if not _is_provisional_id(reference):
					raise CDMLValidationError(
						f"malformed provisional fragment member: {reference}",
					)
				if reference not in id_map:
					raise CDMLValidationError(
						f"dangling provisional fragment member: {reference}",
					)
				element.setAttribute("id", id_map[reference])
		return id_map


#============================================
_TOP_LEVEL_TRANSFORM_MODES = frozenset({
	"align-top", "align-bottom", "align-left", "align-right",
	"align-center-x", "align-center-y", "scale", "mirror-vertical",
	"mirror-horizontal", "translate",
})
_TOP_LEVEL_TRANSFORM_ROOT_NAMES = frozenset({
	"molecule", "arrow", "text", "plus", "rect", "square", "oval", "circle",
	"polygon", "polyline",
})
_SELECTION_TRANSLATE_PRESENTATION_ROOT_NAMES = frozenset({
	"arrow", "text", "plus", "rect", "square", "oval", "circle", "polygon",
	"polyline",
})


@dataclasses.dataclass
class _TopLevelTransformGeometry:
	"""Validated coordinate pairs and persistent bounds for one selected root."""

	element: object
	pairs: list[tuple[object, str, str, float, float]]
	bounds: tuple[float, float, float, float]


#============================================
def _validate_top_level_transform_request(
		request: object,
		) -> tuple[
			str, tuple[str, ...], float | None, float | None,
			tuple[float, float] | None,
		]:
	"""Validate the exact immutable grammar before looking up document roots."""
	if type(request) is not CDMLTopLevelTransformRequest:
		raise CDMLTopLevelTransformError("top-level transform requires an exact request")
	if type(request.expected_revision) is not int:
		raise CDMLTopLevelTransformError("top-level transform expected_revision must be an int")
	if type(request.mode) is not str or request.mode not in _TOP_LEVEL_TRANSFORM_MODES:
		raise CDMLTopLevelTransformError("top-level transform mode is unsupported")
	if (
		type(request.root_ids) is not tuple or not request.root_ids
		or any(type(identifier) is not str or not identifier for identifier in request.root_ids)
		or len(set(request.root_ids)) != len(request.root_ids)
	):
		raise CDMLTopLevelTransformError(
			"top-level transform root_ids must be unique nonempty strings",
		)
	if request.mode == "scale":
		if request.delta is not None:
			raise CDMLTopLevelTransformError("only translate accepts a delta")
		for name, value in (("scale_x", request.scale_x), ("scale_y", request.scale_y)):
			if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
				raise CDMLTopLevelTransformError(
					"top-level transform %s must be a finite positive non-bool factor" % name,
				)
		return request.mode, request.root_ids, float(request.scale_x), float(request.scale_y), None
	if request.scale_x is not None or request.scale_y is not None:
		raise CDMLTopLevelTransformError(
			"only scale accepts scale_x and scale_y factors",
		)
	if request.mode == "translate":
		try:
			delta = _validate_insertion_translation(request.delta)
		except CDMLValidationError as error:
			raise CDMLTopLevelTransformError(
				"top-level translation delta must be two finite non-bool point values",
			) from error
		return request.mode, request.root_ids, None, None, delta
	if request.delta is not None:
		raise CDMLTopLevelTransformError("only translate accepts a delta")
	if request.mode.startswith("align-") and len(request.root_ids) < 2:
		raise CDMLTopLevelTransformError("top-level alignment requires at least two roots")
	return request.mode, request.root_ids, None, None, None


#============================================
def _top_level_transform_point_pair(point: object) -> tuple[object, str, str, float, float]:
	"""Read one direct core point without normalizing its authored spelling."""
	if _element_children(point) or not point.hasAttribute("x") or not point.hasAttribute("y"):
		raise CDMLTopLevelTransformError("top-level transform point requires direct x and y")
	try:
		x = _insertion_coordinate(point.getAttribute("x"))
		y = _insertion_coordinate(point.getAttribute("y"))
		if point.hasAttribute("z"):
			_insertion_coordinate(point.getAttribute("z"))
	except CDMLValidationError as error:
		raise CDMLTopLevelTransformError("top-level transform point has invalid geometry") from error
	return point, "x", "y", x, y


#============================================
def _core_descendant_points(element: object) -> list:
	"""Return editable point descendants, excluding preserved opaque subtrees."""
	points = []
	for descendant in _descendant_elements(element)[1:]:
		if _is_cdml_element(descendant) and _local_name(descendant) == "point":
			points.append(descendant)
	return points


#============================================
def _top_level_transform_molecule_geometry(element: object) -> list[tuple[object, str, str, float, float]]:
	"""Read every transformable molecule vertex and explicit direct mark point."""
	pairs = []
	for vertex in _element_children(element):
		if not _is_cdml_element(vertex) or _local_name(vertex) not in _MOLECULE_VERTEX_NAMES:
			continue
		points = [
			child for child in _element_children(vertex)
			if _is_cdml_element(child) and _local_name(child) == "point"
		]
		if len(points) != 1:
			raise CDMLTopLevelTransformError(
				"top-level transform molecule vertex requires exactly one direct core point",
			)
		pairs.append(_top_level_transform_point_pair(points[0]))
		for mark in _element_children(vertex):
			if not _is_cdml_element(mark) or _local_name(mark) != "mark":
				continue
			has_x = mark.hasAttribute("x")
			has_y = mark.hasAttribute("y")
			if has_x != has_y:
				raise CDMLTopLevelTransformError(
					"top-level transform mark x and y must be present together",
				)
			if has_x:
				try:
					x = _insertion_coordinate(mark.getAttribute("x"))
					y = _insertion_coordinate(mark.getAttribute("y"))
				except CDMLValidationError as error:
					raise CDMLTopLevelTransformError(
						"top-level transform mark has invalid geometry",
					) from error
				pairs.append((mark, "x", "y", x, y))
	accounted_points = {id(pair[0]) for pair in pairs if _local_name(pair[0]) == "point"}
	if {id(point) for point in _core_descendant_points(element)} != accounted_points:
		raise CDMLTopLevelTransformError(
			"top-level transform molecule has ambiguous core coordinate geometry",
		)
	if not pairs:
		raise CDMLTopLevelTransformError("top-level transform molecule has no vertex geometry")
	return pairs


#============================================
def _top_level_transform_geometry(element: object) -> _TopLevelTransformGeometry:
	"""Validate one supported direct-root record and derive durable bounds."""
	name = _local_name(element)
	pairs: list[tuple[object, str, str, float, float]]
	if name == "molecule":
		pairs = _top_level_transform_molecule_geometry(element)
	elif name in ("arrow", "polygon", "polyline", "text", "plus"):
		minimum_points = {"arrow": 2, "polygon": 3, "polyline": 2, "text": 1, "plus": 1}[name]
		points = [
			child for child in _element_children(element)
			if _is_cdml_element(child) and _local_name(child) == "point"
		]
		all_points = _core_descendant_points(element)
		if (
			len(points) < minimum_points
			or (name in ("text", "plus") and len(points) != minimum_points)
			or len(all_points) != len(points)
		):
			raise CDMLTopLevelTransformError(
				"top-level transform %s has ambiguous point cardinality" % name,
			)
		pairs = [_top_level_transform_point_pair(point) for point in points]
	elif name in ("rect", "square", "oval", "circle"):
		if _core_descendant_points(element):
			raise CDMLTopLevelTransformError(
				"top-level transform %s has ambiguous core coordinate geometry" % name,
			)
		try:
			coordinates = [
				_insertion_coordinate(element.getAttribute(attribute))
				if element.hasAttribute(attribute) else None
				for attribute in ("x1", "y1", "x2", "y2")
			]
		except CDMLValidationError as error:
			raise CDMLTopLevelTransformError(
				"top-level transform %s has invalid corners" % name,
			) from error
		if any(value is None for value in coordinates):
			raise CDMLTopLevelTransformError(
				"top-level transform %s requires x1, y1, x2, and y2" % name,
			)
		x1, y1, x2, y2 = coordinates
		pairs = [(element, "x1", "y1", x1, y1), (element, "x2", "y2", x2, y2)]
	else:
		raise CDMLTopLevelTransformError("top-level transform root is unsupported: %s" % name)
	accounted_coordinate_elements = {id(pair[0]) for pair in pairs}
	for descendant in _descendant_elements(element)[1:]:
		if not _is_cdml_element(descendant):
			continue
		if (
			(descendant.hasAttribute("x") or descendant.hasAttribute("y"))
			and id(descendant) not in accounted_coordinate_elements
		):
			raise CDMLTopLevelTransformError(
				"top-level transform root has ambiguous core coordinate geometry",
			)
	x_coordinates = [pair[3] for pair in pairs]
	y_coordinates = [pair[4] for pair in pairs]
	return _TopLevelTransformGeometry(
		element=element,
		pairs=pairs,
		bounds=(min(x_coordinates), min(y_coordinates), max(x_coordinates), max(y_coordinates)),
	)


#============================================
def _direct_top_level_transform_roots(
		document: "CDMLDocument", root_ids: tuple[str, ...],
		) -> list[_TopLevelTransformGeometry]:
	"""Resolve selected durable direct roots in canonical document order."""
	selected = set(root_ids)
	geometries = []
	for child in _element_children(document._dom_document.documentElement):
		if child.getAttribute("id") not in selected:
			continue
		if not _is_cdml_element(child) or _local_name(child) not in _TOP_LEVEL_TRANSFORM_ROOT_NAMES:
			raise CDMLTopLevelTransformError("top-level transform root is not supported")
		geometries.append(_top_level_transform_geometry(child))
	if {geometry.element.getAttribute("id") for geometry in geometries} != selected:
		raise CDMLTopLevelTransformError("top-level transform root is not a durable direct core root")
	return geometries


#============================================
def _direct_selection_translate_roots(
		document: "CDMLDocument", root_ids: tuple[str, ...],
		) -> list[_TopLevelTransformGeometry]:
	"""Resolve selected direct-root presentation records in source order."""
	selected = set(root_ids)
	geometries = []
	for child in _element_children(document._dom_document.documentElement):
		if child.getAttribute("id") not in selected:
			continue
		if (
			not _is_cdml_element(child)
			or _local_name(child) not in _SELECTION_TRANSLATE_PRESENTATION_ROOT_NAMES
		):
			raise CDMLSelectionTranslateError(
				"selection translation root is not a supported durable direct presentation root",
			)
		try:
			geometries.append(_top_level_transform_geometry(child))
		except CDMLTopLevelTransformError as error:
			raise CDMLSelectionTranslateError(
				"selection translation root has invalid geometry",
			) from error
	if {geometry.element.getAttribute("id") for geometry in geometries} != selected:
		raise CDMLSelectionTranslateError(
			"selection translation root is not a durable direct core root",
		)
	return geometries


#============================================
def _transform_top_level_geometry(
		geometry: _TopLevelTransformGeometry, pivot_x: float, pivot_y: float,
		factor_x: float, factor_y: float,
		) -> None:
	"""Apply one affine coordinate map, retaining source spelling for equal axes."""
	for element, x_name, y_name, x, y in geometry.pairs:
		transformed_x = pivot_x + factor_x * (x - pivot_x)
		transformed_y = pivot_y + factor_y * (y - pivot_y)
		if not math.isfinite(transformed_x) or not math.isfinite(transformed_y):
			raise CDMLTopLevelTransformError("top-level transform coordinate is nonfinite")
		canonical_x = _canonical_authored_coordinate(transformed_x)
		canonical_y = _canonical_authored_coordinate(transformed_y)
		if _canonical_authored_coordinate(x) != canonical_x:
			element.setAttribute(x_name, canonical_x)
		if _canonical_authored_coordinate(y) != canonical_y:
			element.setAttribute(y_name, canonical_y)


#============================================
def _validate_top_level_affine_results(
		geometries: list[_TopLevelTransformGeometry], transforms: list[tuple[float, float, float, float]],
		) -> None:
	"""Reject nonfinite affine results before a detached candidate exists."""
	for geometry, (pivot_x, pivot_y, factor_x, factor_y) in zip(
			geometries, transforms, strict=True,
	):
		for _element, _x_name, _y_name, x, y in geometry.pairs:
			transformed_x = pivot_x + factor_x * (x - pivot_x)
			transformed_y = pivot_y + factor_y * (y - pivot_y)
			if not math.isfinite(transformed_x) or not math.isfinite(transformed_y):
				raise CDMLTopLevelTransformError("top-level transform coordinate is nonfinite")


#============================================
def _align_top_level_geometry(
		geometry: _TopLevelTransformGeometry, dx: float, dy: float,
		) -> None:
	"""Translate one root after validating every finite coordinate result."""
	transformed_pairs = []
	for element, x_name, y_name, x, y in geometry.pairs:
		transformed_x = x + dx
		transformed_y = y + dy
		if not math.isfinite(transformed_x) or not math.isfinite(transformed_y):
			raise CDMLTopLevelTransformError("top-level transform coordinate is nonfinite")
		transformed_pairs.append((element, x_name, y_name, x, y, transformed_x, transformed_y))
	for element, x_name, y_name, x, y, transformed_x, transformed_y in transformed_pairs:
		canonical_x = _canonical_authored_coordinate(transformed_x)
		canonical_y = _canonical_authored_coordinate(transformed_y)
		if _canonical_authored_coordinate(x) != canonical_x:
			element.setAttribute(x_name, canonical_x)
		if _canonical_authored_coordinate(y) != canonical_y:
			element.setAttribute(y_name, canonical_y)


#============================================
class CDMLDocumentSession:
	"""Revisioned backend owner for atomic complete-document CDML commits."""

	#============================================
	def __init__(self, document: CDMLDocument, history_capacity: int) -> None:
		"""Create a clean revision-zero backend session from one accepted document."""
		if history_capacity < 3:
			raise CDMLValidationError("history_capacity must be at least three")
		# Reparse into session-owned DOM state so caller-held documents cannot
		# mutate the accepted revision outside an atomic transaction.
		detached_document = CDMLDocument.parse(document.serialize(), validation="strict")
		self._history_capacity = history_capacity
		self._revision = 0
		self._document = detached_document
		self._saved_revision = 0
		self._saved_cdml = detached_document.serialize()
		self._saved_digest = _content_digest(self._saved_cdml)
		self._history = {0: detached_document}
		# Correlation tokens belong to this backend document session.  They are
		# consumed only after a commit has become authoritative, never by a
		# detached candidate that is later rejected.
		self._consumed_provisional_tokens: set[str] = set()
		# A restore behaves like an undo navigation step.  Keep the revision that
		# was current immediately before that step available for one redo.
		self._redo_revision: int | None = None

	#============================================
	@classmethod
	def load(cls, text: str, *, history_capacity: int = 20) -> "CDMLDocumentSession":
		"""Load a strict, clean revision-zero complete CDML backend document."""
		document = CDMLDocument.parse(text, validation="strict")
		return cls(document, history_capacity)

	#============================================
	@classmethod
	def load_imported(
			cls, text: str, *, history_capacity: int = 20,
			) -> "CDMLDocumentSession":
		"""Stage strict imported CDML against the empty-document saved baseline.

		An external chemistry file has not yet been published as native CDML.
		Its canonical document is therefore authoritative immediately but dirty
		until ordinary Save publishes that exact snapshot.
		"""
		document = CDMLDocument.parse(text, validation="strict")
		session = cls(document, history_capacity)
		empty_document = CDMLDocument.parse(_EMPTY_CDML, validation="strict")
		session._saved_cdml = empty_document.serialize()
		session._saved_digest = _content_digest(session._saved_cdml)
		return session

	#============================================
	@property
	def revision(self) -> int:
		"""Return the current backend revision number."""
		return self._revision

	#============================================
	@property
	def is_dirty(self) -> bool:
		"""Return content-based dirty state relative to the saved backend baseline."""
		current_cdml = self._document.serialize()
		return _content_digest(current_cdml) != self._saved_digest

	#============================================
	def snapshot(self) -> CDMLSnapshot:
		"""Return an immutable view of the current authoritative backend state."""
		cdml = self._document.serialize()
		return CDMLSnapshot(
			revision=self._revision,
			cdml=cdml,
			is_dirty=self.is_dirty,
		)

	#============================================
	def projection_snapshot(self) -> CDMLProjectionSnapshot:
		"""Return every projection fact atomically for the current snapshot."""
		snapshot = self.snapshot()
		plan = _projection_plan(self._document, self._revision)
		return CDMLProjectionSnapshot(snapshot, plan)

	#============================================
	def presentation_description(
			self, query: CDMLPresentationDescriptionQuery,
			) -> CDMLPresentationDescription:
		"""Observe the current direct-root presentation stack without mutation."""
		if type(query) is not CDMLPresentationDescriptionQuery:
			raise CDMLPresentationDescriptionError("presentation description requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLPresentationDescriptionError("presentation description revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _presentation_description(self._document, self._revision)

	#============================================
	def paper_layout(self, query: CDMLPaperLayoutQuery) -> CDMLPaperLayout:
		"""Observe current direct-core paper/layout facts without mutation."""
		if type(query) is not CDMLPaperLayoutQuery:
			raise CDMLPaperLayoutError("paper layout requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLPaperLayoutError("paper layout revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _paper_layout(self._document, self._revision)

	#============================================
	def drawing_standard(
			self, query: oasa.cdml_standard.CDMLDrawingStandardQuery,
			) -> oasa.cdml_standard.CDMLDrawingStandardObservation:
		"""Observe effective drawing defaults without exposing header XML."""
		return oasa.cdml_standard.query_session(self, query)

	#============================================
	def fragment_metadata(
			self, query: CDMLFragmentMetadataQuery,
			) -> CDMLFragmentMetadata:
		"""Observe current fragment eligibility without changing retained CDML."""
		if type(query) is not CDMLFragmentMetadataQuery:
			raise CDMLFragmentMetadataError("fragment metadata requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLFragmentMetadataError("fragment metadata revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _fragment_metadata(self._document, self._revision)

	#============================================
	def atom_mark_observation(
			self, query: CDMLAtomMarkObservationQuery,
			) -> CDMLAtomMarkObservation:
		"""Observe direct atom marks without changing retained CDML or history."""
		if type(query) is not CDMLAtomMarkObservationQuery:
			raise CDMLAtomMarkObservationError("atom-mark observation requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLAtomMarkObservationError("atom-mark observation revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _atom_mark_observation(self._document, self._revision)

	#============================================
	def group_observation(self, query: CDMLGroupObservationQuery) -> CDMLGroupObservation:
		"""Observe direct groups without changing retained CDML or history."""
		if type(query) is not CDMLGroupObservationQuery:
			raise CDMLGroupObservationError("group observation requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLGroupObservationError("group observation revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _group_observation(self._document, self._revision)

	#============================================
	def molecule_core_observation(
			self, query: CDMLMoleculeCoreObservationQuery,
			) -> CDMLMoleculeCoreObservation:
		"""Observe exact-revision molecule-core facts without mutation."""
		if type(query) is not CDMLMoleculeCoreObservationQuery:
			raise CDMLMoleculeCoreObservationError("molecule-core observation requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLMoleculeCoreObservationError("molecule-core observation revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _molecule_core_observation(self._document, self._revision)

	#============================================
	def molecule_render_observation(
			self, query: CDMLMoleculeRenderObservationQuery,
			) -> CDMLMoleculeRenderObservation:
		"""Observe exact-revision portable molecule paint batches without mutation."""
		if type(query) is not CDMLMoleculeRenderObservationQuery:
			raise CDMLMoleculeRenderObservationError("molecule render observation requires an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLMoleculeRenderObservationError("molecule render observation revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _molecule_render_observation(self._document, self._revision)

	#============================================
	def atom_chemistry_facts(
			self, query: CDMLAtomChemistryFactsQuery,
			) -> CDMLAtomChemistryFactsObservation:
		"""Observe exact-revision direct-graph chemistry without mutation."""
		if type(query) is not CDMLAtomChemistryFactsQuery:
			raise CDMLAtomChemistryFactsError("atom chemistry facts require an exact query")
		if type(query.expected_revision) is not int:
			raise CDMLAtomChemistryFactsError("atom chemistry facts revision must be an int")
		self._check_expected_revision(query.expected_revision)
		return _atom_chemistry_facts_observation(self._document, self._revision)

	#============================================
	def paper_catalog(self) -> dict[str, list[float] | None]:
		"""Return the backend-owned plain-data catalog for a document client.

		The catalog is document-format policy rather than frontend presentation
		state.  Returning a fresh value keeps callers from retaining mutable
		backend-owned catalog data between operations.
		"""
		return paper_catalog()

	#============================================
	def paper_properties_context(self) -> dict[str, object]:
		"""Return fresh plain data for one paper-properties client view.

		The backend identifies the editable first direct core ``paper`` record
		and calculates the effective creation defaults.  A frontend uses this
		observation to display an absent paper consistently with a later patch;
		it must not infer a separate UI default from its own document projection.
		"""
		paper = _first_direct_core_child(self._document, "paper")
		default_type, default_orientation = _new_paper_defaults(self._document)
		return {
			"paper_present": paper is not None,
			"attributes": (
				{} if paper is None else {
					paper.attributes.item(index).name: paper.attributes.item(index).value
					for index in range(paper.attributes.length)
				}
			),
			"default_type": default_type,
			"default_orientation": default_orientation,
		}

	#============================================
	def commit(self, *, expected_revision: int, complete_cdml: str) -> CDMLCommit:
		"""Atomically accept a detached complete-CDML candidate at one revision."""
		self._check_expected_revision(expected_revision)
		candidate = CDMLDocument.parse(complete_cdml, validation="compat")
		id_map = candidate._commit_candidate_ids()
		candidate.validate(validation="strict")
		reused_tokens = set(id_map).intersection(self._consumed_provisional_tokens)
		if reused_tokens:
			reused_token = sorted(reused_tokens)[0]
			raise CDMLValidationError(
				f"provisional correlation token already consumed: {reused_token}",
			)
		# A new accepted edit starts a different history branch, so it clears the
		# one-step redo protection.  Validation above must finish first so failed
		# candidates leave the session state, including redo, untouched.
		commit = self._accept_document(candidate, id_map, redo_revision=None)
		self._consumed_provisional_tokens.update(id_map)
		return commit

	#============================================
	def insert_molecules(
			self, request: CDMLMoleculeInsertionRequest,
			) -> "oasa.cdml_molecule_insertion.CDMLMoleculeInsertionResult":
		"""Append a detached molecule-only proposal through the complete commit path.

		The optional request label is operation metadata only.  It never enters the
		persistent CDML candidate and does not affect validation or ID allocation.
		"""
		if request.label is not None and not isinstance(request.label, str):
			raise CDMLValidationError("molecule insertion label must be a string or None")
		self._check_expected_revision(request.expected_revision)
		proposal = CDMLDocument.parse(request.proposal_cdml, validation="compat")
		molecules = _proposal_molecules(proposal)
		provisional_root_ids = tuple(molecule.getAttribute("id") for molecule in molecules)
		candidate = CDMLDocument.parse(self.snapshot().cdml, validation="compat")
		candidate_root = candidate._dom_document.documentElement
		proposal_root = proposal._dom_document.documentElement
		for molecule in molecules:
			imported_molecule = candidate._dom_document.importNode(molecule, deep=True)
			_copy_proposal_namespace_declarations(proposal_root, imported_molecule)
			candidate_root.appendChild(imported_molecule)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		import oasa.cdml_molecule_insertion
		return oasa.cdml_molecule_insertion.CDMLMoleculeInsertionResult(
			commit=commit,
			root_id_map={
				provisional_id: commit.id_map[provisional_id]
				for provisional_id in provisional_root_ids
			},
		)

	#============================================
	def insert_user_template(self, request: CDMLUserTemplateInsertionRequest) -> CDMLCommit:
		"""Insert one authored-scale serialized saved template through normal acceptance.

		The template is an exact complete CDML value.  Its optional standard and
		paper records provide saved context only; the one detached molecule is the
		only imported persistent root.  OASA preserves its compatible subtree,
		assigns fresh IDs, rewrites recognized internal references, and translates
		its authored atom centroid to the finite requested anchor without scaling.
		"""
		template_cdml, anchor_cm, _label = _validate_user_template_request(request)
		# A stale request has no parsing or inspection side effect.
		self._check_expected_revision(request.expected_revision)
		template = CDMLDocument.parse(template_cdml, validation="compat")
		_inspect_user_template_document(template)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		prepared_molecule = _prepare_user_template_molecule(
			template, candidate.serialize(), self._consumed_provisional_tokens, anchor_cm,
		)
		imported_molecule = candidate._dom_document.importNode(prepared_molecule, deep=True)
		_copy_proposal_namespace_declarations(
			template._dom_document.documentElement, imported_molecule,
		)
		candidate._dom_document.documentElement.appendChild(imported_molecule)
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def insert_top_level(self, request: CDMLTopLevelInsertionRequest) -> CDMLCommit:
		"""Append an allowlisted, translated fragment through one normal commit.

		The fragment is a complete untrusted CDML document.  Its IDs are source
		labels only: this method creates fresh private provisional IDs in detached
		state, so a pasted reference can never accidentally bind the destination.
		Translation is expressed in CDML/PostScript scene points.
		"""
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("top-level insertion expected_revision must be an int")
		if request.label is not None and not isinstance(request.label, str):
			raise CDMLValidationError("top-level insertion label must be a string or None")
		if not isinstance(request.fragment_cdml, str):
			raise CDMLValidationError("top-level insertion fragment_cdml must be a string")
		dx, dy = _validate_insertion_translation(request.translation)
		# Reject obsolete requests before parsing or building detached work.
		self._check_expected_revision(request.expected_revision)
		fragment = CDMLDocument.parse(request.fragment_cdml, validation="compat")
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		roots = _prepare_top_level_fragment(
			fragment,
			candidate.serialize(),
			self._consumed_provisional_tokens,
			dx,
			dy,
		)
		candidate_root = candidate._dom_document.documentElement
		fragment_root = fragment._dom_document.documentElement
		for root in roots:
			imported_root = candidate._dom_document.importNode(root, deep=True)
			_copy_proposal_namespace_declarations(fragment_root, imported_root)
			candidate_root.appendChild(imported_root)
		# ``commit`` repeats the revision check immediately before its final
		# acceptance path, retaining the ordinary optimistic-transaction contract.
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def edit_structure(self, request: CDMLStructuralEditRequest) -> CDMLStructuralEditResult:
		"""Accept one narrow Draw-mode structural operation atomically.

		The operation acts on a detached copy of the authoritative complete CDML
		document.  It neither receives nor returns frontend objects, and all
		created IDs are allocated by OASA before the ordinary commit path accepts
		the validated candidate.
		"""
		validated = _validate_structural_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		root = candidate._dom_document.documentElement
		used_ids = _candidate_durable_ids(candidate)
		kind = validated[0]
		created_molecule_id = None
		created_atom_ids: tuple[str, ...] = ()
		created_bond_ids: tuple[str, ...] = ()
		updated_bond_ids: tuple[str, ...] = ()
		if kind == "create-bonded-pair":
			(_kind, source_position, target_position, element, bond_type, bond_order, simple_double) = validated
			created_molecule_id = _next_durable_id("molecule", used_ids)
			used_ids.add(created_molecule_id)
			first_atom_id = _next_durable_id("atom", used_ids)
			used_ids.add(first_atom_id)
			second_atom_id = _next_durable_id("atom", used_ids)
			used_ids.add(second_atom_id)
			bond_id = _next_durable_id("bond", used_ids)
			molecule = _new_core_element(candidate, root, "molecule")
			molecule.setAttribute("id", created_molecule_id)
			root.appendChild(molecule)
			_append_atom(candidate, molecule, first_atom_id, element, source_position)
			_append_atom(candidate, molecule, second_atom_id, element, target_position)
			_append_bond(
				candidate, molecule, bond_id, first_atom_id, second_atom_id,
				bond_type, bond_order, simple_double,
			)
			created_atom_ids = (first_atom_id, second_atom_id)
			created_bond_ids = (bond_id,)
		elif kind == "extend-atom":
			(_kind, molecule_id, source_atom_id, target_position, element, bond_type, bond_order, simple_double) = validated
			molecule = _direct_root_molecule(candidate, molecule_id)
			_direct_molecule_atom(molecule, source_atom_id)
			new_atom_id = _next_durable_id("atom", used_ids)
			used_ids.add(new_atom_id)
			bond_id = _next_durable_id("bond", used_ids)
			_append_atom(candidate, molecule, new_atom_id, element, target_position)
			_append_bond(
				candidate, molecule, bond_id, source_atom_id, new_atom_id,
				bond_type, bond_order, simple_double,
			)
			created_atom_ids = (new_atom_id,)
			created_bond_ids = (bond_id,)
		elif kind == "join-atoms":
			(_kind, molecule_id, source_atom_id, target_atom_id, bond_type, bond_order, simple_double) = validated
			molecule = _direct_root_molecule(candidate, molecule_id)
			_direct_molecule_atom(molecule, source_atom_id)
			_direct_molecule_atom(molecule, target_atom_id)
			if source_atom_id == target_atom_id:
				raise CDMLValidationError("join-atoms requires two distinct atoms")
			if _has_direct_bond(molecule, source_atom_id, target_atom_id):
				raise CDMLValidationError("join-atoms rejects a duplicate direct-molecule bond")
			bond_id = _next_durable_id("bond", used_ids)
			_append_bond(
				candidate, molecule, bond_id, source_atom_id, target_atom_id,
				bond_type, bond_order, simple_double,
			)
			created_bond_ids = (bond_id,)
		else:
			(_kind, molecule_id, bond_id, bond_type, bond_order, simple_double) = validated
			molecule = _direct_root_molecule(candidate, molecule_id)
			bond = _direct_molecule_bond(molecule, bond_id)
			_require_editable_bond_endpoints(molecule, bond)
			_apply_bond_tool_transition(bond, bond_type, bond_order, simple_double)
			updated_bond_ids = (bond_id,)
		import oasa.cdml_linear_form
		oasa.cdml_linear_form.remove_invalid_generated_forms(
			candidate,
			(created_molecule_id,) if kind == "create-bonded-pair" else (molecule_id,),
		)
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLStructuralEditResult(
			commit=commit,
			created_molecule_id=created_molecule_id,
			created_atom_ids=created_atom_ids,
			created_bond_ids=created_bond_ids,
			updated_bond_ids=updated_bond_ids,
		)

	#============================================
	def set_atom_element(self, request: CDMLAtomElementEditRequest) -> CDMLCommit:
		"""Atomically replace one direct core atom name in complete CDML.

		The operation intentionally preserves every other atom field and every
		unrelated document record.  Valence, bond, charge, and presentation
		changes require separately specified backend operations.
		"""
		molecule_id, atom_id, element = _validate_atom_element_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		current_element = atom.getAttribute("name")
		if current_element not in oasa.periodic_table.periodic_table:
			raise CDMLValidationError("atom element edit target has an unsupported atom symbol")
		if element == current_element:
			raise CDMLValidationError("atom element edit replacement must differ from the current symbol")
		atom.setAttribute("name", element)
		candidate.validate(validation="strict")
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def patch_atom_properties(
			self, request: CDMLAtomPropertiesPatch,
			) -> CDMLAtomPropertiesPatchResult:
		"""Apply one complete explicit atom-properties intent atomically.

		The patch changes only direct core atom fields and its direct core font.
		Every scalar is validated before the target or detached candidate changes.
		"""
		molecule_id, atom_id, changes = _validate_atom_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		if atom.getAttribute("name") not in oasa.periodic_table.periodic_table:
			raise CDMLAtomPropertiesPatchError(
				"atom properties target has an unsupported atom symbol",
			)
		if not changes:
			return CDMLAtomPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_atom = _direct_molecule_atom(candidate_molecule, atom_id)
		change_map = dict(changes)
		for field_name, value in changes:
			if field_name == "element":
				candidate_atom.setAttribute("name", value)
			elif field_name == "charge":
				if value == 0:
					candidate_atom.removeAttribute("charge")
				else:
					candidate_atom.setAttribute("charge", str(value))
			elif field_name == "valency":
				candidate_atom.setAttribute("valency", str(value))
			elif field_name == "isotope":
				if value is None:
					candidate_atom.removeAttribute("isotope")
				else:
					candidate_atom.setAttribute("isotope", str(value))
			elif field_name == "multiplicity":
				if value == 1:
					candidate_atom.removeAttribute("multiplicity")
				else:
					candidate_atom.setAttribute("multiplicity", str(value))
			elif field_name == "show":
				candidate_atom.setAttribute("show", "yes" if value else "no")
			elif field_name == "show_hydrogens":
				candidate_atom.setAttribute("hydrogens", "on" if value else "off")
		if "font_size" in change_map or "line_color" in change_map:
			fonts = [
				child for child in _element_children(candidate_atom)
				if _is_cdml_element(child) and _local_name(child) == "font"
			]
			if len(fonts) > 1:
				raise CDMLAtomPropertiesPatchError(
					"atom properties target has multiple direct core fonts",
				)
			font = fonts[0] if fonts else _new_core_element(candidate, candidate_atom, "font")
			if "font_size" in change_map:
				font.setAttribute("size", str(change_map["font_size"]))
			if "line_color" in change_map:
				font.setAttribute("color", change_map["line_color"])
			if not fonts:
				candidate_atom.appendChild(font)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLAtomPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLAtomPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def patch_text_properties(
			self, request: CDMLTextPropertiesPatch,
			) -> CDMLTextPropertiesPatchResult:
		"""Apply one explicit plain Text intent atomically through complete CDML."""
		text_id, changes = _validate_text_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		text = _direct_root_text(self._document, text_id)
		_editable_text_children(text)
		if not changes:
			return CDMLTextPropertiesPatchResult(self.snapshot(), False, None)
		change_map = dict(changes)
		if (
			"background_color" in change_map
			and change_map["background_color"] == _optional_background_color(
				text, CDMLTextPropertiesPatchError, "Text properties target",
			)
		):
			del change_map["background_color"]
		if not change_map:
			return CDMLTextPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_text = _direct_root_text(candidate, text_id)
		font, ftext = _editable_text_children(candidate_text)
		if "text" in change_map:
			text_nodes = tuple(
				child for child in ftext.childNodes
				if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE)
			)
			insertion_reference = None
			if text_nodes:
				following = text_nodes[0].nextSibling
				while following is not None and following in text_nodes:
					following = following.nextSibling
				insertion_reference = following
			for child in text_nodes:
				ftext.removeChild(child)
			plain_text = candidate._dom_document.createTextNode(change_map["text"])
			if insertion_reference is None:
				ftext.appendChild(plain_text)
			else:
				ftext.insertBefore(plain_text, insertion_reference)
		if any(name in change_map for name in ("font_family", "font_size", "font_color")):
			if font is None:
				font = _new_core_element(candidate, candidate_text, "font")
				candidate_text.insertBefore(font, ftext)
			if "font_family" in change_map:
				font.setAttribute("family", change_map["font_family"])
			if "font_size" in change_map:
				font.setAttribute("size", str(change_map["font_size"]))
			if "font_color" in change_map:
				font.setAttribute("color", change_map["font_color"])
		if "background_color" in change_map:
			candidate_text.setAttribute(
				"background-color", change_map["background_color"] or "",
			)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLTextPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLTextPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def patch_rich_text(
			self, request: CDMLRichTextPatch,
			) -> CDMLRichTextPatchResult:
		"""Apply one formatted Text run request through one atomic CDML commit."""
		if type(request) is not CDMLRichTextPatch:
			raise CDMLRichTextPatchError("rich Text requires an exact rich Text patch")
		if type(request.expected_revision) is not int:
			raise CDMLRichTextPatchError("rich Text expected_revision must be an int")
		# A stale request is rejected before target or run-payload interpretation.
		self._check_expected_revision(request.expected_revision)
		text_id, runs, changes = _validate_rich_text_patch(request)
		text = _direct_root_rich_text(self._document, text_id)
		font, ftext = _editable_rich_text_children(text)
		current_authored = "".join(child.data for child in ftext.childNodes)
		try:
			current_runs = oasa.cdml_ftext.decode(current_authored)
		except oasa.cdml_ftext.CDMLFTextCodecError as error:
			raise CDMLRichTextPatchError("rich Text target ftext is invalid: %s" % error) from error
		if not any(run.text.strip() for run in current_runs):
			raise CDMLRichTextPatchError("rich Text target ftext is blank")
		change_map = dict(changes)
		font_unchanged = True
		if "font_family" in change_map:
			font_unchanged = (
				font is not None
				and font.getAttribute("family") == change_map["font_family"]
			)
		if "font_size" in change_map:
			font_unchanged = (
				font_unchanged and font is not None
				and font.getAttribute("size") == str(change_map["font_size"])
			)
		if "font_color" in change_map:
			font_unchanged = (
				font_unchanged and font is not None
				and font.getAttribute("color") == change_map["font_color"]
			)
		if current_runs == runs and font_unchanged:
			return CDMLRichTextPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_text = _direct_root_rich_text(candidate, text_id)
		candidate_font, candidate_ftext = _editable_rich_text_children(candidate_text)
		for child in tuple(candidate_ftext.childNodes):
			candidate_ftext.removeChild(child)
		candidate_ftext.appendChild(
			candidate._dom_document.createTextNode(oasa.cdml_ftext.encode(runs)),
		)
		if changes:
			if candidate_font is None:
				candidate_font = _new_core_element(candidate, candidate_text, "font")
				candidate_text.insertBefore(candidate_font, candidate_ftext)
			if "font_family" in change_map:
				candidate_font.setAttribute("family", change_map["font_family"])
			if "font_size" in change_map:
				candidate_font.setAttribute("size", str(change_map["font_size"]))
			if "font_color" in change_map:
				candidate_font.setAttribute("color", change_map["font_color"])
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLRichTextPatchResult(commit.snapshot, True, commit)

	#============================================
	def patch_plus_properties(
			self, request: CDMLPlusPropertiesPatch,
			) -> CDMLPlusPropertiesPatchResult:
		"""Apply one explicit plain Plus root-property intent atomically."""
		plus_id, changes = _validate_plus_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		plus = _direct_root_plus(self._document, plus_id)
		font = _editable_plus_children(plus)
		current_family, current_size, current_color, current_background = (
			_plus_property_values(plus, font)
		)
		if not changes:
			return CDMLPlusPropertiesPatchResult(self.snapshot(), False, None)
		change_map = dict(changes)
		if (
			("font_family" not in change_map or change_map["font_family"] == current_family)
			and ("font_size" not in change_map or change_map["font_size"] == current_size)
			and ("color" not in change_map or change_map["color"] == current_color)
			and (
				"background_color" not in change_map
				or change_map["background_color"] == current_background
			)
		):
			return CDMLPlusPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_plus = _direct_root_plus(candidate, plus_id)
		candidate_font = _editable_plus_children(candidate_plus)
		if "font_family" in change_map:
			if candidate_font is None:
				candidate_font = _new_core_element(candidate, candidate_plus, "font")
				candidate_plus.appendChild(candidate_font)
			candidate_font.setAttribute("family", change_map["font_family"])
		if "font_size" in change_map:
			candidate_plus.setAttribute("font_size", str(change_map["font_size"]))
		if "color" in change_map:
			candidate_plus.setAttribute("color", change_map["color"])
		if "background_color" in change_map:
			candidate_plus.setAttribute(
				"background-color", change_map["background_color"] or "",
			)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLPlusPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLPlusPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def patch_wavy_properties(
			self, request: CDMLWavyPropertiesPatch,
			) -> CDMLWavyPropertiesPatchResult:
		"""Apply one explicit plain Wavy root-property intent atomically."""
		wavy_id, changes = _validate_wavy_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		wavy = _direct_root_wavy(self._document, wavy_id)
		current_width, current_color = _wavy_property_values(wavy)
		if not changes:
			return CDMLWavyPropertiesPatchResult(self.snapshot(), False, None)
		change_map = dict(changes)
		if (
			("width" not in change_map or change_map["width"] == current_width)
			and ("line_color" not in change_map or change_map["line_color"] == current_color)
		):
			return CDMLWavyPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_wavy = _direct_root_wavy(candidate, wavy_id)
		_wavy_property_values(candidate_wavy)
		if "width" in change_map:
			candidate_wavy.setAttribute("width", "%g" % change_map["width"])
		if "line_color" in change_map:
			candidate_wavy.setAttribute("line_color", change_map["line_color"])
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLWavyPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLWavyPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def create_fragment(
			self, request: CDMLFragmentCreateRequest,
			) -> CDMLFragmentCreateResult:
		"""Create one ordinary fragment without rebuilding its molecule.

		The request contains durable member IDs only.  OASA allocates the fragment
		identity after reading every document-wide reserved ID, then accepts the
		complete detached candidate through the standard history transaction.
		"""
		molecule_id, name, fragment_type, atom_ids, bond_ids = _validate_fragment_create_request(
			request,
		)
		self._check_expected_revision(request.expected_revision)
		try:
			molecule = _direct_root_molecule(self._document, molecule_id)
		except CDMLValidationError as exc:
			raise CDMLFragmentOperationError("fragment creation molecule target is invalid") from exc
		_validate_fragment_members(molecule, atom_ids, bond_ids)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		used_ids = {
			element.getAttribute("id")
			for element in _descendant_elements(candidate._dom_document.documentElement)
			if _is_id_definition(element) and element.getAttribute("id")
		}
		fragment_id = _next_durable_id("fragment", used_ids)
		fragment = _new_core_element(candidate, candidate_molecule, "fragment")
		fragment.setAttribute("id", fragment_id)
		fragment.setAttribute("type", fragment_type)
		name_element = _new_core_element(candidate, fragment, "name")
		name_element.appendChild(candidate._dom_document.createTextNode(name))
		fragment.appendChild(name_element)
		for bond_id in bond_ids:
			member = _new_core_element(candidate, fragment, "bond")
			member.setAttribute("id", bond_id)
			fragment.appendChild(member)
		for atom_id in atom_ids:
			member = _new_core_element(candidate, fragment, "vertex")
			member.setAttribute("id", atom_id)
			fragment.appendChild(member)
		candidate_molecule.appendChild(fragment)
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLFragmentCreateResult(commit.snapshot, commit, fragment_id)

	#============================================
	def delete_fragment(
			self, request: CDMLFragmentDeleteRequest,
			) -> CDMLFragmentDeleteResult:
		"""Remove exactly one ordinary direct fragment from one molecule."""
		if type(request) is not CDMLFragmentDeleteRequest:
			raise CDMLFragmentOperationError("fragment deletion requires an exact request")
		if type(request.expected_revision) is not int:
			raise CDMLFragmentOperationError("fragment deletion expected_revision must be an int")
		if type(request.molecule_id) is not str or not request.molecule_id:
			raise CDMLFragmentOperationError("fragment deletion molecule_id must be a nonempty string")
		if type(request.fragment_id) is not str or not request.fragment_id:
			raise CDMLFragmentOperationError("fragment deletion fragment_id must be a nonempty string")
		self._check_expected_revision(request.expected_revision)
		try:
			molecule = _direct_root_molecule(self._document, request.molecule_id)
		except CDMLValidationError as exc:
			raise CDMLFragmentOperationError("fragment deletion molecule target is invalid") from exc
		matches = [
			child for child in _element_children(molecule)
			if _is_cdml_element(child) and _local_name(child) == "fragment"
			and child.getAttribute("id") == request.fragment_id
		]
		if len(matches) != 1:
			raise CDMLFragmentOperationError("fragment deletion target is missing or ambiguous")
		_fragment_id, atom_ids, bond_ids = _ordinary_fragment_members(matches[0])
		_validate_fragment_members(molecule, atom_ids, bond_ids)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, request.molecule_id)
		candidate_matches = [
			child for child in _element_children(candidate_molecule)
			if _is_cdml_element(child) and _local_name(child) == "fragment"
			and child.getAttribute("id") == request.fragment_id
		]
		if len(candidate_matches) != 1:
			raise CDMLFragmentOperationError("fragment deletion target is missing or ambiguous")
		candidate_molecule.removeChild(candidate_matches[0])
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLFragmentDeleteResult(commit.snapshot, commit, request.fragment_id)

	#============================================
	def convert_linear_form(
			self, request: CDMLLinearFormConvertRequest,
			) -> CDMLLinearFormConvertResult:
		"""Convert one direct atom path through OASA's atomic CDML authority.

		The persistent geometry, hydrogen state, fragment identity, and path order
		are derived from the accepted snapshot.  A matching canonical conversion is
		a semantic no-op and deliberately creates neither history nor a new ID.
		"""
		molecule_id, atom_ids = _validate_linear_form_convert_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		import oasa.cdml_linear_form
		details = oasa.cdml_linear_form.convert(candidate, molecule_id, atom_ids)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLLinearFormConvertResult(
				self.snapshot(), False, None, details.fragment_id,
				details.atom_ids, details.bond_ids,
			)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLLinearFormConvertResult(
			commit.snapshot, True, commit, details.fragment_id,
			details.atom_ids, details.bond_ids,
		)

	#============================================
	def apply_atom_mark(
			self, request: CDMLAtomMarkOperationRequest,
			) -> CDMLAtomMarkOperationResult:
		"""Add or remove one direct atom mark and its declared chemistry delta.

		The request is fully validated before the detached candidate changes.  A
		matching removal uses direct-child order, so duplicate compatible marks
		remain distinguishable without inventing mark IDs in the 26.07 profile.
		"""
		molecule_id, atom_id, action, mark_type, matching_mark_index = (
			_validate_atom_mark_request(request)
		)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		matching_marks = _direct_atom_marks(atom, mark_type)
		if matching_mark_index is None:
			matching_mark = matching_marks[0] if matching_marks else None
		elif matching_mark_index >= len(matching_marks):
			raise CDMLAtomMarkOperationError("atom mark matching mark index is out of range")
		else:
			matching_mark = matching_marks[matching_mark_index]
		if action == "remove" and matching_mark is None:
			return CDMLAtomMarkOperationResult(self.snapshot(), False, None, "unchanged")
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_atom = _direct_molecule_atom(candidate_molecule, atom_id)
		if action == "add":
			attributes = _authored_atom_mark_attributes(candidate_atom, mark_type)
			mark = _new_core_element(candidate, candidate_atom, "mark")
			for name, value in attributes.items():
				mark.setAttribute(name, value)
			candidate_atom.appendChild(mark)
		else:
			candidate_marks = _direct_atom_marks(candidate_atom, mark_type)
			candidate_mark = (
				candidate_marks[matching_mark_index]
				if matching_mark_index is not None else (
					candidate_marks[0] if candidate_marks else None
				)
			)
			if candidate_mark is None:
				raise CDMLAtomMarkOperationError("atom mark disappeared from detached candidate")
			candidate_atom.removeChild(candidate_mark)
		_apply_atom_mark_scalar_delta(candidate_atom, mark_type, action)
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLAtomMarkOperationResult(
			commit.snapshot, True, commit, "added" if action == "add" else "removed",
		)

	#============================================
	def set_atom_number(self, request: CDMLAtomNumberEditRequest) -> CDMLCommit:
		"""Atomically assign, replace, or clear one direct core atom number."""
		molecule_id, atom_id, number, show_number = _validate_atom_number_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		for child in _element_children(atom):
			if (
					_is_cdml_element(child)
					and _local_name(child) == "mark"
					and child.getAttribute("type") == "atom_number"
				):
				raise CDMLAtomNumberCompatibilityError(
					"atom number edit target has a direct legacy atom_number mark",
				)
		if number is None:
			atom.removeAttribute("number")
			atom.removeAttribute("show_number")
		else:
			atom.setAttribute("number", str(number))
			atom.setAttribute("show_number", "yes" if show_number else "no")
		candidate.validate(validation="strict")
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def set_molecule_name(self, request: CDMLMoleculeNameEditRequest) -> CDMLCommit:
		"""Atomically replace or clear one direct-root molecule display name."""
		molecule_id, name = _validate_molecule_name_request(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		current_name = molecule.getAttribute("name") if molecule.hasAttribute("name") else ""
		if current_name == name:
			return CDMLCommit(self.snapshot(), types.MappingProxyType({}))
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		if name:
			molecule.setAttribute("name", name)
		else:
			molecule.removeAttribute("name")
		candidate.validate(validation="strict")
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def patch_paper_properties(self, request: CDMLPaperPropertiesPatch) -> CDMLCommit:
		"""Apply explicit paper-field intent through one detached CDML commit.

		Only the first direct core ``paper`` record is editable.  The operation
		never reconstructs that record, so unrecognized attributes, descendants,
		and later compatibility paper records retain their exact XML ownership.
		"""
		changes = _validate_paper_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		if not changes:
			return CDMLCommit(self.snapshot(), types.MappingProxyType({}))
		current_paper = _first_direct_core_child(self._document, "paper")
		if current_paper is None:
			current_type, _current_orientation = _new_paper_defaults(self._document)
		else:
			current_type = current_paper.getAttribute("type") if current_paper.hasAttribute("type") else ""
		effective_type = changes.get("type", current_type)
		if "dimensions" in changes and effective_type != "custom":
			raise CDMLPaperPropertiesError(
				"paper properties dimensions apply only to custom paper",
			)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		paper = _first_direct_core_child(candidate, "paper")
		if paper is None:
			root = candidate._dom_document.documentElement
			paper = _new_core_element(candidate, root, "paper")
			default_type, default_orientation = _new_paper_defaults(candidate)
			paper.setAttribute("type", default_type)
			paper.setAttribute("orientation", default_orientation)
			viewport = _first_direct_core_child(candidate, "viewport")
			if viewport is None:
				root.appendChild(paper)
			else:
				root.insertBefore(paper, viewport)
		if "type" in changes:
			paper.setAttribute("type", changes["type"])
		if "orientation" in changes:
			paper.setAttribute("orientation", changes["orientation"])
		for name in ("crop_svg", "use_real_minus", "replace_minus"):
			if name in changes:
				paper.setAttribute(name, "1" if changes[name] else "0")
		if "crop_margin" in changes:
			paper.setAttribute("crop_margin", str(changes["crop_margin"]))
		if effective_type == "custom":
			if "dimensions" in changes:
				dimensions = changes["dimensions"]
				paper.setAttribute("size_x", _paper_dimension_text(dimensions[0]))
				paper.setAttribute("size_y", _paper_dimension_text(dimensions[1]))
		elif "type" in changes:
			for name in ("size_x", "size_y"):
				if paper.hasAttribute(name):
					paper.removeAttribute(name)
		candidate.validate(validation="strict")
		if candidate.serialize() == self._document.serialize():
			return CDMLCommit(self.snapshot(), types.MappingProxyType({}))
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def patch_drawing_standard(
			self, request: oasa.cdml_standard.CDMLDrawingStandardRequest,
			) -> CDMLCommit:
		"""Apply explicit standard intent through one complete-CDML commit."""
		return oasa.cdml_standard.patch_session(self, request, CDMLCommit)

	#============================================
	def molecule_summary(self, query: object) -> object:
		"""Return exact authoritative chemistry facts without mutation."""
		return oasa.cdml_molecule_summary.query_session(self, query)

	#============================================
	def query_molecule_smiles(
			self, request: CDMLMoleculeSmilesQuery,
			) -> CDMLMoleculeSmilesResult:
		"""Return canonical isomeric SMILES without changing session state."""
		molecule_id = _validate_molecule_smiles_query(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		try:
			oasa_molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(
				molecule,
			)
			if oasa_molecule is None:
				raise ValueError("CDML molecule has no supported chemistry conversion")
			smiles = oasa.codecs.rdkit_formats.depiction_stereo_smiles_mol_to_text(
				oasa_molecule,
			)
		except (
				AttributeError, IndexError, KeyError, RuntimeError,
				TypeError, ValueError,
			) as error:
			raise CDMLMoleculeSmilesUnavailableError(
				f"molecule SMILES query is unavailable for direct-root molecule: {molecule_id}",
			) from error
		return CDMLMoleculeSmilesResult(self._revision, molecule_id, smiles)

	#============================================
	def delete_structure(
			self, request: CDMLStructureDeleteRequest,
			) -> CDMLStructureDeleteResult:
		"""Atomically remove direct atoms or bonds from one eligible root molecule.

		The operation has a deliberately narrower grammar than full molecule
		edits.  It accepts only direct core atom and bond children, retains opaque
		content below those owned nodes, and makes component root allocation a
		backend concern before ordinary complete-CDML acceptance.
		"""
		molecule_id, atom_ids, bond_ids = _validate_structure_delete_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		_validate_structure_delete_molecule(molecule)
		atoms, bonds = _structure_delete_direct_nodes(molecule)
		if any(identifier not in atoms for identifier in atom_ids):
			raise CDMLValidationError("structure deletion atom target is not a direct durable atom")
		if any(identifier not in bonds for identifier in bond_ids):
			raise CDMLValidationError("structure deletion bond target is not a direct durable bond")
		removed_atom_ids, removed_bond_ids, components = _structure_delete_components(
			atoms, bonds, atom_ids, bond_ids,
		)
		if any(role.target_identifier == molecule_id for role in candidate.reaction_roles()):
			if len(components) != 1:
				raise CDMLValidationError(
					"structure deletion cannot remove or split a reaction-referenced molecule",
				)
		root = candidate._dom_document.documentElement
		component_records = []
		if not components:
			root.removeChild(molecule)
		elif len(components) == 1:
			component_atom_ids, component_bond_ids = components[0]
			_remove_structure_delete_children(molecule, component_atom_ids, component_bond_ids)
			component_records.append(CDMLStructureDeleteComponent(
				molecule_id, component_atom_ids, component_bond_ids,
			))
		else:
			used_ids = _candidate_durable_ids(candidate)
			first_atom_ids, first_bond_ids = components[0]
			later_components = []
			for component_atom_ids, component_bond_ids in components[1:]:
				component_molecule_id = _next_durable_id("molecule", used_ids)
				used_ids.add(component_molecule_id)
				component = _structure_delete_component_root(
					candidate, molecule, component_molecule_id,
					component_atom_ids, component_bond_ids,
				)
				later_components.append((
					component_molecule_id, component_atom_ids, component_bond_ids, component,
				))
			_remove_structure_delete_children(molecule, first_atom_ids, first_bond_ids)
			component_records.append(CDMLStructureDeleteComponent(
				molecule_id, first_atom_ids, first_bond_ids,
			))
			insertion_reference = molecule.nextSibling
			for component_molecule_id, component_atom_ids, component_bond_ids, component in later_components:
				root.insertBefore(component, insertion_reference)
				component_records.append(CDMLStructureDeleteComponent(
					component_molecule_id, component_atom_ids, component_bond_ids,
				))
		if component_records:
			import oasa.cdml_linear_form
			oasa.cdml_linear_form.remove_invalid_generated_forms(
				candidate, tuple(record.molecule_id for record in component_records),
			)
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLStructureDeleteResult(
			commit=commit,
			removed_atom_ids=removed_atom_ids,
			removed_bond_ids=removed_bond_ids,
			components=tuple(component_records),
		)

	#============================================
	def extract_structure_fragment(
			self, query: CDMLStructureFragmentExtractionQuery,
			) -> CDMLStructureFragmentExtractionResult:
		"""Return one detached, insertion-valid structural clipboard fragment.

		This is a read-only observation.  It validates the same narrow source
		molecule grammar as structural deletion and the shared insertion grammar
		before returning any clipboard data.
		"""
		molecule_id, atom_ids, bond_ids = _validate_structure_fragment_extraction_query(query)
		self._check_expected_revision(query.expected_revision)
		try:
			molecule = _direct_root_molecule(self._document, molecule_id)
			_validate_structure_delete_molecule(molecule)
			atoms, bonds = _structure_delete_direct_nodes(molecule)
			copied_atom_ids, copied_bond_ids = _structure_fragment_selection(
				atoms, bonds, atom_ids, bond_ids,
			)
			fragment = _structure_fragment_document(
				molecule, copied_atom_ids, copied_bond_ids,
			)
			_validate_structure_fragment_insertion_path(fragment)
		except CDMLStructureFragmentExtractionError:
			raise
		except CDMLValidationError as exc:
			raise CDMLStructureFragmentExtractionError(
				"structure fragment extraction source is unavailable",
			) from exc
		return CDMLStructureFragmentExtractionResult(
			self._revision, fragment.serialize(), copied_atom_ids, copied_bond_ids,
		)

	#============================================
	def extract_top_level_fragment(
			self, query: CDMLTopLevelFragmentExtractionQuery,
			) -> CDMLTopLevelFragmentExtractionResult:
		"""Return selected durable direct roots as one insertion-valid CDML fragment.

		The query observes one exact snapshot only.  It neither creates history nor
		changes the saved baseline, and it validates the detached result through the
		same top-level insertion grammar used by Paste.
		"""
		root_ids = _validate_top_level_fragment_extraction_query(query)
		self._check_expected_revision(query.expected_revision)
		try:
			selected_roots = _top_level_fragment_selection(self._document, root_ids)
			fragment = _top_level_fragment_document(selected_roots)
			_validate_top_level_fragment_insertion_path(fragment)
		except CDMLTopLevelFragmentExtractionError:
			raise
		except CDMLDocumentError as exc:
			raise CDMLTopLevelFragmentExtractionError(
				"top-level fragment extraction source is unavailable",
			) from exc
		return CDMLTopLevelFragmentExtractionResult(
			self._revision, fragment.serialize(), tuple(
				child.getAttribute("id") for child in selected_roots
			),
		)

	#============================================
	def delete_top_level(self, request: CDMLTopLevelDeleteRequest) -> CDMLCommit:
		"""Atomically remove selected durable core records from the root stack.

		The request is deliberately narrower than a generic XML deletion: it only
		addresses direct core-CDML records with durable IDs.  This preserves opaque
		extensions and leaves structural atom/bond editing to its separate grammar.
		"""
		if not isinstance(request, CDMLTopLevelDeleteRequest):
			raise CDMLValidationError("top-level deletion requires a deletion request")
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("top-level deletion expected_revision must be an int")
		if request.label is not None and not isinstance(request.label, str):
			raise CDMLValidationError("top-level deletion label must be a string or None")
		if (
			not isinstance(request.root_ids, tuple)
			or not request.root_ids
			or any(not isinstance(identifier, str) or not identifier for identifier in request.root_ids)
			or len(set(request.root_ids)) != len(request.root_ids)
		):
			raise CDMLValidationError(
				"top-level deletion root_ids must be unique nonempty strings",
			)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		root = candidate._dom_document.documentElement
		eligible = {}
		for child in _element_children(root):
			if (
				_is_cdml_element(child)
				and _local_name(child) in _TOP_LEVEL_DELETE_NAMES
				and child.getAttribute("id")
			):
				eligible[child.getAttribute("id")] = child
		missing = [identifier for identifier in request.root_ids if identifier not in eligible]
		if missing:
			raise CDMLValidationError(
				"top-level deletion target is not a supported durable root: %s" % missing[0],
			)
		target_ids = frozenset(request.root_ids)
		for role in candidate.reaction_roles():
			if role.target_identifier in target_ids:
				raise CDMLValidationError(
					"top-level deletion target is referenced by reaction role: %s" % role.target_identifier,
				)
		for identifier in request.root_ids:
			root.removeChild(eligible[identifier])
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def repair_geometry(
			self, request: CDMLGeometryRepairRequest,
			) -> CDMLGeometryRepairResult:
		"""Run one supported geometry repair through the authoritative CDML path."""
		if not isinstance(request, CDMLGeometryRepairRequest):
			raise CDMLValidationError("geometry repair requires a geometry repair request")
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("geometry repair expected_revision must be an int")
		if request.kind not in (
				"normalize-bond-lengths", "normalize-bond-angles", "clean-geometry",
				"snap-to-hex-grid", "straighten-bonds", "normalize-rings",
				):
			raise CDMLValidationError("unsupported geometry repair kind: %s" % request.kind)
		if (
			not isinstance(request.molecule_ids, tuple)
			or not request.molecule_ids
			or any(not isinstance(identifier, str) or not identifier for identifier in request.molecule_ids)
			or len(set(request.molecule_ids)) != len(request.molecule_ids)
		):
			raise CDMLValidationError(
				"geometry repair molecule_ids must be unique nonempty strings",
			)
		if (
			isinstance(request.target_spacing_pt, bool)
			or not isinstance(request.target_spacing_pt, (int, float))
			or not math.isfinite(request.target_spacing_pt)
			or request.target_spacing_pt <= 0
		):
			raise CDMLValidationError(
				"geometry repair target_spacing_pt must be a finite positive number",
			)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		try:
			import oasa.cdml_geometry_repair
			if request.kind == "normalize-bond-lengths":
				oasa.cdml_geometry_repair.normalize_bond_lengths_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			elif request.kind == "normalize-bond-angles":
				oasa.cdml_geometry_repair.normalize_bond_angles_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			elif request.kind == "straighten-bonds":
				oasa.cdml_geometry_repair.straighten_bonds_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			elif request.kind == "normalize-rings":
				oasa.cdml_geometry_repair.normalize_rings_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			elif request.kind == "clean-geometry":
				oasa.cdml_geometry_repair.clean_geometry_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			else:
				oasa.cdml_geometry_repair.snap_to_hex_grid_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
		except ValueError as exc:
			raise CDMLValidationError(str(exc)) from exc
		import oasa.cdml_linear_form
		oasa.cdml_linear_form.remove_invalid_generated_forms(candidate, request.molecule_ids)
		candidate.validate(validation="strict")
		if candidate.serialize() == self._document.serialize():
			return CDMLGeometryRepairResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLGeometryRepairResult(commit.snapshot, True, commit)

	#============================================
	def align_atoms(self, request: CDMLAtomAlignRequest) -> CDMLAtomAlignResult:
		"""Align direct-root durable atoms on one authoritative coordinate axis."""
		if not isinstance(request, CDMLAtomAlignRequest):
			raise CDMLValidationError("atom alignment requires an atom alignment request")
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("atom alignment expected_revision must be an int")
		if request.axis not in ("horizontal", "vertical"):
			raise CDMLValidationError("atom alignment axis must be horizontal or vertical")
		if not isinstance(request.targets, tuple) or not request.targets:
			raise CDMLValidationError("atom alignment targets must be a nonempty immutable tuple")
		if any(
				not isinstance(target, tuple) or len(target) != 2
				or any(not isinstance(identifier, str) or not identifier for identifier in target)
				for target in request.targets
			):
			raise CDMLValidationError("atom alignment targets must contain nonempty ID pairs")
		if len(set(request.targets)) != len(request.targets):
			raise CDMLValidationError("atom alignment targets must be unique")
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		root = candidate._dom_document.documentElement
		molecules = {
			child.getAttribute("id"): child
			for child in _element_children(root)
			if _is_cdml_element(child) and _local_name(child) == "molecule" and child.getAttribute("id")
		}
		points = []
		for molecule_id, atom_id in request.targets:
			molecule = molecules.get(molecule_id)
			if molecule is None:
				raise CDMLValidationError(
					"atom alignment target is not a durable direct-root molecule: %s" % molecule_id,
				)
			atoms = {
				child.getAttribute("id"): child
				for child in _element_children(molecule)
				if _is_cdml_element(child) and _local_name(child) == "atom" and child.getAttribute("id")
			}
			atom = atoms.get(atom_id)
			if atom is None:
				raise CDMLValidationError(
					"atom alignment target is not a durable direct molecule atom: %s" % atom_id,
				)
			atom_points = [
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			]
			if len(atom_points) != 1:
				raise CDMLValidationError("atom alignment atom requires one direct core point")
			point = atom_points[0]
			if not point.hasAttribute("x") or not point.hasAttribute("y"):
				raise CDMLValidationError("atom alignment point requires x and y")
			# Convert through the established coordinate parser before mutation.
			x = _insertion_coordinate(point.getAttribute("x"))
			y = _insertion_coordinate(point.getAttribute("y"))
			points.append((point, x, y))
		if len(points) < 2:
			return CDMLAtomAlignResult(self.snapshot(), False, None)
		axis_index = 2 if request.axis == "horizontal" else 1
		# Equal selected-axis coordinates are a semantic no-op. Decide this before
		# calculating the mean or touching the detached DOM so compatible lexical
		# spellings such as ``3cm`` remain byte-for-byte preserved.
		axis_coordinates = tuple(point[axis_index] for point in points)
		if all(coordinate == axis_coordinates[0] for coordinate in axis_coordinates[1:]):
			return CDMLAtomAlignResult(self.snapshot(), False, None)
		mean = sum(axis_coordinates) / len(axis_coordinates)
		if not math.isfinite(mean):
			raise CDMLValidationError("atom alignment mean coordinate is nonfinite")
		attribute = "y" if request.axis == "horizontal" else "x"
		for point, _x, _y in points:
			point.setAttribute(attribute, f"{mean:.3f}cm")
		import oasa.cdml_linear_form
		oasa.cdml_linear_form.remove_invalid_generated_forms(
			candidate, tuple(dict.fromkeys(molecule_id for molecule_id, _atom_id in request.targets)),
		)
		candidate.validate(validation="strict")
		if candidate.serialize() == self._document.serialize():
			return CDMLAtomAlignResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLAtomAlignResult(commit.snapshot, True, commit)

	#============================================
	def apply_top_level_transform(
			self, request: CDMLTopLevelTransformRequest,
			) -> CDMLTopLevelTransformResult:
		"""Apply one bounded affine transform to selected durable direct roots.

		All persistent geometry and pivots come from the accepted CDML snapshot.
		Validation completes before a detached candidate is created, so unsupported
		or malformed later roots cannot produce a partial transform.
		"""
		mode, root_ids, scale_x, scale_y, delta = _validate_top_level_transform_request(request)
		self._check_expected_revision(request.expected_revision)
		geometries = _direct_top_level_transform_roots(self._document, root_ids)
		if mode == "translate" and delta == (0.0, 0.0):
			return CDMLTopLevelTransformResult(self.snapshot(), False, None)
		minimum_x = min(geometry.bounds[0] for geometry in geometries)
		minimum_y = min(geometry.bounds[1] for geometry in geometries)
		maximum_x = max(geometry.bounds[2] for geometry in geometries)
		maximum_y = max(geometry.bounds[3] for geometry in geometries)
		if mode == "translate":
			transforms = [delta for _geometry in geometries]
		elif mode == "align-top":
			transforms = [(0.0, minimum_y - geometry.bounds[1]) for geometry in geometries]
		elif mode == "align-bottom":
			transforms = [(0.0, maximum_y - geometry.bounds[3]) for geometry in geometries]
		elif mode == "align-left":
			transforms = [(minimum_x - geometry.bounds[0], 0.0) for geometry in geometries]
		elif mode == "align-right":
			transforms = [(maximum_x - geometry.bounds[2], 0.0) for geometry in geometries]
		elif mode in ("align-center-x", "align-center-y"):
			axis = 0 if mode == "align-center-x" else 1
			centers = [
				(geometry.bounds[axis] + geometry.bounds[axis + 2]) / 2.0
				for geometry in geometries
			]
			target_center = (min(centers) + max(centers)) / 2.0
			transforms = [
				((target_center - center, 0.0) if axis == 0 else (0.0, target_center - center))
				for center in centers
			]
		else:
			pivot_x = (minimum_x + maximum_x) / 2.0
			pivot_y = (minimum_y + maximum_y) / 2.0
			if mode == "scale":
				factors = (scale_x, scale_y)
			elif mode == "mirror-vertical":
				factors = (-1.0, 1.0)
			else:
				factors = (1.0, -1.0)
			transforms = [(pivot_x, pivot_y, factors[0], factors[1]) for _geometry in geometries]
		if mode == "translate" or mode.startswith("align-"):
			for geometry, (dx, dy) in zip(geometries, transforms, strict=True):
				if not math.isfinite(dx) or not math.isfinite(dy):
					raise CDMLTopLevelTransformError("top-level transform coordinate is nonfinite")
				for _element, _x_name, _y_name, x, y in geometry.pairs:
					if not math.isfinite(x + dx) or not math.isfinite(y + dy):
						raise CDMLTopLevelTransformError("top-level transform coordinate is nonfinite")
		else:
			_validate_top_level_affine_results(geometries, transforms)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_geometries = _direct_top_level_transform_roots(candidate, root_ids)
		if mode == "translate" or mode.startswith("align-"):
			for geometry, (dx, dy) in zip(candidate_geometries, transforms, strict=True):
				_align_top_level_geometry(geometry, dx, dy)
		else:
			for geometry, (pivot_x, pivot_y, factor_x, factor_y) in zip(
				candidate_geometries, transforms, strict=True,
			):
				_transform_top_level_geometry(geometry, pivot_x, pivot_y, factor_x, factor_y)
		import oasa.cdml_linear_form
		oasa.cdml_linear_form.remove_invalid_generated_forms(
			candidate,
			tuple(
				child.getAttribute("id") for child in _element_children(
					candidate._dom_document.documentElement,
				)
				if _is_cdml_element(child) and _local_name(child) == "molecule"
				and child.getAttribute("id") in root_ids
			),
		)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLTopLevelTransformResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLTopLevelTransformResult(commit.snapshot, True, commit)

	#============================================
	def translate_atoms(self, request: CDMLAtomTranslateRequest) -> CDMLAtomTranslateResult:
		"""Translate selected direct-core atom points through one atomic commit.

		The request expresses its delta in PostScript scene points. Validate every
		durable target and coordinate against the accepted snapshot before making a
		detached candidate, so an invalid later target cannot partially move an
		earlier atom.
		"""
		targets, (dx_cm, dy_cm) = _validate_atom_translate_request(request)
		self._check_expected_revision(request.expected_revision)
		points = []
		for molecule_id, atom_id in targets:
			molecule = _direct_root_molecule(self._document, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			_point, x, y = _atom_translation_point(atom, error_type=CDMLValidationError)
			points.append((molecule_id, atom_id, x, y))
		if dx_cm == 0.0 and dy_cm == 0.0:
			return CDMLAtomTranslateResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		for molecule_id, atom_id, x, y in points:
			molecule = _direct_root_molecule(candidate, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			point = next(
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			)
			# Preserve the untouched source attribute exactly. Compatible CDML may
			# use unitless PostScript points that parsing would otherwise rewrite.
			new_x, new_y = _atom_translation_result(
				x, y, dx_cm, dy_cm,
				error_type=CDMLValidationError, canonical_noop=False,
			)
			if new_x is not None:
				point.setAttribute("x", new_x)
			if new_y is not None:
				point.setAttribute("y", new_y)
		import oasa.cdml_linear_form
		oasa.cdml_linear_form.remove_invalid_generated_forms(
			candidate, tuple(dict.fromkeys(molecule_id for molecule_id, _atom_id in targets)),
		)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLAtomTranslateResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLAtomTranslateResult(commit.snapshot, True, commit)

	#============================================
	def translate_selection(
				self, request: CDMLSelectionTranslateRequest,
				) -> CDMLSelectionTranslateResult:
		"""Translate mixed direct atoms and presentation roots as one transaction.

		The request is deliberately narrower than a general transform: every atom
		and presentation root is resolved against one authoritative snapshot before
		any candidate exists.  Both halves therefore either commit together or
		leave the complete document untouched.
		"""
		atom_targets, root_ids, (dx_cm, dy_cm) = _validate_selection_translate_request(request)
		self._check_expected_revision(request.expected_revision)
		try:
			atom_geometries = []
			for molecule_id, atom_id in atom_targets:
				molecule = _direct_root_molecule(self._document, molecule_id)
				atom = _direct_molecule_atom(molecule, atom_id)
				geometry = _selection_translate_atom_geometry(atom, dx_cm, dy_cm)
				atom_geometries.append((molecule_id, atom_id, geometry))
			geometries = _direct_selection_translate_roots(self._document, root_ids)
			for geometry in geometries:
				for _element, _x_name, _y_name, x, y in geometry.pairs:
					if not math.isfinite(x + dx_cm) or not math.isfinite(y + dy_cm):
						raise CDMLSelectionTranslateError(
							"selection translation coordinate is nonfinite",
						)
			if dx_cm == 0.0 and dy_cm == 0.0:
				return CDMLSelectionTranslateResult(self.snapshot(), False, None)
			presentation_changes = any(
				_canonical_authored_coordinate(x) != _canonical_authored_coordinate(x + dx_cm)
				or _canonical_authored_coordinate(y) != _canonical_authored_coordinate(y + dy_cm)
				for geometry in geometries
				for _element, _x_name, _y_name, x, y in geometry.pairs
			)
			atom_changes = any(
				coordinate.new_x is not None or coordinate.new_y is not None
				for _molecule_id, _atom_id, geometry in atom_geometries
				for coordinate in geometry.coordinates
			)
			if not presentation_changes and not atom_changes:
				return CDMLSelectionTranslateResult(self.snapshot(), False, None)
			candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
			for molecule_id, atom_id, _geometry in atom_geometries:
				molecule = _direct_root_molecule(candidate, molecule_id)
				atom = _direct_molecule_atom(molecule, atom_id)
				candidate_geometry = _selection_translate_atom_geometry(atom, dx_cm, dy_cm)
				_apply_selection_translate_atom_geometry(candidate_geometry)
			candidate_geometries = _direct_selection_translate_roots(candidate, root_ids)
			for geometry in candidate_geometries:
				try:
					_align_top_level_geometry(geometry, dx_cm, dy_cm)
				except CDMLTopLevelTransformError as error:
					raise CDMLSelectionTranslateError(
						"selection translation root has invalid geometry",
					) from error
			import oasa.cdml_linear_form
			oasa.cdml_linear_form.remove_invalid_generated_forms(
				candidate, tuple(dict.fromkeys(molecule_id for molecule_id, _atom_id in atom_targets)),
			)
			candidate.validate(validation="strict")
			candidate_cdml = candidate.serialize()
			if candidate_cdml == self._document.serialize():
				return CDMLSelectionTranslateResult(self.snapshot(), False, None)
			commit = self.commit(
				expected_revision=request.expected_revision,
				complete_cdml=candidate_cdml,
			)
		except CDMLSelectionTranslateError:
			raise
		except CDMLValidationError as error:
			raise CDMLSelectionTranslateError(
				"selection translation target or candidate is invalid",
			) from error
		return CDMLSelectionTranslateResult(commit.snapshot, True, commit)

	#============================================
	def rotate_atoms(self, request: CDMLAtomRotateRequest) -> CDMLAtomRotateResult:
		"""Rotate selected direct-core atom points through one atomic commit.

		The center arrives in PostScript scene points, matching frontend preview
		coordinates.  Convert it once at this boundary, validate every target in
		the authoritative snapshot, and then rotate the detached candidate using
		the same positive-angle convention as the 2D preview.
		"""
		targets, (center_x, center_y), angle = _validate_atom_rotate_request(request)
		self._check_expected_revision(request.expected_revision)
		points = []
		for molecule_id, atom_id in targets:
			molecule = _direct_root_molecule(self._document, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			atom_points = [
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			]
			if len(atom_points) != 1:
				raise CDMLValidationError("atom rotation atom requires one direct core point")
			point = atom_points[0]
			if not point.hasAttribute("x") or not point.hasAttribute("y"):
				raise CDMLValidationError("atom rotation point requires x and y")
			x = _insertion_coordinate(point.getAttribute("x"))
			y = _insertion_coordinate(point.getAttribute("y"))
			points.append((molecule_id, atom_id, x, y))
		cosine = math.cos(angle)
		sine = math.sin(angle)
		rotations = []
		for molecule_id, atom_id, x, y in points:
			rotated_x = center_x + (x - center_x) * cosine - (y - center_y) * sine
			rotated_y = center_y + (x - center_x) * sine + (y - center_y) * cosine
			if not math.isfinite(rotated_x) or not math.isfinite(rotated_y):
				raise CDMLValidationError("atom rotation coordinate is nonfinite")
			canonical_x = _canonical_authored_coordinate(rotated_x)
			canonical_y = _canonical_authored_coordinate(rotated_y)
			rotations.append((
				molecule_id, atom_id, x, y, canonical_x, canonical_y,
			))
		if all(
				_canonical_authored_coordinate(x) == canonical_x
				and _canonical_authored_coordinate(y) == canonical_y
				for _molecule_id, _atom_id, x, y, canonical_x, canonical_y
				in rotations
			):
			return CDMLAtomRotateResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		for molecule_id, atom_id, x, y, canonical_x, canonical_y in rotations:
			molecule = _direct_root_molecule(candidate, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			point = next(
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			)
			if _canonical_authored_coordinate(x) != canonical_x:
				point.setAttribute("x", canonical_x)
			if _canonical_authored_coordinate(y) != canonical_y:
				point.setAttribute("y", canonical_y)
		import oasa.cdml_linear_form
		oasa.cdml_linear_form.remove_invalid_generated_forms(
			candidate, tuple(dict.fromkeys(molecule_id for molecule_id, _atom_id in targets)),
		)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLAtomRotateResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLAtomRotateResult(commit.snapshot, True, commit)

	#============================================
	def expand_implicit_group(
			self, request: CDMLImplicitGroupExpandRequest,
			) -> CDMLImplicitGroupExpandResult:
		"""Expand one direct implicit group without rewriting its containing graph.

		The replacement graph is generated in detached OASA state.  Its local
		coordinates are aligned to the existing exterior bond, so an expansion
		cannot move any pre-existing atom in the authoritative document.
		"""
		if type(request) is not CDMLImplicitGroupExpandRequest:
			raise CDMLImplicitGroupExpandError("implicit expansion requires an exact request")
		if type(request.expected_revision) is not int:
			raise CDMLImplicitGroupExpandError("implicit expansion expected_revision must be an int")
		if type(request.molecule_id) is not str or not request.molecule_id:
			raise CDMLImplicitGroupExpandError("implicit expansion molecule_id is required")
		if type(request.group_id) is not str or not request.group_id:
			raise CDMLImplicitGroupExpandError("implicit expansion group_id is required")
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, request.molecule_id)
		group = _direct_core_child_by_id(molecule, request.group_id, "group")
		(
			group_name, anchor_x, anchor_y, exterior_bond, exterior_atom, exterior_order,
		) = _implicit_group_source(molecule, group)
		dx = anchor_x - exterior_atom[0]
		dy = anchor_y - exterior_atom[1]
		bond_length = math.hypot(dx, dy)
		if not math.isfinite(bond_length) or bond_length <= 0:
			raise CDMLImplicitGroupExpandError("implicit group exterior bond must have length")
		try:
			plan = oasa.group_expansion.plan_group_expansion(
				"implicit", group_name, None,
				oasa.group_expansion.GroupAnchor(request.group_id, anchor_x, anchor_y),
				(oasa.group_expansion.GroupAttachment(
					exterior_bond.getAttribute("id"),
					exterior_bond.getAttribute("start")
					if exterior_bond.getAttribute("end") == request.group_id
					else exterior_bond.getAttribute("end"),
					exterior_order,
				),),
				oasa.molecule_lib.Molecule,
				bond_length=bond_length,
			)
		except (TypeError, ValueError) as exc:
			raise CDMLImplicitGroupExpandError(str(exc)) from exc
		graph = plan.graph
		replacement = graph.vertices[plan.replacement_vertex_index]
		layout_stub = graph.create_vertex()
		layout_stub.symbol = "C"
		graph.add_vertex(layout_stub)
		layout_edge = graph.create_edge()
		layout_edge.order = exterior_order
		graph.add_edge(replacement, layout_stub, e=layout_edge)
		for vertex in graph.vertices:
			vertex.x = None
			vertex.y = None
		try:
			oasa.coords_generator.calculate_coords(graph, bond_length=bond_length, force=1)
		except (ArithmeticError, IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
				raise CDMLImplicitGroupExpandError(
					"implicit group replacement layout failed: %s" % exc,
				) from exc
		_align_group_graph(graph, replacement, anchor_x, anchor_y, -dx, -dy, layout_stub)
		graph.remove_vertex(layout_stub)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, request.molecule_id)
		candidate_group = _direct_core_child_by_id(candidate_molecule, request.group_id, "group")
		candidate_bond = _direct_molecule_bond(candidate_molecule, exterior_bond.getAttribute("id"))
		used_ids = _candidate_durable_ids(candidate)
		used_ids.add(request.group_id)
		try:
			serialized = oasa.cdml_writer.write_cdml_molecule_element(
				graph,
				coord_to_text=_canonical_authored_coordinate,
				reserved_atom_ids=used_ids,
				reserved_bond_ids=used_ids,
			)
		except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
			raise CDMLImplicitGroupExpandError(
				"implicit group replacement serialization failed: %s" % exc,
			) from exc
		atom_elements = [child for child in _element_children(serialized)
			if _local_name(child) == "atom"]
		bond_elements = [child for child in _element_children(serialized)
			if _local_name(child) == "bond"]
		if not atom_elements:
			raise CDMLImplicitGroupExpandError("implicit group formula produced no atoms")
		replacement_atom_id = atom_elements[plan.replacement_vertex_index].getAttribute("id")
		for element in atom_elements + bond_elements:
			candidate_molecule.insertBefore(
				candidate._dom_document.importNode(element, deep=True), candidate_group,
			)
		if candidate_bond.getAttribute("start") == request.group_id:
			candidate_bond.setAttribute("start", replacement_atom_id)
		elif candidate_bond.getAttribute("end") == request.group_id:
			candidate_bond.setAttribute("end", replacement_atom_id)
		else:
			raise CDMLImplicitGroupExpandError("implicit group exterior bond is stale")
		candidate_molecule.removeChild(candidate_group)
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLImplicitGroupExpandResult(
			commit, replacement_atom_id,
			tuple(atom.getAttribute("id") for atom in atom_elements),
			tuple(bond.getAttribute("id") for bond in bond_elements),
		)

	#============================================
	def set_bond_order(self, request: CDMLBondOrderEditRequest) -> CDMLBondOrderEditResult:
		"""Set one direct core bond's exact order without changing its type or depiction.

		The operation validates the entire editable target against the accepted
		snapshot before detaching a candidate.  It retains the existing supported
		type character, including styled bonds such as ``w2``, and changes only the
		order digit in ``bond@type``.
		"""
		molecule_id, bond_id, requested_order = _validate_bond_order_edit_request(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		bond = _direct_molecule_bond(molecule, bond_id)
		_require_editable_bond_endpoints(molecule, bond)
		if bond.hasAttribute("order"):
			raise CDMLValidationError("bond order edit rejects an independent bond@order attribute")
		type_char, current_order = _editable_bond_type(bond.getAttribute("type"))
		if type_char == "q" and requested_order != 1:
			raise CDMLValidationError("bond order edit Haworth bonds require order 1")
		if current_order == requested_order:
			return CDMLBondOrderEditResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_bond = _direct_molecule_bond(candidate_molecule, bond_id)
		candidate_bond.setAttribute("type", "%s%s" % (type_char, requested_order))
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLBondOrderEditResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLBondOrderEditResult(commit.snapshot, True, commit)

	#============================================
	def set_bond_type(self, request: CDMLBondTypeEditRequest) -> CDMLBondTypeEditResult:
		"""Set one direct core bond's exact ordinary type without changing its order.

		Compatibility ``l1`` and ``r1`` spellings are semantically hashed wedges:
		requesting ``h`` preserves their original lexical spelling, while another
		ordinary request replaces only the type character.  A current ``q1``
		Haworth edge may similarly become an ordinary type.
		"""
		molecule_id, bond_id, requested_type = _validate_bond_type_edit_request(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		bond = _direct_molecule_bond(molecule, bond_id)
		_require_editable_bond_endpoints(molecule, bond)
		if bond.hasAttribute("order"):
			raise CDMLValidationError("bond type edit rejects an independent bond@order attribute")
		current_type, current_order = _editable_bond_type_for_type_edit(
			bond.getAttribute("type"),
		)
		if current_type in ("l", "r") and requested_type == "h":
			return CDMLBondTypeEditResult(self.snapshot(), False, None)
		if current_type == requested_type:
			return CDMLBondTypeEditResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_bond = _direct_molecule_bond(candidate_molecule, bond_id)
		candidate_bond.setAttribute("type", "%s%s" % (requested_type, current_order))
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLBondTypeEditResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLBondTypeEditResult(commit.snapshot, True, commit)

	#============================================
	def patch_bond_properties(
			self, request: CDMLBondPropertiesPatch,
			) -> CDMLBondPropertiesPatchResult:
		"""Apply one explicit bond-property intent atomically through CDML.

		Order and type are interpreted as one final spelling.  All target and
		grammar checks precede the detached candidate so malformed late fields or
		unsupported final combinations cannot leave a partial backend commit.
		"""
		molecule_id, bond_id, changes = _validate_bond_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		bond = _direct_molecule_bond(molecule, bond_id)
		_require_editable_bond_endpoints(molecule, bond)
		if bond.hasAttribute("order"):
			raise CDMLBondPropertiesPatchError(
				"bond properties rejects an independent bond@order attribute",
			)
		current_type, current_order = _editable_bond_type_for_type_edit(
			bond.getAttribute("type"),
		)
		change_map = dict(changes)
		final_order = change_map.get("order", current_order)
		requested_type = change_map.get("type")
		if current_type in ("l", "r") and requested_type == "h" and final_order == 1:
			final_type = current_type
		elif requested_type is None:
			final_type = current_type
		else:
			final_type = requested_type
		compatibility_hashed = current_type in ("l", "r") and requested_type == "h" and final_order == 1
		if ("order" in change_map or "type" in change_map) and not compatibility_hashed:
			if not oasa.bond_semantics.is_authored_bond_order(final_type, final_order):
				raise CDMLBondPropertiesPatchError(
					"bond properties final type/order is unsupported",
				)
		if not changes:
			return CDMLBondPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_bond = _direct_molecule_bond(candidate_molecule, bond_id)
		if "order" in change_map or "type" in change_map:
			candidate_bond.setAttribute("type", "%s%s" % (final_type, final_order))
		for field_name, value in changes:
			if field_name in ("order", "type"):
				continue
			if field_name == "center":
				candidate_bond.setAttribute("center", "yes" if value else "no")
			elif field_name in ("line_width", "bond_width", "wedge_width"):
				candidate_bond.setAttribute(field_name, "%g" % value)
			else:
				candidate_bond.setAttribute("color", value)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLBondPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLBondPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def restore(self, *, target_revision: int, expected_revision: int) -> CDMLCommit:
		"""Restore retained content as a new monotonic backend revision."""
		self._check_expected_revision(expected_revision)
		if target_revision not in self._history:
			raise CDMLRevisionUnavailableError(
				f"CDML revision is not retained: {target_revision}",
		)
		target_cdml = self._history[target_revision].serialize()
		restored = CDMLDocument.parse(target_cdml, validation="strict")
		# Capture the pre-restore current revision before accepting the forward
		# revision.  The next restore can then redo this exact content.
		return self._accept_document(restored, {}, redo_revision=self._revision)

	#============================================
	def mark_saved(self, *, expected_revision: int) -> CDMLSnapshot:
		"""Set the current authoritative content as the clean saved baseline."""
		self._check_expected_revision(expected_revision)
		self._saved_cdml = self._document.serialize()
		self._saved_digest = _content_digest(self._saved_cdml)
		self._saved_revision = self._revision
		self._prune_history()
		return self.snapshot()

	#============================================
	def _check_expected_revision(self, expected_revision: int) -> None:
		"""Require optimistic-concurrency callers to name the current revision."""
		if expected_revision != self._revision:
			raise CDMLRevisionConflictError(
				f"expected revision {expected_revision}, current revision is {self._revision}",
			)

	#============================================
	def _accept_document(
		self,
		document: CDMLDocument,
		id_map: dict[str, str],
		*,
		redo_revision: int | None,
	) -> CDMLCommit:
		"""Install one already-valid document and retain it under a new revision."""
		self._revision += 1
		self._document = document
		self._history[self._revision] = document
		self._redo_revision = redo_revision
		self._prune_history()
		immutable_id_map = types.MappingProxyType(dict(id_map))
		commit = CDMLCommit(snapshot=self.snapshot(), id_map=immutable_id_map)
		return commit

	#============================================
	def _prune_history(self) -> None:
		"""Bound history while retaining current, saved, and immediate redo content."""
		protected_revisions = {self._revision, self._saved_revision}
		if self._redo_revision is not None:
			protected_revisions.add(self._redo_revision)
		while len(self._history) > self._history_capacity:
			removable_revisions = [
				revision for revision in sorted(self._history)
				if revision not in protected_revisions
			]
			if not removable_revisions:
				raise CDMLValidationError("history capacity cannot retain required revisions")
			del self._history[removable_revisions[0]]

#============================================
def _content_digest(text: str) -> str:
	"""Return a stable content digest used for backend dirty-state comparison."""
	digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
	return digest
