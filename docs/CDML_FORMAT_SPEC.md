# CDML Format Specification

## Overview

CDML (Chemical Drawing Markup Language) is an XML format used by BKChem and
OASA to represent 2D chemical drawings. It stores molecular structure
(atoms, bonds, groups), depiction metadata (coordinates, colors, line widths),
and drawing objects (arrows, text, shapes) in a single document.

CDML is the serialization contract between:

- **OASA document backend**: owns and preserves the complete ordered
  persistent document, including typed and opaque content.
- **OASA molecule codecs and renderers**: provide typed chemistry adapters for
  `<molecule>` content; they do not replace the complete-document session.
- **BKChem Qt frontend**: submits complete candidate CDML and projects the
  backend's canonical complete response.
- **CD-SVG**: embeds a `<cdml>` node inside standard SVG for round-trip
  editing.

### Namespace

```
http://www.freesoftware.fsf.org/bkchem/cdml
```

The namespace URI is an identifier and may not be dereferenceable; it is kept
for compatibility and identity, not as a guaranteed fetch target.

The canonical namespace is required by the 26.07 authored profile. Its absence
is accepted only as standalone legacy compatibility input; it is not a new
authoring option. It is also required for embedded CDML inside SVG (CD-SVG).
BKChem may load legacy CDML without the namespace but may prompt when loading
embedded CDML in SVG files with missing or incorrect namespaces.

Documentation URL: [CDML Format Specification](https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md).

### Current version

`26.07`

`26.07` is the authored-current CDML profile. `26.02` and the earlier
versions in the migration chain remain accepted compatibility inputs. The
implemented writer/default, transformer, and focused-test wiring author new
documents as 26.07 and preserve loaded supported-old and unknown-future root
values unless the legacy transformer is explicitly invoked. `26.07` documents
and makes the authored profile explicit for long-standing direct-child order
and opaque-preservation behavior; it does not reinterpret or alter the meaning
of 26.02 documents.

### File extensions

| Extension | Content |
|-----------|---------|
| `.cdml` | Plain XML CDML |
| `.cdgz` | Gzip-compressed CDML |
| `.svg` | CD-SVG: standard SVG with embedded `<cdml>` node |
| `.svgz` | Gzip-compressed CD-SVG |

---

## Document structure

A CDML document has the following top-level structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<cdml version="26.07" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  <info>...</info>
  <metadata>
    <doc href="https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"/>
  </metadata>
  <standard>...</standard>
  <paper .../>
  <viewport .../>
  <!-- drawing objects -->
  <molecule>...</molecule>
  <arrow>...</arrow>
  <plus>...</plus>
  <text>...</text>
  <rect .../>
  <oval .../>
  <polygon>...</polygon>
  <circle .../>
  <square .../>
  <polyline>...</polyline>
  <reaction>...</reaction>
  <external-data>...</external-data>
</cdml>
```

All direct child elements of `<cdml>` are optional. Root `version` is an
attribute, not a child element. The complete direct-child sequence is
persistent document order and must be preserved. Persistent
drawable records paint in that relative sequence; header/default/metadata
records such as `<info>`, `<metadata>`, `<standard>`, `<paper>`, and
`<viewport>` are not painted layers. The current transitional Qt
reconstruction writer can regroup records and is therefore not authoritative
for CDML order.

## Conformance vocabulary

This specification distinguishes authored requirements from compatible input
and preservation behavior. It does not define a transaction protocol; that is
covered separately by
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md).

| Class | Meaning | Current evidence |
|-------|---------|------------------|
| Normative authored 26.07 | New documents use root `<cdml version="26.07">`, the canonical namespace, existing documented CDML vocabulary, and the preserved direct-child sequence. | Implemented writer/default and legacy-transformer wiring. |
| Legacy-compatible input | Earlier chain versions, including `26.02`, and historical namespace/cardinality/order variants remain readable when accepted by compatibility handling. | Implemented migration chain and complete-document preservation behavior. |
| Opaque preservation | Unknown elements, attributes, namespaces, and unsupported known content retain their XML meaning and sequence without CDML lookup, reference, or provisional-token semantics. Every literal `id` in an ID-definition position, including one in opaque content, reserves a document-wide collision name. | Complete-document backend preservation. |
| Proposal | A possible future addition has no authored grammar or editor requirement until separately specified and implemented. | Proposal registry below. |

The detailed element sections below describe established CDML semantics and
compatibility evidence. They do not turn an unimplemented proposal into a
newly required element grammar.

External CML, CDXML, and SVG material is comparison-only: it may identify a
coverage gap, but supplies neither replacement schema nor migration target.
CDML's existing semantics and version chain remain authoritative.

### Machine inspection profiles

The public, Qt-free conformance inspector has exactly two profiles. Its API,
CLI, and versioned semantic corpus are provided by
`packages/oasa/oasa/cdml_conformance.py`, `tools/cdml_conformance.py`, and
`docs/cdml_conformance/cdml_26_07_manifest.json`.

| Profile | Behavioral question | Bounded implemented checks |
|---------|---------------------|----------------------------|
| `compat` | Can the complete document be safely parsed and preserved as compatible CDML? | CDML root/namespace and safe XML parsing. Historical versions, incomplete records, and opaque extension content remain preservation-compatible. |
| `authored-26.07` | Does a newly authored document meet the implemented 26.07 safety/profile boundary? | `compat`, canonical root version and namespace, nonempty, non-whitespace durable IDs on selectable direct children, recognized-reference safety checks, and typed direct-root reaction-role targets. |

The authored inspector is deliberately a bounded safety/profile checker, not a
total XSD, cardinality, geometry, or chemistry validator. The prose grammar in
this document remains normative for authors. Backend transaction/session
validation remains exclusively in the backend-to-frontend contract; it is not
a third format-inspection profile.

An authored requirement does not imply that compatible input is rejected.
Complete-document compatibility validation is intentionally narrower: it
preserves records that omit authored fields when their XML can be preserved.

### Acceptance frontier

Ordinary complete-document Load and Commit accept compatibility-preservation
content that is XML-safe and identity/reference-safe. This acceptance frontier
preserves legacy, incomplete, and opaque persistent records without claiming
that every accepted record has complete authored geometry, chemistry, or
renderer support. `authored-26.07` is the stricter opt-in assessment for a
producer that chooses to check the implemented authored profile before it
emits a document. A future authoring operation states its own emitted-profile
rule; until it does, generic Load and Commit continue to use the compatibility
frontier rather than silently adding authored-profile enforcement.

### Complete-CDML XML safety and preservation

Complete CDML input must not declare a `DOCTYPE`, use entity expansion, or
refer to external entities. The complete-CDML policy gate uses an isolated
`lxml.etree.XMLParser` with entity resolution, DTD loading, network access,
recovery, and huge-tree mode disabled; it retains comments, processing
instructions, CDATA character data, and whitespace for preservation. Other
legacy XML remains behind its owning hardened parser until it is migrated to a
dedicated lxml boundary. A rejected XML source produces the backend's typed
parse failure and cannot become a document snapshot or committed revision.

For accepted CDML, comments, processing instructions, namespaces, attributes,
text, tail text, and element sequence are persistent preservation content.
Round trips preserve that XML semantically rather than promising byte-identical
whitespace formatting or serializer layout. Known CDML element and attribute
names compare by expanded name, so a prefix rename in known CDML syntax is
semantically equivalent. CDATA is character data for this purpose; preserving
its original CDATA-section spelling is not required.

This expanded-name rule covers the documented CDML records and their deliberate
reader/writer compatibility attributes. It does not classify arbitrary markup
inside old direct-child rich text as CDML vocabulary. That markup has no
current typed grammar and remains opaque preservation content.

An unrecognized attribute on an otherwise known CDML element remains opaque
extension content. Its lexical QName, literal value, and complete current
namespace context are preservation semantics; only the element's documented
or deliberate compatibility attributes use expanded-name comparison.

### Backend snapshot identity

Semantic preservation describes whether accepted compatibility content retains
its XML meaning across a boundary. It does not let a client choose a competing
normalization for a live document. For revisions, clean/dirty state, Save,
Recovery Export, and backend interchange, the document's content identity is
the exact immutable complete-CDML serialization returned by the owning backend
for that session. An implementation may serialize formatting differently while
crossing the boundary, but clients use the returned snapshot as the one
authoritative value; transaction details are defined by
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md).

An unknown or foreign element begins an opaque subtree, even when a descendant
uses a familiar CDML local name. The generic backend retains that subtree's
lexical element and attribute QNames, literal attribute values and character
data, and complete in-scope namespace context. It must not rename or remove an
opaque namespace binding because an unknown extension may use it in QName-like
content. A typed extension handler may normalize only content governed by its
own schema.

---

## Root element: `<cdml>`

| Attribute | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `version` | string | Yes | -- | Format version (e.g. `"26.07"`) |
| `type` | enum | No | `"normal"` | `"normal"`, `"template"`, or `"standard"` |
| `xmlns` | URI | Yes (authored 26.07) | -- | Legacy standalone input may omit it. |

### `<metadata>`

Optional metadata for human-oriented discovery pointers.

```xml
<metadata>
  <doc href="https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"/>
