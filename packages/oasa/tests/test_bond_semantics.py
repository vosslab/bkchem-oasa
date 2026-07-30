"""CDML 26.07 bond-style and legacy-normalization behavior."""

# local repo modules
from oasa import bond_semantics


#============================================
def test_canonical_bond_styles_expose_their_authored_order_matrix() -> None:
	"""Every canonical style retains its documented authorable orders."""
	observed = {
		bond_type: bond_semantics.authored_bond_orders(bond_type)
		for bond_type in bond_semantics.BOND_TYPES
	}

	assert observed == {
		"n": (1, 2, 3), "w": (1, 2, 3), "h": (1, 2, 3), "a": (1, 2, 3),
		"b": (1, 2, 3), "d": (1, 2, 3), "o": (1, 2, 3), "s": (1, 2, 3),
		"q": (1,),
	}


#============================================
def test_legacy_hashed_forms_normalize_without_expanding_authored_styles() -> None:
	"""Historical l/r inputs remain readable but serialize through hashed semantics."""
	left = bond_semantics.parse_cdml_bond_type("l1")
	right = bond_semantics.parse_cdml_bond_type("r2")

	assert left == ("h", 1, "l")
	assert right == ("h", 2, "r")
