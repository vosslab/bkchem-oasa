"""Behavior test for GUI-thread delivery of prepared OASA imports."""

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.file_actions
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.bridge.worker


#============================================
def test_import_relay_converts_prepared_oasa_parts_on_gui_thread(
		qapp: PySide6.QtWidgets.QApplication,
		main_window: object,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Prepared OASA parts become Qt models only in the GUI-thread relay."""
	component = object()
	deliveries = []

	def convert_component(part: object, bond_length_pt: float) -> object:
		"""Record whether Qt conversion runs on the QApplication thread."""
		return (
			part,
			bond_length_pt,
			PySide6.QtCore.QThread.currentThread() == qapp.thread(),
		)

	def on_loaded(molecules: list) -> None:
		"""Capture the models delivered by the relay."""
		deliveries.append(molecules)

	monkeypatch.setattr(
		bkchem_qt.bridge.oasa_bridge,
		"oasa_mol_to_qt_mol",
		convert_component,
	)
	relay = bkchem_qt.actions.file_actions._ImportResultRelay(
		main_window,
		object(),
		"test-file",
		42.0,
		on_loaded=on_loaded,
	)
	relay.on_result([component])

	assert deliveries == [[(component, 42.0, True)]]
	relay.deleteLater()
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	qapp.processEvents()


#============================================
def test_import_relay_delivers_frozen_complete_cdml_without_graph_conversion(
		qapp: PySide6.QtWidgets.QApplication,
		main_window: object,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""External document Open crosses the GUI boundary as plain complete CDML."""
	deliveries = []
	prepared = bkchem_qt.bridge.worker.PreparedCompleteCDML(
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"></cdml>',
		"sample.mol",
	)

	def fail_conversion(*_args: object, **_kwargs: object) -> object:
		"""Fail if the complete-document relay enters the retired graph route."""
		raise AssertionError("complete CDML delivery must not convert an OASA graph")

	monkeypatch.setattr(
		bkchem_qt.bridge.oasa_bridge, "oasa_mol_to_qt_mol", fail_conversion,
	)
	relay = bkchem_qt.actions.file_actions._ImportResultRelay(
		main_window, object(), "sample.mol", 42.0,
		on_loaded=deliveries.append,
	)
	relay.on_result(prepared)
	assert deliveries == [prepared]
	relay.deleteLater()
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	qapp.processEvents()
