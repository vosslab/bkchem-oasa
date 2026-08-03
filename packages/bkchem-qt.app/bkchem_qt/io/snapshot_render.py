"""Qt-only rendering of immutable backend CDML snapshot requests.

This adapter intentionally reconstructs a disposable scene from complete CDML.
It never reads the retained document scene after request capture.
"""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtSvg
import PySide6.QtWidgets

# local repo modules
import oasa.cdml_render
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.io.cdml_document_io
import bkchem_qt.io.render_plan


#============================================
class _SnapshotProjectionCleanupError(RuntimeError):
	"""Retain every independent terminal-owner diagnostic from one projection."""

	#============================================
	def __init__(self, errors: list[BaseException]) -> None:
		"""Expose the collected ownership failures to the typed result adapter."""
		super().__init__("Snapshot render projection cleanup failed")
		self.errors = tuple(errors)


@dataclasses.dataclass
class _SnapshotProjection:
	"""Temporary scene and decoded document owned by one render invocation."""

	scene: PySide6.QtWidgets.QGraphicsScene
	prepared: bkchem_qt.io.cdml_document_io.PreparedProjection
	items: list[object]
	_disposed: bool = False

	#============================================
	def dispose(self) -> None:
		"""Retire installed roots first, then sever decoded model ownership."""
		if self._disposed:
			return
		self._disposed = True
		errors = []
		try:
			# Snapshot actual scene roots before any retirement begins.  ``items``
			# is construction bookkeeping and can omit children installed below an
			# atom; the terminal scene protocol owns the complete native tree.
			scene_items = list(self.scene.items())
			# The temporary scene may be queued for deferred deletion during drain.
			# Its decoded Document must stop referring to that wrapper before the
			# event boundary, then prepared cleanup can retire only uninstalled
			# graphics and release model callbacks.
			self.prepared.document.set_scene(None)
			record = bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.retire(
				self.scene, scene_items, [],
			)
			bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()
		except Exception as exc:
			errors.append(exc)
		else:
			errors.extend(record.diagnostics)
		try:
			bkchem_qt.io.cdml_document_io.dispose_prepared_projection(self.prepared)
		except Exception as exc:
			errors.append(exc)
		if errors:
			raise _SnapshotProjectionCleanupError(errors) from errors[0]


#============================================
class _ProjectionConstructionError(RuntimeError):
	"""Keep a projection-construction fault distinct from its cleanup fault."""

	#============================================
	def __init__(self, primary_error: Exception, cleanup_error: Exception) -> None:
		"""Record both terminal diagnostics for the render-result adapter."""
		super().__init__(str(primary_error))
		self.primary_error = primary_error
		self.cleanup_error = cleanup_error


#============================================
def _warning_values(
		prepared: bkchem_qt.io.cdml_document_io.PreparedProjection,
		) -> tuple[oasa.cdml_render.CDMLRenderWarning, ...]:
	"""Expose retained unsupported CDML as explicit visual-coverage warnings."""
	warnings = []
	for content in prepared.document.unsupported_content:
		warnings.append(oasa.cdml_render.CDMLRenderWarning(
			"unsupported-persistent-object", content.path, content.object_id,
			"%s: %s" % (content.tag, content.reason),
		))
	return tuple(warnings)


#============================================
def _selected_molecule_ids(
		prepared: bkchem_qt.io.cdml_document_io.PreparedProjection,
		keys: tuple[oasa.cdml_render.CDMLRenderSelectionKey, ...],
		) -> set[str]:
	"""Resolve atom, bond, and group keys to their snapshot owning molecule."""
	requested = {(key.kind, key.identifier) for key in keys}
	result = set()
	for molecule, _items in prepared.molecule_projections:
		molecule_id = getattr(molecule, "mol_id", None)
		if molecule_id and ("molecule", str(molecule_id)) in requested:
			result.add(str(molecule_id))
			continue
		for atom in molecule.atoms:
			if ("atom", str(getattr(atom, "atom_id", ""))) in requested:
				result.add(str(molecule_id))
		for bond in molecule.bonds:
			if ("bond", str(getattr(bond, "bond_id", ""))) in requested:
				result.add(str(molecule_id))
		for group in molecule.groups:
			if ("group", str(getattr(group, "group_id", ""))) in requested:
				result.add(str(molecule_id))
	return result


