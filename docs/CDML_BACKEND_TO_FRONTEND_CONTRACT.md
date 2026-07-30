# CDML backend-to-frontend contract

This is the stable behavioral boundary between the CDML backend and a frontend.
It defines observable persistence behavior, not a particular language,
UI-toolkit, or scene-graph implementation.

It is not the CDML element grammar, version registry, schema, or validator.
Those format concerns are defined by
[CDML_FORMAT_SPEC.md](CDML_FORMAT_SPEC.md); this document defines only how a
complete CDML value crosses the backend/frontend transaction boundary. Declared
bounded operations may carry durable IDs and scalar intent, but canonical CDML
remains the sole persistent document boundary.

## Authority and boundary

- The backend owns the complete persistent CDML document and its chemistry
  semantics. It preserves typed and opaque persistent content, including
  order, namespaces, identifiers, references, paper/header data, presentation
  records, and unknown XML.
- The complete direct-child sequence is persistent document order. Drawable
  records retain their relative paint order; header/default/metadata records
  are persistent but are not painted layers.
- A frontend owns disposable projections and transient interaction state only:
  view state, selection, hover, handles, previews, dialogs, and wrapper
  lifetime. It may restore selection only by stable backend-issued IDs.
- CDML is the sole persistent frontend/backend boundary. Requests and results
  use complete CDML, scalar values, and immutable backend-owned values. They
  do not expose frontend objects, callbacks, graphics, or lifetime state.
- A backend round trip preserves complete persistent content. A frontend never
  repairs a backend response by merging state retained from an older
  projection.
- Established preservation-only CDML containers (`display-form`, `user-data`,
  and handler-less `external-data`) retain literal XML payloads. Their
  descendants receive no backend CDML lookup, reference rewrite, provisional
  token, or semantic-normalization behavior, while every literal `id` still
  reserves a document-wide collision name. `external-data@id` is literal
  preservation content rather than an editable provisional declaration.
- The boundary is frontend-neutral. It defines no browser, WASM, TypeScript,
  or other frontend delivery.

## Transaction behavior

An edit proposal starts from one immutable backend snapshot and names that
snapshot's revision. A complete-CDML route supplies a complete candidate; a
declared bounded route supplies only its documented durable targets and scalar
intent. The backend validates and applies either route in detached state, then
either rejects it with a typed failure or accepts it as one final, atomic
commit.

Ordinary complete-document Load and Commit use the compatibility acceptance
frontier: XML-safe content with safe persistent identity and recognized
reference relationships. Acceptance preserves compatible incomplete and opaque
content, but is not a promise that every record has complete authored geometry,
chemistry, or projection support. `authored-26.07` is a stricter opt-in format
assessment for producers that choose to use it. A future authoring operation
declares its own emitted-profile rule; ordinary Load and Commit remain
compatibility-preserving unless that operation explicitly adds such a rule.

An accepted commit:

1. creates one new monotonically increasing revision;
2. installs one canonical complete-CDML snapshot;
3. returns only immutable result values, including any durable-ID mapping; and
4. consumes every provisional token in its candidate, so neither the accepted
   candidate nor any of its tokens can be submitted again.

Rejected requests change neither the current document, revision, saved
baseline, nor retained history. A revision conflict is also a rejection. There
is no partial-success commit.

After acceptance, the accepted snapshot remains authoritative even if a
frontend cannot install its projection. Recovery is limited to exact
reprojection of the accepted/current backend snapshot; retained projection
objects, locally reconstructed XML, and the accepted candidate are not a
recovery source. The client discards the accepted candidate and its tokens;
the backend rejects a resubmission of a consumed token.

## Snapshots, values, and failures

The backend exposes these behavioral operations:

