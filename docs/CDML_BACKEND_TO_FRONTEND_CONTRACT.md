# CDML backend-to-frontend contract

This is the stable behavioral boundary between the CDML backend and a frontend.
It defines observable persistence behavior, not a particular language,
UI-toolkit, or scene-graph implementation.

Format grammar lives in [CDML_FORMAT_SPEC.md](CDML_FORMAT_SPEC.md); this
document covers transaction behavior and canonical CDML persistence.

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
- Root-only insertion facts are immutable backend results.  A molecule
  insertion exposes only the durable IDs of the newly inserted direct roots;
  it does not expose descendant DOM, graph, or frontend projection objects.
- A backend round trip preserves complete persistent content. A frontend never
  repairs a backend response by merging state retained from an older
  projection.
- A synchronized molecule projection retains no raw molecule XML. Whole-root
  Copy and Cut obtain their complete fragment from the exact backend snapshot,
  including unknown molecule attributes and descendant extensions. Raw
  molecule XML is an explicitly named compatibility-decoder value used only
  by the isolated legacy clipboard/export route; it is never a synchronized recovery or
  persistence source.
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

A document-bearing external codec returns frontend-neutral complete CDML text,
not an OASA graph or frontend model. The backend validates that extracted
document before it crosses the worker boundary. The frontend installs it as an
import against an empty saved baseline, so source-container paths never become
native CDML Save destinations.

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

A frontend consumes rich Text as a disposable projection only. Its
`text.rich.patch` request contains an expected revision, durable direct-root
Text ID, an immutable ordered sequence of serialized text/style run records,
and unique explicit root-font changes; the backend adapter alone constructs
its typed run and patch values. A supported current ftext may project with native character formats,
while preservation-only direct markup, comments, processing instructions, or
foreign content has safe plain display text but no rich-edit capability. One
accepted dialog creates at most one backend commit, and failed projection
recovery uses only its accepted snapshot.

The read-only direct-root presentation description is a revision-bound backend
observation. Its immutable plain records cover arrow, plus, Text, rect, square,
oval, circle, polygon, and polyline (including wavy style), in authoritative
source order. Records carry scalar attributes, finite PostScript scene points,
normalized bounds, authored font attributes, standard-resolved family, safe
display text, and supported authored ftext runs. A
durable record is `editable`; an ID-less compatible record is `display-only`.
A compatible presentation root with preservation-only child content produces
a safe display-only record plus a plain diagnostic. A frontend may render that
record but does not expose it as a persistent mutation address. Entirely
opaque, unknown, or malformed direct roots produce diagnostics without
projection records. Recognized headers, molecules, reactions, and
external-data remain outside this presentation observation. The description
contains neither XML nor DOM values.

`CDMLPaperLayoutQuery` is the corresponding exact-revision, read-only paper
observation. Its frozen plain result contains the revision, whether a direct
core paper exists, only the first direct-core paper and viewport attribute
mappings, and the backend's effective type/orientation for absent paper. It
separately
supplies effective paper attributes for rendering, while preserving empty
authored attributes and `paper_present=false` when paper is absent. Foreign
lookalikes and later duplicates remain backend CDML. Live Qt projection and
snapshot rendering obtain this value from the same exact snapshot as the
presentation description; they retain no root, header, paper, reaction, or
external-data XML in their synchronized envelope. Standalone compatibility
loading remains available where no backend session supplies the observation.

`CDMLDrawingStandardQuery` observes the first direct core `standard` at one
exact revision. Its immutable result contains only effective drawing scalars
and plain diagnostics. OASA applies those values to molecule projection and
render observations only where atom or bond depiction fields are absent;
lexically explicit per-object values remain explicit overrides. Foreign
lookalikes, later standards, unknown attributes, and child extensions remain
backend-owned document content.

A frontend may use that exact-revision observation when authoring a new
presentation proposal. The proposal records applicable values as ordinary
explicit CDML attributes; the frontend never infers or reparses the retained
`standard` XML.

`CDMLProjectionPlan` is the synchronized projection boundary.  It is one
immutable, exact-revision backend value containing the canonical snapshot,
ordered root facts, and all matching projection observations.  A synchronized
frontend hydrates only from that plan.  It does not parse CDML, construct a
DOM, or combine separately obtained facts while replacing a projection.

The typed presentation insertion grammar keeps interaction flexible without
making XML a frontend concern.  Arrow requests name one of the supported arrow
kinds, an ordered finite point sequence, spline intent, and endpoints.  Vector
requests name a supported geometric kind and its finite points; rectangles,
squares, ovals, circles, polygons, and ordinary polylines retain their distinct
geometry rules.  Plain Text requests carry only position and text.  Frontends
may preview or edit Text directly, but accepted changes use the revision-bound
backend Text operation and canonical reprojection.

## Snapshots, values, and failures

The backend exposes these behavioral operations:

