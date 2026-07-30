"""Qt-facing labels and choice sets for canonical CDML bond styles."""


# These choices are editor presentation data.  OASA defines code semantics
# and authorable orders in oasa.bond_semantics without importing this module.
ORDINARY_BOND_TYPE_CHOICES = (
	("n", "Normal"),
	("w", "Wedge"),
	("h", "Hashed wedge"),
	("a", "Adder"),
	("b", "Bold"),
	("d", "Dashed"),
	("o", "Dotted"),
	("s", "Wavy"),
)
HAWORTH_BOND_TYPE_CHOICE = ("q", "Haworth front edge")

# The YAML submode names are a frontend implementation detail.  Their output
# remains the canonical backend-owned CDML type character.
DRAW_BOND_TYPE_BY_SUBMODE = {
	"normal": "n",
	"wedge": "w",
	"hashed": "h",
	"adder": "a",
	"bbold": "b",
	"dash": "d",
	"dotted": "o",
	"wavy": "s",
}


#============================================
def choices_for_display(current_type: str | None = None) -> tuple:
	"""Return generic choices plus Haworth when displaying an existing q bond.

	Args:
		current_type: Existing projected canonical CDML bond type.

	Returns:
		Ordered ``(code, label)`` pairs suitable for a Qt choice surface.
	"""
	if current_type == "q":
		return ORDINARY_BOND_TYPE_CHOICES + (HAWORTH_BOND_TYPE_CHOICE,)
	return ORDINARY_BOND_TYPE_CHOICES


#============================================
def label_for_bond_type(bond_type: str) -> str:
	"""Return the accurate presentation label for one known CDML style.

	Args:
		bond_type: Canonical CDML bond type character.

	Returns:
		Human-facing label, including a visible unknown value when unsupported.
	"""
	for code, label in choices_for_display("q"):
		if code == bond_type:
			return label
	return f"Unknown bond style ({bond_type})"