| Operation | Request | Success | Typed failure |
| --- | --- | --- | --- |
| Load | Complete CDML and optional history policy | Clean initial snapshot | Parse or validation failure |
| Snapshot | None | Immutable current snapshot | None |
| Commit | Expected revision and complete candidate CDML | Immutable accepted snapshot and ID mapping | Parse, validation, or revision conflict |
| Insert molecules | Expected revision, complete molecule-only proposal CDML, optional display label | Immutable accepted snapshot and ID mapping | Parse, validation, or revision conflict |
| Insert system template | Expected revision, exact backend-catalog template name, and finite scene-point anchor | Immutable accepted snapshot and ID mapping for the detached inserted root and its records | Invalid input, unknown template, preparation, validation, or revision conflict |
| Insert top level | Expected revision, complete CDML fragment, finite scene-point translation, optional display label | Immutable accepted snapshot and old-to-new durable-ID mapping | Parse, validation, or revision conflict |
| Edit structure | Expected revision; one of `create-bonded-pair`, `extend-atom`, `join-atoms`, or `apply-bond-tool`; direct editable durable targets where applicable; finite scalar positions and bond settings | Immutable accepted canonical snapshot and created or updated durable IDs | Invalid input, target, topology, bond setting, or revision conflict |
| Set atom element | Expected revision, direct-root molecule ID, direct core atom ID, and a different exact supported element symbol | Immutable accepted canonical snapshot | Invalid request, target, element symbol, same symbol, or revision conflict |
| Patch atom properties | Expected revision, direct-root molecule ID, direct core atom ID, and unique explicit field/value pairs for atom chemistry and presentation scalars | Immutable accepted snapshot, or unchanged current snapshot for a canonical no-op | Invalid request, repeated field, target, direct font ambiguity, scalar value, or revision conflict |
| Set atom number | Expected revision, direct-root molecule ID, direct core atom ID, and either a positive integer plus explicit boolean visibility or the exact `(null, null)` clear pair | Immutable accepted canonical snapshot | Invalid request or pair, target, legacy compatibility, or revision conflict |
| Align atoms | Expected revision, exact `horizontal` or `vertical` axis, and nonempty unique direct-root molecule/direct-core-atom ID pairs | Immutable accepted snapshot, or unchanged current snapshot for a semantic coordinate no-op | Invalid request, target, point coordinate, or revision conflict |
| Translate atoms | Expected revision, nonempty unique direct-root molecule/direct-core-atom ID pairs, and a finite two-value scene/PostScript-point delta | Immutable accepted snapshot, or unchanged current snapshot for a canonical coordinate no-op | Invalid request, target, point coordinate, or revision conflict |
| Rotate atoms | Expected revision, nonempty unique direct-root molecule/direct-core-atom ID pairs, one finite two-value scene/PostScript-point center, and one finite angle in radians | Immutable accepted snapshot, or unchanged current snapshot for an exact zero or canonical coordinate no-op | Invalid request, target, point coordinate, angle, or revision conflict |
| Set bond order | Expected revision, direct-root molecule ID, direct core bond ID, and exact order 1, 2, or 3 | Immutable accepted snapshot, or unchanged current snapshot for a matching semantic order | Invalid request, target, bond type/order grammar, Haworth restriction, or revision conflict |
| Set bond type | Expected revision, direct-root molecule ID, direct core bond ID, and exact ordinary type character `n`, `w`, `h`, `a`, `b`, `d`, `o`, or `s` | Immutable accepted snapshot, or unchanged current snapshot for a semantic type no-op | Invalid request, target, current spelling, independent order attribute, endpoint, or revision conflict |
| Patch bond properties | Expected revision, direct-root molecule ID, direct core bond ID, and unique explicit field/value pairs for order, type, center, widths, or six-digit color | Immutable accepted snapshot, or unchanged current snapshot for a canonical no-op | Invalid request, repeated field, target, endpoint, final type/order, depiction value, or revision conflict |
| Set molecule name | Expected revision, direct-root molecule ID, and exact display-name string | Immutable accepted canonical snapshot, or unchanged current snapshot for a no-op | Invalid request, target, or revision conflict |
| Set paper properties | Expected revision plus explicit field intent: recognized type or orientation, boolean crop/minus fields, nonnegative crop margin, and an atomic positive finite dimensions pair only for effective `custom` type | Immutable accepted canonical snapshot, or unchanged current snapshot for a no-op | Invalid request shape, repeated or unsupported field, invalid paper value, or revision conflict |
| Query molecule SMILES | Expected revision and one direct-root molecule durable ID | Immutable revision-tagged canonical/isomeric SMILES value | Invalid request, target, unavailable chemistry conversion, or revision conflict |
| Repair geometry | Expected revision, nonempty direct-root molecule IDs, supported kind, and finite-positive `target_spacing_pt` in PostScript points | Immutable current snapshot; a changed repair includes one immutable accepted commit | Invalid request, target, geometry, or revision conflict |
| Reorder presentation stack | Expected revision, declared `bring-to-front`, `send-back`, or `swap-at-slots` mode, and nonempty unique durable IDs for direct-root core presentation records | Immutable accepted snapshot, or unchanged current snapshot for a no-op | Invalid request, target, mode, or revision conflict |
| Delete top level | Expected revision, nonempty unique durable IDs for supported direct-root records, optional display label | Immutable accepted snapshot | Invalid request, target, reaction reference, or revision conflict |
| Restore | Retained target revision and expected current revision | New immutable accepted snapshot | Revision conflict or unavailable revision |
| Mark saved | Expected current revision after external publication | Immutable current snapshot with updated baseline | Revision conflict |

