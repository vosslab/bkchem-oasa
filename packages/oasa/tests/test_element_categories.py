"""Test OASA periodic_table element category data and accessors.

Usage:
	source source_me.sh && python -m pytest packages/oasa/tests/test_element_categories.py -v
"""

# local repo modules
import oasa.periodic_table


# elements that are placeholders / query types (not real elements)
_SKIP_SYMBOLS = {"X", "Q", "R", "Xx", "Tv", "Ts", "Og", "Mc", "Nh", "Fl", "Lv"}


#============================================
def test_real_elements_have_cat_key() -> None:
	"""Every non-query element in periodic_table should have a 'cat' key."""
	missing = []
	for symbol, data in oasa.periodic_table.periodic_table.items():
		if symbol in _SKIP_SYMBOLS:
			continue
		# skip entries without standard element data
		if not isinstance(data, dict):
			continue
		if "name" not in data:
			continue
		if "cat" not in data:
			missing.append(symbol)
	assert not missing, f"Elements missing 'cat' key: {missing}"


#============================================
def test_get_element_category_returns_string() -> None:
	"""get_element_category should return a non-empty string for C, O, Fe."""
	for symbol in ("C", "O", "Fe", "He", "F"):
		cat = oasa.periodic_table.get_element_category(symbol)
		assert isinstance(cat, str), f"Expected str for {symbol}, got {type(cat)}"
		assert len(cat) > 0, f"Empty category for {symbol}"


#============================================
def test_get_element_category_color_returns_hex() -> None:
	"""get_element_category_color should return a valid hex color string."""
	for symbol in ("C", "O", "Fe", "He", "F", "Si"):
		color = oasa.periodic_table.get_element_category_color(symbol)
		assert isinstance(color, str), f"Expected str for {symbol}, got {type(color)}"
		assert color.startswith("#"), f"Expected hex color for {symbol}, got {color}"
		assert len(color) == 7, f"Expected 7-char hex for {symbol}, got {color}"


#============================================
def test_element_category_colors_dict_complete() -> None:
	"""ELEMENT_CATEGORY_COLORS should have an entry for every category used."""
	categories_used = set()
	for symbol, data in oasa.periodic_table.periodic_table.items():
		if not isinstance(data, dict):
			continue
		if "cat" in data:
			categories_used.add(data["cat"])
	for cat in categories_used:
		assert cat in oasa.periodic_table.ELEMENT_CATEGORY_COLORS, (
			f"Category '{cat}' missing from ELEMENT_CATEGORY_COLORS"
		)


#============================================
def test_known_element_categories() -> None:
	"""Verify specific elements have the expected categories."""
	expected = {
		"C": "nonmetal",
		"O": "nonmetal",
		"F": "halogen",
		"Cl": "halogen",
		"He": "noble_gas",
		"Ne": "noble_gas",
		"Fe": "transition_metal",
		"Cu": "transition_metal",
		"Si": "metalloid",
		"Na": "metal",
		"Ca": "metal",
		"La": "lanthanide",
		"U": "actinide",
	}
	for symbol, expected_cat in expected.items():
		actual = oasa.periodic_table.get_element_category(symbol)
		assert actual == expected_cat, (
			f"Expected {symbol} category '{expected_cat}', got '{actual}'"
		)


#============================================
def test_unknown_element_category_fallback() -> None:
	"""get_element_category should return 'metal' for unknown symbols."""
	cat = oasa.periodic_table.get_element_category("Zz")
	assert cat == "metal", f"Expected 'metal' fallback, got '{cat}'"


#============================================
def test_unknown_element_color_fallback() -> None:
	"""get_element_category_color should return a valid hex for unknown."""
	color = oasa.periodic_table.get_element_category_color("Zz")
	assert isinstance(color, str)
	assert color.startswith("#")