</metadata>
```

| Child element | Attributes | Cardinality | Notes |
|---------------|------------|-------------|-------|
| `doc` | `href` (URL) | 0..* | Link to human-readable CDML documentation |

---

## `<info>`

Metadata about the document and authoring program.

```xml
<info>
  <author_program version="application-version">BKChem</author_program>
  <author>User Name</author>
  <note>Optional notes</note>
</info>
```

`author_program@version` identifies the authoring application release. It is
independent of root `cdml@version` and may have a different value.

| Child element | Attributes | Content | Cardinality |
|---------------|------------|---------|-------------|
| `author_program` | `version` (optional) | Program name (text) | 0..1 |
| `author` | -- | Author name (text) | 0..* |
| `note` | -- | Free-form text | 0..* |

---

## `<standard>`

Drawing defaults applied when per-object values are absent. Saved as part of
the document and can be stored separately as a personal standard. Unit-bearing
defaults are retained document data. Where a delivered typed adapter must
convert a unit-bearing default, `cm` is the portable authored unit. Bare,
`px`, `mm`, and `in` values remain compatibility-preserved historical/default
values according to the readers that accept them; 26.07 does not define a
shared portable conversion for those forms. Paper dimensions remain separately
defined in millimetres.

### Attributes

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `line_width` | string (with units) | `"1px"` | Retained default; use `cm` for portable authored conversion where a delivered typed adapter converts the value |
| `font_size` | int | `12` | Point size |
| `font_family` | string | `"helvetica"` | Font family name |
| `line_color` | hex color | `"#000"` | Default line/stroke color |
| `area_color` | hex color | `""` | Default fill color; empty = transparent |
| `paper_type` | string | `"A4"` | Paper size name |
| `paper_orientation` | string | `"portrait"` | `"portrait"` or `"landscape"` |
| `paper_crop_svg` | int | `0` | `0` or `1` |
| `paper_crop_margin` | int | `10` | Pixels |

### Children

**`<bond>`** -- bond drawing defaults. Unit-bearing entries follow the
`<standard>` unit policy above; their listed historical defaults are not a
claim of a shared `px` or `mm` conversion.

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `length` | string (with units) | `"0.7cm"` | Standard bond length |
| `width` | string (with units) | `"6px"` | Double bond line spacing |
| `wedge-width` | string (with units) | `"5px"` | Wedge bond width |
| `double-ratio` | float | `0.75` | Length ratio for double bond inner line |
| `min_wedge_angle` | float | `0.3927` (~pi/8) | Minimum wedge angle in radians |

**`<arrow>`** -- arrow defaults. Its unit-bearing value follows the same
`<standard>` unit policy.

| Attribute | Type | Default |
|-----------|------|---------|
| `length` | string (with units) | `"1.6cm"` |

**`<atom>`** -- atom display defaults:

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `show_hydrogens` | int | `0` | `0` or `1`; also accepts `"True"`/`"False"` on read |

---

## `<paper>`

Page layout and export options are persistent CDML data owned and preserved by
the OASA document backend. BKChem edits and projects these values through a
revision-bound explicit-field backend patch; it does not rebuild the paper
record or complete document.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `type` | string | Yes | Paper size name (e.g. `"A4"`, `"Letter"`, `"custom"`) |
| `orientation` | string | Yes | `"portrait"` or `"landscape"` |
| `crop_svg` | int | No | `0` or `1`; crop SVG to content |
| `crop_margin` | int | No | Margin in pixels when cropping |
| `use_real_minus` | int | No | `0` or `1`; use Unicode minus sign |
| `replace_minus` | int | No | `0` or `1` |
| `size_x` | positive finite decimal millimetres | When `type="custom"` | Custom width |
| `size_y` | positive finite decimal millimetres | When `type="custom"` | Custom height |

For a `type="custom"` paper, `size_x` and `size_y` are positive finite
decimal millimetre values, for example `200.5` and `300.25`. Backend-authored
changes validate and serialize that form. Existing accepted legacy lexical
values remain compatibility-preserved unchanged until an explicit paper patch
changes the corresponding field.

### Recognized paper types

Standard ISO and US sizes: `A0`--`A10`, `B0`--`B10`, `C0`--`C10`, `Ledger`,
`Legal`, `Letter`, `Tabloid`. Values are stored as `[width_mm, height_mm]`.
OASA publishes this plain catalog to clients; Qt scene and snapshot renderers
use that catalog for recognized page sizing. Unknown legacy values remain
compatibility-preserved and retain the established default-page projection.

---

## `<viewport>`

Visible area of the drawing canvas.

```xml
<viewport viewport="x1 y1 x2 y2"/>
```

The `viewport` attribute is a space-separated string of 4 float coordinates.

---

## Coordinate system and units

### Coordinate values

Portable authored coordinates and shape bounds use a `cm` suffix, for example
`"1.500cm"`. OASA writers emit `cm` using `POINTS_PER_CM = 72.0 / 2.54`
(~28.3465 points per cm).

Bare numeric coordinates and `px` values are compatibility input for legacy
documents and the current Qt projection. They are not portable authored form.
`mm` and `in` remain legacy-Tk compatibility values only until a future shared,
frontend-neutral conversion rule is implemented. Paper dimensions are a
separate case: recognized paper sizes and custom paper dimensions use
millimetres by definition.

### Y-axis convention

BKChem stores CDML in canvas coordinates: **+Y points down**. This matches the
Tk canvas origin (top-left). OASA may canonicalize coordinates internally
(**+Y up**) for computation or format interchange, but CDML written on disk
remains **+Y down** unless an explicit versioned migration says otherwise.

### Width and length values

Unit-bearing `<standard>` defaults, such as bond length and arrow length, are
not interchangeable with per-bond depiction fields. Per-bond `line_width`,
`bond_width`, `wedge_width`, and `double_ratio` are numeric depiction values;
authors must not attach a unit suffix unless that field's established reader
supports one. This distinction prevents a document from claiming portable
geometry that its typed chemistry adapter cannot consume.

---

## `<molecule>`

A molecular graph containing atoms (vertices) and bonds (edges).

```xml
<molecule id="m1" name="ethanol">
  <template atom="a1" bond_first="b1" bond_second="b2"/>
  <atom id="a1" name="C">
    <point x="0.000cm" y="0.000cm"/>
  </atom>
  <group id="a2" name="OH" group-type="builtin" pos="center-last">
    <point x="0.700cm" y="0.000cm"/>
  </group>
  <bond id="b1" start="a1" end="a2" type="n1"/>
  <display-form>...</display-form>
  <fragment id="f1" type="explicit">...</fragment>
  <user-data>...</user-data>
