# CDML Format Specification

## Overview

CDML (Chemical Drawing Markup Language) is an XML format used by BKChem and
OASA to represent 2D chemical drawings. It stores molecular structure
(atoms, bonds, groups), depiction metadata (coordinates, colors, line widths),
and drawing objects (arrows, text, shapes) in a single document.

CDML is the serialization contract between:

- **BKChem** (GUI editor): reads and writes full CDML documents with paper
  layout, viewport, standards, and all drawing object types.
- **OASA** (standalone library): reads and writes the `<molecule>` subset for
  codec operations and rendering pipelines.
- **CD-SVG**: embeds a `<cdml>` node inside standard SVG for round-trip
  editing.

### Namespace

```
http://www.freesoftware.fsf.org/bkchem/cdml
```

The namespace URI is an identifier and may not be dereferenceable; it is kept
for compatibility and identity, not as a guaranteed fetch target.

The namespace is optional for standalone `.cdml` files but required for
embedded CDML inside SVG (CD-SVG). BKChem will load CDML without the
namespace but may prompt when loading embedded CDML in SVG files with missing
or incorrect namespaces.

Documentation URL:

```
https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md
```

### Current version

`26.02`

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
<cdml version="26.02" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
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

All children except `version` on `<cdml>` are optional. Drawing objects may
appear in any order and any quantity.

---

## Root element: `<cdml>`

| Attribute | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `version` | string | Yes | -- | Schema version (e.g. `"26.02"`) |
| `type` | enum | No | `"normal"` | `"normal"`, `"template"`, or `"standard"` |
| `xmlns` | URI | No | -- | Should be `"http://www.freesoftware.fsf.org/bkchem/cdml"` |

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
  <author_program version="26.02">BKChem</author_program>
  <author>User Name</author>
  <note>Optional notes</note>