Insert molecules is a bounded composition operation. Its proposal is a complete
CDML document with one or more direct top-level molecule elements and no other
direct persistent object. The backend appends detached proposal molecules after
the current document's direct children in proposal order, then follows the same
atomic complete-candidate rules as Commit. The optional display label is scalar
operation metadata only and is never persistent CDML.

Rectangular Bracket uses the ordinary complete-candidate Commit operation. A
client supplies one revision-bound candidate containing two new direct
top-level `polyline` records; the backend validates, allocates durable IDs for
both provisional records, and accepts or rejects the whole candidate atomically.
The pair has no backend-specific wrapper, attachment, or container semantics:
all surviving CDML records, comments, and opaque extension content remain the
backend-owned document state.

Set paper properties is a revision-bound backend patch whose immutable request
carries only explicitly changed paper fields. OASA validates the authored
paper-name catalog (`A0`--`A10`, `B0`--`B10`, `C0`--`C10`, `Ledger`, `Legal`,
`Letter`, `Tabloid`, and `custom`) and publishes its plain millimetre size data
to clients. It applies the request only to the first direct core `paper`
record, preserving every untouched attribute and child, all later direct paper
records, viewport data, headers, references, opaque XML, and the complete
direct-record order. A named type clears dimensions; an explicitly selected
`custom` type requires one atomic positive finite dimensions pair; dimensions
otherwise apply only while the effective type is `custom`. A first nonempty
patch creates a paper from valid direct `standard` paper defaults or
`A4`/portrait and inserts it immediately before the first direct core
`viewport` (or appends it). Empty intent leaves paper absence untouched. A
paper-properties observation reports that same direct-core-paper boundary and
effective absent-paper defaults as fresh plain data, so a client can display
one later patch without inventing a frontend fallback. A
canonical no-op allocates no revision or history entry and replaces no frontend
projection.

Patch bond properties is a revision-bound backend patch for one direct core
bond.  Its request is an immutable tuple of unique explicit field/value pairs:
`order` (1--3), ordinary `type`, boolean `center`, finite bounded widths, and
six-digit hexadecimal `color`.  OASA validates every target, endpoint,
independent-order ambiguity, and final order/type combination before changing a
detached candidate.  It writes order and type together, preserves every
unmentioned attribute, child, ID, direction, opaque record, and root order, and
does not materialize absent depiction fields without explicit intent.  Numeric
values use canonical CDML text and colors normalize to lowercase.  Compatibility
`l1`/`r1` retain their lexical spelling for explicit `h` while other requested
fields still apply; untouched q/l/r type/order spellings remain preserved.

Insert system template is a bounded composition operation for one named entry
from the backend's system-template catalog. The backend is the final authority
for catalog-name resolution, source interpretation, coordinate generation,
finite placement, and detached proposal construction. It scales a bonded
template to a 40-point mean bond length and translates its centroid to the
requested finite scene-point anchor; an atom-only template is centered at that
anchor without inventing a bond length. The accepted result appends one
separate direct-root molecule. An anchor may be derived from a frontend hit,
but it is not an attachment target: the operation does not fuse, edit, or bond
to a source molecule. This operation uses the same final atomic acceptance,
history, canonical-response, and token-consumption semantics as Insert
molecules. Attachment, fusion, marker, and user-catalog behavior require
separately declared operations.

Insert top level is a bounded composition operation for a complete CDML
fragment containing supported direct persistent objects. The backend validates
the fragment in detached state, translates its persistent geometry by the
finite scene-point offset, privately allocates fresh durable IDs and rewrites
fragment-local references, then appends the accepted objects in fragment order.
It follows the same final atomic transaction semantics as Commit: typed
invalid-input or revision-conflict failure leaves the document and retained
history unchanged, while acceptance returns the immutable canonical snapshot
and mapping. The optional display label is scalar operation metadata only and
is never persistent CDML.

