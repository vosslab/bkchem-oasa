"""Tests for mode submode parity: template, draw, and biotemplate modes."""


#============================================
def test_template_mode_has_submodes(main_window: object) -> None:
	"""Switch to template mode and verify submodes is non-empty."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("template")
	mode = mode_manager.current_mode
	assert mode is not None, "template mode should be active"
	assert isinstance(mode.submodes, list), "submodes should be a list"
	assert len(mode.submodes) > 0, "template mode should have submodes"
	# the first group should contain template names
	assert len(mode.submodes[0]) > 0, (
		"template mode group 0 should have entries"
	)


#============================================
def test_template_submode_sets_template(main_window: object) -> None:
	"""Switch to template mode and verify on_submode_switch changes template."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("template")
	mode = mode_manager.current_mode
	assert mode is not None, "template mode should be active"
	# need at least two templates to test switching
	if len(mode.submodes[0]) < 2:
		return
	# record initial template
	initial_template = mode._current_template
	# switch to the second template
	second_name = mode.submodes[0][1]
	mode.on_submode_switch(0, second_name)
	assert mode._current_template == second_name, (
		f"expected _current_template={second_name!r}, "
		f"got {mode._current_template!r}"
	)
	assert mode._current_template != initial_template, (
		"template should have changed after on_submode_switch"
	)


#============================================
def test_draw_mode_has_submodes(main_window: object) -> None:
	"""Switch to draw mode and verify submodes are present from YAML."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("draw")
	mode = mode_manager.current_mode
	assert mode is not None, "draw mode should be active"
	assert isinstance(mode.submodes, list), "submodes should be a list"
	assert len(mode.submodes) > 0, (
		"draw mode should have submodes injected from YAML"
	)


#============================================
def test_biotemplate_mode_has_categories(main_window: object) -> None:
	"""Switch to biotemplate mode and verify category group is present."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("biotemplate")
	mode = mode_manager.current_mode
	assert mode is not None, "biotemplate mode should be active"
	assert isinstance(mode.submodes, list), "submodes should be a list"
	assert len(mode.submodes) > 0, (
		"biotemplate mode should have submodes"
	)
	# group 0 should be the category group
	assert len(mode.submodes[0]) > 0, (
		"biotemplate mode group 0 (categories) should have entries"
	)
	# verify group_labels includes Category
	assert "Category" in mode.group_labels, (
		f"group_labels should contain 'Category', got {mode.group_labels}"
	)


#============================================
def test_bracket_mode_exposes_both_classic_styles(main_window: object) -> None:
	"""The bracket ribbon declares rectangular and round backend styles."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("bracket")
	mode = mode_manager.current_mode
	if mode is None:
		raise AssertionError("bracket mode should be active")

	assert mode.submodes == [["rectangularbracket", "roundbracket"]]
	mode.set_submode("roundbracket")
	assert mode.status_hint.startswith("Round")


#============================================
def test_mode_toolbar_single_checked_action(main_window: object) -> None:
	"""Mode toolbar should keep exactly one checkable mode active."""
	mode_manager = main_window._mode_manager
	mode_sequence = ["edit", "draw", "template", "atom", "mark"]
	for mode_name in mode_sequence:
		mode_manager.set_mode(mode_name)
		checked = [
			name for name, action in main_window._mode_toolbar._actions.items()
			if action.isCheckable() and action.isChecked()
		]
		assert checked == [mode_name], (
			f"expected only '{mode_name}' checked, got {checked}"
		)


#============================================
def test_template_grid_adapts_columns_with_window_width(
	main_window: object, qapp: object,
) -> None:
	"""Template grid should use more columns when the window is widened."""
	main_window.show()
	main_window.resize(640, 800)
	qapp.processEvents()

	mode_manager = main_window._mode_manager
	mode_manager.set_mode("template")
	qapp.processEvents()

	mode = mode_manager.current_mode
	keys = mode.submodes[0] if mode.submodes else []
	if not keys:
		return

	grid_widget = main_window._submode_ribbon._group_widgets[0]
	narrow_columns = getattr(grid_widget, "_effective_columns", 0)
	base_columns = getattr(grid_widget, "_base_columns", 0)
	assert narrow_columns >= 1, "narrow grid should have at least one column"
	assert base_columns >= 1, "base grid columns should be tracked"

	main_window.resize(1800, 800)
	qapp.processEvents()

	wide_grid_widget = main_window._submode_ribbon._group_widgets[0]
	wide_columns = getattr(wide_grid_widget, "_effective_columns", 0)
	assert wide_columns >= narrow_columns, (
		f"wider window should not reduce columns: {wide_columns} < "
		f"{narrow_columns}"
	)
	if len(keys) > base_columns:
		assert wide_columns > base_columns, (
			f"wide layout should exceed base columns {base_columns}, got "
			f"{wide_columns}"
		)
