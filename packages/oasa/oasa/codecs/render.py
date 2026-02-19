#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Registry adapters for OASA render outputs."""

# local repo modules
from oasa import render_out


#============================================
def svg_mol_to_file(mol, file_obj, **kwargs):
	"""Render one molecule to SVG."""
	render_out.render_to_svg(mol, file_obj, **kwargs)


#============================================
def pdf_mol_to_file(mol, file_obj, **kwargs):
	"""Render one molecule to PDF."""
	render_out.render_to_pdf(mol, file_obj, **kwargs)


#============================================
def png_mol_to_file(mol, file_obj, **kwargs):
	"""Render one molecule to PNG."""
	render_out.render_to_png(mol, file_obj, **kwargs)


#============================================
def ps_mol_to_file(mol, file_obj, **kwargs):
	"""Render one molecule to PostScript."""
	render_out.render_to_ps(mol, file_obj, **kwargs)
