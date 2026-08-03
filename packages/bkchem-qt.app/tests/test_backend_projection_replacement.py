"""Behavioral checks for disposable Qt projections of backend CDML."""

# PIP3 modules
import dataclasses
import pytest
import PySide6.QtCore
import PySide6.QtWidgets
import shiboken6

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.items.mark_item
import bkchem_qt.canvas.document_projection
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.io.cdml_document_io
import bkchem_qt.io.cdml_fragment_builder
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
import tests.graphics_test_retirement


_ARROW_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow></cdml>'
)
_ARROW_AND_PLUS_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow><plus id="plus-1"><point x="4cm" y="1cm"/>'
	'</plus></cdml>'
)
_TWO_ATOM_CDML = (
	'<cdml version="0.15"><molecule id="molecule-1">'
	'<atom id="atom-1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="atom-2" name="O"><point x="2cm" y="1cm"/></atom>'
	'</molecule></cdml>'
)
_TWO_ATOM_BOND_CDML = (
	'<cdml version="0.15"><molecule id="molecule-1">'
	'<atom id="atom-1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="atom-2" name="O"><point x="2cm" y="1cm"/></atom>'
	'<bond id="bond-1" start="atom-1" end="atom-2" type="n1"/>'
	'</molecule></cdml>'
)
_MARKED_ATOM_CDML = (
	'<cdml version="0.15"><molecule id="molecule-1">'
	'<atom id="atom-1" name="C"><point x="1cm" y="1cm"/>'
	'<mark type="plus"/></atom></molecule></cdml>'
)
_INTERLEAVED_CDML = (
	'<cdml xmlns:vendor="urn:vendor" version="0.15">'
	'<molecule id="molecule-1"><atom id="atom-1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule>'
	'<arrow id="arrow-1"><point x="2cm" y="1cm"/>'
	'<point x="3cm" y="1cm"/></arrow>'
	'<molecule id="molecule-2"><atom id="atom-2" name="O">'
	'<point x="4cm" y="1cm"/></atom></molecule>'
	'<plus id="plus-1"><point x="5cm" y="1cm"/></plus>'
	'<vendor:opaque id="opaque-1"/></cdml>'
)


#============================================
def _new_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create one isolated session for a backend projection test."""
	main_window._on_new()
	return main_window.sessions[-1]


#============================================
def _close_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Retire one test session without changing its backend saved baseline."""
	assert main_window._remove_session(session)


#============================================
def _projection_snapshot(
		document: oasa.cdml_document.CDMLDocument,
		) -> oasa.cdml_document.CDMLProjectionSnapshot:
	"""Return one backend-owned envelope for a canonical test snapshot."""
	return oasa.cdml_document.CDMLDocument.projection_snapshot(
		oasa.cdml_document.CDMLSnapshot(0, document.serialize(), False),
	)


#============================================
def test_stale_or_foreign_snapshot_cannot_mutate_live_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Only the exact current snapshot may replace a session projection."""
	session = _new_tab(main_window)
	try:
		stale = session.backend_snapshot
		commit = session.commit_complete_candidate(_ARROW_CDML)
		foreign = oasa.cdml_document.CDMLDocumentSession.load(
			_ARROW_AND_PLUS_CDML,
		).snapshot()
		old_document = session.document
		assert not session.replace_projection_from_backend_snapshot(stale)
		assert (
			not session.replace_projection_from_backend_snapshot(foreign)
			and session.document is old_document
			and session.backend_snapshot == commit.snapshot
		)
	finally:
		_close_tab(main_window, session)


#============================================
def test_first_accepted_candidate_installs_from_atomic_projection_envelope(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The session lifecycle port installs an accepted first native arrow."""
	session = _new_tab(main_window)
	try:
		commit = session.commit_complete_candidate(_ARROW_CDML)
		result = session._projection_lifecycle_port.project(commit.snapshot)
		assert result.installed and session.backend_projection_synchronized
		assert session.document.presentation_objects[0].object_id == "arrow-1"
	finally:
		_close_tab(main_window, session)