Edit structure is a bounded backend operation for the four declared Draw
gestures. `create-bonded-pair` creates a new direct-root molecule with a bonded
atom pair at two finite positions. `extend-atom` adds a bonded atom from one
editable atom, `join-atoms` adds one bond between two distinct editable atoms
in the same direct-root molecule, and `apply-bond-tool` updates one editable
bond using the selected bond settings. The request contains only its expected
revision, direct durable targets, scalar positions, and scalar bond settings;
it is not frontend-built complete CDML and does not establish a second
persistent owner. The backend applies the intent to a detached authoritative
document, validates the complete candidate, and returns the canonical result
with backend-issued created or updated durable IDs. Invalid input, missing or
noneditable targets, invalid topology, unsupported bond settings, and stale
revisions are typed atomic failures.

Set bond order is a bounded backend operation for one direct core `<bond>`.
Its immutable request names the expected revision, direct-root molecule ID,
direct core bond ID, and exact order 1, 2, or 3. The backend verifies two
distinct direct core atom endpoints and an unambiguous supported `bond@type`,
then preserves that type character and changes only its order digit. Thus
styled forms such as `w2` remain styled when changed to `w3`; `q` remains
restricted to `q1`. A matching parsed order returns the unchanged lexical
snapshot without revision, history, or dirty-state change. Legacy `l`/`r`,
malformed type strings, an independent `bond@order`, nested or opaque targets,
invalid endpoints, and stale revisions are typed atomic failures. Every other
attribute, child, endpoint direction, extension, document record, and order
remains backend-owned preservation content.

Set bond type is a bounded backend operation for one direct core `<bond>`. Its
immutable request names the expected revision, direct-root molecule ID, direct
core bond ID, and one ordinary type character: `n`, `w`, `h`, `a`, `b`, `d`,
`o`, or `s`. The backend checks revision before any no-op, verifies direct
distinct atom endpoints, and changes only the type character while preserving
the exact order digit, endpoint direction, attributes, children, extensions,
and document order. Current `q1` may become an ordinary type. Compatibility
`l1` and `r1` are semantically hashed (`h`): requesting `h` is a
lexical-preserving no-op, while another ordinary request replaces just their
type character. Every other matching type is an exact no-op. Requested `q`,
`l`, `r`, multicharacter, and unknown values; independent `bond@order`, bad
or nested targets, invalid endpoints, unsupported current spellings, and stale
revisions are typed atomic failures. Accepted changes commit once through
backend history; no-op snapshots keep the same revision, content, and history.

Set atom element is a bounded backend operation for one direct core `<atom>`.
The immutable request contains an expected revision, direct-root molecule ID,
direct core atom ID, and a different exact supported element symbol. The
backend replaces only that atom's persistent `name` field in a detached
authoritative document, validates the complete candidate, and atomically
returns its canonical snapshot. It preserves the atom's identity, coordinates,
chemical and presentation attributes, child content, unknown extensions,
document order, and every other persistent record unchanged. This narrow
operation performs no implicit valence, charge, hydrogen, bond, or presentation
repair. A stale revision, missing, nested, opaque, wrong-kind, invalid-symbol,
or same-symbol target is a typed atomic failure and leaves authoritative state
unchanged.

Patch atom properties is a revision-bound backend operation for one direct core
`<atom>`. Its immutable request contains unique explicit fields for element,
charge, valency, isotope, multiplicity, visibility, hydrogens, and direct-font
size/color. OASA validates all request scalars before detached mutation, then
preserves every unmentioned attribute and child, including point, ftext, mark,
unknown extension, document order, and font content outside the explicitly
changed attributes. A zero charge, null isotope, and multiplicity one remove
their documented default attributes. A patch creates one direct core font only
when a font field is explicitly changed; multiple direct core fonts are a
typed ambiguity failure. Canonical equality is history-free.

