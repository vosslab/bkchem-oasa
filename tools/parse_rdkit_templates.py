#!/usr/bin/env python3
"""Parse RDKit TemplateSmiles.h and generate ring_templates.py for OASA."""

import re

def main():
	with open("rdkit/Code/GraphMol/Depictor/TemplateSmiles.h") as f:
		content = f.read()

	# find all template strings: "SMILES |(coords)|"
	pattern = r'"(.+?)\s+\|(.*?)\|"'
	matches = re.findall(pattern, content)
	print(f"Found {len(matches)} templates")

	templates = {}
	for smiles, coords_str in matches:
		# coords are like (x1,y1,;x2,y2,;...)
		coords_str = coords_str.strip("()")
		pairs = coords_str.split(";")
		coords = []
		for pair in pairs:
			pair = pair.strip().strip(",")
			if not pair:
				continue
			parts = pair.split(",")
			if len(parts) == 2:
				coords.append((float(parts[0]), float(parts[1])))
		if coords:
			templates[smiles] = coords

	print(f"Parsed {len(templates)} templates with coords")

	# Print some key ones
	for smiles, coords in templates.items():
		n = len(coords)
		if n <= 10:
			print(f"  {n} atoms: {smiles[:60]}")

if __name__ == "__main__":
	main()