</molecule>
```

### `<molecule>` attributes

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | ID | No | Unique identifier |
| `name` | string | No | Molecule name |

### `<molecule>` children

| Child | Cardinality | Notes |
|-------|-------------|-------|
| `template` | 0..1 | Template attachment metadata |
| `atom` | 0..* | Standard chemical atoms |
| `group` | 0..* | Chemical groups (since v0.14) |
| `text` | 0..* | Rich-text labels in molecule context (since v0.14) |
| `query` | 0..* | Query/wildcard atoms |
| `bond` | 0..* | Chemical bonds |
| `display-form` | 0..1 | Verbatim DOM children preserved on round-trip |
| `fragment` | 0..* | Named substructure fragments |
| `user-data` | 0..1 | Arbitrary DOM nodes preserved on round-trip |

All listed children are established CDML records. In the current delivery, the
OASA typed molecule adapter provides editable chemistry for `<atom>` and
`<bond>`. Other established molecule children remain complete-document content
unless an active frontend documents a supported projection for them.

---

## Vertex elements: `<atom>`, `<group>`, `<text>`, `<query>`

These four element types represent vertices in the molecular graph. They were
unified from a single `<atom>` element in version 0.14 (see Version History).

### `<atom>` -- standard chemical atom

| Attribute | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `id` | ID | Yes | -- | Unique identifier |
| `name` | string | No | -- | Element symbol (e.g. `"C"`, `"O"`, `"N"`) |
| `charge` | int | No | `0` | Formal charge; only written when nonzero |
| `pos` | enum | No | `"center-first"` | `"center-first"` or `"center-last"`; only written when `show` is `"yes"` |
| `show` | enum | No | Auto | `"yes"` or `"no"`; default is `"yes"` for non-C, `"no"` for C |
| `hydrogens` | enum | No | `"off"` | `"on"` or `"off"`; show hydrogen count |
| `show_number` | enum | No | `"no"` | `"yes"` or `"no"` |
| `number` | string | No | -- | Atom number text |
| `background-color` | hex color | No | -- | Only written when different from standard |
| `multiplicity` | int | No | `1` | Spin multiplicity; only written when != 1 |
| `valency` | int | No | -- | Explicit valency |
| `free_sites` | int | No | `0` | Free coordination sites; only written when nonzero |
| `isotope` | int | No | -- | Mass number (OASA level) |
| `explicit_hydrogens` | int | No | `0` | Explicit hydrogen count used by OASA chemistry; read when present and written only when nonzero |

#### `<atom>` children

| Child | Cardinality | Notes |
|-------|-------------|-------|
| `point` | 1 | **Required.** Coordinates. |
| `font` | 0..1 | Only when font differs from standard |
| `ftext` | 0..1 | Rich text content for formatted label |
| `mark` | 0..* | Electron marks, charges, annotations |

### `<group>` -- chemical group

Groups represent multi-atom abbreviations (e.g. OCH3, NO2, COOH). Introduced
in version 0.14 when named atoms matching a builtin list were reclassified.

| Attribute | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `id` | ID | Yes | -- | |
| `name` | string | Yes | -- | Group symbol (e.g. `"OCH3"`, `"NO2"`) |
| `group-type` | enum | No | -- | `"builtin"`, `"implicit"`, or `"explicit"` |
| `pos` | enum | No | `"center-first"` | `"center-first"` or `"center-last"` |
| `background-color` | hex color | No | -- | |
| `show_number` | enum | No | `"no"` | |
| `number` | string | No | -- | |

Children: `point`, `font`, `mark` (same as `<atom>`).

#### Builtin group names

`OCH3`, `NO2`, `COOH`, `COOCH3`, `Me`, `CN`, `SO3H`, `PPh3`, `OMe`, `Et`,
`Ph`, `COCl`, `CH2OH`.

### `<text>` (textatom, inside `<molecule>`)

Rich-text labels that participate in the molecular graph as vertices.
Introduced in version 0.14 when nameless atoms became `<text>` elements.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | ID | Yes | |
| `pos` | enum | No | `"center-first"` or `"center-last"` |
| `background-color` | hex color | No | |
| `show_number` | enum | No | |
| `number` | string | No | |

Children: `point`, `font`, `ftext`, `mark`.

### `<query>` -- query/wildcard atom

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | ID | Yes | |
| `name` | string | No | Query symbol |
| `pos` | enum | No | |
| `background-color` | hex color | No | |
| `show_number` | enum | No | |
| `number` | string | No | |
| `free_sites` | int | No | |

Children: `point`, `font`, `mark`.

---

## `<bond>`

A chemical bond connecting two vertex elements.

### Core attributes

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `type` | string | Yes | Bond type + order (e.g. `"n1"`, `"n2"`, `"w1"`) |
| `start` | IDREF | Yes | ID of first vertex; narrow/tip endpoint for `w1` and `h1` |
| `end` | IDREF | Yes | ID of second vertex; wide/base endpoint for `w1` and `h1` |
| `id` | ID | No | Bond identifier |

### Bond type string format

The `type` attribute is a string: `<type_char><order_digit>`.

**Type characters:**

| Char | Meaning | Visual |
|------|---------|--------|
| `n` | Normal | Plain line(s) |
| `w` | Wedge | Filled triangle (stereo up) |
| `h` | Hashed | Dashed wedge (stereo down) |
| `a` | Adder / unspecified stereochemistry | Established non-aromatic adder style |
| `b` | Bold | Thick line |
| `d` | Dashed | Dashed line |
| `o` | Dotted | Dotted line |
| `s` | Wavy | Squiggly/wave line |
| `q` | Haworth front edge | Author only as `q1`; it is not a generic quadruple bond |

**Legacy type characters** (normalized on read):

| Legacy | Normalized to | Origin |
|--------|---------------|--------|
| `l` | `h` | Legacy left-hashed |
| `r` | `h` | Legacy right-hashed |

**Ordinary authored order digit:** `1` (single), `2` (double), `3` (triple).
`q1` is the established Haworth front-edge form. A generic order `4` and a
generic four-line bond are not authored 26.07 features. Compatibility loading
may preserve other historical values without assigning them new typed meaning.

Examples: `n1` = normal single, `n2` = normal double, `n3` = normal triple,
`w1` = wedge single, `h1` = hashed single, `a1` = adder single,
`b1` = bold single, `d1` = dashed single, `o1` = dotted single, and
`s1` = wavy single. Aromaticity is a separate chemical property of an OASA
bond; `a` does not encode aromaticity.

### Directed wedge endpoints

`start` and `end` are ordered IDREFs. For authored `w1` and `h1`, that order
is persistent depiction data: `start` is the narrow tip and `end` is the wide
base. OASA's normal CDML molecule decoder preserves the serialized order; it
does not rederive it from X/Y geometry. This is the same order consumed by the
filled and hashed wedge renderers, not an additional stereo record.

`q1` Haworth front edges and `n*` ordinary bonds retain their existing ordered
endpoint references but have no new wide/narrow interpretation. Every `q1`,
`w1`, `h1`, and `n1` remains chemical order one. A caller that constructs a
new directionless wedge may explicitly apply a geometry policy through the
OASA bond-ordering helper. Any repair for historical documents whose producer
did not provide meaningful wedge endpoint order must be an explicit,
version-scoped migration choice, never normal authoritative CDML decoding.

### Depiction attributes (optional)

These are only written when their values differ from the document `<standard>`.

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `line_width` | float (string) | from standard | Stroke width |
| `bond_width` | float (string) | from standard | Spacing for double/triple bonds |
| `wedge_width` | float (string) | from standard | Width of wedge bonds |
| `double_ratio` | float (string) | from standard | Length ratio for double bond inner line |
| `center` | enum | -- | `"yes"` or `"no"`; centered double bond |
| `auto_sign` | int (string) | `"1"` | Double bond side selection; `"-1"` to flip |
| `equithick` | int (string) | `"0"` | `"0"` or `"1"`; equal thickness for all lines |
| `simple_double` | int (string) | `"1"` | `"0"` or `"1"`; simple double bond drawing |
| `color` | hex color | `"#000"` | Bond line color |
| `wavy_style` | enum | -- | For `s*` bonds: `"sine"`, `"half-circle"`, `"box"`, `"triangle"` |
| `haworth_position` | enum | -- | `"front"` or `"back"`; Haworth depth metadata used with established Haworth styles |

### Direct-glycosidic Haworth profile

The supported 26.07 direct-glycosidic Haworth authoring route is a bounded
two-ring drawing profile, not a general carbohydrate stereochemistry model. It
accepts exactly two vertex-disjoint five- or six-member C/O rings joined by one
single, degree-two exterior oxygen bridge. The durable output records the
ordinary bond type plus the established `q`, `w`, or `n` depiction style and
the `haworth_position="front"` or `"back"` attribute where applicable.
Coordinates, ordered endpoints, style, and these depiction attributes persist
through normal CDML insertion, Save, reload, and backend round trips.

This profile describes an unambiguous two-dimensional Haworth drawing
convention. It does not infer, validate, or claim alpha/beta anomeric state,
tetrahedral configuration, or a general reaction/carbohydrate semantics model.
Fused, spiro, bridged, indirect-link, non-single-bridge, and other multi-ring
topologies are outside this authoring route; compatible imported CDML retains
its content through ordinary opaque/compatibility preservation.

For `a*`, `d*`, and `o*`, the selected style always occupies the primary bond
axis. Their additional lanes use the following matrix:

| Order and centering | Primary axis | Additional lanes |
|---------------------|--------------|------------------|
| `1` | One styled lane | None |
| `2`, `center` absent or `"no"` | One styled lane | One offset lane; plain when `simple_double="1"`, styled when `"0"` |
| `2`, `center="yes"` | None | Two equal, full-length styled flanking lanes |
| `3` | One styled lane | Two full-length outer lanes; plain when `simple_double="1"`, styled when `"0"` |

An absent `simple_double` has the effective value `"1"` without becoming an
authored attribute. A backend or frontend projection must retain that lexical
absence. For styled triples, `center` is ignored and an authored structural
operation retains or creates `simple_double` so the outer-lane choice remains
persistent.

`double_ratio` shortens only the added lane of an uncentered order-2 bond,
symmetrically about its midpoint. Centered order-2 lanes and all order-3 lanes
remain full length. `equithick` changes only adder (`a*`) amplitude:
`"0"` is tapered and `"1"` is constant-width. It has no visual effect on
`d*` or `o*`. A styled bond whose resolved endpoints coincide emits no
rendering primitives.

The `d*` family is an ordinary dashed depiction and uses the same length
profile as the corresponding `n*` order. The separately named
`dashed_hbond` length profile remains available for explicit hydrogen-bond
semantics; CDML `d1` does not select it implicitly.

### Serialization order

Bond depiction attributes are written in this order:
`line_width`, `bond_width`, `center`, `auto_sign`, `equithick`, `wedge_width`,
`double_ratio`, `simple_double`, `color`, `wavy_style`, `haworth_position`.

---

## Common child elements

### `<point>`

Stores 2D (or 3D) coordinates for a vertex or control point.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `x` | string | Yes | Coordinate, may include unit suffix (`"1.500cm"`) |
| `y` | string | Yes | Same |
| `z` | string | No | Only present when z != 0 |

### `<font>`

Overrides the document `<standard>` font for a specific object. Only written
when the object's font differs from the standard.

| Attribute | Type | Notes |
|-----------|------|-------|
| `size` | int | Font point size |
| `family` | string | Font family name |
| `color` | hex color | Font color; only when different from standard line_color |

Atom font `size` uses a positive decimal integer grammar. A compatibility
document with a fractional, non-decimal, non-positive, or otherwise malformed
atom font size remains authoritative source content, but its affected atom is
display-only in a synchronized projection and carries a backend diagnostic. A
frontend never rounds or repairs that source value.

### `<ftext>` -- rich text

Rich text content stored as an escaped XML text node (since version 0.16).

Supported formatting tags within the escaped content:
- `<sub>` -- subscript
- `<sup>` -- superscript
- `<b>` -- bold
- `<i>` -- italic

Tags may be nested. Example:

```xml
<ftext>&lt;i&gt;n&lt;/i&gt;-butanol</ftext>
```

CDML 26.07 authored rich text has one deliberately small fragment grammar.
The ftext character-data value contains only literal rendered text plus nested,
unqualified `b`, `i`, `sub`, and `sup` tags. Tags have no attributes or
namespace declarations; comments, processing instructions, DTDs, entity
declarations, custom entity references, unknown tags, and other elements are
outside the authored grammar. In the
canonical run representation, styles use the stable order `b`, `i`, `sub`,
`sup`; duplicate styles and a combined `sub` plus `sup` are rejected. Adjacent
runs with identical styles join; empty runs are omitted. Literal
rendered `<`, `>`, and `&` use ordinary XML character references inside the
authored value, for example `&lt;`, `&gt;`, and `&amp;` before the complete CDML
serializer applies its outer escaping.

An authored direct-root Text may carry at most one simple direct `<font>` before
its `<ftext>`. Rich Text patches replace complete canonical runs and may name
only `family`, `size`, or `color` root-font attributes. Named values are
canonical nonblank family text, integer size 4--144, and lowercase six-digit
hex color. An absent font remains absent unless a named font change requires
one; unmentioned attributes, including unknown font attributes, are preserved.

In versions before 0.16, rich text was stored as direct XML children of
`<ftext>` rather than escaped text. Those direct child nodes are
compatibility/preservation content, not globally recognized core CDML names:
the current authored form stores formatting as escaped character data, and
generic direct markup could be external or user data. Their lexical QName and
in-scope namespace context therefore remain semantic preservation data; a
generic backend must not normalize a prefix spelling or treat such nodes as
typed `<sub>`, `<sup>`, `<b>`, or `<i>` records.

### `<mark>` -- electron marks and annotations

Marks are visual annotations attached to atoms (lone pairs, radicals, charges,
orbital indicators, text labels).

#### Common mark attributes

| Attribute | Type | Notes |
|-----------|------|-------|
| `type` | string | Mark class name (see table below) |
| `x` | string | Coordinate with unit |
| `y` | string | Coordinate with unit |
| `auto` | int | `0` or `1`; auto-positioned |
| `size` | float | Size of the mark |

#### Mark types

| Type string | Visual | Extra attributes |
|-------------|--------|-----------------|
| `radical` | Single dot | -- |
| `biradical` | Two dots | -- |
| `dotted_electronpair` | Two dots (lone pair) | -- |
| `electronpair` | Line (lone pair) | `line_width`: float |
| `plus` | Plus sign | `draw_circle`: `"yes"`/`"no"` |
| `minus` | Minus sign | `draw_circle`: `"yes"`/`"no"` |
| `text_mark` | Custom text | `text`: string |
| `referencing_text_mark` | Reference text | `refname`: string |
| `atom_number` | Atom number | `refname`: string |
| `free_sites` | Free sites | `refname`: string |
| `oxidation_number` | Oxidation state | `refname`: string |
| `pz_orbital` | p-orbital lobes | -- |

#### Authored atom-mark operation profile (26.07)

The revision-bound `atom.mark.apply` backend operation authors only `plus`,
`minus`, `radical`, `biradical`, `electronpair`, `dotted_electronpair`, and
`pz_orbital` through exact `add` and `remove` intent. It appends a new direct
`<mark>` as the final atom child; it does not assign a mark `id`.
Removal without a selector identifies the first direct matching type in child
order, so later duplicate compatible marks remain persistent content. A
selected-mark remove may use `matching_mark_index`, a nonnegative exact
integer ordinal among direct core same-type mark children; malformed or
out-of-range selectors reject atomically. The operation always
writes `auto="0"` and paired `x`/`y` centimetre coordinates derived from the
authoritative atom's one direct core point. Plus and minus use a 12-point
45-degree offset, size `10`, and `draw_circle="yes"`; radical and biradical
use a 12-point 90-degree offset and size `4`; electronpair and
dotted_electronpair use a 12-point 180-degree offset and sizes `10` and `4`;
electronpair additionally writes `line_width="2"`. `pz_orbital` uses the atom
point itself and size `40`; its renderer retains the established default
orientation when no separate orientation attribute is present.

Adding/removing plus, minus, radical, or biradical also applies the matching
atom `charge` or `multiplicity` delta in the same atomic document operation.
Plus/minus validate only their addressed `charge` scalar within -9 through 9;
radical/biradical validate only their addressed `multiplicity` scalar within 1
through 3. The other scalar is preserved verbatim even when legacy or
incompatible, and presentation-only marks preserve both scalars.
This authored behavior adds to, rather than normalizes, accepted legacy CDML:
older documents may retain omitted coordinates, legacy scalar spelling, extra
attributes, unsupported mark types, or duplicate direct marks as compatible
preservation content until an operation explicitly addresses them.

---

## `<template>`

Template attachment metadata inside a molecule. Used for fragment-based
drawing where molecules connect at designated attachment points.

| Attribute | Type | Notes |
|-----------|------|-------|
| `atom` | IDREF | Attachment atom |
| `bond_first` | IDREF | First attachment bond (optional) |
| `bond_second` | IDREF | Second attachment bond (optional) |

---

## `<fragment>`

Named substructure within a molecule.

| Attribute | Type | Notes |
|-----------|------|-------|
| `id` | ID | Fragment identifier |
| `type` | enum | `"explicit"` (default), `"implicit"`, or `"linear_form"` |

### Children

| Child | Attributes | Notes |
|-------|------------|-------|
| `name` | -- | Text content (XML-escaped) |
| `bond` | `id` (IDREF) | References a bond in the molecule |
| `vertex` | `id` (IDREF) | References a vertex in the molecule |
| `property` | `name`, `value`, `type` | Arbitrary key-value property |

The backend ordinary-fragment metadata operations author and edit only the
narrow `explicit`/`implicit` form with one direct nonblank `name`, followed by
direct `bond` and `vertex` IDREF children. They preserve richer compatible
fragment XML, including `linear_form`, properties, extension content, and
ambiguous historical shapes, as read-only document content.

The backend-authored narrow `linear_form` grammar is exactly a `fragment` with
only `id` and `type="linear_form"`, a direct `<name>linear_form</name>`, path-
ordered direct `bond` IDREF children, path-ordered direct `vertex` IDREF
children, and one final `<property name="bond_length" value="10"
type="IntType"/>`. Only whitespace character data may surround direct child
elements. This fixed 10 PostScript-point layout is persistent molecule geometry,
not a renderer spacing promise. Richer or differently shaped imported linear
forms remain preservation-only.

---

## `<display-form>` and `<user-data>`

Both elements preserve their XML subtree, namespace bindings, values, and
relative document position without interpretation. Serialization may change
lexical XML spelling or formatting. Their descendants receive no CDML lookup,
reference, or provisional-token semantics; literal IDs still reserve global
collision names.

- `<display-form>`: stores alternative display representations.
- `<user-data>`: stores arbitrary application-specific data.

Content is cloned on read and appended on write without interpretation.

---

## Drawing objects

### Top-level identity and geometry

An `authored-26.07` assessment requires a producer to assign a nonempty,
non-whitespace, document-unique durable `id` to every newly authored selectable direct child:
molecule, arrow, plus, standalone text, rect, square, oval, circle, polygon,
polyline, and reaction. This is an authored-output requirement. Compatibility
Load and Commit continue to accept and preserve ID-less legacy records.
An operation that needs backend correlation MUST use a valid operation-scoped
provisional identifier in a recognized declaration and consume it through an
accepted backend transaction. ID-less legacy records remain compatible and are
preserved without frontend repair. `reaction@id` remains optional compatibility
data in 26.07.

Every literal `id` in an ID-definition position reserves a collision name
across the complete document, including opaque extension content. A recognized
`id` field documented as an IDREF is a reference, not a definition: currently
this means `fragment/vertex@id` and `fragment/bond@id` do not reserve another
name. Opaque XML receives no CDML lookup, reference, or provisional-token
semantics. Only recognized editable declarations and recognized reference
fields receive those semantics; opaque reference-like strings remain
uninterpreted literal content. The established `<display-form>`,
`<user-data>`, and handler-less `<external-data>` records are
preservation-only containers: their descendants are opaque for these purposes,
even when they use CDML-looking names or provisional-looking values. Their
literal `id` values still reserve document-wide collision names. An
`external-data@id` is literal preservation content rather than an editable
provisional declaration.

The following minima are authored requirements. Incomplete historical records
remain compatible preservation input; they are not portable authored output.

### `<arrow>`

```xml
<arrow id="arr1" type="normal" start="no" end="yes" width="1.0" spline="no">
  <point x="0.000cm" y="0.000cm"/>
  <point x="1.764cm" y="0.000cm"/>