#============================================
def test_synchronized_preparation_installs_portable_batches_for_all_projected_children(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""One complete backend observation bundle gives every projected child paint facts."""
	del qapp
	document = oasa.cdml_document.CDMLDocument.parse(_TWO_ATOM_BOND_CDML, validation="strict")
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		_projection_snapshot(document),
	)
	try:
		assert all(
			getattr(model, "_backend_render_batch", None) is not None
			for molecule, _items in prepared.molecule_projections
			for model in (*molecule.atoms, *molecule.bonds)
		)
	finally:
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)


#============================================
def test_synchronized_items_paint_portable_batches_without_compatibility_bridge(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Exact-revision batches keep scene installation out of legacy rendering."""
	del qapp
	document = oasa.cdml_document.CDMLDocument.parse(_TWO_ATOM_BOND_CDML, validation="strict")
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		_projection_snapshot(document),
	)
	def compatibility_called(*args: object, **kwargs: object) -> list[object]:
		raise AssertionError("synchronized rendering reached the compatibility bridge")
	monkeypatch.setattr(bkchem_qt.bridge.oasa_bridge, "legacy_atom_render_operations", compatibility_called)
	monkeypatch.setattr(bkchem_qt.bridge.oasa_bridge, "legacy_bond_render_operations", compatibility_called)
	atom_item = None
	bond_item = None
	try:
		molecule, _items = prepared.molecule_projections[0]
		atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(molecule.atoms[0])
		bond_item = bkchem_qt.canvas.items.bond_item.BondItem(molecule.bonds[0])
		assert not atom_item.boundingRect().isEmpty() and not bond_item.boundingRect().isEmpty()
	finally:
		if atom_item is not None:
			atom_item.dispose()
		if bond_item is not None:
			bond_item.dispose()
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)


#============================================
def test_backend_projection_envelope_rejects_missing_backend_fact() -> None:
	"""A synchronized route rejects an incomplete backend envelope."""
	backend_document = oasa.cdml_document.CDMLDocument.parse(_ARROW_CDML, validation="strict")
	with pytest.raises(ValueError, match="seven exact backend facts"):
		dataclasses.replace(
			_projection_snapshot(backend_document), molecule_render_observation=None,
		)


#============================================
def test_synchronized_hydration_requires_portable_render_coverage() -> None:
	"""Synchronized staging cannot create a later compatibility-rendering seam."""
	backend_document = oasa.cdml_document.CDMLDocument.parse(
		_TWO_ATOM_BOND_CDML, validation="strict",
	)
	projection_snapshot = _projection_snapshot(backend_document)
	incomplete = dataclasses.replace(
		projection_snapshot,
		molecule_render_observation=dataclasses.replace(
			projection_snapshot.molecule_render_observation, batches=(),
		),
	)
	with pytest.raises(ValueError, match="coverage is incomplete"):
		bkchem_qt.io.cdml_document_io.hydrate_synchronized_cdml_document(
			incomplete,
		)


#============================================
def test_named_compatibility_decoder_retains_standalone_molecule_loading() -> None:
	"""Standalone CDML still uses its explicitly named compatibility decoder."""
	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string(
		_TWO_ATOM_BOND_CDML,
	)
	assert document.molecules[0].compatibility_source_xml is not None


#============================================
def test_legacy_fragment_builder_refuses_synchronized_molecule_projection() -> None:
	"""The compatibility-only builder cannot become a synchronized save path."""
	backend_document = oasa.cdml_document.CDMLDocument.parse(
		_TWO_ATOM_BOND_CDML, validation="strict",
	)
	document = bkchem_qt.io.cdml_document_io.hydrate_synchronized_cdml_document(
		_projection_snapshot(backend_document),
	)
	with pytest.raises(ValueError, match="compatibility-decoded molecule XML"):
		bkchem_qt.io.cdml_fragment_builder.build_top_level_fragment(
			document, [document.molecules[0]],
		)


