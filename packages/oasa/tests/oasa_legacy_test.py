import os
import tempfile

import oasa
import oasa.cairo_out
import oasa.smiles_lib

def cairo_out_test2():
    mol = oasa.smiles_lib.text_to_mol( "c1ccccc1Cl.c1ccccc1OC.CCCl")
    mol.normalize_bond_length( 30)
    mol.remove_unimportant_hydrogens()
    c = oasa.cairo_out.cairo_out( color_bonds=True, color_atoms=True)
    c.show_hydrogens_on_hetero = True
    c.font_size = 20
    mols = list( mol.get_disconnected_subgraphs())
    with tempfile.TemporaryDirectory( prefix="oasa_legacy_test_") as output_dir:
        pdf_path = os.path.join( output_dir, "oasa_legacy_test.pdf")
        png_path = os.path.join( output_dir, "oasa_legacy_test.png")
        svg_path = os.path.join( output_dir, "oasa_legacy_test.svg")
        c.mols_to_cairo( mols, pdf_path, format="pdf")
        c.mols_to_cairo( mols, png_path)
        c.mols_to_cairo( mols, svg_path, format="svg")

def inchi_test():
    mol = oasa.smiles_lib.text_to_mol( r"c1ccccc1\C=C/CC")
    print(oasa.inchi.mol_to_text(mol, program="stdinchi-1.exe", fixed_hs=False))

cairo_out_test2()
#inchi_test()