</arrow>
```

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | ID | -- | |
| `type` | string | `"normal"` | Arrow style type |
| `start` | enum | `"no"` | `"yes"` or `"no"`; arrowhead at start |
| `end` | enum | `"no"` | `"yes"` or `"no"`; arrowhead at end |
| `spline` | enum | `"no"` | `"yes"` or `"no"`; spline interpolation |
| `width` | float (string) | -- | Line width |
| `shape` | string | -- | Arrow shape parameters |
| `color` | string | -- | Line color |

Children: two or more direct `<point>` elements defining the ordered path.

### `<plus>`

A plus sign between reactants/products.

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | ID | -- | |
| `font_size` | int | `14` | |
| `color` | hex color | `"#000"` | Only written when not default |
| `background-color` | hex color | `"#ffffff"` | Only written when not default |

Children: exactly one direct `<point>`, optional `<font>`.

### `<text>` (standalone, top-level)

A free-form rich text label on the canvas.

| Attribute | Type | Notes |
|-----------|------|-------|
| `id` | ID | |
| `background-color` | hex color | Optional |

Children: optional `<font>`, exactly one direct `<point>`, and exactly one
direct `<ftext>`.

### Vector graphics: `<rect>`, `<square>`, `<oval>`, `<circle>`

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | ID | -- | Optional compatibility data; new selectable records follow the top-level identity rule |
| `x1` | string (with unit) | -- | Bounding box corner |
| `y1` | string (with unit) | -- | |
| `x2` | string (with unit) | -- | |
| `y2` | string (with unit) | -- | |
| `area_color` | hex color | -- | Fill color |
| `line_color` | hex color | -- | Outline color |
| `width` | float | `1.0` | Line width |

Authored box shapes require all four bounds: `x1`, `y1`, `x2`, and `y2`.

### `<polygon>`

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | ID | -- | Optional compatibility data; new selectable records follow the top-level identity rule |
| `area_color` | hex color | -- | Fill color |
| `line_color` | hex color | -- | Outline color |
| `width` | float | `1.0` | Line width |

Children: at least three ordered direct `<point>` elements.

### `<polyline>`

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | ID | -- | Optional compatibility data; new selectable records follow the top-level identity rule |
| `line_color` | hex color | -- | Line color |
| `width` | float | `1.0` | Line width |
| `spline` | int | `0` | `0` or `1`; spline interpolation |

Children: at least two ordered direct `<point>` elements.

---

## `<reaction>`

Groups related drawing objects into a reaction scheme. Children are IDREF
elements pointing to persistent objects. The child name states the intended
target category. `authored-26.07` requires every recognized role to reference
a nonempty durable ID on a core direct child of the CDML root in that category.
Compatibility Load and Commit remain lossless and permissive for historical
reaction structures, including nested or ID-less references that do not meet
the authored profile.

```xml
<reaction>
  <reactant idref="m1"/>
  <product idref="m2"/>
  <arrow idref="arr1"/>
  <condition idref="text1"/>
  <plus idref="plus1"/>
