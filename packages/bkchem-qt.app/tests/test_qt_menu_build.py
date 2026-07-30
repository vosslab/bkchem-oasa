"""Test that YAML-driven menu builder creates all 10 menus."""


#============================================
def test_menu_bar_has_ten_menus(main_window: object) -> None:
	"""Verify 10 top-level menus are created from menus.yaml."""
	menubar = main_window.menuBar()
	menus = []
	for action in menubar.actions():
		if action.menu() is not None:
			menus.append(action.text().replace("&", ""))
	# expect at least 10 menus from YAML
	assert len(menus) >= 10, f"Expected 10+ menus, got {len(menus)}: {menus}"
	# verify YAML order for the first 10
	expected = [
		"File", "Edit", "Insert", "Align", "Object",
		"View", "Chemistry", "Repair", "Options", "Help",
	]
	for i, name in enumerate(expected):
		assert menus[i] == name, f"Menu {i}: expected {name!r}, got {menus[i]!r}"
