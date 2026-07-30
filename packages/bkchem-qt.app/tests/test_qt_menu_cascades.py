"""Test that YAML-driven menu builder creates cascade submenus."""


#============================================
def test_file_menu_has_three_cascades(main_window: object) -> None:
	"""Verify Recent files, Export, and Import cascades exist under File."""
	builder_cascades = main_window._menu_builder._cascade_names
	assert "Recent files" in builder_cascades, f"Missing Recent files: {builder_cascades}"
	assert "Export" in builder_cascades, f"Missing Export: {builder_cascades}"
	assert "Import" in builder_cascades, f"Missing Import: {builder_cascades}"
