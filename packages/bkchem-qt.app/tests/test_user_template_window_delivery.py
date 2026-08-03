"""Focused public MainWindow behavior checks for saved user templates."""

# Standard Library
import pathlib

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window


_TEMPLATE_CDML = (
	'<cdml version="26.07"><molecule name="Reusable carbon">'
	'<atom id="atom-a" name="C"><point x="1cm" y="2cm"/></atom>'
	'</molecule></cdml>'
)
_INELIGIBLE_CDML = '<cdml version="26.07"><molecule/><plus id="plus-a"/></cdml>'


#============================================
def _write_cdml(path: pathlib.Path, cdml: str) -> None:
	"""Write one CDML document used by a real MainWindow open flow."""
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(cdml, encoding="utf-8")


#============================================
def _session_for_path(
		window: bkchem_qt.main_window.MainWindow, path: pathlib.Path,
		) -> object:
	"""Return the open session identified by its public native source path."""
	return next(session for session in window.sessions if session.origin_path == str(path))


#============================================
def _open_session(
		window: bkchem_qt.main_window.MainWindow, path: pathlib.Path,
		) -> object:
	"""Open one native path through MainWindow's public document flow."""
	if not window.open_file_path(str(path)):
		raise RuntimeError("MainWindow could not open the test CDML document")
	return _session_for_path(window, path)