| Operation | Request | Success | Typed failure |
| --- | --- | --- | --- |
| Load | Complete CDML and optional history policy | Clean initial snapshot | Parse or validation failure |
| Snapshot | None | Immutable current snapshot | None |
| Projection snapshot | None | Immutable current snapshot plus all exact-revision projection observations | None |
| Commit | Expected revision and complete candidate CDML | Immutable accepted snapshot and ID mapping | Parse, validation, or revision conflict |
| Insert molecules | Expected revision, complete molecule-only proposal CDML, optional display label | Immutable accepted snapshot and ID mapping | Parse, validation, or revision conflict |
| Insert system template | Expected revision, exact backend-catalog template name, and finite scene-point anchor | Immutable accepted snapshot and ID mapping for the detached inserted root and its records | Invalid input, unknown template, preparation, validation, or revision conflict |
| Insert biomolecule template | Expected revision, exact backend packaged-catalog key, and finite scene-point anchor | Immutable accepted snapshot and ID mapping for one detached inserted molecule | Invalid input, unknown catalog key, preparation, validation, or revision conflict |
| Inspect user template | Exact serialized complete template CDML | Immutable plain inspection with optional nonblank molecule display name | Typed ineligible template or parse failure |
| Insert user template | Expected revision, exact serialized complete template CDML, finite scene-point anchor, optional display label | Immutable accepted snapshot and ID mapping for one detached inserted molecule | Invalid template, validation, or revision conflict |
| Insert top level | Expected revision, complete CDML fragment, finite scene-point translation, optional display label | Immutable accepted snapshot and old-to-new durable-ID mapping | Parse, validation, or revision conflict |
| Insert brackets | Expected revision, exact rectangular/round style, finite normalized bounds | Immutable accepted snapshot and durable pair, left, and right polyline IDs | Invalid request, style, bounds, standard, validation, or revision conflict |
| Insert presentation | Expected revision plus exact Arrow endpoints, Text position/content, Plus position, geometric kind/endpoints, or Wavy endpoints | Immutable accepted snapshot and allocated presentation ID | Invalid request, variant, geometry, standard, validation, or revision conflict |
| Edit structure | Expected revision; one of `create-bonded-pair`, `extend-atom`, `join-atoms`, or `apply-bond-tool`; direct editable durable targets where applicable; finite scalar positions and bond settings | Immutable accepted canonical snapshot and created or updated durable IDs | Invalid input, target, topology, bond setting, or revision conflict |
| Set atom element | Expected revision, direct-root molecule ID, direct core atom ID, and a different exact supported element symbol | Immutable accepted canonical snapshot | Invalid request, target, element symbol, same symbol, or revision conflict |
| Patch atom properties | Expected revision, direct-root molecule ID, direct core atom ID, and unique explicit field/value pairs for atom chemistry and presentation scalars | Immutable accepted snapshot, or unchanged current snapshot for a canonical no-op | Invalid request, repeated field, target, direct font ambiguity, scalar value, or revision conflict |
| Patch plain Text properties | Expected revision, one durable direct-root core Text ID, and unique explicit changes for text, font family, font size, six-digit font color, or optional six-digit background | Immutable accepted snapshot, or unchanged current snapshot for a semantic no-op | Invalid request, repeated field, target or direct-child ambiguity, rich ftext, scalar value, or revision conflict |
| Patch rich Text | Expected revision, one durable direct-root core Text ID, immutable CDML 26.07 formatted text runs, and unique explicit optional root `font_family`, `font_size`, or `font_color` changes | Immutable accepted snapshot, or unchanged current snapshot for normalized runs plus every requested canonical root-font value | Invalid request, repeated field, target ambiguity, preservation-only ftext, unsupported markup, font scalar, blank content, or revision conflict |
| Patch plain Plus properties | Expected revision, one durable direct-root core Plus ID, and unique explicit changes for child font family, root font size, six-digit root color, or optional six-digit background | Immutable accepted snapshot, or unchanged current snapshot for a semantic no-op | Invalid request, repeated field, target or direct-child ambiguity, scalar value, or revision conflict |
| Patch plain Wavy properties | Expected revision, one durable direct-root core `<polyline style="wavy">` ID, and unique explicit width or six-digit line color changes | Immutable accepted snapshot, or unchanged current snapshot for a semantic no-op | Invalid request, repeated field, target or point ambiguity, scalar value, malformed Wavy content, or revision conflict |
| Patch Arrow properties | Expected revision, one durable editable direct-root core Arrow ID, and unique explicit start-head, end-head, spline, width, or six-digit color changes | Immutable accepted snapshot, or unchanged current snapshot for a semantic no-op | Invalid request, repeated field, target or presentation ambiguity, scalar value, malformed Arrow content, or revision conflict |
| Patch bracket-pair properties | Expected revision, one structurally valid durable pair ID and unique explicit common width or six-digit color changes | Immutable accepted snapshot, or unchanged current snapshot for a semantic no-op | Invalid request, malformed pair, repeated field, scalar value, or revision conflict |
| Patch geometric presentation properties | Expected revision, one durable editable direct-root rect, square, oval, circle, polygon, or ordinary polyline ID, and unique explicit width, stroke color, or applicable fill-color changes | Immutable accepted snapshot, or unchanged current snapshot for a semantic no-op | Invalid request, repeated or inapplicable field, target or presentation ambiguity, scalar value, specialized Wavy target, or revision conflict |
| Create fragment metadata | Expected revision, one direct-root molecule ID, nonblank name, exact `explicit` or `implicit` type, and ordered duplicate-free direct atom/bond IDs | Immutable accepted snapshot and backend-allocated fragment ID | Invalid request, member, endpoint, target, or revision conflict |
| Delete fragment metadata | Expected revision, one direct-root molecule ID, and one durable ordinary-fragment ID | Immutable accepted snapshot | Invalid request, preservation-only fragment grammar, target, or revision conflict |
| Observe fragment metadata | Exact expected revision | Immutable ordinary-fragment facts and display-only diagnostics | Invalid query or revision conflict |
| Observe direct atom marks | Exact expected revision | Immutable normalized rendering facts, actionable durable addresses and same-type ordinals, plus display-only diagnostics | Invalid query or revision conflict |
| Observe direct groups | Exact expected revision | Immutable visible group facts, unambiguous durable addresses only where selectable, exact implicit-expansion eligibility, and display-only diagnostics | Invalid query or revision conflict |
| Observe molecule core | Exact expected revision | Immutable molecule, atom, bond, endpoint-order, and depiction facts with renderability, actionability, and diagnostics. Child actionability requires a unique durable direct-root molecule and child ID; a bond renders only when both endpoint IDs name one observed direct atom. | Invalid query or revision conflict |
| Observe atom chemistry facts | Exact expected revision | Immutable complete-direct-graph atom facts associated by durable molecule/atom IDs plus source positions. Usable records include plain element and charge display facts, effective, occupied, and free valency, implicit hydrogen count, atomic number, and the backend's electronegativity-derived oxidation result; malformed, ambiguous, foreign, nested, preservation-only, or undecodable content remains display-only with diagnostics. | Invalid query or revision conflict |
| Observe molecule render | Exact expected revision | Immutable atom and bond paint batches from that same canonical molecule snapshot. The closed grammar is line, polygon, circle, path, and structured text runs; geometry is finite and colors are explicit or use a semantic foreground/document-background role. | Invalid query, revision conflict, or render preparation failure |
| Observe drawing standard | Exact expected revision | Immutable effective line, color, font, atom-hydrogen, and bond drawing defaults plus plain diagnostics | Invalid query or revision conflict |
| Expand implicit group | Expected revision, one direct-root molecule ID, and one direct implicit-group ID with exactly one editable exterior bond | Immutable accepted snapshot and generated durable atom/bond IDs | Invalid request, unsupported target content, formula, geometry, bond, target, or revision conflict |
| Convert to linear form | Expected revision, one direct-root molecule ID, and a nonempty ordered sequence of unique selected direct atom IDs | Immutable accepted snapshot, changed/commit semantics, backend fragment ID, and derived ordered atom/bond IDs | Invalid path, target, coordinate/mark geometry, external bridge, ambiguity, or revision conflict |
| Apply atom mark | Expected revision, direct-root molecule ID, direct core atom ID, exact `add` or `remove` action, one supported exact mark type, and optional nonnegative same-type core-child removal ordinal | Immutable accepted snapshot plus `added`, `removed`, or `unchanged` action result | Invalid request, selector, target, coordinate geometry, scalar result, or revision conflict |
| Set atom number | Expected revision, direct-root molecule ID, direct core atom ID, and either a positive integer plus explicit boolean visibility or the exact `(null, null)` clear pair | Immutable accepted canonical snapshot | Invalid request or pair, target, legacy compatibility, or revision conflict |
| Align atoms | Expected revision, exact `horizontal` or `vertical` axis, and nonempty unique direct-root molecule/direct-core-atom ID pairs | Immutable accepted snapshot, or unchanged current snapshot for a semantic coordinate no-op | Invalid request, target, point coordinate, or revision conflict |
| Translate atoms | Expected revision, nonempty unique direct-root molecule/direct-core-atom ID pairs, and a finite two-value scene/PostScript-point delta | Immutable accepted snapshot, or unchanged current snapshot for a canonical coordinate no-op | Invalid request, target, point coordinate, or revision conflict |
| Translate mixed selection | Expected revision, nonempty unique direct-root molecule/direct-core-atom ID pairs (pairs may share a molecule ID), nonempty unique durable direct-root presentation IDs, and a finite two-value scene/PostScript-point delta | Immutable accepted snapshot, or unchanged current snapshot for an exact zero or canonical coordinate no-op | Operation-specific invalid request, ambiguous ID, target, geometry, coordinate, or revision conflict |
| Rotate atoms | Expected revision, nonempty unique direct-root molecule/direct-core-atom ID pairs, one finite two-value scene/PostScript-point center, and one finite angle in radians | Immutable accepted snapshot, or unchanged current snapshot for an exact zero or canonical coordinate no-op | Invalid request, target, point coordinate, angle, or revision conflict |
| Set bond order | Expected revision, direct-root molecule ID, direct core bond ID, and exact order 1, 2, or 3 | Immutable accepted snapshot, or unchanged current snapshot for a matching semantic order | Invalid request, target, bond type/order grammar, Haworth restriction, or revision conflict |
| Set bond type | Expected revision, direct-root molecule ID, direct core bond ID, and exact ordinary type character `n`, `w`, `h`, `a`, `b`, `d`, `o`, or `s` | Immutable accepted snapshot, or unchanged current snapshot for a semantic type no-op | Invalid request, target, current spelling, independent order attribute, endpoint, or revision conflict |
| Patch bond properties | Expected revision, direct-root molecule ID, direct core bond ID, and unique explicit field/value pairs for order, type, center, widths, or six-digit color | Immutable accepted snapshot, or unchanged current snapshot for a canonical no-op | Invalid request, repeated field, target, endpoint, final type/order, depiction value, or revision conflict |
| Set molecule name | Expected revision, direct-root molecule ID, and exact display-name string | Immutable accepted canonical snapshot, or unchanged current snapshot for a no-op | Invalid request, target, or revision conflict |
| Set paper properties | Expected revision plus explicit field intent: recognized type or orientation, boolean crop/minus fields, nonnegative crop margin, and an atomic positive finite dimensions pair only for effective `custom` type | Immutable accepted canonical snapshot, or unchanged current snapshot for a no-op | Invalid request shape, repeated or unsupported field, invalid paper value, or revision conflict |
| Apply drawing standard | Expected revision; unique changed default fields; exact `defaults`, `selected`, or `all` scope; durable selected root IDs where applicable; and unique fields to materialize as overrides | Immutable accepted canonical snapshot, or unchanged current snapshot for a no-op | Invalid request shape, scope, repeated or unsupported field, target, ambiguous direct font, value, or revision conflict |
| Query molecule SMILES | Expected revision and one direct-root molecule durable ID | Immutable revision-tagged canonical/isomeric SMILES value | Invalid request, target, unavailable chemistry conversion, or revision conflict |
| Repair geometry | Expected revision, nonempty direct-root molecule IDs, supported kind, and finite-positive `target_spacing_pt` in PostScript points | Immutable current snapshot; a changed repair includes one immutable accepted commit | Invalid request, target, geometry, or revision conflict |
| Transform top level | Expected revision, exact supported mode, nonempty unique durable direct-root IDs, scale factors only for `scale`, or an exact finite two-value scene/PostScript-point delta only for `translate` | Immutable accepted snapshot, or unchanged current snapshot for a canonical no-op | Invalid request, target, geometry, scalar, or revision conflict |
| Reorder presentation stack | Expected revision, declared `bring-to-front`, `send-back`, or `swap-at-slots` mode, and nonempty unique durable IDs for direct-root core presentation records | Immutable accepted snapshot, or unchanged current snapshot for a no-op | Invalid request, target, mode, or revision conflict |
| Delete top level | Expected revision, nonempty unique durable IDs for supported direct-root records, optional display label | Immutable accepted snapshot | Invalid request, target, reaction reference, or revision conflict |
| Extract top-level fragment | Expected revision and nonempty unique durable direct-root IDs supported by the existing top-level insertion grammar | Immutable source revision and detached source-ordered CDML proven by the same complete Paste preparation and acceptance path | Invalid request, ambiguous, ID-less, unsupported, insertion-invalid, missing, or stale target |
| Extract structure fragment | Expected revision, one durable direct-root molecule ID, and nonempty unique direct atom and/or bond IDs | Immutable source revision, detached molecule-only CDML proven by the same complete Paste preparation and acceptance path, and source-ordered copied atom/bond IDs | Invalid request, eligible-molecule grammar, insertion grammar, target, disconnected selection, or revision conflict |
| Delete structure | Expected revision, one durable direct-root molecule ID, nonempty unique direct atom and/or bond durable IDs, and optional display label | Immutable accepted snapshot plus source-ordered removed atom/bond IDs and surviving ordered component records | Invalid request, molecule grammar, target, reaction reference, component split/removal, or revision conflict |
| Restore | Retained target revision and expected current revision | New immutable accepted snapshot | Revision conflict or unavailable revision |
| Mark saved | Expected current revision after external publication | Immutable current snapshot with updated baseline | Revision conflict |