</info>
```

| Child element | Attributes | Content | Cardinality |
|---------------|------------|---------|-------------|
| `author_program` | `version` (optional) | Program name (text) | 0..1 |
| `author` | -- | Author name (text) | 0..* |
| `note` | -- | Free-form text | 0..* |

---

## `<standard>`

Drawing defaults applied when per-object values are absent. Saved as part of
the document and can be stored separately as a personal standard.

### Attributes

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `line_width` | string (with units) | `"1px"` | Supports `px`, `cm`, `mm` |
| `font_size` | int | `12` | Point size |
| `font_family` | string | `"helvetica"` | Font family name |
| `line_color` | hex color | `"#000"` | Default line/stroke color |
| `area_color` | hex color | `""` | Default fill color; empty = transparent |
| `paper_type` | string | `"A4"` | Paper size name |
| `paper_orientation` | string | `"portrait"` | `"portrait"` or `"landscape"` |
| `paper_crop_svg` | int | `0` | `0` or `1` |
| `paper_crop_margin` | int | `10` | Pixels |

### Children

**`<bond>`** -- bond drawing defaults:

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `length` | string (with units) | `"0.7cm"` | Standard bond length |
| `width` | string (with units) | `"6px"` | Double bond line spacing |
| `wedge-width` | string (with units) | `"5px"` | Wedge bond width |
| `double-ratio` | float | `0.75` | Length ratio for double bond inner line |
| `min_wedge_angle` | float | `0.3927` (~pi/8) | Minimum wedge angle in radians |

**`<arrow>`** -- arrow defaults:

| Attribute | Type | Default |
|-----------|------|---------|
| `length` | string (with units) | `"1.6cm"` |

**`<atom>`** -- atom display defaults:

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `show_hydrogens` | int | `0` | `0` or `1`; also accepts `"True"`/`"False"` on read |

---

## `<paper>`

Page layout and export options. Written by BKChem only.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `type` | string | Yes | Paper size name (e.g. `"A4"`, `"Letter"`, `"custom"`) |
| `orientation` | string | Yes | `"portrait"` or `"landscape"` |
| `crop_svg` | int | No | `0` or `1`; crop SVG to content |
| `crop_margin` | int | No | Margin in pixels when cropping |
| `use_real_minus` | int | No | `0` or `1`; use Unicode minus sign |
| `replace_minus` | int | No | `0` or `1` |
| `size_x` | int | When `type="custom"` | Custom width |
| `size_y` | int | When `type="custom"` | Custom height |

### Recognized paper types

Standard ISO and US sizes: `A0`--`A10`, `B0`--`B10`, `C0`--`C10`, `Ledger`,
`Legal`, `Letter`, `Tabloid`. Values are stored as `[width_mm, height_mm]`.

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

Coordinate attributes (`x`, `y`, `z` on `<point>` elements) may be:

- **Pure numbers**: interpreted as raw float values (pixels in BKChem screen
  space).
- **Values with unit suffix**: `"1.5cm"`, `"10mm"`, `"40px"`.

OASA writes coordinates as `"%.3fcm"` strings using the conversion constant
`POINTS_PER_CM = 72.0 / 2.54` (~28.3465 points per cm). BKChem uses
`misc.split_number_and_unit()` to parse any supported unit suffix.

### Y-axis convention

BKChem stores CDML in canvas coordinates: **+Y points down**. This matches the
Tk canvas origin (top-left). OASA may canonicalize coordinates internally
(**+Y up**) for computation or format interchange, but CDML written on disk
remains **+Y down** unless an explicit versioned migration says otherwise.

### Width and length values

Attributes like `line_width`, `bond length`, `wedge-width` use the same unit
system (`px`, `cm`, `mm`). BKChem normalizes all values through
`Screen.any_to_px()` on read.

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
| `start` | IDREF | Yes | ID of first vertex |
| `end` | IDREF | Yes | ID of second vertex |
| `id` | ID | No | Bond identifier |

### Bond type string format

The `type` attribute is a string: `<type_char><order_digit>`.

**Type characters:**

| Char | Meaning | Visual |
|------|---------|--------|
| `n` | Normal | Plain line(s) |
| `w` | Wedge | Filled triangle (stereo up) |
| `h` | Hashed | Dashed wedge (stereo down) |
| `a` | Bold | Thick line |
| `b` | Dashed | Dashed line |
| `d` | Dotted | Dotted line |
| `o` | Partial | Half/partial bond |
| `s` | Wavy | Squiggly/wave line |
| `q` | Quadruple | Four lines |

**Legacy type characters** (normalized on read):

| Legacy | Normalized to | Origin |
|--------|---------------|--------|
| `l` | `h` | Legacy left-hashed |
| `r` | `h` | Legacy right-hashed |

**Order digit:** `1` (single), `2` (double), `3` (triple).

Examples: `n1` = normal single, `n2` = normal double, `n3` = normal triple,
`w1` = wedge single, `h1` = hashed single, `a1` = bold single,
`b1` = dashed single, `s1` = wavy single.

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

### Serialization order

Bond depiction attributes are written in this order:
`line_width`, `bond_width`, `center`, `auto_sign`, `equithick`, `wedge_width`,
`double_ratio`, `simple_double`, `color`, `wavy_style`.

### Unknown attribute preservation

Any XML attribute on `<bond>` or `<atom>` that is not in the known set is
preserved through round-trip read/write. This allows forward-compatible
extension: older readers ignore unknown attributes, newer writers emit them.
The preserved attributes are stored in `_cdml_unknown_attrs` and tracked via
`_cdml_present`.

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

In versions before 0.16, rich text was stored as direct XML children of
`<ftext>` rather than escaped text.

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

---

## `<display-form>` and `<user-data>`

Both elements preserve arbitrary DOM content verbatim through round-trip.

- `<display-form>`: stores alternative display representations.
- `<user-data>`: stores arbitrary application-specific data.

Content is cloned on read and appended on write without interpretation.

---

## Drawing objects

### `<arrow>`

```xml
<arrow id="arr1" type="normal" start="no" end="yes" width="1.0" spline="no">
  <point x="0.0" y="0.0"/>
  <point x="50.0" y="0.0"/>
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

