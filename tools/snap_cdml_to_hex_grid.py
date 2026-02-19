#!/usr/bin/env python3

#--------------------------------------------------------------------------
#     This file is part of BKChem - a free chemical drawing program
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#     Copyright (C) 2025-2026 Neil Voss

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program
#--------------------------------------------------------------------------

"""Snap CDML atom coordinates to a hexagonal grid."""

# Standard Library
import math
import argparse

# local repo modules
import oasa.hex_grid
import oasa.safe_xml
import oasa.dom_extensions

# conversion factor: 72 PostScript points per inch, 2.54 cm per inch
POINTS_PER_CM = 72.0 / 2.54


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments.

	Returns:
		Parsed argument namespace.
	"""
	parser = argparse.ArgumentParser(
		description="Snap CDML atom coordinates to a hexagonal grid."
	)
	parser.add_argument(
		'-i', '--input', dest='input_file', required=True,
		help="Input CDML file path",
	)
	parser.add_argument(
		'-o', '--output', dest='output_file', required=True,
		help="Output CDML file path",
	)
	parser.add_argument(
		'-s', '--spacing', dest='spacing', type=float, default=0.7,
		help="Hex grid spacing in cm (default: 0.7)",
	)
	# dry-run / write toggle
	parser.add_argument(
		'-w', '--write', dest='dry_run',
		help="Write the snapped output file",
		action='store_false',
	)
	parser.add_argument(
		'-n', '--dry-run', dest='dry_run',
		help="Only print a displacement report, do not write output",
		action='store_true',
	)
	parser.set_defaults(dry_run=True)
	args = parser.parse_args()
	return args


#============================================
def parse_cm_value(value_str: str) -> float:
	"""Parse a CDML coordinate string, stripping optional 'cm' suffix.

	Converts the value to points (internal units).

	Args:
		value_str: Coordinate string, e.g. "3.500cm" or "99.21".

	Returns:
		Coordinate value in points.
	"""
	if value_str.endswith("cm"):
		# strip "cm" suffix and convert cm to points
		cm_value = float(value_str[:-2])
		pts_value = cm_value * POINTS_PER_CM
	else:
		pts_value = float(value_str)
	return pts_value


#============================================
def points_to_cm_string(pts_value: float) -> str:
	"""Convert a points value back to a CDML coordinate string.

	Args:
		pts_value: Coordinate value in points.

	Returns:
		String formatted as 'X.XXXcm'.
	"""
	cm_value = pts_value / POINTS_PER_CM
	cm_str = f"{cm_value:.3f}cm"
	return cm_str


#============================================
def process_molecule(mol_element: object, spacing_pts: float,
		dry_run: bool) -> list:
	"""Snap all atoms in one molecule element to the hex grid.

	Args:
		mol_element: DOM element for a <molecule>.
		spacing_pts: Grid spacing in points.
		dry_run: If True, do not modify the DOM; collect report lines.

	Returns:
		List of report strings describing each atom displacement.
	"""
	report_lines = []
	# find atom elements within this molecule
	atom_elements = oasa.dom_extensions.simpleXPathSearch(
		mol_element, "atom"
	)
	# gather coordinates and point elements for each atom
	atom_data = []
	for atom_el in atom_elements:
		# each atom has a child <point x="..." y="..." />
		point_elements = atom_el.getElementsByTagName("point")
		if not point_elements:
			continue
		point_el = point_elements[0]
		x_str = point_el.getAttribute("x")
		y_str = point_el.getAttribute("y")
		if not x_str or not y_str:
			continue
		x_pts = parse_cm_value(x_str)
		y_pts = parse_cm_value(y_str)
		# get atom id and name for reporting
		atom_id = atom_el.getAttribute("id")
		atom_name = atom_el.getAttribute("name")
		atom_data.append((x_pts, y_pts, point_el, atom_id, atom_name))

	if not atom_data:
		return report_lines

	# extract coordinate tuples for hex_grid functions
	atom_coords = [(x, y) for x, y, _, _, _ in atom_data]

	# find the best grid origin to minimize total displacement
	ox, oy = oasa.hex_grid.find_best_grid_origin(atom_coords, spacing_pts)

	# snap all atoms to the hex grid
	snapped_coords = oasa.hex_grid.snap_molecule_to_hex_grid(
		atom_coords, spacing_pts, origin_x=ox, origin_y=oy
	)

	# update DOM or build report
	total_dist = 0.0
	for i, entry in enumerate(atom_data):
		old_x, old_y, point_el, atom_id, atom_name = entry
		new_x, new_y = snapped_coords[i]
		# compute displacement
		dx = new_x - old_x
		dy = new_y - old_y
		displacement = math.sqrt(dx * dx + dy * dy)
		total_dist += displacement
		# convert to cm for display
		old_x_cm = old_x / POINTS_PER_CM
		old_y_cm = old_y / POINTS_PER_CM
		new_x_cm = new_x / POINTS_PER_CM
		new_y_cm = new_y / POINTS_PER_CM
		disp_cm = displacement / POINTS_PER_CM
		line = (
			f"  {atom_id} ({atom_name}): "
			f"({old_x_cm:7.3f}, {old_y_cm:7.3f}) -> "
			f"({new_x_cm:7.3f}, {new_y_cm:7.3f})  "
			f"moved {disp_cm:.4f} cm"
		)
		report_lines.append(line)
		if not dry_run:
			# update the point element with snapped coordinates
			point_el.setAttribute("x", points_to_cm_string(new_x))
			point_el.setAttribute("y", points_to_cm_string(new_y))

	# append summary line for the molecule
	avg_cm = total_dist / POINTS_PER_CM / max(len(atom_data), 1)
	report_lines.append(f"  average displacement: {avg_cm:.4f} cm")
	return report_lines


#============================================
def main() -> None:
	"""Main entry point: parse CDML, snap atoms, write or report."""
	args = parse_args()

	# convert spacing from cm to points
	spacing_pts = args.spacing * POINTS_PER_CM

	# parse the CDML file
	doc = oasa.safe_xml.parse_dom_from_file(args.input_file)

	# find all molecule elements in the document
	mol_elements = doc.getElementsByTagName("molecule")

	print(f"Spacing: {args.spacing} cm ({spacing_pts:.2f} pts)")
	print(f"Molecules found: {len(mol_elements)}")

	# process each molecule independently
	all_report_lines = []
	for mol_idx, mol_el in enumerate(mol_elements):
		report_lines = process_molecule(mol_el, spacing_pts, args.dry_run)
		if report_lines:
			all_report_lines.append(f"molecule {mol_idx + 1}:")
			all_report_lines.extend(report_lines)

	# print displacement report
	for line in all_report_lines:
		print(line)

	if args.dry_run:
		print()
		print("Dry run: no file written. Use -w to write output.")
	else:
		# write the updated CDML file
		xml_text = doc.toxml(encoding="utf-8")
		with open(args.output_file, "wb") as outfile:
			outfile.write(xml_text)
		print()
		print(f"Written: {args.output_file}")


#============================================
if __name__ == '__main__':
	main()
