#!/usr/bin/env bash

tools/archive_matrix_summary.py --regenerate-haworth-svgs
file=$(find output_smoke/archive_matrix_previews/generated/ -type f -name "*.svg" | sort -R | head -n 1)
echo ""
echo "$file"
tools/measure_glyph_bond_alignment.py -i "$file" --write-diagnostic-svg
diagnostic_file="output_smoke/glyph_bond_alignment_diagnostics/$(basename "${file%.svg}").diagnostic.svg"
sleep 0.1
echo "source_svg= $file"
echo "diagnostic_svg= $diagnostic_file"
#python tools/run_glyph_alignment_fixture_runner.py ;
#open "$file"
sleep 0.1
open "$diagnostic_file"
sleep 0.1
#open output_smoke/glyph_alignment_fixture_runner/unit_03_bonds_nearby_strokes/diagnostics/unit_03_bonds_nearby_strokes.diagnostic.svg