A projection snapshot is one immutable backend result, not a client-assembled
set of otherwise matching observations. It contains the canonical snapshot and
every projection fact generated from that same document state. A synchronized
frontend accepts this result as a unit, rejects a malformed or incoherent
result before it constructs a projection, and never combines a snapshot from
one backend result with observations from another.

Bracket-pair observation is part of that projection result.  A valid pair is
exactly two direct core polylines with distinct durable IDs, the same
`bracket_pair` value, and one `bracket_side="left"` and one
`bracket_side="right"`; the pair value is the left polyline ID.  OASA alone
recognizes the pair and applies shared appearance edits atomically.  Pair
membership remains ordinary durable CDML data, while selection, shift-toggle,
rubber-band expansion, and handles are transient frontend semantics.  No
frontend infers a pair by proximity or stores a second persistent registry.

Insert molecules is a bounded composition operation. Its proposal is a complete
CDML document with one or more direct top-level molecule elements and no other
direct persistent object. The backend appends detached proposal molecules after
the current document's direct children in proposal order, then follows the same
atomic complete-candidate rules as Commit. The optional display label is scalar
operation metadata only and is never persistent CDML.

Insert presentation accepts only one exact revision-bound Arrow, plain Text,
Plus, geometric, or Wavy request. Requests contain scalar content and finite
scene points, never XML. OASA owns geometry, drawing-standard styling, CDML
grammar, ID allocation, and atomic commit. The frontend owns only tool,
gesture, and preview state. Existing records, comments, namespaces, order, and
opaque extensions remain backend-owned; results expose durable IDs without a
frontend provisional token or complete-CDML candidate.