Children: one or more `<point>` elements defining the path.

### `<plus>`

A plus sign between reactants/products.

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | ID | -- | |
| `font_size` | int | `14` | |
| `color` | hex color | `"#000"` | Only written when not default |
| `background-color` | hex color | `"#ffffff"` | Only written when not default |

Children: one `<point>`, optional `<font>`.

### `<text>` (standalone, top-level)

A free-form rich text label on the canvas.

| Attribute | Type | Notes |
|-----------|------|-------|
| `id` | ID | |
| `background-color` | hex color | Optional |

Children: `<font>` (optional), `<point>`, `<ftext>`.

### Vector graphics: `<rect>`, `<square>`, `<oval>`, `<circle>`

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `x1` | string (with unit) | -- | Bounding box corner |
| `y1` | string (with unit) | -- | |
| `x2` | string (with unit) | -- | |
| `y2` | string (with unit) | -- | |
| `area_color` | hex color | -- | Fill color |
| `line_color` | hex color | -- | Outline color |
| `width` | float | `1.0` | Line width |

### `<polygon>`

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `area_color` | hex color | -- | Fill color |
| `line_color` | hex color | -- | Outline color |
| `width` | float | `1.0` | Line width |

Children: multiple `<point>` elements.

### `<polyline>`

| Attribute | Type | Default | Notes |
|-----------|------|---------|-------|
| `line_color` | hex color | -- | Line color |
| `width` | float | `1.0` | Line width |
| `spline` | int | `0` | `0` or `1`; spline interpolation |

Children: multiple `<point>` elements.

---

## `<reaction>`

Groups related drawing objects into a reaction scheme. Children are IDREF
elements pointing to existing top-level objects.

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
| `reactant` | `idref` | References a molecule |
| `product` | `idref` | References a molecule |
| `arrow` | `idref` | References an arrow |
| `condition` | `idref` | References a text object |
| `plus` | `idref` | References a plus sign |

---

## `<external-data>`

Application-specific external data. Read by BKChem's external data manager.
Content and attributes are application-defined.

---

## Planned extensions

### `attach_atom` attribute

An optional attribute that stores attachment intent for multi-atom labels.

| Attribute | Type | Default | Applies to |
|-----------|------|---------|------------|
| `attach_atom` | enum | `"first"` | Label-bearing elements that participate in connector clipping |

Values: `"first"` or `"last"`.

**What is stored:**
- Attachment intent, not coordinates.
- Renderers derive connector geometry from text layout (`label_bbox()` /
  `label_attach_bbox()`) and line-rectangle intersection.

**Where it lives:**
- On the CDML element that represents the label participating in connector
  clipping.
- For ordinary molecules: on label-bearing vertex elements (`<atom>`,
  `<group>`, or `<text>`) when the displayed label is multi-atom.
- For Haworth substituents: on the label-bearing node generated for the
  substituent label in CDML data.

**Semantics:**
- `"first"`: attach to the first atom token in label text (for example the `C`
  in `CH2OH`).
- `"last"`: attach to the last atom token in label text (for example the `O`
  in `CH2OH`).
- `first`/`last` are defined by token order in text, not screen direction,
  not mirroring, and not coordinate-system orientation.
- Tokenization is renderer-defined but must be stable.
- Minimum tokenization rule for interoperability: atom tokens are element
  symbols (uppercase letter with optional lowercase letter).
- Digits, charge markers (`+`/`-`), and text markup are treated as decorations
  attached to atom tokens, not standalone attachable atom tokens.

**Write rules:**
- Do not write for single-atom labels where attachment is unambiguous (`O`,
  `N`, `Cl`, etc.).
