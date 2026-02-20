#!/usr/bin/env bash

tools/render_beta_sheets.py;
open /Users/vosslab/nsh/bkchem/output_smoke/oasa_generic_renders/parallel_beta_sheet.svg;
open /Users/vosslab/nsh/bkchem/output_smoke/oasa_generic_renders/antiparallel_beta_sheet.svg;

tools/measure_glyph_bond_alignment.py -i /Users/vosslab/nsh/bkchem/output_smoke/oasa_generic_renders/parallel_beta_sheet.svg;
open /Users/vosslab/nsh/bkchem/output_smoke/glyph_bond_alignment_diagnostics/parallel_beta_sheet.diagnostic.svg

tools/measure_glyph_bond_alignment.py -i /Users/vosslab/nsh/bkchem/output_smoke/oasa_generic_renders/antiparallel_beta_sheet.svg;
open /Users/vosslab/nsh/bkchem/output_smoke/glyph_bond_alignment_diagnostics/antiparallel_beta_sheet.diagnostic.svg