Set paper properties is a revision-bound backend patch whose immutable request
carries only explicitly changed paper fields. The backend validates the authored
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

Apply drawing standard is a revision-bound backend transaction over the first
direct core `standard`. A first nonempty patch creates that record before paper,
viewport, or drawable roots; empty intent preserves absence. The backend
changes only requested attributes or direct `atom`/`bond` defaults, writes
portable width values in centimetres, and preserves every other attribute,
child, foreign record, later standard, and root position. Colors normalize to
six-digit lowercase hexadecimal; widths, font values, the double-line ratio,
and the hydrogen flag are bounded typed values. `defaults` changes no object
override. `selected` resolves a nonempty set of unique durable direct molecule
or presentation roots; `all` resolves every supported direct root. The backend
then materializes only the requested applicable fields on direct atoms, bonds,
and supported presentation records in the same detached candidate. An invalid
target or ambiguous direct font rejects the whole transaction without partial
mutation. The accepted snapshot uses the ordinary dirty/history/reprojection
path. A modal frontend captures the exact session, revision, and selection
before displaying values, and Cancel, invalid input, a tab switch, disposal,
or stale revision cannot mutate or retarget a document.

Patch bond properties is a revision-bound backend patch for one direct core
bond. Its request is an immutable ordered sequence of unique explicit
field/value records:
`order` (1--3), ordinary `type`, boolean `center`, finite bounded widths, and
six-digit hexadecimal `color`. The backend validates every target, endpoint,
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

