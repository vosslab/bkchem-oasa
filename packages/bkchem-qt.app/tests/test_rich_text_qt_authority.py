"""Focused Qt consumption checks for backend-owned CDML rich Text."""

# PIP3 modules
import pathlib
import PySide6.QtGui
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.text_item
import bkchem_qt.dialogs.rich_text_dialog
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle


_AUTHORED_CDML = (
	'<cdml version="26.07"><text id="text1"><point x="3cm" y="4cm"/>'
	'<font family="Arial" size="13" color="#112233"/><ftext>&lt;b&gt;H&lt;sub&gt;2'
	'&lt;/sub&gt;&lt;/b&gt;O &amp;amp; &lt;i&gt;x&lt;/i&gt;</ftext></text></cdml>'
)
_PRESERVATION_CDML = (
	'<cdml xmlns:v="urn:vendor" version="26.07"><text id="text1"><point x="3cm" '
	'y="4cm"/><ftext v:preserve="yes"><!--keep--><?vendor value?>'
	'<v:span>H</v:span>2</ftext></text></cdml>'
)


#============================================
def _open_native_session(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path, source: str,
		) -> object:
	"""Open one public native-CDML tab with a durable Text projection."""
	path = tmp_path / "rich_text.cdml"
	path.write_text(source, encoding="utf-8")
	if not main_window.open_file_path(str(path)):
		raise AssertionError("Native CDML projection is unavailable")
	session = main_window.sessions[-1]
	return session


#============================================
def _text_item(session: object) -> bkchem_qt.canvas.items.text_item.TextItem:
	"""Return the current durable Text item without retaining a retired wrapper."""
	for item in session.scene.items():
		model = getattr(item, "document_object_model", None)
		if isinstance(item, bkchem_qt.canvas.items.text_item.TextItem) and model.object_id == "text1":
			return item
	raise AssertionError("Projected Text item is unavailable")


#============================================
def _close_session(main_window: bkchem_qt.main_window.MainWindow, session: object) -> None:
	"""Close one public tab without retaining any retired graphics wrapper."""
	if session in main_window.sessions:
		closed = main_window.close_session_at(main_window.sessions.index(session))
		if not closed and session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def _fail_if_rich_dialog_opens(_dialog: object) -> int:
	"""Fail a preservation-only action before it can enter a modal dialog."""
	raise AssertionError("Rich Text dialog opened")


#============================================
def test_authored_projection_uses_literal_cursor_formats(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Nested authored styles reach the live document without an HTML parser."""
	session = _open_native_session(main_window, tmp_path, _AUTHORED_CDML)
	try:
		item = _text_item(session)
		cursor = PySide6.QtGui.QTextCursor(item.document())
		cursor.setPosition(2)
		format = cursor.charFormat()

		assert item.document().toPlainText() == "H2O & x"
		assert (
			format.fontWeight() >= PySide6.QtGui.QFont.Weight.Bold
			and format.verticalAlignment()
			== PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript
		)
	finally:
		_close_session(main_window, session)


#============================================
def test_preservation_ftext_stays_plain_and_rich_action_is_inert(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Attributed or foreign ftext content remains safe display-only content."""
	session = _open_native_session(main_window, tmp_path, _PRESERVATION_CDML)
	try:
		item = _text_item(session)
		before = session.backend_snapshot
		item.setSelected(True)
		bkchem_qt.actions.object_actions.handle_edit_rich_text(main_window)

		assert item.document().toPlainText() == "H2"
		assert session.backend_snapshot == before
	finally:
		_close_session(main_window, session)


#============================================
def test_rich_dialog_returns_plain_runs_and_excludes_opposite_baseline(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The dialog exposes only immutable plain runs from its QTextDocument."""
	dialog = bkchem_qt.dialogs.rich_text_dialog.RichTextDialog((
		("H", ("b",)), ("2", ("b", "sub")), ("\nO", ()),
	))
	try:
		result = dialog.get_runs()

		assert result == (("H", ("b",)), ("2", ("b", "sub")), ("\nO", ()))
	finally:
		dialog.close()


#============================================
def test_public_rich_action_commits_backend_runs_and_restores_selection(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""One accepted dialog result becomes one backend patch and fresh Text selection."""
	session = _open_native_session(main_window, tmp_path, _AUTHORED_CDML)
	try:
		old_item = _text_item(session)
		old_item.setSelected(True)
		del old_item
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "exec",
			lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
		)
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "get_runs",
			lambda _dialog: (("N", ("i",)), ("2", ("sub",))),
		)
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "changes",
			lambda _dialog: (("font_size", 18), ("font_color", "#aabbcc")),
		)
		bkchem_qt.actions.object_actions.handle_edit_rich_text(main_window)
		new_item = _text_item(session)
		selected_ids = {
			item.document_object_model.object_id for item in session.scene.selectedItems()
		}

		assert "size=\"18\" color=\"#aabbcc\"" in session.backend_snapshot.cdml
		assert (
			new_item.document().toPlainText() == "N2"
			and new_item.font().pointSize() == 18
			and new_item.defaultTextColor().name() == "#aabbcc"
			and selected_ids == {"text1"}
		)
	finally:
		_close_session(main_window, session)