#============================================
def _retire_window(
		qapp: PySide6.QtWidgets.QApplication,
		window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Retire a test window through the product's controlled Qt lifecycle."""
	window.close()
	if not bkchem_qt.main_window.drain_pending_session_deletions(qapp, window):
		raise RuntimeError("MainWindow session retirement did not drain")
	if not bkchem_qt.main_window.delete_qobject_and_wait(qapp, window):
		raise RuntimeError("MainWindow QObject deletion was not delivered")


#============================================
def _discard_unsaved_changes(*_args: object) -> PySide6.QtWidgets.QMessageBox.StandardButton:
	"""Choose the normal explicit discard route during deterministic test retirement."""
	return PySide6.QtWidgets.QMessageBox.StandardButton.Discard


#============================================
def test_configured_catalog_reaches_initial_and_later_open_sessions(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Startup catalog entries work in documents opened before and after startup."""
	directory = tmp_path / "templates"
	_write_cdml(directory / "source.cdml", _TEMPLATE_CDML)
	first_path = tmp_path / "first.cdml"
	later_path = tmp_path / "later.cdml"
	_write_cdml(first_path, _TEMPLATE_CDML)
	_write_cdml(later_path, _TEMPLATE_CDML)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "question", _discard_unsaved_changes)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		entry = window.user_template_catalog.entries[0]
		_open_session(window, first_path)
		_open_session(window, later_path)
		outcomes = tuple(
			session.submit_user_template(entry.catalog_key, (3.0, 4.0))
			for session in window.sessions
		)
		assert all(outcome.submitted for outcome in outcomes)
	finally:
		_retire_window(qapp, window)


#============================================
def test_refresh_replaces_live_catalogs_and_active_template_ribbon(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Refreshing changes live placement choices and the active visible ribbon."""
	directory = tmp_path / "templates"
	first_template = directory / "first.cdml"
	_write_cdml(first_template, _TEMPLATE_CDML)
	first_path = tmp_path / "first.cdml"
	later_path = tmp_path / "later.cdml"
	_write_cdml(first_path, _TEMPLATE_CDML)
	_write_cdml(later_path, _TEMPLATE_CDML)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "question", _discard_unsaved_changes)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		_open_session(window, first_path)
		active = _open_session(window, later_path)
		active.mode_manager.set_mode("usertemplate")
		first_template.unlink()
		_write_cdml(
			directory / "second.cdml",
			_TEMPLATE_CDML.replace("Reusable carbon", "Second template"),
		)
		current = window.refresh_user_templates().entries[0]
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		qapp.processEvents()
		labels = {button.text() for button in window.findChildren(PySide6.QtWidgets.QPushButton)}
		outcomes = tuple(
			session.submit_user_template(current.catalog_key, (5.0, 6.0))
			for session in window.sessions
		)
		assert all(outcome.submitted for outcome in outcomes)
		assert "Second template" in labels and "Reusable carbon" not in labels
	finally:
		_retire_window(qapp, window)


#============================================
def test_refresh_action_reports_every_skip_and_keeps_valid_neighbor(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Refresh reports each typed failed file while keeping eligible placement live."""
	directory = tmp_path / "templates"
	_write_cdml(directory / "good.cdml", _TEMPLATE_CDML)
	_write_cdml(directory / "broken.cdml", "<cdml>")
	_write_cdml(directory / "ineligible.cdml", _INELIGIBLE_CDML)
	messages = []

	def record_information(*args: object) -> None:
		"""Capture the visible refresh detail message without opening a native dialog."""
		messages.append(str(args[-1]))

	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "information", record_information)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "question", _discard_unsaved_changes)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		snapshot = window.refresh_user_templates()
		entry = snapshot.entries[0]
		outcome = window.sessions[0].submit_user_template(entry.catalog_key, (7.0, 8.0))
		assert outcome.submitted and all(
			failure.source_name in messages[-1] and failure.message in messages[-1]
			for failure in snapshot.failures
		)
	finally:
		_retire_window(qapp, window)


#============================================
def test_embedded_window_without_directory_disables_template_file_actions(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		) -> None:
	"""An embedded host can intentionally provide no template filesystem capability."""
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=None)
	try:
		assert not window.can_save_as_template() and not window.can_refresh_user_templates()
	finally:
		_retire_window(qapp, window)


#============================================
def test_ineligible_save_as_template_creates_no_directory(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Ineligible input is rejected before the configured catalog path is created."""
	directory = tmp_path / "templates"
	path = tmp_path / "ineligible.cdml"
	_write_cdml(path, _INELIGIBLE_CDML)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		_open_session(window, path)
		assert not window.save_as_template()
		assert not directory.exists()
	finally:
		_retire_window(qapp, window)


#============================================
@pytest.mark.parametrize(
	"relative_target", ("nested/template.cdml", "../outside.cdml", "uppercase.CDML"),
)
def test_save_as_template_accepts_only_direct_lowercase_catalog_children(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, relative_target: str,
		) -> None:
	"""The visible save action admits only a direct lowercase catalog target."""
	directory = tmp_path / "templates"
	path = tmp_path / "eligible.cdml"
	_write_cdml(path, _TEMPLATE_CDML)
	target = directory / relative_target
	monkeypatch.setattr(
		PySide6.QtWidgets.QFileDialog,
		"getSaveFileName",
		lambda *_args: (str(target), ""),
	)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		_open_session(window, path)
		assert not window.save_as_template()
		assert not target.exists()
	finally:
		_retire_window(qapp, window)


#============================================
def test_save_as_template_publishes_exact_snapshot_without_session_mutation(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A suffixless File save publishes, refreshes, and delivers the exact snapshot."""
	directory = tmp_path / "templates"
	path = tmp_path / "eligible.cdml"
	target = directory / "saved"
	published = target.with_suffix(".cdml")
	_write_cdml(path, _TEMPLATE_CDML)
	monkeypatch.setattr(
		PySide6.QtWidgets.QFileDialog,
		"getSaveFileName",
		lambda *_args: (str(target), ""),
	)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "question", _discard_unsaved_changes)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		session = _open_session(window, path)
		before = session.backend_snapshot
		saved = window.save_as_template()
		entry = next(
			entry for entry in window.user_template_catalog.entries
			if entry.template_cdml == before.cdml
		)
		published_exact = published.read_text(encoding="utf-8") == before.cdml
		unchanged = session.backend_snapshot == before
		outcome = session.submit_user_template(entry.catalog_key, (3.0, 4.0))
		assert saved and published_exact and unchanged
		assert outcome.submitted
	finally:
		_retire_window(qapp, window)


#============================================
def test_save_as_template_fences_tab_activation_during_native_dialog(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A native dialog cannot redirect publication from its captured origin tab."""
	directory = tmp_path / "templates"
	first_path = tmp_path / "first.cdml"
	second_path = tmp_path / "second.cdml"
	target = directory / "origin-bound.cdml"
	_write_cdml(first_path, _TEMPLATE_CDML)
	_write_cdml(second_path, _TEMPLATE_CDML)

	def choose_target(*_args: object) -> tuple[str, str]:
		"""Activate the other existing document while the native dialog is open."""
		_open_session(window, second_path)
		return str(target), ""

	monkeypatch.setattr(PySide6.QtWidgets.QFileDialog, "getSaveFileName", choose_target)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		_open_session(window, first_path)
		assert not window.save_as_template() and not target.exists()
	finally:
		_retire_window(qapp, window)


#============================================
def test_save_as_template_fences_origin_snapshot_change_during_native_dialog(
		qapp: PySide6.QtWidgets.QApplication, theme_manager: object,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A real accepted persistent edit during dialog display cancels publication."""
	directory = tmp_path / "templates"
	_write_cdml(directory / "source.cdml", _TEMPLATE_CDML)
	path = tmp_path / "eligible.cdml"
	target = directory / "changed-origin.cdml"
	_write_cdml(path, _TEMPLATE_CDML)
	accepted = {}

	def choose_target(*_args: object) -> tuple[str, str]:
		"""Commit one catalog placement while the original native dialog is open."""
		entry = window.user_template_catalog.entries[0]
		accepted["outcome"] = origin.submit_user_template(entry.catalog_key, (9.0, 10.0))
		return str(target), ""

	monkeypatch.setattr(PySide6.QtWidgets.QFileDialog, "getSaveFileName", choose_target)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "question", _discard_unsaved_changes)
	window = bkchem_qt.main_window.MainWindow(theme_manager, user_template_directory=directory)
	try:
		origin = _open_session(window, path)
		saved = window.save_as_template()
		assert accepted["outcome"].submitted and not saved
		assert not target.exists()
	finally:
		_retire_window(qapp, window)
