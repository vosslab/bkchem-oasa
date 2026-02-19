# BKChem format spec

## Overview
BKChem stores drawings in CDML, an XML format used by the application and
embedded inside CD-SVG. CDML files use the `.cdml` extension, while compressed
CDML uses `.cdgz`. CD-SVG uses `.svg` or `.svgz` and includes a `<cdml>` node
inside the SVG.

This document describes the current CDML structure as used by BKChem 26.02.
The legacy DTD in `packages/bkchem-app/bkchem_data/dtd/cdml.dtd` is incomplete and
does not reflect all modern elements or attributes.

## File types
- `.cdml`: plain CDML XML.
- `.cdgz`: gzip-compressed CDML XML.
- `.svg`: CD-SVG with embedded CDML.
- `.svgz`: gzip-compressed CD-SVG.

## Root element
```xml
<cdml version="26.02" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  ...
</cdml>
```

Attributes:
- `version` (required): CDML schema version, currently `26.02`.
- `type` (optional): `normal`, `template`, or `standard`. Defaults to `normal`.

## Core sections
CDML typically includes the following sections in this order:
- `info` (optional): metadata.
- `standard` (optional): drawing defaults.
- `paper` (optional): page layout and export defaults.
- `viewport` (optional): visible area.
- drawing objects: `molecule`, `arrow`, `text`, and other supported objects.

## Namespaces
CDML uses the namespace from `bkchem/data.py`:
- `http://www.freesoftware.fsf.org/bkchem/cdml`

BKChem will still load CDML without the namespace but may prompt when loading
embedded CDML in SVG files with missing or incorrect namespaces.

## Info block
```xml
<info>
  <author_program version="26.02">BKChem</author_program>
  <author>...</author>
  <note>...</note>
</info>
```

## Standard values
The `standard` element stores drawing defaults. It is read by
`classes.standard` and can be saved as a personal standard.

Attributes:
- `line_width` (string, units allowed, default `1px`)
- `font_size` (int)
- `font_family` (string, default `helvetica`)
- `line_color` (string color, default `#000`)
- `area_color` (string color, default empty)
- `paper_type` (string, default `A4`)
- `paper_orientation` (string, default `portrait`)
- `paper_crop_svg` (int, 0 or 1)
- `paper_crop_margin` (int, pixels)

Children:
```xml
<bond length="0.7cm" width="6px" wedge-width="5px"
      double-ratio="0.75" min_wedge_angle="0.3926990817"/>
<arrow length="1.6cm"/>
<atom show_hydrogens="0"/>
```

## Paper
The `paper` element stores page layout and export options.

Attributes:
- `type`: paper type such as `A4` or `custom`.
- `orientation`: `portrait` or `landscape`.
- `crop_svg`: `0` or `1` for SVG export cropping.
- `crop_margin`: integer margin in pixels.
- `use_real_minus`: `0` or `1`.
- `replace_minus`: `0` or `1`.
- `size_x`, `size_y`: required when `type="custom"`.

## Viewport
```xml
<viewport viewport="x1 y1 x2 y2"/>
```
Coordinates are floats in paper units.

## Drawing objects
Top-level drawing objects are loaded based on `data.loadable_types`:
- `molecule`, `arrow`, `plus`, `text`
- `rect`, `oval`, `polygon`, `circle`, `square`, `polyline`
- `reaction`

### Molecule
```xml
<molecule id="m1" name="...">
  <atom id="a1" name="C">
    <point x="0.0" y="0.0"/>
  </atom>
  <atom id="a2" name="O">
    <point x="40.0" y="0.0"/>
  </atom>
  <bond id="b1" start="a1" end="a2" type="n1" line_width="1.0"/>
</molecule>
```

Common atom attributes:
- `id` (required)
- `name` (element symbol)
- `charge`, `number`
- `hydrogens` (`on` or `off`)
- `pos` (`center-first` or `center-last`)
- `show` (`yes` or `no`)
- `show_number` (`yes` or `no`)

Common bond attributes:
- `id` (optional)
- `start`, `end` (atom id refs)
- `type` (string, for example `n1`, `n2`, `w1`, `h1`, `a1`, `b1`, `d1`, `o1`,
  `s1`, `q1`)
- `line_width`, `bond_width`, `double_ratio`, `wedge_width`
- `color` (optional hex RGB, for example `#239e2d`)
- `wavy_style` (optional, for `s*` bonds: `sine`, `half-circle`, `box`,
  `triangle`)

Legacy `l`/`r` hashed variants are normalized to `h` on read.

### Arrow
```xml
<arrow start="yes" end="yes" width="1.0" spline="no">
  <point x="0.0" y="0.0"/>
  <point x="50.0" y="0.0"/>
</arrow>
```

### Text
BKChem stores rich text using nested `ftext`, `sub`, `sup`, `b`, and `i`
elements plus a `font` element where present.

## Units
Numeric attributes may be stored as:
- pure numbers (interpreted as pixels or raw values), or
- values with units (such as `px` or `cm`).

BKChem normalizes values using `misc.split_number_and_unit`, so values like
`"1.0cm"` and `"10mm"` should be consistent after conversion.

## Embedded CDML in SVG
CD-SVG embeds a `<cdml>` node inside a standard SVG. BKChem reads the embedded
node when present, and will prompt if the namespace is missing or incorrect.

## Compatibility notes
- The legacy DTD does not reflect all modern fields.
- Some attributes are optional but used by the current UI.
- If you produce CDML externally, include `version="26.02"` and the CDML
  namespace, and prefer the current `standard` and `paper` attributes.