#============================================
def test_rich_projection_refresh_uses_the_current_root_font() -> None:
	"""Styled runs inherit refreshed root values instead of retaining copied formats."""
	item = bkchem_qt.canvas.items.text_item.TextItem()
	try:
		item.setFont(PySide6.QtGui.QFont("Courier", 13))
		item.set_color("#112233")
		item.set_formatted_text_runs((("H", ("b",)), ("2<>&", ("sub",))))
		root_font = PySide6.QtGui.QFont("Times", 17)
		item.setFont(root_font)
		item.set_color("#aabbcc")
		item.set_formatted_text_runs((("H", ("b",)), ("2<>&", ("sub",))))
		cursor = PySide6.QtGui.QTextCursor(item.document())
		cursor.setPosition(1)
		bold_format = cursor.charFormat()
		cursor.setPosition(2)
		sub_format = cursor.charFormat()
		formats = (bold_format, sub_format)
		inherits_root = all(
			not format.hasProperty(property_name)
			for format in formats
			for property_name in (
				PySide6.QtGui.QTextFormat.Property.FontFamily,
				PySide6.QtGui.QTextFormat.Property.FontPointSize,
				PySide6.QtGui.QTextFormat.Property.ForegroundBrush,
			)
		)
		authored_styles = (
			bold_format.fontWeight() >= PySide6.QtGui.QFont.Weight.Bold
			and sub_format.verticalAlignment()
			== PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript
		)

		assert item.document().defaultFont().family() == "Times"
		assert authored_styles and inherits_root
	finally:
		item.setParentItem(None)


#============================================
def test_configure_directs_selected_rich_text_to_the_rich_action(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Configure does not open the intentionally plain-only Text dialog for authored runs."""
	session = _open_native_session(main_window, tmp_path, _AUTHORED_CDML)
	try:
		_text_item(session).setSelected(True)
		bkchem_qt.actions.object_actions.handle_configure(main_window)

		assert "Edit Rich Text" in main_window.statusBar().currentMessage()
	finally:
		_close_session(main_window, session)


#============================================
def test_malformed_root_font_leaves_rich_editing_unavailable(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Malformed persisted root font values do not enter the rich dialog."""
	session = _open_native_session(
		main_window, tmp_path, _AUTHORED_CDML.replace('size="13"', 'size="bad"'),
	)
	try:
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "exec",
			_fail_if_rich_dialog_opens,
		)
		_text_item(session).setSelected(True)
		bkchem_qt.actions.object_actions.handle_edit_rich_text(main_window)

		assert "unavailable" in main_window.statusBar().currentMessage().lower()
	finally:
		_close_session(main_window, session)


