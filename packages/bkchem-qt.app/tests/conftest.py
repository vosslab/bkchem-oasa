"""Shared pytest fixtures for bkchem-qt tests."""

# Standard Library
import os
import sys

_REPO_TESTS_DIR = os.path.abspath(os.path.join(
	os.path.dirname(__file__), "..", "..", "..", "tests",
))
if _REPO_TESTS_DIR not in sys.path:
	sys.path.insert(0, _REPO_TESTS_DIR)

pytest_plugins = ("pytest_kill_after",)

# Qt reads its platform choice when QApplication is initialized.  Set the
# headless test policy before importing any PySide6 module.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# suppress "This plugin does not support propagateSizeHints()" noise
# from Qt's Cocoa platform plugin on macOS
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets
import PySide6.QtTest

# local repo modules
import bkchem_qt.bridge.chemistry_preparation
import bkchem_qt.bridge.insertion_placement
import bkchem_qt.themes.theme_manager
import bkchem_qt.main_window
import oasa.cdml_writer
import oasa.coords_generator
import oasa.insertion_geometry
import oasa.smiles_lib
import tests.graphics_test_retirement


#============================================
def _env_is_truthy(name: str) -> bool:
	"""Return True when an env var is set to a truthy value."""
	value = os.environ.get(name, "").strip().lower()
	return value in ("1", "true", "yes", "on")


#============================================
def _env_int(name: str, default: int = 0) -> int:
	"""Parse integer env var with safe fallback."""
	raw = os.environ.get(name, "")
	if not raw.strip():
		return default
	try:
		return int(raw)
	except ValueError:
		return default


VISUAL_TEST_MODE = _env_is_truthy("BKCHEM_QT_TEST_VISUAL")
VISUAL_HOLD_MS = max(0, _env_int("BKCHEM_QT_TEST_VISUAL_HOLD_MS", 0))


#============================================
def _drain_deferred_deletes(
		app: PySide6.QtWidgets.QApplication,
		window: bkchem_qt.main_window.MainWindow = None,
		) -> bool:
	"""Deliver deferred deletion through the production bounded reaper drain."""
	return bkchem_qt.main_window.drain_pending_session_deletions(app, window)


#============================================
def _using_offscreen_backend() -> bool:
	"""Return True when tests are running with offscreen Qt platform."""
	return os.environ.get("QT_QPA_PLATFORM", "").strip().lower() == "offscreen"


#============================================
def _should_show_windows(request: pytest.FixtureRequest) -> bool:
	"""Decide whether GUI windows should be shown during pytest runs.

	Visual mode is enabled either explicitly via env var or implicitly
	when capture is disabled (-s) on a non-offscreen platform.
	"""
	if VISUAL_TEST_MODE:
		return True
	capture_mode = request.config.getoption("capture")
	return capture_mode == "no" and not _using_offscreen_backend()


#============================================
@pytest.fixture(scope="session")
def qapp() -> PySide6.QtWidgets.QApplication:
	"""Return the QApplication singleton, creating it if needed.

	Returns:
		QApplication: The application instance.
	"""
	app = PySide6.QtWidgets.QApplication.instance()
	if app is None:
		app = PySide6.QtWidgets.QApplication([])
	yield app
	# Explicit Qt teardown avoids GC-time shiboken crashes on interpreter exit.
	# QClipboard owns QMimeData passed through setMimeData().  Clear that native
	# owner while both Qt and Python are still live; otherwise its wrapped
	# QMimeData can be destroyed during interpreter shutdown.
	app.clipboard().clear()
	tests.graphics_test_retirement.retire_terminal_top_level_widgets(app)


#============================================
@pytest.fixture(scope="session")
def theme_manager(
		qapp: PySide6.QtWidgets.QApplication,
		) -> bkchem_qt.themes.theme_manager.ThemeManager:
	"""Return a ThemeManager bound to the QApplication.

	Args:
		qapp: The QApplication fixture.

	Returns:
		ThemeManager: The theme manager instance.
	"""
	tm = bkchem_qt.themes.theme_manager.ThemeManager(qapp)
	return tm


