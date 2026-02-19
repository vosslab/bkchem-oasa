"""Smoke tests for biomolecule templates."""


#============================================
def test_biomolecule_template_files_have_anchors():

	from bkchem import safe_xml
	from bkchem import template_catalog

	entries = template_catalog.scan_template_dirs(
		template_catalog.discover_biomolecule_template_dirs()
	)
	assert entries

	for entry in entries:
		doc = safe_xml.parse_dom_from_file(entry.path)
		molecules = doc.getElementsByTagName('molecule')
		assert molecules
		for mol in molecules:
			atoms = {atom.getAttribute('id') for atom in mol.getElementsByTagName('atom')}
			assert atoms
			bonds = mol.getElementsByTagName('bond')
			assert bonds
			templates = mol.getElementsByTagName('template')
			assert templates
			template = templates[0]
			t_atom = template.getAttribute('atom')
			bond_first = template.getAttribute('bond_first')
			bond_second = template.getAttribute('bond_second')
			assert t_atom in atoms
			assert bond_first in atoms
			assert bond_second in atoms
