"""Behavior tests for the responsive Qt mode chooser."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets


#============================================
def _resize_and_process(main_window: object, qapp: object, width: int) -> None:
	"""Resize a shown window and allow Qt to apply the toolbar layout."""
	main_window.resize(width, 800)
	main_window.show()
	qapp.processEvents()


#============================================
def _visible_inside(
		widget: PySide6.QtWidgets.QWidget,
		container: PySide6.QtWidgets.QWidget,
		) -> bool:
	"""Return whether a visible control occupies the visible toolbar area."""
	widget_rect = PySide6.QtCore.QRect(
		widget.mapToGlobal(PySide6.QtCore.QPoint()), widget.size()
	)
	container_rect = PySide6.QtCore.QRect(
		container.mapToGlobal(PySide6.QtCore.QPoint()), container.size()
	)
	return widget.isVisible() and container_rect.contains(widget_rect)


#============================================
def _toolbar_action(
		toolbar: PySide6.QtWidgets.QToolBar, name: str,
		) -> PySide6.QtGui.QAction:
	"""Return the action identified by its stable interaction name."""
	object_name = f"mode-action-{name}"
	for action in toolbar.actions():
		if action.objectName() == object_name:
			return action
	raise AssertionError(f"No toolbar action named {name!r}")


#============================================
def test_mode_toolbar_supports_compact_workspace_widths(
		main_window: object, qapp: object,
		) -> None:
	"""A compact chooser keeps every mode available at narrow widths."""
	toolbar = main_window._mode_toolbar
	registered_modes = set(main_window._mode_manager.mode_names())
	chooser = toolbar.findChild(
		PySide6.QtWidgets.QToolButton, "mode-chooser",
	)
	if chooser is None:
		raise AssertionError("The compact mode chooser is missing.")

	for width in (640, 1024):
		_resize_and_process(main_window, qapp, width)
		assert main_window.width() == width
		assert _visible_inside(chooser, toolbar)
		menu_modes = {
			action.data() for action in chooser.menu().actions()
			if action.isCheckable()
		}
		assert menu_modes == registered_modes
		for name in ("undo", "redo"):
			button = toolbar.widgetForAction(_toolbar_action(toolbar, name))
			if button is None:
				raise AssertionError(f"The {name} action has no toolbar button.")
			assert _visible_inside(button, toolbar)
		for action in chooser.menu().actions():
			if not action.isCheckable():
				continue
			action.trigger()
			qapp.processEvents()
			assert action.isChecked()


#============================================
def test_mode_toolbar_restores_full_row_and_active_feedback(
		main_window: object, qapp: object,
		) -> None:
	"""Wide workspaces show mode buttons while the compact label tracks state."""
	toolbar = main_window._mode_toolbar
	_resize_and_process(main_window, qapp, 1280)
	assert main_window.width() == 1280
	chooser = toolbar.findChild(
		PySide6.QtWidgets.QToolButton, "mode-chooser",
	)
	if chooser is None:
		raise AssertionError("The compact mode chooser is missing.")
	assert not chooser.isVisible()
	for mode_name in main_window._mode_manager.mode_names():
		button = toolbar.findChild(
			PySide6.QtWidgets.QToolButton, f"mode-button-{mode_name}",
		)
		if button is None:
			raise AssertionError(f"The {mode_name} action has no toolbar button.")
		assert _visible_inside(button, toolbar)

	main_window._mode_manager.set_mode("draw")
	_resize_and_process(main_window, qapp, 640)
	assert _visible_inside(chooser, toolbar)
	draw_action = next(
		action for action in chooser.menu().actions()
		if action.data() == "draw"
	)
	assert draw_action.isChecked()
