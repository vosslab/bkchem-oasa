# Code architecture

## Overview
- BKChem is a Tkinter desktop application for drawing chemical structures.
- OASA (Open Architecture for Sketching Atoms and Molecules) provides the
  chemistry graph model, format conversions, and render backends.
- CDML is the native document format, with SVG and other formats supported via
  exporters and plugins.

## Major components
- Application entry points
  - [packages/bkchem-app/bkchem/bkchem.py](packages/bkchem-app/bkchem/bkchem.py) boots
    the app, loads preferences, and parses CLI flags.
  - [packages/bkchem-app/bkchem/cli.py](packages/bkchem-app/bkchem/cli.py) exposes the
    console entry point for BKChem.
  - [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) defines the
    `BKChem` Tk application class, menus, and mode wiring.
- UI and interaction layer
  - [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) implements
    `chem_paper`, the main Tk Canvas for drawing, selection, and events.
  - [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py),
    [packages/bkchem-app/bkchem/interactors.py](packages/bkchem-app/bkchem/interactors.py),
    and [packages/bkchem-app/bkchem/context_menu.py](packages/bkchem-app/bkchem/context_menu.py)
    define editing modes and input handlers.
  - [packages/bkchem-app/bkchem/undo.py](packages/bkchem-app/bkchem/undo.py) and
    [packages/bkchem-app/bkchem/edit_pool.py](packages/bkchem-app/bkchem/edit_pool.py)
    manage undo stacks and edit history.
- Chemistry model and drawing objects
  - [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py)
    wraps [packages/oasa/oasa/molecule.py](packages/oasa/oasa/molecule.py).
  - [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py) and
    [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py) extend OASA
    atoms and bonds with drawing metadata.
  - [packages/bkchem-app/bkchem/group.py](packages/bkchem-app/bkchem/group.py),
    [packages/bkchem-app/bkchem/fragment.py](packages/bkchem-app/bkchem/fragment.py),
    [packages/bkchem-app/bkchem/reaction.py](packages/bkchem-app/bkchem/reaction.py),
    [packages/bkchem-app/bkchem/arrow.py](packages/bkchem-app/bkchem/arrow.py), and
    [packages/bkchem-app/bkchem/textatom.py](packages/bkchem-app/bkchem/textatom.py)
    implement higher-level drawing objects.
- OASA core library
  - [packages/oasa/oasa/](packages/oasa/oasa/) contains the chemistry graph
    model, parsers, and conversions.
  - [packages/oasa/oasa/render_ops.py](packages/oasa/oasa/render_ops.py) defines
    shared render ops for SVG and Cairo.
  - [packages/oasa/oasa/svg_out.py](packages/oasa/oasa/svg_out.py) and
    [packages/oasa/oasa/cairo_out.py](packages/oasa/oasa/cairo_out.py) render
    shared ops to SVG and Cairo surfaces.
  - [packages/oasa/oasa/haworth.py](packages/oasa/oasa/haworth.py) provides
    Haworth layout helpers for carbohydrate projections.
- File formats and I/O
  - CDML serialization is handled by
    [packages/oasa/oasa/cdml_writer.py](packages/oasa/oasa/cdml_writer.py),
    [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py),
    and [packages/bkchem-app/bkchem/CDML_versions.py](packages/bkchem-app/bkchem/CDML_versions.py).
  - Export routing lives in
    [packages/bkchem-app/bkchem/format_loader.py](packages/bkchem-app/bkchem/format_loader.py),
    [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py), and
    [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py).
  - Built-in exporters live under
    [packages/bkchem-app/bkchem/plugins/](packages/bkchem-app/bkchem/plugins/).
- Templates and reusable structures
  - Template loading is handled by
    [packages/bkchem-app/bkchem/temp_manager.py](packages/bkchem-app/bkchem/temp_manager.py)
    and catalog discovery in
    [packages/bkchem-app/bkchem/template_catalog.py](packages/bkchem-app/bkchem/template_catalog.py).
  - Built-in templates live under
    [packages/bkchem-app/bkchem_data/templates/](packages/bkchem-app/bkchem_data/templates/),
    including biomolecule templates in
    [packages/bkchem-app/bkchem_data/templates/biomolecules/](packages/bkchem-app/bkchem_data/templates/biomolecules/).
- Plugin system
  - [packages/bkchem-app/bkchem/plugin_support.py](packages/bkchem-app/bkchem/plugin_support.py)
    loads addon XML descriptors and scripts from
    [packages/bkchem-app/addons/](packages/bkchem-app/addons/).

## Data flow
1. [packages/bkchem-app/bkchem/bkchem.py](packages/bkchem-app/bkchem/bkchem.py) loads
   preferences, initializes locale, and creates a `BKChem` instance.
2. [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) builds the UI
   and constructs a [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py)
   canvas.
3. User input routes through modes and interactors into canvas operations.
4. `chem_paper` maintains a stack of top-level objects (molecules, arrows, text).
5. Model edits update atoms and bonds, which redraw onto the canvas.
6. Save and export paths serialize CDML or render SVG/bitmap output through OASA.
7. Imports use OASA parsers and
   [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
   to create BKChem molecules.

## Testing and verification
- Tests live under [tests/](tests/) with smoke and lint runners such as
  [tests/run_smoke.sh](tests/run_smoke.sh) and
  [tests/test_pyflakes_code_lint.py](tests/test_pyflakes_code_lint.py).
- Haworth and render ops coverage includes
  [tests/test_haworth_layout.py](tests/test_haworth_layout.py),
  [tests/test_oasa_bond_styles.py](tests/test_oasa_bond_styles.py), and
  [tests/test_render_ops_snapshot.py](tests/test_render_ops_snapshot.py).
- Reference image checks live in
  [tests/test_reference_outputs.py](tests/test_reference_outputs.py).

## Extension points
- Add new BKChem addons under [packages/bkchem-app/addons/](packages/bkchem-app/addons/)
  with XML descriptors for discovery.
- Add export plugins under
  [packages/bkchem-app/bkchem/plugins/](packages/bkchem-app/bkchem/plugins/).
- Add templates under
  [packages/bkchem-app/bkchem_data/templates/](packages/bkchem-app/bkchem_data/templates/)
  or subfolders scanned by
  [packages/bkchem-app/bkchem/template_catalog.py](packages/bkchem-app/bkchem/template_catalog.py).

## Known gaps
- Verify how installer packaging bundles `bkchem_data` assets in macOS and
  Windows distributions.
