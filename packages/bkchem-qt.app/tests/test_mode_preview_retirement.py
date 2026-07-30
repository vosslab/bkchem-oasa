"""Terminal-retirement coverage for transient Qt mode previews."""

# PIP3 modules
import PySide6.QtCore
import shiboken6

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.modes.arrow_mode
import bkchem_qt.modes.bracket_mode
import bkchem_qt.modes.edit_mode
import bkchem_qt.modes.misc_mode
import bkchem_qt.modes.vector_mode


#============================================
class _NoModifiersEvent:
	"""Provide the fixed modifier state needed for a blank-canvas drag."""

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return no keyboard modifiers for the edit-mode press."""
		return PySide6.QtCore.Qt.KeyboardModifier.NoModifier


#============================================
def test_session_modes_share_the_session_terminal_preview_owner(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Every transient-preview mode receives its tab's explicit reaper."""
	session = main_window._active_session
	modes = session.mode_manager._modes
	assert all(
		modes[name]._graphics_retirement_reaper
		is session._projection_retirement_reaper
		for name in ("draw", "arrow", "vector", "bracket", "misc", "edit")
	)


#============================================
def test_arrow_preview_deactivation_terminally_retires_native_wrapper(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An interrupted Arrow gesture explicitly destroys its transient line."""
	mode = bkchem_qt.modes.arrow_mode.ArrowMode(main_window.view)
	mode.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), object())
	mode.mouse_move(PySide6.QtCore.QPointF(40.0, 10.0), object())
	preview = mode._preview_line
	mode.deactivate()

	assert preview is not None and mode._preview_line is None and not shiboken6.isValid(preview)


#============================================
def test_vector_preview_deactivation_terminally_retires_native_wrapper(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An interrupted Vector gesture explicitly destroys its transient shape."""
	mode = bkchem_qt.modes.vector_mode.VectorMode(main_window.view)
	mode.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), object())
	mode.mouse_move(PySide6.QtCore.QPointF(40.0, 25.0), object())
	preview = mode._preview_item
	mode.deactivate()

	assert preview is not None and mode._preview_item is None and not shiboken6.isValid(preview)


#============================================
def test_bracket_preview_deactivation_terminally_retires_native_wrapper(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An interrupted Bracket gesture explicitly destroys its transient rectangle."""
	mode = bkchem_qt.modes.bracket_mode.BracketMode(main_window.view)
	mode.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), object())
	mode.mouse_move(PySide6.QtCore.QPointF(40.0, 25.0), object())
	preview = mode._preview_rect
	mode.deactivate()

	assert preview is not None and mode._preview_rect is None and not shiboken6.isValid(preview)


#============================================
def test_wavy_preview_deactivation_terminally_retires_native_wrapper(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An interrupted Wavy gesture destroys its transient path without scene probing."""
	mode = bkchem_qt.modes.misc_mode.MiscMode(main_window.view)
	mode.on_submode_switch(0, "wavy")
	mode.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), object())
	mode.mouse_move(PySide6.QtCore.QPointF(80.0, 10.0), object())
	preview = mode._wavy_preview
	mode.deactivate()

	assert preview is not None and mode._wavy_preview is None and not shiboken6.isValid(preview)


#============================================
def test_edit_rubber_band_deactivation_terminally_retires_native_wrapper(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An interrupted selection drag explicitly destroys its transient rubber band."""
	mode = bkchem_qt.modes.edit_mode.EditMode(main_window.view)
	event = _NoModifiersEvent()
	mode.mouse_press(PySide6.QtCore.QPointF(180.0, 180.0), event)
	mode.mouse_move(PySide6.QtCore.QPointF(220.0, 210.0), event)
	preview = mode._rubber_band
	mode.deactivate()

	assert preview is not None and mode._rubber_band is None and not shiboken6.isValid(preview)