#============================================
def _build_projection(
		request: oasa.cdml_render.CDMLRenderRequest,
		) -> tuple[_SnapshotProjection, tuple[oasa.cdml_render.CDMLRenderWarning, ...]]:
	"""Decode one snapshot and install only its requested supported graphics."""
	projection_snapshot = oasa.cdml_document.CDMLDocument.projection_snapshot(
		request.snapshot,
	)
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		projection_snapshot,
	)
	scene = PySide6.QtWidgets.QGraphicsScene()
	items = []
	try:
		attributes = prepared.document.paper.attributes
		scene._paper_attributes = dict(attributes)
		scene._snapshot_paper_rect = _paper_rect(attributes)
		scene.setSceneRect(scene._snapshot_paper_rect)
		prepared.document.set_scene(scene)
		selected_molecule_ids = _selected_molecule_ids(prepared, request.selection_keys)
		selected_presentations = {
			key.identifier for key in request.selection_keys if key.kind == "presentation"
		}
		include_all = request.scope != "selection"
		for molecule, molecule_items in prepared.molecule_projections:
			if include_all or str(getattr(molecule, "mol_id", "")) in selected_molecule_ids:
				for item in molecule_items:
					scene.addItem(item)
					items.append(item)
		for item in prepared.presentation_items:
			identifier = getattr(getattr(item, "document_object_model", None), "object_id", None)
			if include_all or str(identifier) in selected_presentations:
				scene.addItem(item)
				items.append(item)
		included_atoms = {
			item for _molecule, molecule_items in prepared.molecule_projections
			for item in molecule_items if getattr(item, "atom_model", None) is not None
		}
		for atom_item, mark_items in prepared.mark_parent_items:
			if atom_item in included_atoms:
				items.extend(mark_items)
		bkchem_qt.canvas.document_projection.synchronize_document_stack_z_order(
			prepared.document, scene,
		)
		warnings = _warning_values(prepared)
		return _SnapshotProjection(scene, prepared, items), warnings
	except Exception as primary_error:
		projection = _SnapshotProjection(scene, prepared, items)
		try:
			projection.dispose()
		except Exception as cleanup_error:
			raise _ProjectionConstructionError(
				primary_error, cleanup_error,
			) from cleanup_error
		raise


#============================================
def _render_bounds(
		projection: _SnapshotProjection, request: oasa.cdml_render.CDMLRenderRequest,
		) -> bkchem_qt.io.render_plan.RenderPlan:
	"""Derive page or content bounds from the disposable snapshot projection."""
	if request.scope == "selection":
		return bkchem_qt.io.render_plan.build_render_plan(
			projection.scene, request.format_name, 10.0, force_content_crop=True,
		)
	if request.format_name == "svg" and _is_truthy(
		getattr(projection.scene, "_paper_attributes", {}).get("crop_svg", "0"),
	):
		return bkchem_qt.io.render_plan.build_render_plan(
			projection.scene, request.format_name, force_content_crop=True,
		)
	return bkchem_qt.io.render_plan.RenderPlan(
		PySide6.QtCore.QRectF(projection.scene._snapshot_paper_rect), True, False,
	)


#============================================
def _is_truthy(value: object) -> bool:
	"""Return whether one persisted CDML bool attribute is enabled."""
	return str(value).strip().lower() in ("1", "true", "yes", "on")


#============================================
def _paper_rect(attributes: dict[str, str]) -> PySide6.QtCore.QRectF:
	"""Map snapshot paper metadata to a page rectangle without a live ChemScene."""
	sizes = {
		name.lower(): dimensions
		for name, dimensions in bkchem_qt.bridge.oasa_bridge.paper_catalog().items()
		if dimensions is not None
	}
	paper_type = attributes.get("type", "").lower()
	if paper_type == "custom":
		try:
			width_mm = float(str(attributes["size_x"]).removesuffix("mm"))
			height_mm = float(str(attributes["size_y"]).removesuffix("mm"))
		except (KeyError, ValueError):
			width_mm, height_mm = sizes["a4"]
	else:
		width_mm, height_mm = sizes.get(paper_type, sizes["a4"])
	if attributes.get("orientation", "portrait").lower() == "landscape":
		width_mm, height_mm = height_mm, width_mm
	return PySide6.QtCore.QRectF(0, 0, width_mm * 72.0 / 25.4, height_mm * 72.0 / 25.4)


