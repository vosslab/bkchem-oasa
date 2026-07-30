"""Focused ownership coverage for ChemScene terminal disposal."""

# PIP3 modules
import PySide6.QtWidgets
import pytest
import shiboken6

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.scene
import bkchem_qt.main_window


#============================================
def test_dispose_contents_retires_decorations_and_anonymous_items(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""One terminal disposal invalidates named and anonymous scene-owned items."""
	scene = bkchem_qt.canvas.scene.ChemScene()
	paper = scene._paper_item
	grid = scene._grid_overlay
	anonymous = scene.addRect(10.0, 20.0, 30.0, 40.0)
	scene.dispose_contents()
	scene.dispose_contents()

	assert (
		not shiboken6.isValid(paper)
		and not shiboken6.isValid(grid)
		and not shiboken6.isValid(anonymous)
	)
	assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, scene)


#============================================
def test_dispose_contents_retains_failed_decoration_until_controlled_retry(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed paper deletion remains reaper-owned instead of reaching GC."""
	scene = bkchem_qt.canvas.scene.ChemScene()
	paper = scene._paper_item
	grid = scene._grid_overlay
	reaper = bkchem_qt.canvas.graphics_retirement.detached_graphics_retirement_reaper
	real_delete = shiboken6.delete

	#============================================
	def fail_paper_delete(item: object) -> None:
		"""Keep the paper root live for the explicit reaper retry."""
		if item is paper:
			raise RuntimeError("injected paper retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_paper_delete,
	)
	with pytest.raises(RuntimeError, match="ChemScene decoration retirement failed"):
		scene.dispose_contents()

	assert shiboken6.isValid(paper) and not shiboken6.isValid(grid)
	assert reaper.owns_detached_root(paper)

	monkeypatch.undo()
	reaper.drain()
	assert not shiboken6.isValid(paper) and not reaper.owns_detached_root(paper)
	assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, scene)