Insert biomolecule template follows the same bounded composition behavior for
one immutable backend packaged-catalog key. The key joins URL-escaped category,
subcategory, and name components with slashes; labels remain plain frontend
display data. The backend resolves fixed SMILES, generates coordinates, scales bonded
geometry to 40 points, and centers the detached molecule at the finite anchor
before the ordinary molecule-insertion commit. An atom hit provides only anchor
coordinates: it creates no attachment, fusion, source mutation, or catalog
provenance record in CDML.

Inspect user template is a frontend-neutral pure admission operation for one
exact saved complete CDML value. It returns only an immutable plain result with
the direct molecule's stripped nonblank display name or `None`. Its shared
eligibility grammar requires exactly one direct molecule, at most one direct
`standard` and one direct `paper`, finite direct-atom geometry, unique
recognized source IDs, and resolved recognized molecule-local references.
Other direct roots, zero or multiple molecules, and a direct molecule-child
legacy `template` marker are typed failures. Compatible nested unknown XML
remains accepted, while duplicate literal IDs anywhere inside the template are
typed failures. Inspection does not use the filesystem or Qt, touch a session,
allocate durable IDs, or rewrite coordinates.

Insert user template is a bounded composition operation for that same exact
saved complete CDML value. Its immutable request carries an expected revision,
the frozen template string, one finite scene-point anchor, and optional plain
display metadata. It first applies the shared inspection eligibility grammar,
then preserves the accepted molecule subtree, including compatible unknown
nested extension content, assigns fresh durable IDs only to recognized
declarations, rewrites recognized molecule-local references, and translates
recognized geometry so the finite direct-atom centroid reaches the anchor. It
preserves the authored scale; unlike a system or packaged template, it does not
normalize bond length. Destination collisions with opaque literal IDs are typed
atomic failures. The detached candidate commits through ordinary session
acceptance, producing one history revision and the authoritative snapshot. A
stale revision is checked before parsing the frozen payload; every rejection
leaves the current snapshot, saved baseline, and history unchanged. The anchor
is placement only: it does not create an attachment, fusion, or bond to
existing content.

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
size/color. The backend validates all request scalars before detached mutation, then
preserves every unmentioned attribute and child, including point, ftext, mark,
unknown extension, document order, and font content outside the explicitly
changed attributes. A zero charge, null isotope, and multiplicity one remove
their documented default attributes. A patch creates one direct core font only
when a font field is explicitly changed; multiple direct core fonts are a
typed ambiguity failure. Canonical equality is history-free.

Convert to linear form is a revision-bound backend operation for one direct-
root molecule and a nonempty unique selection of direct atoms. The backend
derives one deterministic induced unbranched path (including a single atom),
lays it out horizontally at fixed 10 PostScript-point spacing, turns selected
hydrogens on, and translates explicit marks plus each external component that
has exactly one selected anchor. Invalid geometry, topology, targets, external
bridges, ambiguity, and stale revisions are typed atomic failures.

The generated metadata is exactly `<fragment id="..." type="linear_form">`
with `<name>linear_form</name>`, path-ordered bonds then vertices, and final
`<property name="bond_length" value="10" type="IntType"/>`; richer imported
forms remain preservation-only. A single matching narrow record is repaired
under its existing durable ID, while multiple matches are ambiguous and a
canonical repeat is history-free. Accepted coordinate or topology operations
recheck exact narrow records: rigid whole-path translations preserve them,
while bends, rotations, scales, path changes, and invalid member references
retire only the invalid generated metadata.

Fragment observation is Qt-free and never changes or rejects retained CDML.
Only one direct core `explicit` or `implicit` fragment with exact `id` and
`type` attributes, one plain nonblank direct `name`, exact-ID direct `vertex`
and `bond` members, whitespace-only surrounding text, unique nonempty members,
and resolved same-molecule bond-endpoint closure is editable. Exact generated
`linear_form` metadata and every richer, foreign, malformed, or historical
fragment are reported as readable display-only facts where safe; their XML,
properties, and unknown children remain authoritative backend content.
The frozen observation carries the queried revision and plain values only, uses
no history capacity, and accompanies the presentation description and paper
layout from that same snapshot during synchronized projection and rendering.
Those synchronized projections retain no direct fragment child XML, while the
separate standalone compatibility-loading path retains its legacy XML behavior.

Patch plain Text properties is a revision-bound backend operation for one
durable direct-root core `<text>`. Its immutable request carries one expected
revision, the Text ID, and unique explicit changes from `text`, `font_family`,
`font_size`, `font_color`, or optional `background_color`. Text must contain a
non-whitespace character and retains exact spacing; family becomes a nonblank
stripped string, size is an integer from 4 through 144, and submitted colors are
six-digit hexadecimal values that become lowercase. Background also accepts no
fill; compact backgrounds normalize. After validation, the grammar has one
direct point and ftext plus at most one direct font; namespace-owned extension
children remain opaque. Multiple direct fonts or ftexts, missing core children,
unsupported direct core content, and legacy rich ftext with element children
or modern escaped `sub`, `sup`, `b`, or `i` formatting markup are typed atomic
failures. Literal comparison symbols remain ordinary editable character data.

An accepted patch changes only requested ftext data, named font attributes, or
root background. No background writes an explicit empty `background-color` so
document defaults cannot reappear. Ftext comments and processing instructions,
other Text attributes, point content, unknown font attributes, extensions,
unrelated roots, namespaces, and source order remain persistent. A requested
font field creates one core font immediately before ftext when absent. Empty or
equal intent returns the exact current snapshot without history. Every failure
leaves snapshot, saved baseline, and retained history unchanged.