</reaction>
```

| Child element | Attribute | Notes |
|---------------|-----------|-------|
| `reactant` | `idref` | `authored-26.07`: direct-root molecule |
| `product` | `idref` | `authored-26.07`: direct-root molecule |
| `arrow` | `idref` | `authored-26.07`: direct-root arrow |
| `condition` | `idref` | `authored-26.07`: direct-root standalone text |
| `plus` | `idref` | `authored-26.07`: direct-root plus sign |

The profile checks target scope and target category only. It does not define
reaction cardinality, ordering, stoichiometry, chemistry, or a uniqueness rule
for repeated role targets. Those semantics remain available for a later
versioned reaction model.

---

## `<external-data>`

Application-specific external data. A typed handler may interpret its content
and attributes, but the OASA document backend preserves them even without one.
Without such a handler, its own attributes (including `id`) and complete
descendant subtree are preservation-only literal content. Literal IDs reserve
global collision names without becoming editable provisional declarations.

---

## Proposal registry

This registry is non-normative. Entries preserve design intent and do not add
element grammar, require writer output, or make content editable. A proposal
becomes authored CDML only after a versioned specification, preservation and
projection disposition, and implementation evidence.

### Candidate `attach_atom` design

If adopted in a future version, this candidate optional attribute would store
attachment intent for multi-atom labels.

| Attribute | Type | Default | Applies to |
|-----------|------|---------|------------|
| `attach_atom` | enum | Candidate default: `"first"` | Candidate label-bearing clipping element |

Candidate values would be `"first"` or `"last"`.

**Candidate stored meaning:**
- Attachment intent, not coordinates.
- Renderers would derive connector geometry from text layout (`label_bbox()` /
  `label_attach_bbox()`) and line-rectangle intersection.

**Candidate location:**
- On the CDML element that would represent the label participating in connector
  clipping.
- For ordinary molecules: on label-bearing vertex elements (`<atom>`,
  `<group>`, or `<text>`) when the displayed label would be multi-atom.
- For Haworth substituents: on the label-bearing node that would be generated
  for the substituent label in CDML data.

**Candidate semantics:**
- `"first"` would attach to the first atom token in label text (for example
  the `C` in `CH2OH`).
- `"last"` would attach to the last atom token in label text (for example the
  `O` in `CH2OH`).
- `first`/`last` would be defined by token order in text, not screen direction,
  not mirroring, and not coordinate-system orientation.
- Tokenization would be renderer-defined and would need to be stable.
- Minimum candidate tokenization rule for interoperability: atom tokens would
  be element symbols (uppercase letter with optional lowercase letter).
- Digits, charge markers (`+`/`-`), and text markup would be treated as
  decorations attached to atom tokens, not standalone attachable atom tokens.

**Candidate writer policy:**
- Writers would not write it for single-atom labels where attachment is
  unambiguous (`O`, `N`, `Cl`, etc.).
- Writers would write it for multi-atom labels where attachment intent matters
  (`CH2OH`, `OAc`, `NHCH3`, and similar).
- Omission would mean `"first"`.
- Writers could choose to emit only non-default `"last"` to reduce diff noise.
- Writers could optionally emit it only when attachment intent was explicitly edited
  by a user workflow.

**Compatibility hypothesis:**
- If adopted, the additive attribute would require a versioned compatibility
  and preservation decision before writers emit it.
- Existing readers and documents have no `attach_atom` requirement.

### Deferred document concepts

`bracket`, `vector`, visual `layer`, visual `page`, visual grouping, and
generic stacking containers are proposals, not current CDML grammar. Chemical
`<group>` remains an established molecular vertex and is not a visual
container. The direct-child sequence is the only established document-order
mechanism; it does not imply an unimplemented layer or grouping model.

Legacy or extension `<bracket>` and `<vector>` content is preserve-only opaque
content in 26.07, so it has durable round-trip support while editable typed
bracket/vector grammar remains separately versioned. It does not receive
provisional-ID allocation. The established bracket tool persists its artwork
as top-level `<polyline>` records rather than a first-class `<bracket>` record.

---

## Version history

CDML versions are upgraded by an implemented chain of transformers. Each
transformer performs an in-place DOM transformation from one version to the
next. The implemented runtime chain is: `0.6` -> `0.7` -> `0.8` -> `0.9` -> `0.10` -> `0.11` -> `0.12` ->
`0.13` -> `0.14` -> `0.15` -> `0.16` -> `26.02` -> `26.07`.

### 0.6 -> 0.7

**Bond type rename.** `"forth"` -> `"up"`.

### 0.7 -> 0.8

**Bond type shortening.** Long bond type names replaced with single characters:

| Before | After |
|--------|-------|
| `"single"` | `"s"` |
| `"double"` | `"d"` |
| `"triple"` | `"t"` |
| `"up"` | `"w"` |
| `"back"` | `"h"` |

### 0.8 -> 0.9

No-op. Pass-through.

### 0.9 -> 0.10

**Add `<standard>` element.** If no `<standard>` exists, inserts one with
hardcoded defaults:

```xml
<standard font_family="helvetica" font_size="12" line_width="1.0px">
  <bond double-ratio="1" length="1.0cm" width="6.0px" wedge-width="2.0px"/>
  <arrow length="1.6cm"/>