Set atom number is a bounded backend operation for one direct core `<atom>`.
Its immutable request names the expected revision, one direct-root molecule,
one direct core atom, and either a positive integer with explicit boolean
visibility or the exact `(null, null)` clear pair. Assignment or replacement
changes only the target atom's decimal `number` and explicit `show_number`
fields. Clear removes both fields. The backend neither allocates a sequence nor
requires uniqueness, batch-renumbers atoms, converts legacy marks, or changes
unrelated fields or persistent content. Invalid request shapes or pairs, stale
revisions, ineligible targets, and a targeted direct legacy atom-number mark
are typed atomic failures. A compatibility failure leaves that direct legacy
mark unchanged. Unrelated, nested, and opaque content remain preservation
content and are not number targets. This operation uses existing CDML 26.07
attributes and does not change the format version or grammar.

Translate atoms is a bounded backend operation for selected direct core `<atom>`
records. Its immutable request names an expected revision, ordered unique
direct-root molecule/direct-core-atom ID pairs, and one finite scene/PostScript
point delta. OASA converts points with the established `2.54 / 72` centimetres
per point factor, validates every target and its one direct core point against
the accepted snapshot before detached mutation, and patches only point axes
whose request delta is nonzero. A numerically zero delta is an early semantic
no-op. After candidate validation, any coordinate change that serializes to the
current canonical CDML is also a semantic no-op and returns the current lexical
snapshot without revision, history, or dirty-state change. Missing, ID-less,
nested, foreign, opaque, duplicate, malformed, nonfinite, and stale requests
are typed atomic failures; non-target coordinates,
topology, styles, extensions, identifiers, references, root order, and opaque
XML remain unchanged.

Set molecule name is a bounded backend operation for one direct-root core
`<molecule>`. A nonempty string replaces only `molecule@name`; an empty string
removes that attribute, and whitespace is preserved exactly. The backend checks
the expected revision before evaluating a no-op. A same-result request returns
the unchanged snapshot without creating a revision or history entry. Missing,
nested, opaque, wrong-kind, malformed, and stale targets are typed atomic
failures; identities, references, child content, order, and unrelated records
remain unchanged.

Query molecule SMILES is a bounded nonmutating backend observation. Its
immutable request names one expected revision and one direct-root core
`<molecule>` durable ID. The backend resolves that exact current persistent
record, decodes it through its chemistry codec, and returns the canonical
isomeric SMILES value together with the observed revision and durable ID.
Directed `w1` and `h1` stereobonds produce that value only when their authored
tetrahedral meaning can be represented as isomeric SMILES; an ambiguous,
degenerate, or otherwise unrepresentable styled stereobond returns the typed
SMILES-unavailable failure rather than an achiral value. It
does not receive a frontend or projection molecule, create a CDML candidate,
serialize or rewrite CDML, allocate IDs, or change document content, revision,
history, saved baseline, or dirty state. Missing, nested, opaque, and
wrong-kind IDs are typed target failures; a direct-root molecule without a
supported chemistry conversion returns the typed SMILES-unavailable failure.

Repair geometry is a bounded backend operation. Its accepted kinds are
`normalize-bond-lengths`, `normalize-bond-angles`, `clean-geometry`, and
`snap-to-hex-grid`. Every immutable request is bound to one expected revision,
names nonempty unique durable direct-root molecule IDs, and carries a
finite-positive `target_spacing_pt` in PostScript points.
The backend validates all selected direct-root molecule targets before it
patches a detached copy of the authoritative document, then accepts the whole
result through the same atomic complete-document path as Commit. A successful
canonical lexical no-op returns the current immutable snapshot without a
revision or history entry. Each kind operates on its selected direct-root
molecules in its documented lossless subset and preserves unselected, unknown,
foreign, and opaque persistent CDML without frontend reconstruction.

For selected eligible direct-root molecules, `normalize-bond-lengths` adjusts
eligible non-ring bond distances to `target_spacing_pt` while preserving
existing bond directions and ring geometry, and writes only direct atom-point
`x`/`y` attributes.

`normalize-bond-angles` rounds movable non-ring outgoing directions to the
nearest 60-degree slot while preserving each nondegenerate parent-child
distance. It uses `target_spacing_pt` only when an outgoing vector is
degenerate. Ring atoms are fixed. Each connected non-ring component may have
zero or one adjacent fixed ring atom; a component with multiple ring anchors
is a typed atomic failure. For an anchored component, its anchor and the
anchor-to-component edge remain fixed even when the component reaches greater
depth. Outgoing children are assigned in authored source order. Exact
represented half-slot ties advance to the increasing-angle slot. Incoming and
fixed-ring directions reserve their nearest slots; a child whose nearest slot
is reserved advances through successive slots, and a parent with no free slot
is a typed atomic failure. A successful repair changes only direct core atom
point `x`/`y` attributes. All other persistent content, including atom and
molecule extensions, unknown content, identifiers, references, and unselected
records, survives unchanged.

