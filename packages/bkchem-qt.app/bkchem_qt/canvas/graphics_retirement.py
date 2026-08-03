"""Qt-side ownership protocol for retiring graphics projections.

The backend never sees these objects.  This module centralizes the narrow
native-wrapper boundary used while a live Qt projection is discarded, so a
caller identifies its roots instead of inferring ownership from a potentially
retired ``QGraphicsItem``.
"""

# PIP3 modules
import dataclasses

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import shiboken6


#============================================
def is_valid_native_wrapper(item: object) -> bool:
	"""Return whether a PySide/Shiboken wrapper may cross one native boundary."""
	# Shiboken reports ``None`` as valid, but it is the normal terminal parent
	# sentinel rather than a wrapper that may receive native method calls.
	if item is None:
		return False
	try:
		return shiboken6.isValid(item)
	except TypeError:
		return False


#============================================
def native_scene_for_item(
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> PySide6.QtWidgets.QGraphicsScene | None:
	"""Return an item's live scene without entering C++ through a stale wrapper."""
	if not is_valid_native_wrapper(item):
		return None
	scene = item.scene()
	return scene if is_valid_native_wrapper(scene) else None


#============================================
def native_parent_for_item(
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> PySide6.QtWidgets.QGraphicsItem | None:
	"""Return an item's live parent without traversing an invalid wrapper."""
	if not is_valid_native_wrapper(item):
		return None
	parent = item.parentItem()
	return parent if parent is None or is_valid_native_wrapper(parent) else None


#============================================
def selected_items_from_captured_scene(
		scene: PySide6.QtWidgets.QGraphicsScene | None,
		) -> list[PySide6.QtWidgets.QGraphicsItem]:
	"""Return selected items only from one still-live scene wrapper.

	Selection is a native call. A retired scene therefore has no observable
	selection, rather than a later caller entering C++ through its stale wrapper.
	"""
	if not is_valid_native_wrapper(scene):
		return []
	return list(scene.selectedItems())


#============================================
def item_belongs_to_scene(
		scene: PySide6.QtWidgets.QGraphicsScene,
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> bool:
	"""Return whether a live item still belongs to one captured live scene."""
	return is_valid_native_wrapper(scene) and native_scene_for_item(item) is scene


#============================================
def remove_item_from_captured_scene(
		scene: PySide6.QtWidgets.QGraphicsScene,
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> bool:
	"""Remove one live item only when it still belongs to its captured scene."""
	if not item_belongs_to_scene(scene, item):
		return False
	scene.removeItem(item)
	return True


#============================================
def add_item_to_captured_scene(
		scene: PySide6.QtWidgets.QGraphicsScene,
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> bool:
	"""Attach one detached live item to its captured scene without stealing it."""
	if not can_add_item_to_captured_scene(scene, item):
		return False
	item_scene = native_scene_for_item(item)
	if item_scene is scene:
		return True
	scene.addItem(item)
	return True


#============================================
def can_add_item_to_captured_scene(
		scene: PySide6.QtWidgets.QGraphicsScene,
		item: PySide6.QtWidgets.QGraphicsItem,
		) -> bool:
	"""Return whether a live item may join its captured scene without reassignment."""
	if not is_valid_native_wrapper(scene) or not is_valid_native_wrapper(item):
		return False
	item_scene = native_scene_for_item(item)
	return item_scene is None or item_scene is scene


#============================================
def set_item_parent_in_captured_scene(
		item: PySide6.QtWidgets.QGraphicsItem,
		parent: PySide6.QtWidgets.QGraphicsItem | None,
		scene: PySide6.QtWidgets.QGraphicsScene | None = None,
		) -> bool:
	"""Set a live item's parent only inside its captured graphics ownership tree."""
	if not is_valid_native_wrapper(item):
		return False
	if parent is not None and not is_valid_native_wrapper(parent):
		return False
	if scene is not None:
		if not is_valid_native_wrapper(scene):
			return False
		if parent is not None and native_scene_for_item(parent) is not scene:
			return False
		item_scene = native_scene_for_item(item)
		if item_scene is not None and item_scene is not scene:
			return False
	item.setParentItem(parent)
	return True


#============================================
@dataclasses.dataclass
class GraphicsRetirementReport:
	"""Observable result of one graphics retirement transition."""

	retired_item_count: int = 0
	already_retired_count: int = 0
	callback_errors: list[BaseException] = dataclasses.field(default_factory=list)

	#============================================
	@property
	def completed(self) -> bool:
		"""Return whether every live callback completed without a Python error."""
		return not self.callback_errors


#============================================
@dataclasses.dataclass
class RetainedDetachedGraphics:
	"""Detached roots retained after an explicit native-retirement failure.

	The record owns only wrappers that were already detached from their scene and
	parent tree.  Its long-lived reaper owner selects when a controlled terminal
	resolution is attempted; each attempt checks wrapper validity immediately
	before the sole native deletion boundary.
	"""

	roots: list[PySide6.QtWidgets.QGraphicsItem]
	diagnostics: list[BaseException]

	#============================================
	@property
	def unresolved(self) -> bool:
		"""Return whether the record still owns a detached graphics sentinel."""
		return bool(self.roots)


#============================================
@dataclasses.dataclass
class RetainedSceneProjectionGraphics:
	"""Own roots whose known scene removal reported a native failure.

	Unlike :class:`RetainedDetachedGraphics`, these roots may still be owned by
	a live scene.  The record therefore retains that scene as well as the roots
	until the reaper can repeat the scene-to-detached transition deliberately.
	It never guesses that a failed ``removeItem`` detached a root.
	"""

	scene: PySide6.QtWidgets.QGraphicsScene | None
	roots: list[PySide6.QtWidgets.QGraphicsItem]
	diagnostics: list[BaseException]

	#============================================
	@property
	def unresolved(self) -> bool:
		"""Return whether this record still owns a scene or graphics root."""
		return self.scene is not None or bool(self.roots)


#============================================
@dataclasses.dataclass
class RetainedGraphicsRecords:
	"""One explicit handoff bundle for every unresolved terminal graphic.

	A session transfers this bundle to its MainWindow only after the session has
	queued its QObject roots.  Keeping both native-deletion and scene-transition
	records together prevents a failed scene removal from becoming an ownerless
	process-level fallback during ordinary tab close.
	"""

	detached: RetainedDetachedGraphics | None = None
	scene_projections: list[RetainedSceneProjectionGraphics] = dataclasses.field(
		default_factory=list,
	)

	#============================================
	@property
	def unresolved(self) -> bool:
		"""Return whether this aggregate retains any native graphics ownership."""
		return (
			(self.detached is not None and self.detached.unresolved)
			or any(record.unresolved for record in self.scene_projections)
		)


#============================================
class DetachedGraphicsRetirementReaper:
	"""Own failed terminal graphics deletion until a controlled retry.

	A caller gives this reaper a defined lifetime: a session owns replacement
	failures while it remains live, while the process-level instance owns only
	detached projections that have no session owner.  It deliberately does not
	infer a retry from Python garbage collection.
	"""

	#============================================
	def __init__(self) -> None:
		"""Initialize the explicit terminal graphics ownership records."""
		self._pending: list[RetainedDetachedGraphics] = []
		self._pending_scene_projections: list[RetainedSceneProjectionGraphics] = []

	#============================================
	def retain(self, record: RetainedDetachedGraphics | None) -> None:
		"""Transfer one failed terminal deletion record into reaper ownership."""
		if record is not None and record.unresolved:
			self._pending.append(record)
			if PySide6.QtCore.QCoreApplication.instance() is not None:
				PySide6.QtCore.QTimer.singleShot(0, self.drain)

	#============================================
	def retain_scene_projection(
			self, record: RetainedSceneProjectionGraphics | None,
			) -> None:
		"""Transfer a failed live-scene transition into explicit reaper ownership."""
		if record is not None and record.unresolved:
			self._pending_scene_projections.append(record)
			if PySide6.QtCore.QCoreApplication.instance() is not None:
				PySide6.QtCore.QTimer.singleShot(0, self.drain)

	#============================================
	def drain(self) -> None:
		"""Retry explicit scene and detached transitions at a safe boundary."""
		for record in list(self._pending_scene_projections):
			coordinator = GraphicsRetirementCoordinator()
			coordinator.resolve_retained_scene_projection_graphics(record, self)
			if not record.unresolved:
				self._pending_scene_projections.remove(record)
		for record in list(self._pending):
			coordinator = GraphicsRetirementCoordinator()
			coordinator.resolve_retained_detached_graphics(record)
			if not record.unresolved:
				self._pending.remove(record)

	#============================================
	def owns_detached_root(self, item: PySide6.QtWidgets.QGraphicsItem) -> bool:
		"""Return whether the reaper remains the explicit owner of ``item``."""
		return any(
			item is root for record in self._pending for root in record.roots
		)

	#============================================
	def owns_scene_projection_root(
			self, item: PySide6.QtWidgets.QGraphicsItem,
			) -> bool:
		"""Return whether a failed scene transition still explicitly owns ``item``."""
		return any(
			item is root
			for record in self._pending_scene_projections
			for root in record.roots
		)

	#============================================
	@property
	def has_retained_graphics(self) -> bool:
		"""Return whether this reaper still owns any unresolved terminal record."""
		return bool(self._pending or self._pending_scene_projections)

	#============================================
	def take_retained_detached_graphics(self) -> RetainedDetachedGraphics | None:
		"""Transfer every unresolved record to the caller's next explicit owner."""
		if not self._pending:
			return None
		roots = []
		diagnostics = []
		for record in self._pending:
			roots.extend(record.roots)
			diagnostics.extend(record.diagnostics)
		self._pending.clear()
		return RetainedDetachedGraphics(roots, diagnostics)

	#============================================
	def take_retained_graphics_records(self) -> RetainedGraphicsRecords:
		"""Transfer every record type as one explicit terminal ownership bundle."""
		return RetainedGraphicsRecords(
			detached=self.take_retained_detached_graphics(),
			scene_projections=list(self._take_retained_scene_projections()),
		)

	#============================================
	def retain_graphics_records(self, records: RetainedGraphicsRecords) -> None:
		"""Adopt one explicit aggregate from a session or terminal window owner."""
		self.retain(records.detached)
		for record in records.scene_projections:
			self.retain_scene_projection(record)

	#============================================
	def _take_retained_scene_projections(self) -> list[RetainedSceneProjectionGraphics]:
		"""Transfer scene-transition records without converting their ownership."""
		records = self._pending_scene_projections
		self._pending_scene_projections = []
		return records


#============================================
@dataclasses.dataclass
class TemporarySceneRetirement:
	"""Own one export-only scene until Qt confirms its terminal deletion.

	The record is intentionally frontend-only.  The temporary-scene reaper
	keeps it alive after an export returns so a failed detached root or deferred
	scene deletion cannot fall through to Python finalization.  It relies on a
	live Qt event loop to deliver ``deleteLater``; force termination and Python
	interpreter finalization remain outside this graceful ownership protocol.
	"""

	scene: PySide6.QtWidgets.QGraphicsScene | None
	scene_items: list[PySide6.QtWidgets.QGraphicsItem]
	detached_items: list[PySide6.QtWidgets.QGraphicsItem]
	retained_detached_graphics: RetainedDetachedGraphics | None = None
	diagnostics: list[BaseException] = dataclasses.field(default_factory=list)
	contents_retired: bool = False
	delete_requested: bool = False

	#============================================
	@property
	def resolved(self) -> bool:
		"""Return whether this record owns no live native graphics wrappers."""
		roots_resolved = (
			self.retained_detached_graphics is None
			or not self.retained_detached_graphics.unresolved
		)
		return self.scene is None and roots_resolved


#============================================
class TemporarySceneRetirementReaper:
	"""Retain temporary export scenes until ordinary Qt event delivery resolves them."""

	#============================================
	def __init__(self) -> None:
		"""Initialize the frontend-only pending retirement records."""
		self._pending: list[TemporarySceneRetirement] = []

	#============================================
	def retire(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			scene_items: list[PySide6.QtWidgets.QGraphicsItem],
			detached_items: list[PySide6.QtWidgets.QGraphicsItem],
			) -> TemporarySceneRetirement:
		"""Start one temporary-scene retirement and retain its terminal record."""
		record = TemporarySceneRetirement(scene, scene_items, detached_items)
		self._pending.append(record)
		self._advance(record)
		return record

	#============================================
	def drain(self) -> None:
		"""Deliver queued deletes and resolve retained roots through the coordinator."""
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		for record in list(self._pending):
			self._advance(record)
			if record.resolved:
				self._pending.remove(record)

	#============================================
	def owns_detached_root(self, item: PySide6.QtWidgets.QGraphicsItem) -> bool:
		"""Return whether a pending record retains ``item`` after a native failure."""
		for record in self._pending:
			retained = record.retained_detached_graphics
			if retained is not None and item in retained.roots:
				return True
		return False

	#============================================
	def _advance(self, record: TemporarySceneRetirement) -> None:
		"""Advance one record without dropping an unresolved native wrapper."""
		if not record.contents_retired:
			coordinator = GraphicsRetirementCoordinator()
			try:
				coordinator.retire_temporary_scene(
					record.scene, record.scene_items, record.detached_items,
				)
			except RuntimeError as exc:
				record.diagnostics.append(exc)
			else:
				record.contents_retired = True
				record.detached_items = []
				record.scene_items = []
			retained = coordinator.take_retained_detached_graphics()
			if retained is not None:
				record.retained_detached_graphics = retained
				record.diagnostics.extend(retained.diagnostics)
			if coordinator.report.callback_errors:
				record.diagnostics.extend(coordinator.report.callback_errors)

		retained = record.retained_detached_graphics
		if retained is not None and retained.unresolved:
			coordinator = GraphicsRetirementCoordinator()
			coordinator.resolve_retained_detached_graphics(retained)
			if coordinator.report.callback_errors:
				record.diagnostics.extend(coordinator.report.callback_errors)

		scene = record.scene
		if scene is None:
			return
		if not is_valid_native_wrapper(scene):
			record.scene = None
			return
		if record.contents_retired and not record.delete_requested:
			if not is_valid_native_wrapper(scene):
				record.scene = None
				return
			scene.deleteLater()
			record.delete_requested = True


# The reaper is intentionally process-local: it keeps only temporary frontend
# projection wrappers and releases them on the next ordinary Qt event delivery.
temporary_scene_retirement_reaper = TemporarySceneRetirementReaper()


# Failed terminal replacement/preparation roots have no retained document or
# scene owner.  Keep that exceptional ownership explicit until normal Qt event
# delivery reaches a controlled retry boundary.
detached_graphics_retirement_reaper = DetachedGraphicsRetirementReaper()


#============================================
class GraphicsRetirementCoordinator:
	"""Retire one Qt graphics ownership domain in an explicit order.

	A coordinator receives either an explicitly live scene or roots already
	known to be detached.  It checks ``shiboken6.isValid`` immediately before
	each C++ boundary and never asks an item which scene owns it after retirement
	may have begun.  Scene contents remain scene-owned until the scene performs
	its established terminal clear; detached trees are unparented children first.
	"""

	#============================================
	def __init__(self) -> None:
		"""Initialize the per-transition report and retained detached roots."""
		self.report = GraphicsRetirementReport()
		self.retained_detached_roots: list[PySide6.QtWidgets.QGraphicsItem] = []

	#============================================
	def prepare_scene_retirement(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			undo_stack: PySide6.QtGui.QUndoStack | None = None,
			destroy_detached_undo_items: bool = False,
			reaper: DetachedGraphicsRetirementReaper | None = None,
			) -> GraphicsRetirementReport:
		"""Detach callbacks before ``scene.dispose_contents`` clears one graph.

		Failed terminal retirement of an undo-retained detached root transfers to
		``reaper`` before a subsequent history-clear scan.  That transfer makes
		the reaper the root's sole terminal owner until controlled resolution.
		"""
		items = self._live_scene_items(scene)
		self._dispose_callbacks(items)
		if undo_stack is not None:
			self.dispose_undo_stack_graphics(
				undo_stack, {id(item) for item in items}, destroy_detached_undo_items,
			)
			if destroy_detached_undo_items:
				self._transfer_retained_detached_graphics(reaper)
		return self.report

	#============================================
	def detach_scene_items_for_undo(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			items: list[PySide6.QtWidgets.QGraphicsItem],
			undo_stack: PySide6.QtGui.QUndoStack | None = None,
			) -> GraphicsRetirementReport:
		"""Detach roots whose undo command remains their live future owner.

		This is the only nonterminal scene-removal path.  It releases callbacks
		and scene ownership while deliberately retaining native wrappers for a
		future undo/redo command.  Terminal projection disposal uses
		:meth:`retire_scene_projection_items` instead.
		"""
		ordered = self._child_first_unique(items)
		self._dispose_callbacks(ordered)
		if undo_stack is not None:
			self.dispose_undo_stack_graphics(undo_stack, {id(item) for item in ordered})
		for root in self._roots(ordered):
			if self._is_live(root):
				self._remove_scene_root(scene, root)
		self._detach_parent_links(ordered)
		return self.report

	#============================================
	def retire_scene_projection_items(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			items: list[PySide6.QtWidgets.QGraphicsItem],
			undo_stack: PySide6.QtGui.QUndoStack | None = None,
			reaper: DetachedGraphicsRetirementReaper | None = None,
			) -> GraphicsRetirementReport:
		"""Terminally retire named projection trees from one known live scene.

		The caller identifies the still-live scene and roots before retirement.
		The coordinator snapshots every child, disconnects callbacks, removes
		known roots, unparents children first, and explicitly deletes children
		before parents.  Failed native deletions transfer to ``reaper`` (or the
		process reaper) rather than falling through to Python finalization.
		"""
		ordered = self._child_first_unique(items)
		if not self._is_live(scene):
			# A deleted scene cannot retain a still-live graphics item.  Crossing the
			# detached-root boundary here avoids invoking ``removeItem`` on a stale
			# Shiboken wrapper and gives every surviving root an explicit owner.
			self._dispose_callbacks(ordered)
			if undo_stack is not None:
				self.dispose_undo_stack_graphics(
					undo_stack, {id(item) for item in ordered}, True,
				)
			self._detach_parent_links(ordered, destroy=True)
			self._transfer_retained_detached_graphics(reaper)
			return self.report

		self._dispose_callbacks(ordered)
		if undo_stack is not None:
			self.dispose_undo_stack_graphics(
				undo_stack, {id(item) for item in ordered}, True,
			)
		roots = self._roots(ordered)
		for root in roots:
			if not self._is_live(root):
				continue
			try:
				self._remove_scene_root(scene, root)
			except RuntimeError as exc:
				# The failure leaves scene ownership ambiguous.  Retain the complete
				# root set with the scene so a controlled retry can remove every root
				# before any parent-link or native-deletion call is made.
				self.report.callback_errors.append(exc)
				self._transfer_retained_scene_projection_graphics(
					scene, roots, reaper,
				)
				return self.report
		self._detach_parent_links(ordered, destroy=True)
		self._transfer_retained_detached_graphics(reaper)
		return self.report

	#============================================
	def retire_detached_projection_items(
			self, items: list[PySide6.QtWidgets.QGraphicsItem],
			reaper: DetachedGraphicsRetirementReaper | None = None,
			) -> GraphicsRetirementReport:
		"""Terminally retire detached projection trees in child-first order."""
		ordered = self._child_first_unique(items)
		self._dispose_callbacks(ordered)
		self._detach_parent_links(ordered, destroy=True)
		self._transfer_retained_detached_graphics(reaper)
		return self.report

	#============================================
	def retire_temporary_scene(
			self, scene: PySide6.QtWidgets.QGraphicsScene | None,
			scene_items: list[PySide6.QtWidgets.QGraphicsItem],
			detached_items: list[PySide6.QtWidgets.QGraphicsItem],
			) -> GraphicsRetirementReport:
		"""Retire a known export scene and explicit detached roots in one protocol."""
		if scene is None or not self._is_live(scene):
			raise RuntimeError("Cannot retire an invalid temporary scene wrapper")
		# Explicitly supplied roots leave the scene before native deletion.  This
		# preserves child-before-parent ordering for atom-attached presentation
		# items instead of asking QGraphicsScene.clear() to destroy that mixed tree.
		# Temporary scene retirement retains any failed native deletion in its
		# own long-lived record, so this coordinator must keep failures until the
		# caller transfers them below.
		self._retire_scene_items(scene, scene_items)
		self._retire_detached_items(detached_items)
		# The fully tracked export tree has crossed this coordinator's explicit
		# child-before-parent deletion boundary.  The now-empty scene therefore has
		# no second content owner: its reaper queues only QObject deletion.
		return self.report

	#============================================
	def dispose_undo_stack_graphics(
			self, undo_stack: PySide6.QtGui.QUndoStack, seen: set[int] | None = None,
			destroy_detached_items: bool = False,
			) -> GraphicsRetirementReport:
		"""Disconnect command-retained graphics without inferring scene ownership."""
		known = seen if seen is not None else set()
		for index in range(undo_stack.count()):
			self._dispose_command_graphics(
				undo_stack.command(index), known, destroy_detached_items,
			)
		return self.report

	#============================================
	def raise_if_callback_failed(self, context: str) -> None:
		"""Surface a callback diagnostic after every independent root was visited."""
		if self.report.callback_errors:
			raise RuntimeError(context) from self.report.callback_errors[0]

	#============================================
	def take_retained_detached_graphics(self) -> RetainedDetachedGraphics | None:
		"""Transfer failed detached roots to the session-owned terminal record."""
		if not self.retained_detached_roots:
			return None
		record = RetainedDetachedGraphics(
			roots=self.retained_detached_roots,
			diagnostics=list(self.report.callback_errors),
		)
		self.retained_detached_roots = []
		return record

	#============================================
	def _transfer_retained_detached_graphics(
			self, reaper: DetachedGraphicsRetirementReaper | None,
			) -> None:
		"""Move native-deletion failures to a long-lived frontend owner."""
		record = self.take_retained_detached_graphics()
		if record is None:
			return
		target_reaper = (
			detached_graphics_retirement_reaper
			if reaper is None else reaper
		)
		target_reaper.retain(record)

	#============================================
	def _transfer_retained_scene_projection_graphics(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			roots: list[PySide6.QtWidgets.QGraphicsItem],
			reaper: DetachedGraphicsRetirementReaper | None,
			) -> None:
		"""Retain an incomplete scene-to-detached transition before surfacing it."""
		target_reaper = (
			detached_graphics_retirement_reaper
			if reaper is None else reaper
		)
		target_reaper.retain_scene_projection(
			RetainedSceneProjectionGraphics(
				scene=scene,
				roots=list(roots),
				diagnostics=list(self.report.callback_errors),
			),
		)

	#============================================
	def resolve_retained_detached_graphics(
			self, retained: RetainedDetachedGraphics,
			) -> GraphicsRetirementReport:
		"""Attempt one reaper-owned terminal resolution of detached roots.

		A stale wrapper is released from the Python sentinel list without any C++
		call.  A still-live wrapper crosses only the explicit deletion boundary.
		The caller keeps the record if that boundary reports another failure.
		"""
		unresolved = []
		for item in retained.roots:
			if not self._is_live(item):
				continue
			try:
				shiboken6.delete(item)
			except RuntimeError as exc:
				unresolved.append(item)
				retained.diagnostics.append(exc)
				self.report.callback_errors.append(exc)
		retained.roots = unresolved
		return self.report

	#============================================
	def resolve_retained_scene_projection_graphics(
			self, retained: RetainedSceneProjectionGraphics,
			reaper: DetachedGraphicsRetirementReaper,
			) -> GraphicsRetirementReport:
		"""Retry one reaper-owned scene transition without guessing ownership.

		An invalid retained scene proves that it can no longer own live graphics
		items.  Remaining valid roots then enter the ordinary detached-root
		boundary.  A valid scene retries all original roots together, so a prior
		partial ``removeItem`` result cannot split ownership across transitions.
		"""
		scene = retained.scene
		if scene is None or not self._is_live(scene):
			retained.scene = None
			self._retire_detached_items(retained.roots)
			failed_detached = self.take_retained_detached_graphics()
			if failed_detached is not None:
				reaper.retain(failed_detached)
			retained.diagnostics.extend(self.report.callback_errors)
			retained.roots = []
			return self.report

		ordered = self._child_first_unique(retained.roots)
		roots = self._roots(ordered)
		for root in roots:
			if not self._is_live(root):
				continue
			try:
				self._remove_scene_root(scene, root)
			except RuntimeError as exc:
				self.report.callback_errors.append(exc)
				retained.diagnostics.append(exc)
				return self.report
		self._detach_parent_links(ordered, destroy=True)
		failed_detached = self.take_retained_detached_graphics()
		if failed_detached is not None:
			reaper.retain(failed_detached)
		retained.diagnostics.extend(self.report.callback_errors)
		retained.scene = None
		retained.roots = []
		return self.report

	#============================================
	def _live_scene_items(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			) -> list[PySide6.QtWidgets.QGraphicsItem]:
		"""Snapshot one known live scene before its terminal ownership transfer."""
		if not self._is_live(scene):
			raise RuntimeError("Cannot retire graphics from an invalid scene wrapper")
		return self._child_first_unique(list(scene.items()))

	#============================================
	def _dispose_command_graphics(
			self, command: PySide6.QtGui.QUndoCommand, seen: set[int],
			destroy_detached_items: bool,
			) -> None:
		"""Visit command graphics and macro children through this coordinator."""
		items = getattr(command, "graphics_items", None)
		if callable(items):
			fresh_items = []
			for item in items():
				if id(item) not in seen:
					seen.add(id(item))
					fresh_items.append(item)
			ordered = self._child_first_unique(fresh_items)
			self._dispose_callbacks(ordered)
			self._detach_parent_links(ordered, destroy=destroy_detached_items)
		for index in range(command.childCount()):
			self._dispose_command_graphics(
				command.child(index), seen, destroy_detached_items,
			)

	#============================================
	def _dispose_callbacks(
			self, items: list[PySide6.QtWidgets.QGraphicsItem],
			) -> None:
		"""Disconnect callbacks while each wrapper is known valid."""
		from bkchem_qt.canvas.document_projection import dispose_item_callbacks
		for item in items:
			if not self._is_live(item):
				continue
			try:
				dispose_item_callbacks(item)
			except Exception as exc:
				self.report.callback_errors.append(exc)
			finally:
				self.report.retired_item_count += 1

	#============================================
	def _detach_parent_links(
			self, ordered: list[PySide6.QtWidgets.QGraphicsItem],
			destroy: bool = False,
			) -> None:
		"""Unparent and, when owned here, retire graphics child before parent."""
		for item in ordered:
			if self._is_live(item):
				item.setParentItem(None)
		if not destroy:
			return
		for item in ordered:
			if not self._is_live(item):
				continue
			try:
				shiboken6.delete(item)
			except RuntimeError as exc:
				# Retain the valid root for the controlled owner rather than allowing
				# Python finalization to make an unresolved native transition implicit.
				self.retained_detached_roots.append(item)
				self.report.callback_errors.append(exc)

	#============================================
	def _retire_scene_items(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			items: list[PySide6.QtWidgets.QGraphicsItem],
			) -> None:
		"""Retire scene-owned roots while retaining failures on this coordinator."""
		ordered = self._child_first_unique(items)
		self._dispose_callbacks(ordered)
		for root in self._roots(ordered):
			if self._is_live(root):
				self._remove_scene_root(scene, root)
		self._detach_parent_links(ordered, destroy=True)

	#============================================
	def _remove_scene_root(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			root: PySide6.QtWidgets.QGraphicsItem,
			) -> None:
		"""Remove one validated root through the only scene-removal boundary."""
		if not self._is_live(scene):
			raise RuntimeError("Cannot remove graphics from an invalid scene wrapper")
		if not self._is_live(root):
			raise RuntimeError("Cannot remove an invalid graphics root wrapper")
		scene.removeItem(root)

	#============================================
	def _retire_detached_items(
			self, items: list[PySide6.QtWidgets.QGraphicsItem],
			) -> None:
		"""Retire detached roots while retaining failures on this coordinator."""
		ordered = self._child_first_unique(items)
		self._dispose_callbacks(ordered)
		self._detach_parent_links(ordered, destroy=True)

	#============================================
	def _child_first_unique(
			self, items: list[PySide6.QtWidgets.QGraphicsItem],
			) -> list[PySide6.QtWidgets.QGraphicsItem]:
		"""Snapshot supplied graphics trees deepest-child first while wrappers live."""
		ordered = []
		seen = set()

		#============================================
		def visit(item: PySide6.QtWidgets.QGraphicsItem) -> None:
			"""Record every currently live child before its parent changes owner."""
			key = id(item)
			if key in seen:
				return
			seen.add(key)
			if not self._is_live(item):
				return
			for child in list(item.childItems()):
				visit(child)
			ordered.append(item)

		for item in items:
			visit(item)
		return ordered

	#============================================
	def _roots(
			self, ordered: list[PySide6.QtWidgets.QGraphicsItem],
			) -> list[PySide6.QtWidgets.QGraphicsItem]:
		"""Return the supplied tree roots while all wrappers are still checked."""
		item_ids = {id(item) for item in ordered}
		roots = []
		for item in ordered:
			if not self._is_live(item):
				continue
			parent = item.parentItem()
			if parent is None or id(parent) not in item_ids:
				roots.append(item)
		return roots

	#============================================
	def _is_live(self, item: object) -> bool:
		"""Check a PySide native wrapper immediately before a C++ method call."""
		try:
			valid = is_valid_native_wrapper(item)
		except TypeError:
			valid = False
		if not valid:
			self.report.already_retired_count += 1
		return valid