#============================================
@pytest.fixture(scope="module")
def main_window(
		qapp: PySide6.QtWidgets.QApplication,
		theme_manager: bkchem_qt.themes.theme_manager.ThemeManager,
		request: pytest.FixtureRequest,
		) -> bkchem_qt.main_window.MainWindow:
	"""Return a MainWindow shared across tests in the same module.

	Module scope avoids creating 45+ MainWindow instances during the
	full test suite. Each test module gets one MainWindow that is
	closed at module teardown.

	Args:
		qapp: The QApplication fixture.
		theme_manager: The ThemeManager fixture.

	Yields:
		MainWindow: The main window instance.
	"""
	mw = bkchem_qt.main_window.MainWindow(theme_manager)
	if _should_show_windows(request):
		mw.show()
		mw.raise_()
		mw.activateWindow()
		qapp.processEvents()
	yield mw
	_normalize_main_window(mw)
	mw.close()
	assert _drain_deferred_deletes(qapp, mw)
	assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, mw)


#============================================
def _normalize_main_window(main_window: bkchem_qt.main_window.MainWindow) -> None:
	"""Install one fresh blank backend session through normal session disposal.

	A shared MainWindow cannot clear its current Qt document to reset test state:
	the session may instead own a newer authoritative backend snapshot.  A fresh
	session gives the next test a matching blank backend snapshot and projection,
	while `_remove_session()` retires every old projection through the production
	lifecycle path.
	"""
	fresh_session = main_window._create_session(activate=False)
	for session in tuple(main_window.sessions):
		if session is fresh_session:
			continue
		assert main_window._remove_session(session)
		assert _drain_deferred_deletes(
			PySide6.QtWidgets.QApplication.instance(), main_window,
		)
	main_window._tab_widget.setCurrentIndex(0)
	main_window._activate_session(fresh_session)
	main_window.view.reset_zoom()


#============================================
@pytest.fixture(autouse=True)
def _reset_main_window(
		request: pytest.FixtureRequest,
		) -> None:
	"""Normalize and drain a shared window only for tests that request it.

	Standalone Qt tests frequently need only ``qapp`` or a bare scene.  Obtaining
	the window through the public pytest request API keeps those tests free of
	the window's document/session ownership while retaining the established
	normalization and visual-test behavior for every test whose fixture closure
	requires ``main_window``.
	"""
	if "main_window" not in request.fixturenames:
		yield
		return
	main_window = request.getfixturevalue("main_window")
	_normalize_main_window(main_window)
	yield
	assert _drain_deferred_deletes(
		PySide6.QtWidgets.QApplication.instance(), main_window,
	)
	if main_window.isVisible() and VISUAL_HOLD_MS > 0:
		main_window.repaint()
		PySide6.QtWidgets.QApplication.processEvents()
		PySide6.QtTest.QTest.qWait(VISUAL_HOLD_MS)


#============================================
@pytest.fixture
def insert_smiles_through_backend() -> object:
	"""Return a deterministic authoritative setup seam for unrelated GUI tests."""
	def insert(main_window: object, smiles: str) -> object:
		"""Parse in OASA, submit plain CDML, and return the projected molecule."""
		session = main_window._active_session
		molecule = oasa.smiles_lib.text_to_mol(smiles)
		oasa.coords_generator.calculate_coords(molecule, bond_length=1.0, force=1)
		bond_length, anchor = (
			bkchem_qt.bridge.insertion_placement.capture_insertion_placement(session)
		)
		oasa.insertion_geometry.place_molecules_for_insertion(
			[molecule], bond_length, anchor,
		)
		proposal = bkchem_qt.bridge.chemistry_preparation.MoleculeInsertionProposal(
			oasa.cdml_writer.molecules_to_insertion_proposal(
				[molecule], token_stem="gui-fixture-r%s" % session.backend_snapshot.revision,
			),
			session.backend_snapshot.revision,
			"Insert GUI test molecule",
		)
		request = bkchem_qt.bridge.chemistry_preparation.build_molecule_insertion_request(
			proposal, "Insert GUI test molecule",
		)
		outcome = session.submit_persistent_operation(request)
		if outcome.status != "accepted":
			raise AssertionError("Backend molecule setup failed: %s" % outcome.message)
		return session.document.molecules[-1]

	return insert