Patch rich Text is a separate revision-bound backend operation for one durable
direct-root core `<text>`. Its immutable request contains an expected revision,
the durable Text ID, exact immutable runs of rendered text plus styles, and
unique explicit optional changes for root font family, size, or color. The
backend checks a stale revision before resolving the target or interpreting any
payload. The editable grammar accepts exactly one direct point and ftext, at
most one simple font, and ftext character data only. Ftext attributes, direct
legacy markup, ftext comments or processing instructions, foreign children,
unknown ftext children, duplicate core children, and ambiguous durable IDs are
preservation-only typed failures. The typed codec rejects authored custom
entity references, unknown tags, attributes, namespace declarations, comments,
processing instructions, and declarations.
The backend decodes current authored markup using the CDML 26.07 `b`, `i`, `sub`, and
`sup` grammar, rejects duplicate styles and combined `sub` plus `sup`,
normalizes stable-order runs, and requires nonblank rendered content. Root font
changes accept a nonblank family, integer size from 4 through 144, or six-digit
hexadecimal color. An equal normalized sequence with every requested canonical
font value returns the exact current snapshot without history. Otherwise the backend
replaces ftext with one canonical authored character-data value, applies only
the named font attributes, validates the detached complete candidate, and
commits it once. A named change creates a namespace-consistent core font before
ftext when none exists. The complete-CDML serializer performs the outer XML
escaping. All untouched Text/root attributes, point content, unmentioned font
content, comments, processing instructions, extensions, record order, saved
baseline, and retained history remain backend-owned; every failure is atomic.

Patch plain Plus properties addresses one durable direct-root core `<plus>`.
Its revision-bound request accepts unique child `font_family` or root
`font_size`, `color`, and optional `background_color` changes. Family is
nonblank; size is 4 through 144; submitted six-digit colors become lowercase.
Absent family inherits the effective standard; absent size/color means
14/black. One point and at most one font form the editable grammar. Child
family is effective, while retained child size/color never override the root.
Only named fields change; no-op and failure paths are atomic and history-free.

Insert brackets accepts one exact revision, rectangular/round style, and finite
normalized scene bounds. OASA derives classic proportional control points,
uses the effective drawing-standard stroke, and atomically appends two ordinary
top-level polylines with allocated IDs. Round pairs author `spline="yes"`;
rectangular pairs author `no`. Existing content/order remain unchanged.

Patch plain Wavy properties is a revision-bound backend operation for one
durable direct-root core `<polyline style="wavy">`. Its immutable request carries
one expected revision, the Wavy ID, and unique explicit `width` or `line_color`
changes. Width is a non-boolean finite number from 0.1 through 20 and serializes
with `%g`; color is a six-digit hexadecimal value and becomes lowercase. A
missing width means 1.0, while visible color reads `line_color`, then legacy
`color`, then black. Explicit color writes use `line_color` and preserve legacy
`color`; the operation neither changes spline nor infers or normalizes Wavy
geometry. Its narrow editable grammar requires at least two direct core
`point` children and no other direct core element children; every point has
finite established-CDML `x` and `y` coordinates, an optional finite `z`, no
element children, and whitespace-only character data. The Wavy root itself also
allows only whitespace character data. Comments and processing instructions
remain preserved, while namespace-owned extension children and their complete
subtrees remain opaque. Empty or semantically equal intent is history-free,
including missing-default and lexical width/color variants. Every grammar,
target, scalar, or revision failure is typed and atomic: it preserves the
snapshot, saved baseline, retained history, and opaque content.

Patch Arrow properties is revision-bound for one unique durable editable
direct-root core `<arrow>`. Its request carries one expected revision, Arrow ID,
and unique explicit `start_head`, `end_head`, `spline`, `line_width`, or `color`
changes. Booleans serialize as `yes` or `no`; width is finite from 0.1 through
20 and serializes with `%g`; six-digit color becomes lowercase. Missing values
mean false, true, false, 1.0, and black for semantic comparison only. Historical
spellings participate without normalizing untouched content. Acceptance changes
only requested root attributes and preserves points, control-point order, type,
shape, length, unmentioned attributes, comments, processing instructions,
namespaces, unrelated records, and source position. Empty or semantically equal
intent is history-free; every failure is typed and atomic.

Patch geometric presentation properties is the shared revision-bound appearance
operation for rect, square, oval, circle, polygon, and ordinary polyline roots.
The request has one revision, durable ID, and unique explicit width, stroke, or
fill changes. Width is finite from 0.1 through 20; submitted colors use six-digit
hexadecimal. Closed shapes allow color or no-fill; ordinary polylines allow only
stroke fields. Visible three-digit legacy colors compare as six-digit values.
Explicit stroke writes `line_color` while preserving legacy `color`; no-fill
writes `area_color="none"` so a retained legacy background cannot reappear.
Specialized Wavy remains on its dedicated operation. Acceptance preserves
geometry, attributes, extensions, comments, processing instructions, namespaces,
unrelated roots, and order. Equal intent is history-free; failures are atomic.