`clean-geometry` deterministically regenerates direct core atom layouts at the
requested spacing, translates each generated layout back to its source
direct-point centroid, and patches only direct point `x`/`y` attributes.
`snap-to-hex-grid` applies one shared origin-zero displayed hex lattice at the
requested spacing to every selected direct-root molecule and patches only
direct atom point `x`/`y` attributes. Foreign direct molecule children and
non-element content remain preservation content; unimplemented direct core
molecule semantics are typed target failures.

Delete top level is a bounded backend operation for durable-ID direct children:
`molecule`, `arrow`, `plus`, standalone `text`, and supported vector
presentation roots. It removes only the requested core-CDML roots from a
detached authoritative snapshot, preserves every survivor's order and opaque
XML, and accepts the result through the ordinary revision/history path. A
missing, nested, opaque, ID-less, duplicate, unsupported, or reaction-referenced
target is a typed atomic rejection; Delete neither allocates legacy IDs nor
repairs or rewrites reaction references.

Reorder presentation stack is a bounded backend operation.  Its expected
revision, declared mode, and unique durable IDs identify only direct core
presentation roots.  Acceptance reorders those selected direct records in
their source order, preserves molecule and opaque root records and their
relative order, and returns one immutable revision snapshot.  Validation,
target, or stale-revision failure is typed and atomic.  An already-equivalent
order is a no-op: it returns the current snapshot without a new revision or
history entry.

Snapshots are immutable values: a later operation cannot alter a snapshot
already returned. Commit and restore results are immutable values too. Failures
are typed so clients can distinguish malformed or invalid CDML, obsolete
revisions, and unavailable history without inspecting frontend state.

For a session, canonical content identity is the exact immutable complete-CDML
serialization in the owning backend's returned snapshot. Revisions, saved
baselines, clean/dirty state, ordinary Save, Recovery Export, and backend
interchange use that returned value. Semantic XML preservation explains why
compatibility content survives a round trip; it does not authorize a frontend
or another client to select an independent normalization for session identity.

## Identifiers and correlation tokens

The backend issues durable persistent IDs. A client may use a reserved
transaction-local provisional correlation token only in recognized editable ID
declarations and known reference fields. The token grammar is
`__bkchem_new__<token>`, where `<token>` matches
`[A-Za-z][A-Za-z0-9_-]{0,63}`.

Compatibility loading may retain an ID-less legacy record exactly as authored.
A frontend may create a private projection linkage for that record, but that
linkage is not a durable ID, is not returned by the backend, and cannot appear
in a child-addressed bounded operation request, a durable child-selection or
reprojection key, or a mutation target. A root-only observation may resolve a
selected ID-less child through its owning direct-root record when that root has
a backend-issued durable ID; the request still contains only that root ID and
never fabricates or submits a child identifier. A later explicit backend
operation may introduce durable IDs only when its declared grammar does so
atomically; loading and projection never perform that normalization.

Every literal `id` in an ID-definition position reserves a collision name
across the complete document, including opaque extension content. A recognized
`id` field documented as an IDREF is a reference, not a definition: currently
this means `fragment/vertex@id` and `fragment/bond@id` do not reserve another
name. Only recognized editable declarations and recognized reference fields
receive CDML lookup or provisional-token behavior. Opaque reference-like
attributes and text remain literal opaque content; the backend neither
allocates IDs for them nor interprets them as references.

On acceptance, the backend validates the recognized declaration/reference
scope, consumes the recognized provisional tokens, assigns collision-free
durable IDs, and returns an immutable mapping from those consumed tokens to
durable IDs. It rewrites recognized
positions only. Matching strings in opaque or unknown XML remain unchanged.
Malformed, duplicate, or dangling recognized tokens reject the whole commit.

