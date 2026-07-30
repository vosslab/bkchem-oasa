"""Exercise authoritative Save paths that rebuild a Qt projection."""

# Standard Library
import os
import pathlib


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.themes.theme_manager
import e2e_qt_lifecycle
import oasa.cdml_document


_ARROW_CDML = '<cdml version="0.15"><arrow id="arrow-1"/></cdml>'


#============================================
def _fail(message: str) -> int:
	"""Print one actionable failure message and return a failing status."""
	print("FAIL: %s" % message)
	return 1


#============================================
def _remove_target(target: pathlib.Path) -> None:
	"""Remove one known E2E output file if a prior run left it behind."""
	try:
		target.unlink()
	except FileNotFoundError:
		pass


#============================================
def _project_dirty_arrow(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> tuple[object, object] | None:
	"""Create one backend-dirty arrow snapshot and canonical Qt projection."""
	main_window._on_new()
	session = main_window.sessions[-1]
	commit = session.commit_complete_candidate(_ARROW_CDML)
	if not main_window._replace_session_projection(session, commit.snapshot):
		main_window._remove_session(session)
		return None
	return session, commit.snapshot


#============================================
def _legacy_mutation_refusal_contract(
		main_window: bkchem_qt.main_window.MainWindow, target: pathlib.Path,
		) -> int:
	"""Ensure an already-dirty Qt projection cannot hide a later legacy edit."""
	entry = _project_dirty_arrow(main_window)
	if entry is None:
		return _fail("backend-dirty arrow could not be projected")
	session, captured = entry
	try:
		session.document.mark_dirty()
		try:
			session.write_backend_snapshot(str(target))
		except bkchem_qt.models.document_session.BackendProjectionOutOfSyncError:
			pass
		else:
			return _fail("legacy edit was allowed to write an authoritative snapshot")
		if (
			session.can_write_authoritative_snapshot
			or target.exists()
			or session.backend_snapshot != captured
		):
			return _fail("legacy edit changed backend Save eligibility or baseline")
		return 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def _post_publication_conflict_contract(
		main_window: bkchem_qt.main_window.MainWindow, target: pathlib.Path,
		) -> int:
	"""Ensure a post-replace backend conflict reports its partial result exactly."""
	entry = _project_dirty_arrow(main_window)
	if entry is None:
		return _fail("publication-conflict arrow could not be projected")
	session, captured = entry
	original_mark_saved = session._backend_session.mark_saved

	def reject_saved_baseline(*, expected_revision: int) -> object:
		"""Model OASA rejecting saved-baseline publication after target replacement."""
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"expected revision %s" % expected_revision,
		)

	try:
		target.write_text("old-target", encoding="utf-8")
		session._backend_session.mark_saved = reject_saved_baseline
		try:
			session.write_backend_snapshot(str(target))
		except bkchem_qt.models.document_session.BackendSnapshotPublicationError as error:
			if "atomically replaced" not in str(error):
				return _fail("publication error did not explain target replacement")
			if "did not change the backend saved baseline" not in str(error):
				return _fail("publication error did not explain unchanged saved baseline")
			if not isinstance(error.__cause__, oasa.cdml_document.CDMLRevisionConflictError):
				return _fail("publication error did not preserve the typed backend cause")
		else:
			return _fail("post-replace mark_saved conflict was reported as success")
		if (
			target.read_text(encoding="utf-8") != captured.cdml
			or session.backend_snapshot != captured
			or not session.document.dirty
		):
			return _fail("publication conflict changed backend/Qt state or target bytes")
		return 0
	finally:
		session._backend_session.mark_saved = original_mark_saved
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def main() -> int:
	"""Run the C1c projection-replacement persistence contracts."""
	repo_root = pathlib.Path(__file__).resolve().parents[2]
	output_directory = repo_root / "tmp" / "e2e_qt_authoritative_save"
	output_directory.mkdir(parents=True, exist_ok=True)
	refusal_target = output_directory / "legacy-refusal.cdml"
	conflict_target = output_directory / "published-conflict.cdml"
	_remove_target(refusal_target)
	_remove_target(conflict_target)
	app = PySide6.QtWidgets.QApplication.instance()
	if app is None:
		app = PySide6.QtWidgets.QApplication([])
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)
	try:
		if _legacy_mutation_refusal_contract(main_window, refusal_target) != 0:
			return 1
		if _post_publication_conflict_contract(main_window, conflict_target) != 0:
			return 1
		print("PASS: authoritative Save rejects stale Qt state and reports publication conflicts")
		return 0
	finally:
		e2e_qt_lifecycle.shutdown_main_window(app, main_window)
		_remove_target(refusal_target)
		_remove_target(conflict_target)


if __name__ == "__main__":
	raise SystemExit(main())
