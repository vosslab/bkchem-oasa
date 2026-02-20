# Code architecture

## Overview
- OASA (Open Architecture for Sketching Atoms and Molecules) is a Python
  library for chemical structure representation, parsing, and export.
- The core model is a graph of atoms and bonds with chemistry-aware attributes.
- Parsers and writers translate between external formats and the internal graph model.
- Geometry and coordinate modules add 2D/3D layout and transform support.
- Optional integrations enable extra formats or database-backed features.

## Project references
- [BKChem GitHub repository](https://github.com/vosslab/bkchem) for the primary
  project homepage and documentation.

## Core data model
- `oasa/graph/` contains the generic graph, vertex, and edge primitives.
- `oasa/chem_vertex.py` extends graph vertices with chemical attributes.
- `oasa/atom.py` and `oasa/bond.py` specialize vertices and edges for chemistry.
- `oasa/molecule.py` is the primary container for atoms, bonds, and properties.
- `oasa/oasa_exceptions.py` defines domain-specific exceptions.

## Format I O
- `oasa/smiles.py` parses and writes SMILES.
- `oasa/molfile.py` parses and writes molfile (V2000 style).
- `oasa/inchi.py` reads InChI; writing relies on external InChI tools.
- `oasa/cdml.py` handles CDML import and export.
- `oasa/linear_formula.py` and `oasa/periodic_table.py` support formula utilities.

## Geometry, stereochemistry, and layout
- `oasa/geometry.py` provides geometric primitives and algorithms.
- `oasa/transform.py` and `oasa/transform3d.py` handle coordinate transforms.
- `oasa/coords_generator.py` creates 2D coordinates for drawing.
- `oasa/coords_optimizer.py` improves or relaxes coordinates.
- `oasa/stereochemistry.py` handles limited stereochemical rules.

## Search and chemistry utilities
- `oasa/query_atom.py` handles query atom helpers.
- `oasa/known_groups.py` stores common functional group definitions.

## Output backends
- `oasa/svg_out.py` renders molecules to SVG.
- `oasa/cairo_out.py` renders via pycairo when available.

## Optional integrations
- `oasa/pybel_bridge.py` integrates with OpenBabel if installed.

## Public API surface
- `oasa/__init__.py` imports and re-exports major modules and classes.
- Availability flags (for example `CAIRO_AVAILABLE`) describe optional features.

## Data flow
1. Input format parser reads a file or string and builds a `molecule`.
2. The `molecule` graph is inspected or modified by geometry, search, or
   stereochemistry modules.
3. Coordinate generation and optimization produce 2D layout if needed.
4. Output writers or renderers export the result to files or strings.