</standard>
```

### 0.10 -> 0.11

**Bond type remap to `<type><order>` format.** Old single-character or integer
bond types are converted using the mapping:

| Old value | New value |
|-----------|-----------|
| (index 1 or `"s"` or `"single"`) | `"n1"` |
| (index 2 or `"d"` or `"double"`) | `"n2"` |
| (index 3 or `"t"` or `"triple"`) | `"n3"` |
| (index 4 or `"w"` or `"up"`) | `"w1"` |
| (index 5 or `"h"` or `"back"`) | `"h1"` |

**Bond attribute renames:**
- `distance` -> `bond_width` (for normal bonds, type starts with `n`).
- `distance` -> `wedge_width` (for wedge/hashed bonds; value is doubled).
- `width` -> `line_width`.
- Old attributes (`distance`, `width`) are removed after migration.

### 0.11 -> 0.12

No-op. From this version, `post_read_analysis()` double bond positioning data
is stored in the file.

### 0.12 -> 0.13

**Charge consolidation from marks.** Scans all `<atom>` elements for
`<mark type="plus">` and `<mark type="minus">` children. Each `plus` mark
adds +1 to charge, each `minus` mark adds -1. The total is written to the
atom's `charge` attribute.

### 0.13 -> 0.14

**Atom element type splitting.** Atoms without a `name` attribute become
`<text>` elements. Atoms with names matching the builtin group list (`OCH3`,
`NO2`, `COOH`, `COOCH3`, `Me`, `CN`, `SO3H`, `PPh3`, `OMe`, `Et`, `Ph`,
`COCl`, `CH2OH`) become `<group group-type="builtin">` elements. All other
atoms remain `<atom>`.

### 0.14 -> 0.15

**Electronpair line_width.** For `<mark type="electronpair">` without
`line_width`, computes `round(round(size/2)/2)` and sets `line_width`.

**Explicit multiplicity.** Computes multiplicity from radical marks (+1 each)
and biradical marks (+2 each). Sets `multiplicity` attribute on atoms that
lack it.

### 0.15 -> 0.16

**Rich text escaping.** `<ftext>` children are converted from direct XML
subtrees to escaped text nodes. For example, `<ftext><i>x</i></ftext>` becomes
`<ftext>&lt;i&gt;x&lt;/i&gt;</ftext>`. All child nodes of `<ftext>` are
serialized via `.toxml()`, concatenated, and replaced with a single text node.

### 0.16 -> 26.02

No-op. Placeholder for future extensions. The version number scheme switched
from `0.x` to `YY.MM` format.

### 26.02 -> 26.07

Structurally no-op transition. The transformer changes only root
`cdml@version` to `26.07`; it performs no XML normalization, insertion,
deletion, or reinterpretation. `26.07` documents and makes the authored
root/version/namespace profile explicit for long-standing direct-child order
and opaque-extension preservation. It adds no element grammar or namespace,
and it does not reinterpret or alter the meaning of 26.02 documents. Existing
26.02 documents remain compatible and retain their established semantics and
order when preserved.

---

## OASA and BKChem usage

Persistent CDML authority is not divided by element type. The OASA document
backend accepts and returns the complete ordered document and preserves every
persistent object, typed or opaque. Molecule codecs expose typed chemistry
behavior for `<molecule>` content, and rendering pipelines consume typed
chemistry data; neither substitutes for the complete-document session. BKChem
projects the canonical backend response and must not restore, merge, or
reconstruct omitted persistent content after a backend round-trip.

### Portable render primitives

The backend may describe a renderable molecule with an immutable,
frontend-neutral primitive batch: finite geometry and explicit colors or
semantic foreground/background roles for lines, polygons, circles, paths, and
structured text runs. A frontend maps that batch to its own painter and
metrics. Render primitives are an observation of one snapshot, not a second
document format: they neither replace CDML persistence nor carry frontend
objects, scene items, callbacks, or lifecycle state. An unsupported persistent
record remains in CDML and produces an explicit rendering diagnostic rather
than being removed.

### Top-level transform geometry

The backend transform operation uses only durable direct-root CDML geometry.
For molecules, every direct `atom`, `group`, `text`, and `query` vertex has one
direct core point; explicit direct mark `x`/`y` pairs follow their parent
vertex, while an implicit mark has neither coordinate. Arrows use at least two
points; standalone text and plus records use one; polygons use at least three;
polylines use at least two. Rectangles, squares, ovals, and circles use
`x1`, `y1`, `x2`, and `y2`. Bounds are persistent geometry, not font, Qt, or
rendered visual bounds. A selected root with ambiguous or partial core
coordinate geometry is rejected without changing the document.

### Structural deletion components

The CDML 26.07 backend structural-deletion profile acts on one durable direct
root `<molecule>` without changing the CDML element grammar. The eligible
molecule has only `id`, `name`, and namespace declarations, and its direct
children are only core `<atom>` and `<bond>` records with whitespace text or
CDATA character data between them. Comments, processing instructions,
non-whitespace character data, and every other direct node are unsupported.
The molecule, direct atoms, and direct bonds require unique durable IDs
containing at least one non-whitespace character. Each bond has distinct
nonempty `start` and `end` values that resolve to direct atoms in the same
molecule. Unknown attributes and descendants inside an eligible atom or bond
remain part of that node's preserved XML.

Removing atoms also removes their incident bonds. Remaining atoms are retained
even when isolated. The backend partitions surviving direct atoms and bonds
into connected components ordered by the earliest surviving atom in original
child order; records inside a component retain their original atom and bond
order. No surviving atom removes the original root. One component retains its
original root identity, attributes, name, and root position. A split retains
the original root for the first component and inserts shallow-cloned later
roots immediately after it. Later roots retain namespace declarations, receive
collision-safe molecule IDs reserved against all IDs in the pre-delete
document, and omit `name`.

A direct-core reaction role may keep referencing a molecule only if deletion
leaves exactly one component. The backend rejects a referenced root removal or
split without changing the complete CDML snapshot. This is operation behavior,
not a generic permission to normalize, split, or repair molecules during a
CDML round trip.

| Concern | OASA document backend | OASA molecule codecs and renderers | BKChem Qt frontend |
|---------|-----------------------|------------------------------------|--------------------|
| Complete CDML document | Owns, validates, and preserves | Typed adapters only | Submits candidates and projects response |
| Molecule chemistry | Owns document record | Reads and writes typed chemistry data | Projects and edits through CDML |
| Arrows, text, graphics, reactions, paper, and headers | Preserves typed or opaque records | May omit unsupported semantics | Projects supported records; does not re-merge losses |
| Unknown attributes, elements, namespaces, and nested content | Preserves unchanged | Must not discard through a document round-trip | Must not repair or reconstruct them |

### OASA-level known bond attributes

Core: `type`, `start`, `end`, `id`.

Depiction: `line_width`, `bond_width`, `wedge_width`, `double_ratio`,
`center`, `auto_sign`, `equithick`, `simple_double`, `color`, `wavy_style`,
`haworth_position`.

---

## Historical schema artifacts

The checked-in
[`cdml.dtd`](../packages/bkchem-app/bkchem_data/dtd/cdml.dtd) and
[`cdml.xsd`](../packages/bkchem-app/bkchem_data/dtd/cdml.xsd) are historical,
incomplete, non-authoritative artifacts. Neither is a valid validator for
current CDML, including the 26.07 authored profile. They remain in the tree as
legacy evidence; this package neither deletes nor rewrites them.

The DTD does not include:

- `<paper>`, `<viewport>` elements
- `<group>`, `<query>`, `<text>` (textatom) vertex types
- `<rect>`, `<oval>`, `<polygon>`, `<circle>`, `<square>`, `<polyline>` shapes
- `<reaction>`, `<fragment>`, `<user-data>`, `<display-form>`, `<external-data>`
- `<mark>` elements
- Modern `<standard>` attributes and children
- Modern bond attributes (`line_width`, `bond_width`, `wedge_width`, etc.)
- The `color` attribute on `<font>`

The DTD also contains a typo: `bond_lenght` instead of `bond_length`. The XSD
describes a different `header`/`chemistry`/`graphics` document structure and
does not define the current CDML vocabulary.

This specification and its version chain supersede both historical schemas.
No new XSD is adopted for 26.07. The semantic conformance corpus is the
completion artifact for the two implemented inspection profiles. A future XSD
must first demonstrate, against the recorded corpus, that it catches a useful
structural error more clearly than the semantic checks while preserving opaque
foreign subtrees and compatibility inputs. It is adopted only if that evidence
outweighs the cost of maintaining another grammar artifact.

---

## Producing CDML externally

If you generate CDML outside of BKChem or OASA:

1. Set `version="26.07"` on the root `<cdml>` element.
2. Include the namespace: `xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"`.
3. Optionally include a documentation pointer:
   `<metadata><doc href="https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"/></metadata>`.
4. Use the current bond type format: `<type_char><order_digit>` (e.g. `"n1"`).
5. Provide `<point>` children for all atoms with `x` and `y` attributes.
6. Give every atom a unique `id` attribute.
7. Reference atoms by `id` in bond `start` and `end` attributes.
8. Use a `cm` unit suffix for portable authored coordinates and shape bounds.
9. Prefer the current `<standard>` attribute names and children.
10. Preserve the full direct-child sequence. Persistent drawable records keep
    their relative paint order; metadata/default records remain unpainted.
11. Preserve unknown attributes, elements, namespaces, and nested content
    unchanged in complete-document backend round-trips. A typed codec may lack
    semantics for such content, but it may not remove that content from the
    backend document.
12. Run the `authored-26.07` conformance profile before publishing new CDML.
    It checks the implemented safety boundary; authors remain responsible for
    the normative geometry and cardinality requirements in this specification.
