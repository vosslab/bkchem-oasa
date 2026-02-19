"""Convert a peptide amino acid sequence into an IsoSMILES string.

Provides the core conversion logic for turning single-letter amino acid
sequences (e.g. 'ANKLE') into polypeptide IsoSMILES strings. Used by the
BKChem GUI 'Read Peptide Sequence' menu item.
"""

# Maps single-letter amino acid codes to their side chain SMILES fragments.
# Each fragment is a branch off the backbone alpha-carbon.
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
def sequence_to_smiles(sequence: str) -> str:
	"""Convert a peptide sequence to a polypeptide IsoSMILES string.

	Builds the SMILES string directly with side chains inline,
	no placeholder substitution needed.

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
	# build SMILES directly: N-terminus, then each residue with side chain inline
	length = len(sequence)
	smiles = '[NH3+][C@@H]'
	for i, aa in enumerate(sequence):
		# attach side chain branch to alpha-carbon
		smiles += AMINO_ACID_SMILES[aa]
		# add peptide bond to next residue (except after last)
		if i + 1 < length:
			smiles += '(C(=O)N[C@@H]'
	# C-terminal carboxylate on the last residue
	smiles += '(C(=O)[O-])'
	# close the nested peptide bond parentheses
	for i in range(length - 1):
		smiles += ')'
	return smiles
