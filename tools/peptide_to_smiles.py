#!/usr/bin/env python3

"""Convert a peptide amino acid sequence into an IsoSMILES string.

Standalone script with no repo dependencies. Builds a polypeptide backbone
template with R-group placeholders and replaces each with the amino acid
side chain SMILES fragment.

Usage:
	python3 peptide_to_smiles.py -s ANKLE
"""

# Standard Library
import argparse

# Maps single-letter amino acid codes to their side chain SMILES fragments.
# Each fragment replaces an R-group placeholder on the peptide backbone.
# Proline (P) is excluded because its cyclic side chain modifies the
# backbone nitrogen and does not fit the generic template.
AMINO_ACID_SMILES = {
	'A': '(C)',               # Alanine
	'C': '(CS)',              # Cysteine
	'D': '(CC(=O)[O-])',      # Aspartate
	'E': '(CCC(=O)[O-])',     # Glutamate
	'F': '(Cc1ccccc1)',       # Phenylalanine
	'G': '([H])',             # Glycine
	'H': '(CC1=C[NH]C=N1)',   # Histidine (delta tautomer, pH 7)
	'I': '([C@H](CC)C)',      # Isoleucine
	'K': '(CCCC[NH3+])',      # Lysine
	'L': '(CC(C)C)',          # Leucine
	'M': '(CCSC)',            # Methionine
	'N': '(CC(=O)N)',         # Asparagine
	'Q': '(CCC(=O)N)',        # Glutamine
	'R': '(CCCNC(=[NH2+])N)', # Arginine
	'S': '(CO)',              # Serine
	'T': '([C@H](O)C)',       # Threonine
	'V': '(C(C)C)',           # Valine
	'W': '(CC1=CC=C2C(=C1)C(=CN2))', # Tryptophan
	'Y': '(Cc1ccc(O)cc1)',    # Tyrosine
}

#============================================
def make_generic_polypeptide(length: int) -> str:
	"""Build a generic polypeptide backbone SMILES with R-group placeholders.

	Args:
		length: number of amino acid residues in the chain.

	Returns:
		SMILES string with R1, R2, ... placeholders for side chains.
	"""
	# terminal groups for the peptide chain
	amino_terminal_end = '[NH3+][C@@H]'
	carboxyl_terminal_end = '(C(=O)[O-])'
	peptide_bond = '(C(=O)N[C@@H]'
	# build the backbone from N-terminus to C-terminus
	peptide_chain = ''
	peptide_chain += amino_terminal_end
	for i in range(length):
		peptide_chain += f'R{i+1}'
		if i + 1 < length:
			peptide_chain += peptide_bond
	peptide_chain += carboxyl_terminal_end
	# close the nested parentheses from peptide bonds
	for i in range(length - 1):
		peptide_chain += ')'
	return peptide_chain

#============================================
def sequence_to_smiles(sequence: str) -> str:
	"""Convert a peptide sequence to a polypeptide IsoSMILES string.

	Args:
		sequence: string of single-letter amino acid codes (e.g. 'ANKLE').

	Returns:
		IsoSMILES string for the full polypeptide.
	"""
	sequence = sequence.upper()
	# validate that all residues are supported
	for aa in sequence:
		if aa == 'P':
			raise ValueError(
				"Proline (P) is not supported: its cyclic side chain "
				"modifies the backbone nitrogen and does not fit the "
				"generic polypeptide template"
			)
		if aa not in AMINO_ACID_SMILES:
			raise ValueError(
				f"Unknown amino acid code '{aa}'. "
				f"Supported codes: {sorted(AMINO_ACID_SMILES.keys())}"
			)
	# build backbone with placeholders, then swap in side chains
	polypeptide_smiles = make_generic_polypeptide(len(sequence))
	for i, aa in enumerate(sequence):
		side_chain = AMINO_ACID_SMILES[aa]
		polypeptide_smiles = polypeptide_smiles.replace(f'R{i+1}', side_chain)
	return polypeptide_smiles

#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Convert a peptide amino acid sequence to an IsoSMILES string"
	)
	parser.add_argument(
		'-s', '--sequence', dest='sequence', required=True,
		help="Peptide sequence using single-letter amino acid codes (e.g. ANKLE)"
	)
	args = parser.parse_args()
	return args

#============================================
def main():
	args = parse_args()
	smiles = sequence_to_smiles(args.sequence)
	print(smiles)

#============================================
if __name__ == '__main__':
	main()