#============================================
def test_incomplete_synchronized_render_bundle_fails_before_live_replacement(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A missing portable batch leaves the existing scene projection untouched."""
	session = _new_tab(main_window)
	try:
		commit = session.commit_complete_candidate(_TWO_ATOM_BOND_CDML)
		old_document = session.document
		original_projection_snapshot = session._backend_session.projection_snapshot

		def incomplete_projection_snapshot() -> object:
			"""Model one incomplete backend projection envelope."""
			projection_snapshot = original_projection_snapshot()
			return dataclasses.replace(
				projection_snapshot,
				molecule_render_observation=dataclasses.replace(
					projection_snapshot.molecule_render_observation, batches=(),
				),
			)

		monkeypatch.setattr(
			session._backend_session, "projection_snapshot", incomplete_projection_snapshot,
		)
		result = session.replace_projection_from_backend_snapshot(commit.snapshot)
		assert (
			result.status
			== bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE
			and session.document is old_document
			and isinstance(result.diagnostic, bkchem_qt.models.document_session.ProjectionReplacementError)
			and isinstance(result.diagnostic.__cause__, ValueError)
		)
	finally:
		_close_tab(main_window, session)


#============================================
def test_synchronized_preparation_rejects_duplicate_portable_batch(
		) -> None:
	"""Duplicate backend coverage cannot create a partially hydrated projection."""
	document = oasa.cdml_document.CDMLDocument.parse(_TWO_ATOM_BOND_CDML, validation="strict")
	render_observation = document.molecule_render_observation(0)
	duplicate_observation = dataclasses.replace(
		render_observation, batches=(*render_observation.batches, render_observation.batches[0]),
	)
	with pytest.raises(ValueError, match="association is ambiguous"):
		bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
			dataclasses.replace(
				_projection_snapshot(document), molecule_render_observation=duplicate_observation,
			),
		)


#============================================
def test_synchronized_preparation_rejects_wrong_kind_portable_batch(
		) -> None:
	"""A batch may not claim a core child's position with the other child kind."""
	document = oasa.cdml_document.CDMLDocument.parse(_TWO_ATOM_BOND_CDML, validation="strict")
	render_observation = document.molecule_render_observation(0)
	wrong_kind = dataclasses.replace(render_observation.batches[0], kind="bond")
	wrong_kind_observation = dataclasses.replace(
		render_observation, batches=(wrong_kind, *render_observation.batches[1:]),
	)
	with pytest.raises(ValueError, match="kind does not match"):
		bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
			dataclasses.replace(
				_projection_snapshot(document), molecule_render_observation=wrong_kind_observation,
			),
		)


#============================================
def test_synchronized_preparation_rejects_foreign_molecule_portable_batch(
		) -> None:
	"""A batch cannot be attributed to a molecule absent from the core observation."""
	document = oasa.cdml_document.CDMLDocument.parse(_TWO_ATOM_BOND_CDML, validation="strict")
	render_observation = document.molecule_render_observation(0)
	foreign_batch = dataclasses.replace(render_observation.batches[0], molecule_source_position=99)
	foreign_observation = dataclasses.replace(
		render_observation, batches=(foreign_batch, *render_observation.batches[1:]),
	)
	with pytest.raises(ValueError, match="belongs to no accepted molecule"):
		bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
			dataclasses.replace(
				_projection_snapshot(document), molecule_render_observation=foreign_observation,
			),
		)