Apply atom mark is a revision-bound backend operation for one direct core
`<atom>`. Its immutable request names a direct-root molecule ID, direct atom
ID, exact `add` or `remove` action, and one exact supported type: `plus`,
`minus`, `radical`, `biradical`, `electronpair`, `dotted_electronpair`, or
`pz_orbital`. Add requires no selector and appends one direct core `<mark>`
after every existing atom child. Remove without a selector deletes the first
matching direct core mark in document order; a missing match is a stale-checked
successful no-op with the same snapshot, revision, and retained history. A
selected-mark remove may instead supply `matching_mark_index`: a nonnegative
exact integer ordinal among direct core marks of that exact type in persistent
child order. Out-of-range or malformed selectors are typed atomic failures.
Marks remain ID-less in 26.07, so their operation identity is parent atom,
exact type, and direct-child order.
An accepted add derives paired portable centimetre coordinates from exactly one
direct core atom point, writes `auto="0"`, and applies the documented authored
defaults. Plus/minus add one charge unit, radical adds one multiplicity unit,
and biradical adds two multiplicity units; removal applies the inverse delta.
Absent scalar values mean charge zero and multiplicity one, and canonical
default results omit their attributes. The operation preserves incompatible
legacy residual data except for its own one delta. Presentation-only marks do
not alter chemistry. Bad scalar spelling or bounds is a typed atomic failure
only for the scalar addressed by that chemical mark delta: plus/minus validate
charge and radical/biradical validate multiplicity. The other scalar is an
unrelated legacy residual and is preserved verbatim, including incompatible
spelling or bounds. Missing, duplicate, malformed, nonfinite, or unsupported
point geometry; invalid/nested/opaque targets; and stale revisions are typed
atomic failures. The backend never assigns mark IDs, merges a frontend
projection, or changes an unrelated child or opaque record.

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
The next-number candidate is frontend presentation state derived from the
exact-revision molecule-core observation, not from frontend parsing of the
authoritative snapshot. The backend does not reserve or allocate that value.

Translate atoms is a bounded backend operation for selected direct core `<atom>`
records. Its immutable request names an expected revision, ordered unique
direct-root molecule/direct-core-atom ID pairs, and one finite scene/PostScript
point delta. The backend converts points with the established `2.54 / 72` centimetres
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

Query molecule summary is a bounded nonmutating backend observation. Its
immutable request names one expected revision and a nonempty ordered sequence
of unique direct-root core molecule durable IDs. The backend resolves and
decodes only those exact persistent roots and returns immutable plain facts in
request order: authored name and ID, chemistry-graph atom and bond counts,
formula including implicit and explicit hydrogens, average molecular weight,
monoisotopic mass, elemental counts, and mass percentages. A combined formula,
mass, and composition is calculated from the same batch and revision rather
than from separately observed frontend projections. Foreign lookalikes and
nested opaque chemistry remain preservation-only. Invalid query shapes,
missing or wrong-kind roots, unsupported chemistry conversions, and stale
revisions are typed failures. The observation never receives a frontend model,
serializes CDML, creates a candidate or history entry, changes selection,
revision, saved baseline, dirty state, or document content.

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
`normalize-bond-lengths`, `normalize-bond-angles`, `normalize-rings`,
`straighten-bonds`, `clean-geometry`, and `snap-to-hex-grid`. Every immutable
request is bound to one expected revision,
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

`straighten-bonds` moves only degree-one terminal endpoints. Each
nondegenerate terminal vector preserves its length and snaps to its nearest
canonical 30-degree direction; an exact half slot advances toward the
increasing-angle slot. Degenerate terminal vectors remain unchanged. For an
isolated two-atom component, the lexically smaller validated durable atom ID
is fixed and the other endpoint moves, so authored XML order cannot choose the
anchor. Its finite-positive `target_spacing_pt` request value is validated by
the common geometry-repair envelope but is not used by this kind. It patches
only direct core atom-point `x`/`y` attributes and preserves all other
persistent content. A client submits only the immutable repair envelope and
projects the returned authoritative snapshot; it never applies this geometry
change to retained frontend objects or supplies a recovery candidate.

`normalize-rings` accepts a ring-free target as a semantic no-op, or exactly
one simple independent cycle with acyclic connected substituent components.
The backend validates all selected targets before mutation. It starts the ring
walk at the lexically smallest durable atom ID, selects that atom's
lexically-smallest ring neighbor as the forward direction, and follows the
only remaining ring edge at each later atom. It preserves the ring centroid,
places the ring as a regular polygon with `target_spacing_pt` side length, and
translates each attached acyclic component by its unique ring-anchor movement.
Fused, bridged, spiro, multiple-cycle, malformed-walk, repeated-ID, and
multi-anchor topology are typed atomic failures. It patches only direct core
atom-point `x`/`y` attributes and preserves all other persistent CDML.

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

Delete structure is a distinct bounded backend operation for direct core atoms
and bonds of one durable direct-root molecule. Its request is a plain immutable
value with the expected revision, molecule ID, exact ordered sequences of atom
and bond IDs, and optional display label; every durable request ID contains at least one
non-whitespace character. The operation is defined by those serialized values,
not by an implementation type. The
eligible molecule has only `id`, `name`, and namespace attributes, and only
direct core `atom` and `bond` children, exact narrow generated linear-form
metadata, and whitespace character data as text or CDATA. Exact generated forms
follow their surviving component and are rechecked after mutation; an invalid
form is retired before acceptance. Comments, processing instructions,
non-whitespace character data, richer fragment records, and every other direct
node are unsupported. The molecule and each direct atom and bond have unique
durable IDs containing at least one non-whitespace character; every bond names
two distinct direct atoms. Unknown attributes and descendants remain owned by
an otherwise eligible atom or bond and travel with that node.

The backend resolves every requested target before detached mutation. It
removes selected atoms, selected bonds, and bonds incident to selected atoms;
both returned removal sequences use direct source order, with an incident bond
reported once. Surviving atoms, including isolated atoms, form connected
components ordered by their earliest surviving direct atom. Atom and bond IDs
inside each returned component retain source order. Zero survivors remove the
original root. One component retains the original root, attributes, name, ID,
and root position. A split keeps that original root for the first component;
later component roots appear immediately after it in component order, retain
eligible root namespace declarations, omit `name`, and receive collision-safe
backend molecule IDs reserved against the complete pre-delete document,
including deleted and opaque IDs.