#============================================
def test_named_root_font_color_leaves_rich_editing_unavailable(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A non-CDML named color remains visible but cannot enter rich editing."""
	session = _open_native_session(
		main_window, tmp_path, _AUTHORED_CDML.replace('color="#112233"', 'color="red"'),
	)
	try:
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "exec",
			_fail_if_rich_dialog_opens,
		)
		_text_item(session).setSelected(True)
		bkchem_qt.actions.object_actions.handle_edit_rich_text(main_window)

		assert "unavailable" in main_window.statusBar().currentMessage().lower()
	finally:
		_close_session(main_window, session)


#============================================
def test_rich_action_stays_bound_to_its_origin_tab(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Tab activation during the modal dialog cannot retarget a rich Text patch."""
	origin = _open_native_session(main_window, tmp_path, _AUTHORED_CDML)
	other = None
	try:
		item = _text_item(origin)
		item.setSelected(True)
		del item
		def accept_after_new_tab(_dialog: object) -> int:
			"""Activate an independent tab before accepting the captured dialog."""
			main_window.on_new()
			return PySide6.QtWidgets.QDialog.DialogCode.Accepted
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "exec", accept_after_new_tab,
		)
		monkeypatch.setattr(
			bkchem_qt.dialogs.rich_text_dialog.RichTextDialog, "get_runs",
			lambda _dialog: (("Origin", ("b",)),),
		)
		bkchem_qt.actions.object_actions.handle_edit_rich_text(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert "&lt;b&gt;Origin&lt;/b&gt;" in origin.backend_snapshot.cdml
		assert "Origin" not in other.backend_snapshot.cdml
	finally:
		if other is not None:
			_close_session(main_window, other)
		_close_session(main_window, origin)


#============================================
def test_captured_rich_callback_is_unavailable_after_its_tab_closes(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A closed origin tab makes its captured rich callback typed and inert."""
	origin = _open_native_session(main_window, tmp_path, _AUTHORED_CDML)
	captured = main_window.capture_rich_text_for_view(origin.view, "text1")
	if captured is None:
		raise AssertionError("Live rich Text capability was unavailable")
	expected_revision, submit = captured
	main_window.on_new()
	peer = next(session for session in main_window.sessions if session is not origin)
	peer_before = peer.backend_snapshot
	main_window.close_session_at(main_window.sessions.index(origin))
	outcome = submit(expected_revision, "text1", (("late", ()),))

	assert outcome.status == "unavailable" and outcome.commit is None
	assert peer.backend_snapshot == peer_before
	_close_session(main_window, peer)


#============================================
def test_captured_rich_callback_reports_a_typed_stale_revision(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A later accepted backend patch makes the earlier rich dialog intent stale."""
	session = _open_native_session(main_window, tmp_path, _AUTHORED_CDML)
	try:
		captured = main_window.capture_rich_text_for_view(session.view, "text1")
		if captured is None:
			raise AssertionError("Live rich Text capability was unavailable")
		expected_revision, submit = captured
		session.submit_rich_text_patch(
			session.backend_snapshot.revision, "text1", (("current", ()),),
		)
		outcome = submit(expected_revision, "text1", (("stale", ()),))

		assert outcome.status == "rejected" and outcome.failure_kind == "revision-conflict"
		assert "current" in session.backend_snapshot.cdml
	finally:
		_close_session(main_window, session)


#============================================
def test_rich_projection_retry_uses_only_the_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed delivery retries the accepted rich snapshot without resubmission."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_AUTHORED_CDML,
	)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)
	try:
		def unavailable(_snapshot: object) -> object:
			"""Return one controlled post-acceptance projection failure."""
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
			)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, unavailable),
		)
		outcome = session.submit_rich_text_patch(
			session.backend_snapshot.revision, "text1", (("Accepted", ("b",)),),
		)
		if outcome.commit is None:
			raise AssertionError("Accepted rich Text patch returned no backend snapshot")
		accepted = outcome.commit.snapshot
		def resubmission_must_not_run(*_args: object) -> object:
			"""Fail if retry incorrectly re-enters the public rich patch route."""
			raise AssertionError("Rich patch was resubmitted")
		monkeypatch.setattr(
			session, "submit_rich_text_patch",
			resubmission_must_not_run,
		)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		retry = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and outcome.submitted
		assert retry.status == "accepted" and session.backend_snapshot == accepted
	finally:
		session.dispose()