#============================================
def test_synchronized_preparation_does_not_require_batch_for_ambiguous_bond(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""An endpoint-ambiguous bond remains display-only without blocking atom paint."""
	del qapp
	complete_cdml = (
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='a' name='N'><point x='1cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='b' type='n1'/></molecule></cdml>"
	)
	document = oasa.cdml_document.CDMLDocument.parse(complete_cdml, validation="compat")
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		_projection_snapshot(document),
	)
	try:
		assert not prepared.molecule_projections[0][0].bonds
	finally:
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)


#============================================
def test_backend_paper_layout_projection_retains_no_header_or_reaction_xml(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A live projection gets paper facts while OASA alone preserves its XML."""
	session = _new_tab(main_window)
	try:
		commit = session.commit_complete_candidate(
			'<cdml><info><author>backend</author></info><paper type="A3" '
			'orientation="landscape" /><viewport viewport="0 0 10 10" />'
			'<reaction id="reaction-1" /><external-data>opaque</external-data></cdml>',
		)
		if not session.replace_projection_from_backend_snapshot(commit.snapshot):
			raise RuntimeError("backend paper-layout projection did not install")
		envelope = session.document.cdml_envelope
		assert (
			session.document.paper.attributes["type"] == "A3"
			and session.document.paper.attributes["orientation"] == "landscape"
		)
		backend_objects = oasa.cdml_document.CDMLDocument.parse(
			commit.snapshot.cdml, validation="strict",
		).objects()
		assert (
			not any((envelope.root_attributes, envelope.info_xml, envelope.reactions, envelope.external_data_xml))
			and any(
				record.local_name == "reaction" and record.identifier == "reaction-1"
				for record in backend_objects
			)
			and any(record.local_name == "external-data" for record in backend_objects)
		)
	finally:
		_close_tab(main_window, session)


#============================================
def test_document_graphics_disposal_exhausts_items_after_binding_failure(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An item disposal fault cannot retain its scene or signal connection."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(_ARROW_CDML)
	document = prepared.document
	arrow_item = prepared.presentation_items[0]
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	scene.addItem(arrow_item)
	binding = arrow_item._projection_binding

	def fail_before_item_cleanup() -> None:
		"""Bypass ordinary wrapper cleanup at the first item-disposal boundary."""
		raise RuntimeError("graphics item disposal failed")

	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		monkeypatch.setattr(arrow_item, "dispose", fail_before_item_cleanup)
		try:
			with pytest.raises(RuntimeError, match="Document graphics were detached"):
				document._dispose_document_graphics()
			assert not shiboken6.isValid(arrow_item) and binding._model is None
		finally:
			monkeypatch.undo()


#============================================
def test_detached_projection_disposal_exhausts_items_after_item_failure(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A detached-item fault cannot retain graphics or document-owned models."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	binding = arrow_item._projection_binding

	def fail_before_item_cleanup() -> None:
		"""Bypass ordinary detached-wrapper cleanup at its first boundary."""
		raise RuntimeError("detached graphics item disposal failed")

	monkeypatch.setattr(arrow_item, "dispose", fail_before_item_cleanup)
	try:
		with pytest.raises(RuntimeError, match="Prepared projection was released"):
			bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
		assert not shiboken6.isValid(arrow_item) and binding._item is None
	finally:
		monkeypatch.undo()


#============================================
def test_dispose_prepared_projection_disconnects_detached_graphics(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Prepared detached artwork crosses explicit terminal retirement."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	qapp.processEvents()
	assert not shiboken6.isValid(arrow_item)


#============================================
def test_dispose_prepared_projection_releases_detached_binding(
		) -> None:
	"""Disposing a prepared bundle releases its temporary model callback."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	binding = arrow_item._projection_binding
	bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
	assert binding._item is None


#============================================
def test_backend_description_rebuilds_interleaved_stack_without_opaque_xml(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Qt keeps source order while OASA alone retains an opaque direct root."""
	backend_document = oasa.cdml_document.CDMLDocument.parse(_INTERLEAVED_CDML, validation="strict")
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		_projection_snapshot(backend_document),
	)
	try:
		ordered_ids = tuple(
			getattr(model, "mol_id", None) or getattr(model, "object_id", None)
			for model in prepared.document.objects
		)
		assert ordered_ids == ("molecule-1", "arrow-1", "molecule-2", "plus-1")
		assert prepared.document.unsupported_content[0].raw_xml == ""
	finally:
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)


#============================================
def test_display_only_presentation_renders_without_a_persistent_action_address(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Preservation content remains visible while persistent targeting is inert."""
	cdml = (
		'<cdml xmlns:vendor="urn:vendor" version="0.15">'
		'<plus id="plus-1"><point x="1cm" y="2cm"/>'
		'<vendor:metadata keep="yes"/></plus></cdml>'
	)
	backend_document = oasa.cdml_document.CDMLDocument.parse(cdml, validation="strict")
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		_projection_snapshot(backend_document),
	)
	document = prepared.document
	model = document.presentation_objects[0]
	item = prepared.presentation_items[0]
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	scene.addItem(item)
	with tests.graphics_test_retirement.bare_document_scene_retirement(
			qapp, document, scene,
			):
		item.setSelected(True)
		root_ids = document.selected_presentation_stack_root_ids
		assert item.toPlainText() == "+" and model.supported and not model.editable
		assert root_ids == ()


#============================================
def test_dispose_prepared_projection_uses_supplied_session_reaper(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Prepared cleanup keeps an injected terminal failure with its caller."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	reaper = bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper()
	real_delete = shiboken6.delete

	#============================================
	def fail_arrow_delete(item: object) -> None:
		"""Retain the explicit prepared root until its owner retries it."""
		if item is arrow_item:
			raise RuntimeError("injected prepared projection retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6, "delete", fail_arrow_delete,
	)
	try:
		with pytest.raises(RuntimeError, match="Prepared projection was released"):
			bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared, reaper)
		assert shiboken6.isValid(arrow_item) and reaper.owns_detached_root(arrow_item)
		monkeypatch.undo()
		reaper.drain()
		assert not shiboken6.isValid(arrow_item)
	finally:
		monkeypatch.undo()


#============================================
def test_partial_detached_molecule_builder_releases_earlier_items(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A later atom-construction failure disconnects earlier detached graphics."""
	original_init = bkchem_qt.canvas.items.atom_item.AtomItem.__init__
	created = []

	def fail_second_atom(
			self: bkchem_qt.canvas.items.atom_item.AtomItem,
			*args: object, **kwargs: object,
			) -> None:
		"""Keep the first item, then force the second constructor to fail."""
		if created:
			raise RuntimeError("later atom item failed")
		original_init(self, *args, **kwargs)
		created.append(self)

	monkeypatch.setattr(
		bkchem_qt.canvas.items.atom_item.AtomItem, "__init__", fail_second_atom,
	)
	with pytest.raises(RuntimeError, match="later atom item failed"):
		bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(_TWO_ATOM_CDML)
	first_item = created[0]
	assert not shiboken6.isValid(first_item)


#============================================
def test_invalid_prepared_mark_is_rejected_without_scene_ownership_probe(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Atom-owned marks never need a scene() probe during installation."""
	session = _new_tab(main_window)
	try:
		commit = session.commit_complete_candidate(_MARKED_ATOM_CDML)
		backend_document = oasa.cdml_document.CDMLDocument.parse(
			commit.snapshot.cdml, validation="strict",
		)
		prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
			_projection_snapshot(backend_document),
		)
		mark = prepared.mark_items[0]
		shiboken6.delete(mark)
		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io,
			"prepare_synchronized_projection", lambda *_args, **_kwargs: prepared,
		)
		result = session.replace_projection_from_backend_snapshot(commit.snapshot)
		assert result.status == "installation-failed" and session.document is None
	finally:
		_close_tab(main_window, session)


#============================================
def test_valid_prepared_mark_keeps_atom_parent_without_scene_probe(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A valid mark enters the session scene through its installed atom parent."""
	session = _new_tab(main_window)
	created_marks = []
	original_create_mark = bkchem_qt.canvas.document_projection.create_mark_item
	original_scene = bkchem_qt.canvas.items.mark_item.MarkItem.scene

	def remember_mark(model: object, atom_item: object) -> object:
		"""Capture the one detached mark produced by the prepared projection."""
		item = original_create_mark(model, atom_item)
		if item is not None:
			created_marks.append(item)
		return item

	def fail_mark_scene(self: object) -> object:
		"""Prove installation never probes a child mark's scene ownership."""
		raise AssertionError("mark scene() must not be queried during installation")

	try:
		commit = session.commit_complete_candidate(_MARKED_ATOM_CDML)
		monkeypatch.setattr(
			bkchem_qt.canvas.document_projection, "create_mark_item", remember_mark,
		)
		monkeypatch.setattr(
			bkchem_qt.canvas.items.mark_item.MarkItem, "scene", fail_mark_scene,
		)
		assert session._projection_lifecycle_port.project(commit.snapshot)
		mark = created_marks[0]
		parent = mark.parentItem()
		assert isinstance(parent, bkchem_qt.canvas.items.atom_item.AtomItem)
		assert original_scene(mark) is session.scene
		assert session.backend_projection_synchronized
	finally:
		monkeypatch.undo()
		_close_tab(main_window, session)


#============================================
def test_failed_current_install_retries_only_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An accepted newer revision remains final after projection retirement."""
	session = _new_tab(main_window)
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		assert session.replace_projection_from_backend_snapshot(first.snapshot)
		accepted = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		install = session._install_prepared_projection
		def fail_install(*_args: object) -> None:
			"""Inject one install failure after the live projection retires."""
			raise RuntimeError("install fault")
		monkeypatch.setattr(
			session, "_install_prepared_projection", fail_install,
		)
		assert (
			not session.replace_projection_from_backend_snapshot(accepted.snapshot)
			and session.document is None
			and session.backend_snapshot == accepted.snapshot
		)
		monkeypatch.setattr(session, "_install_prepared_projection", install)
		prepared_snapshots = []
		prepare = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection
		def remember_prepare(projection_snapshot: object, reaper: object) -> object:
			"""Record the exact backend snapshot prepared by explicit recovery."""
			prepared_snapshots.append(projection_snapshot.snapshot)
			return prepare(projection_snapshot, reaper)
		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io, "prepare_synchronized_projection", remember_prepare,
		)
		retry = session.retry_current_backend_projection()
		assert retry.status == "accepted" and prepared_snapshots == [accepted.snapshot]
	finally:
		_close_tab(main_window, session)


#============================================
def test_candidate_cleanup_failure_retains_primary_replacement_diagnostic(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Candidate cleanup cannot hide the post-retirement install failure."""
	session = _new_tab(main_window)
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		assert session.replace_projection_from_backend_snapshot(first.snapshot)
		accepted = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		original_cleanup = session._dispose_prepared_projection

		def fail_install(*_args: object) -> None:
			"""Fail after the current projection has become terminally retired."""
			raise RuntimeError("primary installation failure")

		def cleanup_then_fail(candidate: object) -> None:
			"""Complete candidate retirement, then report its independent fault."""
			original_cleanup(candidate)
			raise RuntimeError("candidate cleanup failure")

		monkeypatch.setattr(session, "_install_prepared_projection", fail_install)
		monkeypatch.setattr(session, "_dispose_prepared_projection", cleanup_then_fail)
		result = session.replace_projection_from_backend_snapshot(accepted.snapshot)
		assert (
			result.status == "installation-failed"
			and result.phase == "installation"
			and session.document is None
			and not session.backend_projection_synchronized
			and not session._projection_replacing
			and session.projection_error is result.diagnostic
			and isinstance(session.projection_error.__cause__, RuntimeError)
			and str(session.projection_error.__cause__) == "primary installation failure"
			and any(
				str(diagnostic) == "candidate cleanup failure"
				for diagnostic in session._teardown_diagnostics
			)
		)
	finally:
		monkeypatch.undo()
		_close_tab(main_window, session)


#============================================
def test_preparation_unavailable_keeps_only_view_aliases_bound(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A stale displayed projection remains view-only after preparation fails."""
	session = _new_tab(main_window)
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		assert session._projection_lifecycle_port.project(first.snapshot)
		old_document = session.document
		assert main_window._document_signal_source is old_document
		accepted = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)

		def fail_prepare(*_args: object) -> object:
			"""Reject preparation without retiring the existing view-only document."""
			raise RuntimeError("preparation fault")

		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io, "prepare_synchronized_projection", fail_prepare,
		)
		result = session._projection_lifecycle_port.project(accepted.snapshot)
		assert (
			result.status == "preparation-unavailable"
			and session.document is old_document
			and main_window.document is old_document
			and main_window._document_signal_source is None
			and main_window._property_dock._document is None
			and not session.backend_projection_synchronized
			and not session.can_commit_persistent_action
		)
	finally:
		monkeypatch.undo()
		_close_tab(main_window, session)


#============================================
def test_stale_session_port_is_inert_and_cannot_retarget_active_aliases(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained foreign port cannot change the active tab or its dock aliases."""
	foreign = main_window.sessions[0]
	active = _new_tab(main_window)
	try:
		port = foreign._projection_lifecycle_port
		result = port.project(foreign.backend_snapshot)
		assert result.installed and main_window.document is active.document
		aliases = (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
		foreign.clear_projection_lifecycle_port()
		assert port.project(foreign.backend_snapshot).status == "session-unavailable"
		assert aliases == (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
	finally:
		_close_tab(main_window, active)


#============================================
def test_delivery_that_clears_its_port_cannot_emit_a_stale_notice(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A synchronous delivery disposal leaves every active alias and dock inert."""
	foreign = main_window.sessions[0]
	active = _new_tab(main_window)
	notices = []
	try:
		def clear_port(_snapshot: object) -> object:
			"""Invalidate this delivery seam while returning a computed result."""
			foreign.clear_projection_lifecycle_port()
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLED,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.COMPLETE,
			)

		port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
			foreign, clear_port,
			lambda _session, result: notices.append(result),
		)
		foreign.install_projection_lifecycle_port(port)
		aliases = (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
		result = port.project(foreign.backend_snapshot)
		assert result.installed and notices == []
		assert aliases == (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
	finally:
		_close_tab(main_window, active)