A recognized direct-core reaction role may continue to reference the original
molecule only when exactly one component survives. Split or root removal in
that case is a typed atomic rejection and does not rewrite reaction roles.
Malformed requests, nested, ID-less, foreign, wrong-kind, missing, or
ambiguous targets, unsupported molecule content, malformed direct topology,
and stale revisions likewise leave the revision, canonical snapshot, and
history unchanged. Acceptance validates the complete detached candidate once
through the ordinary revision/history path, so backend restore returns the
exact predecessor snapshot.

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

## Mixed selection translation operation

`selection.translate` is a revision-bound transaction for one mixed selection
of direct-core atoms and direct-root presentation records. Its immutable request
contains an expected revision, nonempty unique `(molecule_id, atom_id)` pairs
that may share a parent `molecule_id`,
nonempty unique presentation root IDs, and one exact finite non-boolean
two-value scene/PostScript-point delta. An atom or molecule ID cannot also be
a presentation-root ID in the same request; repeated parent molecule IDs do
not create ambiguity when the atom pairs remain unique.

The backend resolves and validates the complete atom and presentation selection
against one backend-owned snapshot before it constructs a detached candidate.
Each selected atom contributes its sole direct core point and every direct core
`<mark>` with explicit `x` and `y` coordinates; coordinate-free marks remain
implicit and unchanged. Marks with one coordinate or malformed explicit
coordinates reject the complete transaction. Supported presentation roots are
arrows, standalone text, plus signs, rectangles, squares, ovals, circles,
polygons, and polylines. It preserves
source order, unrelated records, opaque XML, and lexical coordinate spelling
on untouched axes. A zero delta or authored-precision no-op returns the exact
current immutable snapshot without history; an accepted change commits one
canonical snapshot. Missing, nested, opaque, wrong-kind, duplicate, ambiguous,
malformed, nonfinite, or candidate-validation input returns a typed invalid-
selection failure; a stale revision returns a typed revision-conflict failure.
Every such failure leaves the snapshot and history unchanged. A client that
cannot project an accepted result recovers only by
reprojecting that backend snapshot.

A frontend may use the operation only after it resolves one current mixed
selection to durable atom pairs and presentation root IDs. It may display a
transient drag preview, but restores that preview before submitting one
revision-bound request. The accepted snapshot, rather than any retained
projection wrapper or candidate, is the only source for selection recovery and
projection retry.

## Top-level transform operation

`top-level.transform.apply` is a frontend-neutral, revision-bound operation.
Its exact immutable request is `expected_revision`, one mode, a nonempty
ordered sequence of unique durable direct-root IDs, scale factors only for
`scale`, and one exact two-value finite non-boolean scene/PostScript-point delta only for
`translate`.
The supported modes are `align-top`, `align-bottom`, `align-left`,
`align-right`, `align-center-x`, `align-center-y`, `scale`,
`mirror-vertical`, `mirror-horizontal`, and `translate`.

The backend resolves the requested roots in direct-root document order, derives
all bounds and pivots from persistent authored CDML geometry, and validates the
complete selection before it mutates a detached candidate. Supported roots are
molecules, arrows, standalone text, plus signs, rectangles, squares, ovals,
circles, polygons, and polylines. Missing, nested, opaque, reaction,
unsupported, ID-less, ambiguous, malformed, duplicate, nonfinite, or stale
targets produce a typed atomic failure. The delivered Qt Align and Object menu
routes consume this operation through an exact active-session capability. They
derive canonical durable roots from the current disposable projection, release
those wrappers before submission, and let the accepted snapshot rebuild the
scene and restore only durable root selection. A legacy-isolated Qt session is
the explicit local-undo exception while it contains an earlier local edit.

For modal Scale, Qt freezes the originating session, revision, durable roots,
and capability before opening the dialog. It submits only if that exact session
still owns every active alias after dialog acceptance. A same-session intervening
commit reaches the backend as the frozen stale request; a tab switch, same-tab
replacement, or disposal submits nowhere. Accepted projection recovery uses
the current accepted snapshot only and never repeats the candidate.

Alignment uses selected persistent edges; center alignment uses the midpoint of
the minimum and maximum individual-root centers. Scale and mirrors use the
aggregate selected-bounds center. Molecule vertices and explicit mark pairs
move together, while bonds and all non-coordinate content remain unchanged.
Output uses the established 0.001 cm coordinate form only for axes whose
authored-precision value changes. Translate converts its point delta through
the established PostScript-point-to-centimetre conversion and moves every
selected persistent coordinate pair by that offset. A numeric zero delta and
identity scale remain stale-checked, history-free lexical no-ops.

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

An unrenderable retained object produces a typed warning. Export never commits,
marks saved, consumes a token, or falls back to a retained frontend projection.
It publishes only after disposable render retirement; failure returns a typed
render failure with any cleanup diagnostic.

## Projection rules

Frontends rebuild all-or-nothing from the accepted snapshot. They may reuse
stable selection IDs, never old persistent objects, XML, or wrappers; failure
requires exact-snapshot reprojection or an unavailable frontend state. Complete
routes accept complete CDML; bounded routes accept documented IDs and scalars,
produce canonical CDML internally, and keep previews transient.

Direct atom-mark observations expose only actionable plain addresses, source
positions, removal ordinals, diagnostics, and finite rendering facts. Raw mark
XML remains backend-owned; legacy `atom_number` is a separate compatibility
diagnostic.