#============================================
def render_request(
		request: oasa.cdml_render.CDMLRenderRequest,
		) -> oasa.cdml_render.CDMLRenderResult | oasa.cdml_render.CDMLRenderFailure:
	"""Render one immutable request to bytes using a disposable Qt projection."""
	if not isinstance(request, oasa.cdml_render.CDMLRenderRequest):
		return oasa.cdml_render.CDMLRenderFailure(
			"invalid-render-request", "Expected an immutable CDML render request",
		)
	projection = None
	result = None
	primary_failure = None
	try:
		projection, warnings = _build_projection(request)
		plan = _render_bounds(projection, request)
		if plan.source_rect.isEmpty():
			result = oasa.cdml_render.CDMLRenderFailure(
				"selection-empty", "Snapshot selection has no supported visual content",
				request.snapshot.revision,
			)
		else:
			artifact = _render_bytes(projection.scene, plan, request.format_name)
			result = oasa.cdml_render.CDMLRenderResult(
				request.snapshot.revision, request.format_name, artifact, warnings=warnings,
			)
	except Exception as exc:
		primary_failure = oasa.cdml_render.CDMLRenderFailure(
			"render-failed", str(exc), request.snapshot.revision,
		)
		if isinstance(exc, _ProjectionConstructionError):
			primary_failure = dataclasses.replace(
				primary_failure,
				diagnostics=(_cleanup_diagnostic(exc.cleanup_error),),
			)
	cleanup_error = None
	if projection is not None:
		try:
			projection.dispose()
		except Exception as exc:
			cleanup_error = exc
	if cleanup_error is not None:
		diagnostic = _cleanup_diagnostic(cleanup_error)
		if primary_failure is not None:
			return dataclasses.replace(
				primary_failure,
				diagnostics=primary_failure.diagnostics + (diagnostic,),
			)
		return oasa.cdml_render.CDMLRenderFailure(
			"render-cleanup-failed",
			"Snapshot render completed but temporary projection cleanup failed",
			request.snapshot.revision, (diagnostic,),
		)
	if primary_failure is not None:
		return primary_failure
	if result is None:
		return oasa.cdml_render.CDMLRenderFailure(
			"render-failed", "Snapshot renderer did not produce an outcome",
			request.snapshot.revision,
		)
	return result


#============================================
def _cleanup_diagnostic(error: BaseException) -> str:
	"""Serialize the terminal ownership diagnostic and its specific cause chain."""
	if isinstance(error, _SnapshotProjectionCleanupError):
		parts = [_cleanup_diagnostic(entry) for entry in error.errors]
		return "Snapshot projection cleanup failed: %s" % " | ".join(parts)
	parts = []
	current_error = error
	while current_error is not None:
		parts.append("%s: %s" % (type(current_error).__name__, current_error))
		cause = current_error.__cause__
		current_error = cause if isinstance(cause, BaseException) else None
	return " <- ".join(parts)


#============================================
def _render_bytes(scene: object, plan: bkchem_qt.io.render_plan.RenderPlan,
		format_name: str) -> bytes:
	"""Render one temporary scene to bytes after selecting a declared format."""
	rect = plan.source_rect
	painter = PySide6.QtGui.QPainter()
	buffer = PySide6.QtCore.QBuffer()
	buffer.open(PySide6.QtCore.QIODevice.OpenModeFlag.WriteOnly)
	try:
		if format_name == "svg":
			generator = PySide6.QtSvg.QSvgGenerator()
			generator.setOutputDevice(buffer)
			generator.setSize(PySide6.QtCore.QSize(int(rect.width()), int(rect.height())))
			generator.setViewBox(rect)
			painter.begin(generator)
			scene.render(painter, PySide6.QtCore.QRectF(), rect)
		elif format_name == "png":
			width, height = max(1, int(rect.width() * 2.0)), max(1, int(rect.height() * 2.0))
			image = PySide6.QtGui.QImage(width, height, PySide6.QtGui.QImage.Format.Format_ARGB32_Premultiplied)
			image.fill(PySide6.QtCore.Qt.GlobalColor.transparent)
			painter.begin(image)
			scene.render(painter, PySide6.QtCore.QRectF(0, 0, width, height), rect)
			painter.end()
			if not image.save(buffer, "PNG"):
				raise RuntimeError("Qt could not encode a PNG render artifact")
		elif format_name == "pdf":
			writer = PySide6.QtGui.QPdfWriter(buffer)
			writer.setPageLayout(PySide6.QtGui.QPageLayout(
				PySide6.QtGui.QPageSize(
					PySide6.QtCore.QSizeF(rect.width(), rect.height()),
					PySide6.QtGui.QPageSize.Unit.Point,
				), PySide6.QtGui.QPageLayout.Orientation.Portrait,
				PySide6.QtCore.QMarginsF(0, 0, 0, 0),
			))
			painter.begin(writer)
			scene.render(painter, PySide6.QtCore.QRectF(0, 0, writer.width(), writer.height()), rect)
		else:
			raise ValueError("Unsupported render format: %s" % format_name)
		if painter.isActive():
			painter.end()
		return bytes(buffer.data())
	finally:
		if painter.isActive():
			painter.end()
		buffer.close()