The opt-in `authored-26.07` assessment adds portable reaction-role semantics
without changing that compatibility boundary. Each recognized role in a
persistent reaction names a direct-root object by a nonempty durable ID:
`reactant` and `product` name molecules, `arrow` names an arrow, `condition`
names standalone text, and `plus` names a plus sign. The assessment reports a
typed profile failure for a missing, unstable, nested, unknown, or wrong-kind
target. It neither rewrites legacy relationships nor defines cardinality,
ordering, stoichiometry, or repeated-target semantics. Ordinary Load and
Commit preserve accepted historical reaction structures unchanged.
No accepted canonical snapshot contains a recognized provisional token. A
consumed token is never accepted in a later candidate.

When a bounded insertion needs frontend selection feedback, the backend result
correlates its inserted root's provisional identifier to one durable identifier
through the immutable ID mapping. A frontend may restore selection only from
that returned durable identifier after canonical reprojection. Missing,
dangling, or wrong-kind correlation reports `selection-unavailable` and clears
the affected selection; it neither reuses a retained projection object nor
changes, rejects, or resubmits the accepted commit. The durable selection
correlation remains valid for recovery because recovery reprojects the exact
accepted/current snapshot only.

## Restore, history, and saved state

Restore copies a retained accepted snapshot into a new increasing revision; it
does not move the revision counter backward. The immediate pre-restore content
is retained as the one opposite restore target. A later restore replaces that
opposite target, and a normal accepted edit clears it.

The saved canonical-content baseline is independent of revision and undo
history retention. A session begins with its initial canonical content as its
saved baseline. `mark_saved` changes that baseline only after successful
external publication of the exact current snapshot. Clean/dirty compares the
current canonical content with this saved canonical content, not revision
numbers. Therefore restoring saved content is clean even though restore creates
a new revision.

History capacity, eviction mechanics, and performance limits are implementation
choices. They cannot change these observable rules: current content, the saved
canonical baseline, and immediate restore recovery retain their stated
semantics; an evicted older revision fails with the typed unavailable-revision
error; and eviction never changes whether current content is clean or dirty.

## External publication

Ordinary Save for a synchronized frontend session publishes the exact current
immutable backend snapshot, then marks that snapshot saved. A failure before
replacement leaves the target and saved baseline unchanged. A failure after
replacement but before baseline marking is a partial external result: the file
may contain canonical CDML, but the saved baseline remains unchanged.

Recovery Export writes an exact backend snapshot without changing backend or
frontend session state, including the saved baseline, dirty state, revision,
history, selection, or projection provenance. It is an export/recovery action,
not ordinary Save and not evidence that a frontend projection is synchronized.

## Visual artifact export

Visual output captures one immutable backend snapshot exactly once, plus only
durable selection IDs and scalar render options. The renderer returns artifact
bytes or a caller-controlled artifact path together with typed failures and
coverage warnings. It never receives a live frontend scene, document, widget,
or graphics wrapper as persistent input. SVG, PNG, PDF, cropped SVG, and
selected SVG therefore all describe the same captured revision; later scene or
selection changes cannot alter the artifact.

An unrenderable retained persistent object remains preserved in the snapshot.
Its omission is reported as a typed warning, rather than a claim that the
visual artifact fully rendered every persistent CDML record. Visual export
does not commit, mark saved, consume a candidate token, change history, or
modify the saved baseline. A terminal or unreadable session reports a typed
unavailable failure and never falls back to a retained frontend projection.
An artifact is successful only after its disposable render projection reaches
its terminal retirement phase. A retirement failure returns a typed render
failure with plain cleanup diagnostics and publishes no artifact. If rendering
already failed, that primary typed failure remains the result and carries the
cleanup diagnostic as additional detail.

## Projection rules

Frontends rebuild a projection from the accepted canonical snapshot as an
all-or-nothing operation. A rebuilt projection may reuse stable IDs for
selection, but not persistent objects, raw XML, or wrapper identities from the
previous projection. Failure leaves backend authority unchanged and requires
exact-snapshot reprojection or an explicitly unavailable frontend state.

Complete-CDML routes accept complete CDML rather than frontend-specific partial
state. Declared bounded operations accept only their documented durable IDs and
scalar values, then produce complete canonical CDML internally. A preview is
not persistent and no frontend-owned object becomes authoritative before a
successful commit.

## Compatibility evidence

Legacy artifacts, coordinate conversions, and historical frontend behavior are
compatibility evidence only. They do not assign persistent authority, permit
frontend re-merging, require a legacy frontend, or alter the frontend-neutral
transaction boundary above.