- Write for multi-atom labels where attachment intent matters (`CH2OH`, `OAc`,
  `NHCH3`, and similar).
- Omission means `"first"`.
- Writers may choose to emit only non-default `"last"` to reduce diff noise.
- Writers may optionally emit only when attachment intent was explicitly edited
  by a user workflow.

**Backward compatibility:**
- Optional additive attribute; older BKChem/OASA readers that do not recognize
  it safely ignore it and fall back to full-label clipping behavior.
- No CDML version bump required.

---

## Version history

CDML versions are upgraded by a chain of transformers. Each transformer
performs an in-place DOM transformation from one version to the next. The chain
is: `0.6` -> `0.7` -> `0.8` -> `0.9` -> `0.10` -> `0.11` -> `0.12` ->
`0.13` -> `0.14` -> `0.15` -> `0.16` -> `26.02`.

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

---

## OASA vs BKChem CDML usage

OASA and BKChem both read and write CDML but at different scopes:

| Capability | BKChem | OASA |
|------------|--------|------|
| Full document (info, standard, paper, viewport) | Read + Write | -- |
| `<molecule>` with atoms and bonds | Read + Write | Read + Write |
| `<group>` expansion from SMILES | -- | Yes (via `known_groups.cdml_to_smiles`) |
| Version transformers (0.6 -> 26.02) | Yes | -- |
| Unknown attribute preservation | Yes | Yes |
| `<arrow>`, `<plus>`, `<text>`, graphics | Read + Write | -- |
| `<reaction>` | Read + Write | -- |
| CD-SVG embedding | Read + Write | -- |
| Render-ops pipeline (molecule -> LineOp, TextOp, etc.) | -- | Yes |

### OASA-level known atom attributes

OASA recognizes a smaller set of atom attributes than BKChem:

```
id, name, charge, multiplicity, valency, isotope, free_sites
```

Any other attribute present on an `<atom>` element is preserved as an unknown
attribute and re-emitted on write.

### OASA-level known bond attributes

Core: `type`, `start`, `end`, `id`.

Depiction: `line_width`, `bond_width`, `wedge_width`, `double_ratio`,
`center`, `auto_sign`, `equithick`, `simple_double`, `color`, `wavy_style`.

---

## Legacy DTD

The file `packages/bkchem-app/bkchem_data/dtd/cdml.dtd` contains a legacy DTD that
is **incomplete and outdated**. It does not include:

- `<paper>`, `<viewport>` elements
- `<group>`, `<query>`, `<text>` (textatom) vertex types
- `<rect>`, `<oval>`, `<polygon>`, `<circle>`, `<square>`, `<polyline>` shapes
- `<reaction>`, `<fragment>`, `<user-data>`, `<display-form>`, `<external-data>`
- `<mark>` elements
- Modern `<standard>` attributes and children
- Modern bond attributes (`line_width`, `bond_width`, `wedge_width`, etc.)
- The `color` attribute on `<font>`

The DTD also contains a typo: `bond_lenght` instead of `bond_length`.

This specification supersedes the DTD as the authoritative reference.

---

## Producing CDML externally

If you generate CDML outside of BKChem or OASA:

1. Set `version="26.02"` on the root `<cdml>` element.
2. Include the namespace: `xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"`.
3. Optionally include a documentation pointer:
   `<metadata><doc href="https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"/></metadata>`.
4. Use the current bond type format: `<type_char><order_digit>` (e.g. `"n1"`).
5. Provide `<point>` children for all atoms with `x` and `y` attributes.
6. Give every atom a unique `id` attribute.
7. Reference atoms by `id` in bond `start` and `end` attributes.
8. Use `cm` unit suffix for coordinates if targeting OASA codec compatibility.
9. Prefer the current `<standard>` attribute names and children.
10. Unknown attributes will be preserved on round-trip by both BKChem and OASA.
