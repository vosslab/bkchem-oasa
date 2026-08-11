"""Per-tab ownership and teardown boundary for BKChem Qt documents."""

# Standard Library
import errno
import dataclasses
import math
import numbers
import os
import stat

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.setup.canvas_setup
import bkchem_qt.setup.mode_setup
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.config.drawing_standard_preferences as drawing_standard_preferences
import bkchem_qt.io.cdml_candidate
import bkchem_qt.io.user_template_catalog
import bkchem_qt.models.backend_revision_history
import bkchem_qt.models.document
import bkchem_qt.models.document_header_operations
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.undo.commands
import bkchem_qt.wavy_geometry
import oasa.cdml_document
import oasa.cdml_ftext
import oasa.cdml_molecule_summary
import oasa.cdml_render
import oasa.cdml_standard
import oasa.biomolecule_template_placement
import oasa.template_placement

_ORPHANED_IMPORT_WORKERS: set[PySide6.QtCore.QThread] = set()


#============================================
def orphaned_import_worker_count() -> int:
	"""Return the directly disposed workers awaiting their finished signal."""
	return len(_ORPHANED_IMPORT_WORKERS)


#============================================
def _release_orphaned_import_worker(worker: PySide6.QtCore.QThread) -> None:
	"""Release a directly disposed session's worker after native completion."""
	if worker not in _ORPHANED_IMPORT_WORKERS:
		return
	_ORPHANED_IMPORT_WORKERS.discard(worker)
	relay = getattr(worker, "_result_relay", None)
	if relay is not None:
		try:
			relay.deleteLater()
		except RuntimeError:
			pass
		worker._result_relay = None
	try:
		worker.deleteLater()
	except RuntimeError:
		pass


#============================================
def _adopt_orphaned_import_worker(worker: PySide6.QtCore.QThread) -> None:
	"""Give a directly disposed session's worker an explicit terminal owner.

	The set is established before the connection, so a fast completion cannot
	drop the final strong reference.  The post-connection check covers a worker
	that completed before Qt could queue the slot; release is idempotent.
	"""
	_ORPHANED_IMPORT_WORKERS.add(worker)
	worker.finished.connect(
		lambda worker=worker: _release_orphaned_import_worker(worker),
		PySide6.QtCore.Qt.ConnectionType.QueuedConnection,
	)
	if worker.isFinished():
		_release_orphaned_import_worker(worker)


#============================================
def _freeze_plain_payload(value: object) -> object:
	"""Return one recursively immutable value accepted at the Qt/backend boundary."""
	if value is None or isinstance(value, (bool, int, float, str)):
		return value
	if isinstance(value, tuple):
		frozen = tuple(_freeze_plain_payload(item) for item in value)
		return frozen
	raise TypeError("Persistent operation payload must contain immutable plain data")


#============================================
def _is_unchanged_authoritative_snapshot(
		before: oasa.cdml_document.CDMLSnapshot,
		after: oasa.cdml_document.CDMLSnapshot,
		) -> bool:
	"""Return whether a successful backend operation changed no persistent state.

	The backend owns this decision through its immutable snapshots.  Qt compares
	the complete canonical content, revision, and saved-baseline state instead of
	consulting a projection model, which can be stale or disposable.
	"""
	unchanged = (
		before.revision == after.revision
		and before.cdml == after.cdml
		and before.is_dirty == after.is_dirty
	)
	return unchanged


class BackendProjectionOutOfSyncError(RuntimeError):
	"""Raised when Qt's live projection cannot safely use backend CDML."""


class ProjectionReplacementError(RuntimeError):
	"""Raised when a live Qt projection cannot be recovered from backend CDML."""


class BackendFragmentExtractionError(ValueError):
	"""Expose one typed backend fragment-read failure to Qt-only callers."""


@dataclasses.dataclass(frozen=True)
class PersistentOperationRequest:
	"""Immutable plain-data request for one backend-authoritative operation."""

	operation_key: str
	label: str
	payload: tuple[tuple[str, object], ...]
	target_keys: frozenset[tuple[str, str]] = frozenset()

	#============================================
	def __post_init__(self) -> None:
		"""Validate the request cannot retain mutable frontend or backend objects."""
		if not isinstance(self.operation_key, str) or not isinstance(self.label, str):
			raise TypeError("Persistent operation key and label must be strings")
		payload = tuple(
			(key, _freeze_plain_payload(value)) for key, value in self.payload
		)
		if any(not isinstance(key, str) for key, _value in payload):
			raise TypeError("Persistent operation payload keys must be strings")
		if len({key for key, _value in payload}) != len(payload):
			raise ValueError("Persistent operation payload keys must be unique")
		target_keys = frozenset(self.target_keys)
		if any(
			not isinstance(kind, str) or not isinstance(key, str)
			for kind, key in target_keys
		):
			raise TypeError("Persistent target keys must be durable string pairs")
		object.__setattr__(self, "payload", payload)
		object.__setattr__(self, "target_keys", target_keys)


@dataclasses.dataclass(frozen=True)
class _UserTemplateModeDescriptor:
	"""One Qt-mode projection of a session-owned saved-template record."""

	catalog_key: str
	label: str


#============================================
def _freeze_user_template_catalog(
		entries: object,
		) -> tuple[
		tuple[bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry, ...],
		dict[str, bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry],
		tuple[_UserTemplateModeDescriptor, ...],
		]:
	"""Copy one admitted immutable catalog into session-owned delivery data."""
	if type(entries) is not tuple:
		raise TypeError("User template catalog must be an immutable tuple")
	frozen_entries = []
	for entry in entries:
		if type(entry) is not bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry:
			raise TypeError("User template catalog entries must be admitted catalog records")
		if type(entry.catalog_key) is not str or not entry.catalog_key.strip():
			raise ValueError("User template catalog keys must be nonblank strings")
		if type(entry.label) is not str or not entry.label.strip():
			raise ValueError("User template catalog labels must be nonblank strings")
		if type(entry.template_cdml) is not str or not entry.template_cdml:
			raise ValueError("User template catalog CDML must be nonempty text")
		frozen_entries.append(bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry(
			entry.catalog_key, entry.label, entry.template_cdml,
		))
	if len({entry.catalog_key for entry in frozen_entries}) != len(frozen_entries):
		raise ValueError("User template catalog keys must be unique")
	immutable_entries = tuple(frozen_entries)
	by_key = {entry.catalog_key: entry for entry in immutable_entries}
	descriptors = tuple(
		_UserTemplateModeDescriptor(entry.catalog_key, entry.label)
		for entry in immutable_entries
	)
	return immutable_entries, by_key, descriptors


#============================================
def build_user_template_insert_request(
		expected_revision: int, catalog_key: str, anchor: tuple[float, float],
		) -> PersistentOperationRequest:
	"""Build one immutable detached saved-template insertion intent."""
	if type(expected_revision) is not int:
		raise TypeError("User template insertion expected_revision must be an integer")
	if type(catalog_key) is not str or not catalog_key.strip():
		raise ValueError("User template insertion catalog_key must be nonblank")
	if (
			type(anchor) is not tuple or len(anchor) != 2
			or any(
				isinstance(value, bool) or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in anchor
			)
		):
		raise ValueError("User template insertion anchor must be a finite point tuple")
	return PersistentOperationRequest(
		"user-template.insert", "Place User Template",
		(
			("expected_revision", expected_revision),
			("catalog_key", catalog_key),
			("anchor", (float(anchor[0]), float(anchor[1]))),
		),
		frozenset(),
	)


#============================================
def build_atom_element_request(
		expected_revision: int, molecule_id: str, atom_id: str, element: str,
		) -> PersistentOperationRequest:
	"""Build the one immutable request grammar for an atom element substitution."""
	request = PersistentOperationRequest(
		"atom.element.set", "Change Atom Element",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("atom_id", atom_id),
			("element", element),
		),
		frozenset({("molecule", molecule_id), ("atom", atom_id)}),
	)
	return request


#============================================
def build_atom_align_request(
		expected_revision: int, axis: str, targets: tuple[tuple[str, str], ...],
		) -> PersistentOperationRequest:
	"""Build one immutable request for direct-core atom depiction alignment."""
	return PersistentOperationRequest(
		"atom.align", "Align Selected Atoms",
		(
			("expected_revision", expected_revision),
			("axis", axis),
			("targets", targets),
		),
		frozenset(
			("molecule", molecule_id) for molecule_id, _atom_id in targets
		) | frozenset(("atom", atom_id) for _molecule_id, atom_id in targets),
	)


#============================================
def build_atom_translate_request(
		expected_revision: int, targets: tuple[tuple[str, str], ...],
		delta: tuple[float, float],
		) -> PersistentOperationRequest:
	"""Build one immutable request for direct-core atom translation."""
	return PersistentOperationRequest(
		"atom.translate", "Nudge Selected Atoms",
		(
			("expected_revision", expected_revision),
			("targets", targets),
			("delta", delta),
		),
		frozenset(
			("molecule", molecule_id) for molecule_id, _atom_id in targets
		) | frozenset(("atom", atom_id) for _molecule_id, atom_id in targets),
	)


#============================================
def build_selection_translate_request(
		expected_revision: int, atom_targets: tuple[tuple[str, str], ...],
		presentation_root_keys: tuple[tuple[str, str], ...], delta: tuple[float, float],
		) -> PersistentOperationRequest:
	"""Build one immutable mixed atom/presentation translation request.

	The frontend retains root kinds only to restore canonical selection. OASA
	receives durable presentation IDs and validates authoritative geometry.
	"""
	if type(expected_revision) is not int:
		raise TypeError("Selection translation expected_revision must be an integer")
	if type(atom_targets) is not tuple:
		raise TypeError("Selection translation atom targets must be an immutable tuple")
	if type(presentation_root_keys) is not tuple:
		raise TypeError("Selection translation presentation roots must be an immutable tuple")
	if type(delta) is not tuple:
		raise TypeError("Selection translation delta must be an immutable tuple")
	if not atom_targets:
		raise ValueError("Selection translation requires durable atom targets")
	if not presentation_root_keys:
		raise ValueError("Selection translation requires durable presentation roots")
	if any(
			type(target) is not tuple or len(target) != 2
			or type(target[0]) is not str or not target[0].strip()
			or type(target[1]) is not str or not target[1].strip()
			for target in atom_targets
		):
		raise ValueError("Selection translation atom targets must be durable ID pairs")
	if any(
			type(key) is not tuple or len(key) != 2
			or key[0] != "presentation"
			or type(key[1]) is not str or not key[1].strip()
			for key in presentation_root_keys
		):
		raise ValueError("Selection translation presentation roots must be durable keys")
	presentation_root_ids = tuple(identifier for _kind, identifier in presentation_root_keys)
	target_keys = (
		frozenset(("molecule", molecule_id) for molecule_id, _atom_id in atom_targets)
		| frozenset(("atom", atom_id) for _molecule_id, atom_id in atom_targets)
		| frozenset(presentation_root_keys)
	)
	return PersistentOperationRequest(
		"selection.translate", "Move Selected",
		(
			("expected_revision", expected_revision),
			("atom_targets", atom_targets),
			("presentation_root_ids", presentation_root_ids),
			("delta", delta),
		),
		target_keys,
	)


#============================================
def build_atom_rotate_request(
		expected_revision: int, targets: tuple[tuple[str, str], ...],
		center: tuple[float, float], angle_radians: float,
		) -> PersistentOperationRequest:
	"""Build one immutable request for direct-core atom rotation."""
	return PersistentOperationRequest(
		"atom.rotate", "Rotate Selected Atoms",
		(
			("expected_revision", expected_revision),
			("targets", targets),
			("center", center),
			("angle_radians", angle_radians),
		),
		frozenset(
			("molecule", molecule_id) for molecule_id, _atom_id in targets
		) | frozenset(("atom", atom_id) for _molecule_id, atom_id in targets),
	)


#============================================
def build_bond_order_request(
		expected_revision: int, molecule_id: str, bond_id: str, order: int,
		) -> PersistentOperationRequest:
	"""Build one immutable request for an exact direct-core bond-order edit."""
	return PersistentOperationRequest(
		"bond.order.set", "Set Bond Order",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("bond_id", bond_id),
			("order", order),
		),
		frozenset({("molecule", molecule_id), ("bond", bond_id)}),
	)


#============================================
def build_bond_type_request(
		expected_revision: int, molecule_id: str, bond_id: str, bond_type: str,
		) -> PersistentOperationRequest:
	"""Build one immutable request for an exact direct-core bond-type edit."""
	return PersistentOperationRequest(
		"bond.type.set", "Set Bond Type",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("bond_id", bond_id),
			("bond_type", bond_type),
		),
		frozenset({("molecule", molecule_id), ("bond", bond_id)}),
	)


#============================================
def build_bond_properties_patch_request(
		expected_revision: int, molecule_id: str, bond_id: str,
		changes: tuple[tuple[str, object], ...] = (),
		) -> PersistentOperationRequest:
	"""Build one immutable explicit-field direct-core bond patch request."""
	return PersistentOperationRequest(
		"bond.properties.patch", "Edit Bond Properties",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("bond_id", bond_id),
			("changes", changes),
		),
		frozenset({("molecule", molecule_id), ("bond", bond_id)}),
	)


#============================================
def build_atom_properties_patch_request(
		expected_revision: int, molecule_id: str, atom_id: str,
		changes: tuple[tuple[str, object], ...] = (),
		) -> PersistentOperationRequest:
	"""Build one immutable explicit-field direct-core atom patch request."""
	return PersistentOperationRequest(
		"atom.properties.patch", "Edit Atom Properties",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("atom_id", atom_id),
			("changes", changes),
		),
		frozenset({("molecule", molecule_id), ("atom", atom_id)}),
	)


#============================================
def build_text_properties_patch_request(
		expected_revision: int, text_id: str,
		changes: tuple[tuple[str, object], ...],
		) -> PersistentOperationRequest:
	"""Build one immutable explicit-field direct-root plain Text patch request."""
	return PersistentOperationRequest(
		"text.properties.patch", "Edit Text Properties",
		(
			("expected_revision", expected_revision),
			("text_id", text_id),
			("changes", changes),
		),
		frozenset({("presentation", text_id)}),
	)


#============================================
def build_rich_text_patch_request(
		expected_revision: int, text_id: str,
		runs: tuple[tuple[str, tuple[str, ...]], ...],
		changes: tuple[tuple[str, object], ...] = (),
		) -> PersistentOperationRequest:
	"""Build one immutable plain-run direct-root rich Text patch request."""
	return PersistentOperationRequest(
		"text.rich.patch", "Edit Rich Text",
		(
			("expected_revision", expected_revision),
			("text_id", text_id),
			("runs", runs),
			("changes", changes),
		),
		frozenset({("presentation", text_id)}),
	)


#============================================
def rich_text_patch_from_plain_runs(
		expected_revision: int, text_id: str,
		runs: tuple[tuple[str, tuple[str, ...]], ...],
		changes: tuple[tuple[str, object], ...] = (),
		) -> oasa.cdml_document.CDMLRichTextPatch:
	"""Adapt exact frontend plain runs to the OASA rich-text patch at one seam."""
	if type(runs) is not tuple:
		raise ValueError("Rich Text runs must be an immutable tuple")
	backend_runs = []
	for run in runs:
		if type(run) is not tuple or len(run) != 2:
			raise ValueError("Rich Text runs must be exact text/style pairs")
		text, styles = run
		if type(text) is not str or type(styles) is not tuple:
			raise ValueError("Rich Text runs must contain plain immutable values")
		backend_runs.append(oasa.cdml_ftext.CDMLFTextRun(text, styles))
	try:
		normalized = oasa.cdml_ftext.normalize(tuple(backend_runs))
	except oasa.cdml_ftext.CDMLFTextCodecError as exc:
		raise ValueError("Rich Text runs are invalid: %s" % exc) from exc
	canonical_runs = tuple((run.text, run.styles) for run in normalized)
	if runs != canonical_runs:
		raise ValueError("Rich Text runs must use canonical styles and adjacent spans")
	patch = oasa.cdml_document.CDMLRichTextPatch(
		expected_revision, text_id, normalized, changes,
	)
	return patch


#============================================
def build_plus_properties_patch_request(
		expected_revision: int, plus_id: str,
		changes: tuple[tuple[str, object], ...],
		) -> PersistentOperationRequest:
	"""Build one immutable explicit-field direct-root plain Plus patch request."""
	return PersistentOperationRequest(
		"plus.properties.patch", "Edit Plus Properties",
		(
			("expected_revision", expected_revision),
			("plus_id", plus_id),
			("changes", changes),
		),
		frozenset({("presentation", plus_id)}),
	)


#============================================
def build_wavy_properties_patch_request(
		expected_revision: int, wavy_id: str,
		changes: tuple[tuple[str, object], ...],
		) -> PersistentOperationRequest:
	"""Build one immutable explicit-field direct-root plain Wavy patch request."""
	return PersistentOperationRequest(
		"wavy.properties.patch", "Edit Wavy Properties",
		(
			("expected_revision", expected_revision),
			("wavy_id", wavy_id),
			("changes", changes),
		),
		frozenset({("presentation", wavy_id)}),
	)


#============================================
def build_fragment_create_request(
		expected_revision: int, molecule_id: str, name: str, fragment_type: str,
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> PersistentOperationRequest:
	"""Build one immutable ordinary fragment metadata creation request."""
	return PersistentOperationRequest(
		"fragment.create", "Create Fragment",
		(
			("expected_revision", expected_revision), ("molecule_id", molecule_id),
			("name", name), ("fragment_type", fragment_type),
			("atom_ids", atom_ids), ("bond_ids", bond_ids),
		),
		frozenset({("molecule", molecule_id)})
		| frozenset(("atom", atom_id) for atom_id in atom_ids)
		| frozenset(("bond", bond_id) for bond_id in bond_ids),
	)


#============================================
def build_fragment_delete_request(
		expected_revision: int, molecule_id: str, fragment_id: str,
		) -> PersistentOperationRequest:
	"""Build one immutable ordinary fragment metadata deletion request."""
	return PersistentOperationRequest(
		"fragment.delete", "Delete Fragment",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("fragment_id", fragment_id),
		),
		frozenset({("molecule", molecule_id)}),
	)


#============================================
def build_implicit_group_expand_request(
		expected_revision: int, molecule_id: str, group_id: str,
		) -> PersistentOperationRequest:
	"""Build one immutable backend-owned implicit-group expansion request."""
	return PersistentOperationRequest(
		"group.expand.implicit", "Expand Implicit Group",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("group_id", group_id),
		),
		frozenset({("molecule", molecule_id), ("group", group_id)}),
	)


#============================================
def build_linear_form_convert_request(
		expected_revision: int, molecule_id: str, atom_ids: tuple[str, ...],
		) -> PersistentOperationRequest:
	"""Build one immutable backend-owned linear-form conversion request."""
	return PersistentOperationRequest(
		"linear-form.convert", "Convert to Linear Form",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("atom_ids", atom_ids),
		),
		frozenset({("molecule", molecule_id)})
		| frozenset(("atom", atom_id) for atom_id in atom_ids),
	)


#============================================
def build_atom_mark_request(
		expected_revision: int, molecule_id: str, atom_id: str,
		action: str, mark_type: str, matching_mark_index: int | None = None,
		) -> PersistentOperationRequest:
	"""Build one immutable direct-atom chemical-mark operation."""
	payload = (
		("expected_revision", expected_revision),
		("molecule_id", molecule_id),
		("atom_id", atom_id),
		("action", action),
		("mark_type", mark_type),
	)
	if matching_mark_index is not None:
		payload += (("matching_mark_index", matching_mark_index),)
	return PersistentOperationRequest(
		"atom.mark.apply", "Apply Atom Mark",
		payload,
		frozenset({("molecule", molecule_id), ("atom", atom_id)}),
	)


#============================================
def build_structure_delete_request(
		expected_revision: int, molecule_id: str,
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> PersistentOperationRequest:
	"""Build one immutable direct-atom/bond structural deletion request."""
	if type(expected_revision) is not int:
		raise TypeError("Structure Delete expected_revision must be an integer")
	if type(molecule_id) is not str or not molecule_id.strip():
		raise ValueError("Structure Delete molecule_id must be a nonblank durable ID")
	for name, identifiers in (("atom_ids", atom_ids), ("bond_ids", bond_ids)):
		if type(identifiers) is not tuple:
			raise TypeError("Structure Delete %s must be an immutable tuple" % name)
		if any(type(identifier) is not str or not identifier.strip() for identifier in identifiers):
			raise ValueError("Structure Delete IDs must be nonblank strings")
		if len(set(identifiers)) != len(identifiers):
			raise ValueError("Structure Delete IDs must be unique")
	if not atom_ids and not bond_ids:
		raise ValueError("Structure Delete requires at least one atom or bond")
	if set(atom_ids).intersection(bond_ids):
		raise ValueError("Structure Delete atom and bond IDs must be distinct")
	target_keys = (
		frozenset({("molecule", molecule_id)})
		| frozenset(("atom", identifier) for identifier in atom_ids)
		| frozenset(("bond", identifier) for identifier in bond_ids)
	)
	return PersistentOperationRequest(
		"structure.delete", "Delete",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("atom_ids", atom_ids),
			("bond_ids", bond_ids),
		),
		target_keys,
	)


#============================================
def build_structure_fragment_extraction_query(
		expected_revision: int, molecule_id: str,
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> oasa.cdml_document.CDMLStructureFragmentExtractionQuery:
	"""Build the immutable read-only structural clipboard query."""
	return oasa.cdml_document.CDMLStructureFragmentExtractionQuery(
		expected_revision, molecule_id, atom_ids, bond_ids,
	)


#============================================
def build_top_level_fragment_extraction_query(
		expected_revision: int, root_ids: tuple[str, ...],
		) -> oasa.cdml_document.CDMLTopLevelFragmentExtractionQuery:
	"""Build one immutable backend-owned direct-root clipboard query."""
	return oasa.cdml_document.CDMLTopLevelFragmentExtractionQuery(
		expected_revision, root_ids,
	)


#============================================
def build_molecule_name_request(
		expected_revision: int, molecule_id: str, name: str,
		) -> PersistentOperationRequest:
	"""Build the immutable request grammar for one molecule display-name edit."""
	return PersistentOperationRequest(
		"molecule.name.set", "Set Molecule Name",
		(
			("expected_revision", expected_revision),
			("molecule_id", molecule_id),
			("name", name),
		),
		frozenset({("molecule", molecule_id)}),
	)


#============================================
def build_paper_properties_request(
		expected_revision: int, changes: tuple[tuple[str, object], ...],
		) -> PersistentOperationRequest:
	"""Build one immutable explicit-field paper-properties patch request."""
	return PersistentOperationRequest(
		"paper.properties.set", "Edit Paper Properties",
		(("expected_revision", expected_revision), ("changes", changes)),
	)

#============================================
def build_drawing_standard_request(
		expected_revision: int, changes: tuple[tuple[str, object], ...],
		apply_scope: str = "defaults", root_keys: tuple[tuple[str, str], ...] = (),
		override_fields: tuple[str, ...] = (),
		) -> PersistentOperationRequest:
	"""Build one immutable standard patch plus optional object overrides."""
	return PersistentOperationRequest(
		"document.standard.set", "Edit Document Drawing Style",
		(("expected_revision", expected_revision), ("changes", changes),
			("apply_scope", apply_scope),
			("root_ids", tuple(identifier for _kind, identifier in root_keys)),
			("override_fields", override_fields)),
		frozenset(root_keys),
	)

#============================================
def build_presentation_stack_request(
		expected_revision: int, mode: str, root_ids: tuple[str, ...],
		) -> PersistentOperationRequest:
	"""Build one immutable direct-presentation-root reorder request."""
	labels = {
		"bring-to-front": "Bring to Front",
		"send-back": "Send to Back",
		"swap-at-slots": "Swap on Stack",
	}
	if mode not in labels:
		raise ValueError("Presentation stack mode is unsupported")
	return PersistentOperationRequest(
		"presentation.stack.reorder", labels[mode],
		(
			("expected_revision", expected_revision),
			("mode", mode),
			("root_ids", root_ids),
		),
		frozenset(("presentation", identifier) for identifier in root_ids),
	)


#============================================
def build_top_level_transform_request(
		expected_revision: int, mode: str,
		root_keys: tuple[tuple[str, str], ...],
		scale_x: float | None = None, scale_y: float | None = None,
		delta: tuple[float, float] | None = None,
		) -> PersistentOperationRequest:
	"""Build one immutable mixed direct-root transform request.

	The backend request contains durable root IDs plus only the documented scalar
	intent for its mode. The paired root kinds stay at the frontend boundary
	solely to restore the selected roots after canonical reprojection.
	"""
	allowed_modes = {
		"align-top", "align-bottom", "align-left", "align-right",
		"align-center-x", "align-center-y", "scale", "mirror-vertical",
		"mirror-horizontal", "translate",
	}
	labels = {
		"align-top": "Align Top",
		"align-bottom": "Align Bottom",
		"align-left": "Align Left",
		"align-right": "Align Right",
		"align-center-x": "Align Center Horizontally",
		"align-center-y": "Align Center Vertically",
		"scale": "Scale",
		"mirror-vertical": "Vertical Mirror",
		"mirror-horizontal": "Horizontal Mirror",
		"translate": "Move Selected",
	}
	if type(expected_revision) is not int:
		raise TypeError("Top-level transform expected_revision must be an integer")
	if mode not in allowed_modes:
		raise ValueError("Top-level transform mode is unsupported")
	if type(root_keys) is not tuple or not root_keys:
		raise ValueError("Top-level transform roots must be a nonempty immutable tuple")
	if any(
		type(key) is not tuple or len(key) != 2
		or key[0] not in {"molecule", "presentation"}
		or type(key[1]) is not str or not key[1]
		for key in root_keys
	):
		raise ValueError("Top-level transform roots must be supported durable root keys")
	if len({identifier for _kind, identifier in root_keys}) != len(root_keys):
		raise ValueError("Top-level transform root IDs must be unique")
	if mode == "scale":
		if delta is not None:
			raise ValueError("Only translate accepts a top-level transform delta")
		if any(
			type(value) not in (int, float) or not math.isfinite(value) or value <= 0
			for value in (scale_x, scale_y)
		):
			raise ValueError("Top-level transform scale factors must be finite positive numbers")
	elif mode == "translate":
		if scale_x is not None or scale_y is not None:
			raise ValueError("Only scale accepts top-level transform scale factors")
		if (
			type(delta) is not tuple or len(delta) != 2
			or any(type(value) not in (int, float) or not math.isfinite(value) for value in delta)
		):
			raise ValueError("Top-level transform delta must be two finite non-bool numbers")
	else:
		if scale_x is not None or scale_y is not None or delta is not None:
			raise ValueError("Only scale or translate accepts top-level transform parameters")
	return PersistentOperationRequest(
		"top-level.transform.apply", labels[mode],
		(
			("expected_revision", expected_revision), ("mode", mode),
			("root_ids", tuple(identifier for _kind, identifier in root_keys)),
			("scale_x", scale_x), ("scale_y", scale_y), ("delta", delta),
		),
		frozenset(root_keys),
	)


@dataclasses.dataclass(frozen=True)
class PersistentActionOutcome:
	"""Uniform immutable result for a persistent-operation submission."""

	status: str
	message: str
	commit: oasa.cdml_document.CDMLCommit | None
	submitted: bool = False
	structural_result: oasa.cdml_document.CDMLStructuralEditResult | None = None
	failure_kind: str | None = None


@dataclasses.dataclass(frozen=True)
class _PreparedPersistentOperation:
	"""One validated operation waiting for its named backend commit executor."""

	executor_key: str
	expected_revision: int
	value: object
	provisional_selection_keys: frozenset[tuple[str, str]] = frozenset()
	preserve_existing_selection: bool = False

	#============================================
	def __post_init__(self) -> None:
		"""Keep proposed selection correlation data immutable and plain."""
		selection_keys = frozenset(self.provisional_selection_keys)
		if any(
			not isinstance(kind, str) or not isinstance(identifier, str)
			for kind, identifier in selection_keys
		):
			raise TypeError("Provisional selection keys must be string pairs")
		object.__setattr__(self, "provisional_selection_keys", selection_keys)
		if not isinstance(self.preserve_existing_selection, bool):
			raise TypeError("Selection preservation flag must be boolean")


@dataclasses.dataclass(frozen=True)
class CloseState:
	"""Plain backend and provenance facts used for a close decision."""

	backend_dirty: bool
	backend_unseen: bool
	legacy_local_pending: bool
	authoritative_save_eligible: bool

	#============================================
	@property
	def needs_confirmation(self) -> bool:
		"""Return whether closing would discard backend or local pending content."""
		needed = (
			self.backend_dirty
			or self.backend_unseen
			or self.legacy_local_pending
		)
		return needed

	#============================================
	@property
	def uses_recovery_export(self) -> bool:
		"""Return whether a prompted close must use Recovery Export, not Save."""
		return self.needs_confirmation and not self.authoritative_save_eligible


class PreparedNativeCDML:
	"""One-use detached native projection staged from immutable backend CDML.

	Instances are made only by :meth:`DocumentSession.prepare_native_cdml`.
	The detached Qt document remains private until one receiving session consumes
	it.  Callers may inspect the immutable snapshot or canonical CDML, but cannot
	mutate the staged projection before installation.  Installation parses the
	canonical snapshot again into the receiving session's private authority.
	"""

	def __init__(
			self, factory_token: object, snapshot: oasa.cdml_document.CDMLSnapshot,
			document: bkchem_qt.models.document.Document,
			) -> None:
		"""Create a factory-only value with a private detached Qt document."""
		if factory_token is not _PREPARED_NATIVE_FACTORY_TOKEN:
			raise TypeError("PreparedNativeCDML objects must come from native staging")
		self._snapshot = snapshot
		self._document = document
		self._consumed = False

	#============================================
	@property
	def snapshot(self) -> oasa.cdml_document.CDMLSnapshot:
		"""Return the immutable canonical backend snapshot used for staging."""
		return self._snapshot

	#============================================
	@property
	def canonical_cdml(self) -> str:
		"""Return the immutable canonical CDML value staged for installation."""
		return self._snapshot.cdml

	#============================================
	@property
	def consumed(self) -> bool:
		"""Return whether a session has already adopted this staged projection."""
		return self._consumed

	#============================================
	def _peek(
			self,
			) -> tuple[str, bkchem_qt.models.document.Document]:
		"""Return the private staged projection without completing transfer."""
		if self._consumed:
			raise RuntimeError("Prepared native CDML has already been consumed")
		return self._snapshot.cdml, self._document

	#============================================
	def _finalize(self) -> None:
		"""Complete a successful native transfer exactly once."""
		if self._consumed:
			raise RuntimeError("Prepared native CDML has already been consumed")
		self._consumed = True


_PREPARED_NATIVE_FACTORY_TOKEN = object()
_PREPARED_IMPORTED_FACTORY_TOKEN = object()


class PreparedImportedCDML(PreparedNativeCDML):
	"""One-use detached projection staged from an external complete CDML file."""

	def __init__(
			self, factory_token: object, snapshot: oasa.cdml_document.CDMLSnapshot,
			document: bkchem_qt.models.document.Document,
			) -> None:
		if factory_token is not _PREPARED_IMPORTED_FACTORY_TOKEN:
			raise TypeError("PreparedImportedCDML objects must come from import staging")
		self._snapshot = snapshot
		self._document = document
		self._consumed = False


#============================================
class BackendSnapshotPublicationError(RuntimeError):
	"""Report a filesystem result that may have published CDML already."""


#============================================
def _resolved_publication_target(file_path: str) -> str:
	"""Return the target normal writes reach, following an existing symlink."""
	return os.path.realpath(os.path.abspath(file_path))


#============================================
def _write_backend_snapshot(
		file_path: str, snapshot: oasa.cdml_document.CDMLSnapshot,
		) -> None:
	"""Atomically publish one immutable snapshot without changing session state.

	A failure before replacement leaves an existing target unchanged.  A failure
	after replacement is deliberately distinguished because the named file may
	already contain ``snapshot.cdml`` while durability remains unconfirmed.
	"""
	target_path = _resolved_publication_target(file_path)
	target_directory = os.path.dirname(target_path)
	target_mode = None
	try:
		target_status = os.stat(target_path)
	except FileNotFoundError:
		pass
	else:
		if not stat.S_ISREG(target_status.st_mode):
			raise OSError("Backend CDML target is not a regular file: %s" % target_path)
		target_mode = stat.S_IMODE(target_status.st_mode)
	staged_path = None
	try:
		for _attempt in range(100):
			candidate = os.path.join(
				target_directory,
				".%s.bkchem-%s.tmp" % (os.path.basename(target_path), os.urandom(8).hex()),
			)
			try:
				file_descriptor = os.open(
					candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666,
				)
			except FileExistsError:
				continue
			staged_path = candidate
			break
		else:
			raise OSError("Could not create a unique staged backend CDML file")
		try:
			if target_mode is not None:
				os.fchmod(file_descriptor, target_mode)
			with os.fdopen(file_descriptor, "w", encoding="utf-8") as destination:
				file_descriptor = None
				destination.write(snapshot.cdml)
				destination.flush()
				os.fsync(destination.fileno())
		except Exception:
			if file_descriptor is not None:
				try:
					os.close(file_descriptor)
				except OSError:
					# Staged-path cleanup below remains best effort.  Preserve the
					# write, fchmod, or fdopen diagnostic that triggered this path.
					pass
			raise
		os.replace(staged_path, target_path)
		staged_path = None
		try:
			directory_flags = os.O_RDONLY
			if hasattr(os, "O_DIRECTORY"):
				directory_flags |= os.O_DIRECTORY
			directory_descriptor = os.open(target_directory, directory_flags)
			try:
				os.fsync(directory_descriptor)
			finally:
				os.close(directory_descriptor)
		except OSError as exc:
			if exc.errno not in (errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP, errno.ENOSYS):
				raise BackendSnapshotPublicationError(
					"CDML target was atomically replaced but directory durability "
					"confirmation failed; the target may contain the exact canonical "
					"snapshot, publication durability is unconfirmed, and the publisher "
					"changed no session state",
				) from exc
	finally:
		if staged_path is not None:
			try:
				os.unlink(staged_path)
			except FileNotFoundError:
				pass
			except OSError:
				pass


#============================================
class DocumentSession(PySide6.QtCore.QObject):
	"""Own one tab's transient Qt projection and backend CDML staging seam.

	The private OASA session owns the authoritative complete CDML snapshot.  The
	Qt document, scene, view, mode manager, and import state remain its live
	projection and interaction state.  Until all legacy actions migrate, their
	changes only invalidate the synchronization latch; they do not create a
	backend commit.

	Args:
		parent: QObject that owns this session (normally MainWindow).
		theme_manager: ThemeManager for the initial canvas theme.
		prefs: Preferences singleton.
		mode_host: Window-like object used by FileActionsMode.
		view_parent: Optional QWidget initially parenting the ChemView.
		file_path: Optional native document path for the initial title.
		display_name: Optional non-native label for loading/imported content.
		origin_path: Optional source path used for duplicate-open detection.
		prepared_native_cdml: One-use native staging result from
			:meth:`prepare_native_cdml`.  Its canonical CDML is parsed into this
			session's independently owned backend authority.
		prepared_imported_cdml: One-use imported-content staging result whose
			canonical CDML initializes this session's backend authority.
		user_template_catalog: Immutable admitted saved-template records copied
			into this session's frontend-owned delivery mapping.
	"""

	title_changed = PySide6.QtCore.Signal(str)
	disposed = PySide6.QtCore.Signal()

	#============================================
	def __init__(
		self, parent: PySide6.QtCore.QObject, theme_manager: object,
		prefs: object, mode_host: object,
		view_parent: PySide6.QtWidgets.QWidget | None = None,
		file_path: str | None = None, display_name: str | None = None,
		origin_path: str | None = None,
		prepared_native_cdml: PreparedNativeCDML | None = None,
		prepared_imported_cdml: PreparedImportedCDML | None = None,
		user_template_catalog: tuple[
			bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry, ...
			] = (),
		) -> None:
		"""Create a clean, independently owned document session."""
		super().__init__(parent)
		self._disposed = False
		self._teardown_phase = "live"
		self._teardown_diagnostics: list[BaseException] = []
		self._retained_detached_graphics = None
		from bkchem_qt.canvas.graphics_retirement import DetachedGraphicsRetirementReaper
		self._projection_retirement_reaper = DetachedGraphicsRetirementReaper()
		self._import_generation = 0
		self._import_workers = set()
		self._display_name = display_name
		self._origin_path = origin_path or file_path
		self._backend_session = None
		self._backend_projection_synchronized = False
		self._projected_backend_snapshot = None
		self._projected_persistent_generation = None
		self._projection_replacing = False
		self._projection_error = None
		self._projection_lifecycle_generation = 0
		self._projection_lifecycle_port = None
		self._accepted_projection_selection = None
		self._provisional_action_sequence = 0
		self._backend_history = None
		(
			self._user_template_entries,
			self._user_templates_by_key,
			self._user_template_mode_descriptors,
		) = _freeze_user_template_catalog(user_template_catalog)
		self._operation_dispatcher = {
			"arrow.add": self._build_arrow_candidate,
			"text.add": self._build_text_candidate,
			"plus.add": self._build_plus_candidate,
			"vector.add": self._build_vector_candidate,
			"bracket.add": self._build_bracket_candidate,
			"wavy.add": self._build_wavy_candidate,
			"molecule.insert": self._build_molecule_insertion,
			"template.insert": self._build_template_insertion,
			"biotemplate.insert": self._build_biomolecule_template_insertion,
			"user-template.insert": self._build_user_template_insertion,
			"geometry.repair": self._build_geometry_repair,
			"atom.align": self._build_atom_align,
			"atom.translate": self._build_atom_translate,
			"selection.translate": self._build_selection_translate,
			"atom.rotate": self._build_atom_rotate,
			"bond.order.set": self._build_bond_order_edit,
			"bond.type.set": self._build_bond_type_edit,
			"bond.properties.patch": self._build_bond_properties_patch,
			"atom.properties.patch": self._build_atom_properties_patch,
			"text.properties.patch": self._build_text_properties_patch,
			"text.rich.patch": self._build_rich_text_patch,
			"plus.properties.patch": self._build_plus_properties_patch,
			"wavy.properties.patch": self._build_wavy_properties_patch,
			"fragment.create": self._build_fragment_create,
			"fragment.delete": self._build_fragment_delete,
			"group.expand.implicit": self._build_implicit_group_expand,
			"linear-form.convert": self._build_linear_form_convert,
			"atom.mark.apply": self._build_atom_mark_operation,
			"draw.structure": self._build_structural_edit,
			"atom.element.set": self._build_atom_element_edit,
			"atom.number.set": self._build_atom_number_edit,
			"molecule.name.set": self._build_molecule_name_edit,
			"paper.properties.set": self._build_paper_properties_patch,
			"document.standard.set": self._build_drawing_standard_patch,
			"presentation.stack.reorder": self._build_presentation_stack_reorder,
			"top-level.delete": self._build_top_level_delete,
			"structure.delete": self._build_structure_delete,
			"top-level.transform.apply": self._build_top_level_transform,
		}
		self._operation_commit_executors = {
			"complete-candidate": self._commit_complete_candidate,
			"molecule-insertion": self._commit_molecule_insertion,
			"user-template-insertion": self._commit_user_template_insertion,
			"geometry-repair": self._commit_geometry_repair,
			"atom-align": self._commit_atom_align,
			"atom-translate": self._commit_atom_translate,
			"selection-translate": self._commit_selection_translate,
			"atom-rotate": self._commit_atom_rotate,
			"bond-order-edit": self._commit_bond_order_edit,
			"bond-type-edit": self._commit_bond_type_edit,
			"bond-properties-patch": self._commit_bond_properties_patch,
			"atom-properties-patch": self._commit_atom_properties_patch,
			"text-properties-patch": self._commit_text_properties_patch,
			"rich-text-patch": self._commit_rich_text_patch,
			"plus-properties-patch": self._commit_plus_properties_patch,
			"wavy-properties-patch": self._commit_wavy_properties_patch,
			"fragment-create": self._commit_fragment_create,
			"fragment-delete": self._commit_fragment_delete,
			"implicit-group-expand": self._commit_implicit_group_expand,
			"linear-form-convert": self._commit_linear_form_convert,
			"atom-mark-operation": self._commit_atom_mark_operation,
			"structural-edit": self._commit_structural_edit,
			"atom-element-edit": self._commit_atom_element_edit,
			"atom-number-edit": self._commit_atom_number_edit,
			"molecule-name-edit": self._commit_molecule_name_edit,
			"paper-properties-patch": self._commit_paper_properties_patch,
			"drawing-standard-patch": self._commit_drawing_standard_patch,
			"top-level-delete": self._commit_top_level_delete,
			"structure-delete": self._commit_structure_delete,
			"top-level-transform": self._commit_top_level_transform,
		}
		self._legacy_isolated = False
		self._document = None
		self._document_modified_connected = False
		self._document_persistent_mutation_connected = False
		self._scene = None
		self._view = None
		self._mode_manager = None
		staged_document = None
		try:
			if prepared_native_cdml is None and prepared_imported_cdml is None:
				self._backend_session = drawing_standard_preferences.blank_backend_session(prefs)
				from bkchem_qt.io import cdml_document_io
				staged_document = cdml_document_io.hydrate_synchronized_cdml_document(
					self._backend_session.projection_snapshot())
			elif prepared_native_cdml is not None:
				canonical_cdml, staged_document = prepared_native_cdml._peek()
				self._backend_session = oasa.cdml_document.CDMLDocumentSession.load(
					canonical_cdml,
				)
				# Keep this document detached until every new session root is viable.
			else:
				canonical_cdml, staged_document = prepared_imported_cdml._peek()
				self._backend_session = oasa.cdml_document.CDMLDocumentSession.load_imported(
					canonical_cdml,
				)
			self._document = (
				staged_document
				if staged_document is not None
				else bkchem_qt.models.document.Document()
			)
			self._document.set_graphics_retirement_reaper(
				self._projection_retirement_reaper,
			)
			if file_path is not None:
				self._document.file_path = file_path
			self._scene, self._view = bkchem_qt.setup.canvas_setup.create_canvas(
				view_parent, theme_manager, prefs, self._document, owner=self,
			)
			self._scene.apply_paper_model(self._document.paper)
			self._backend_history = (
				bkchem_qt.models.backend_revision_history.BackendRevisionHistory.baseline(
					"Document", self._backend_session.revision,
				)
			)
			self._mode_manager = bkchem_qt.setup.mode_setup.setup_modes(
				self._view, mode_host, parent=self,
				persistent_action=self.submit_persistent_operation,
				atom_align_action=self.submit_atom_align,
				atom_translate_action=self.submit_atom_translate,
				atom_rotate_action=self.submit_atom_rotate,
				atom_translate_authority=self.atom_translate_drag_authority,
				presentation_translate_action=self.submit_top_level_transform,
				presentation_translate_context=self.presentation_translate_drag_context,
				selection_translate_action=self.submit_selection_translate,
				selection_translate_context=self.selection_translate_drag_context,
				top_level_delete_context=self.top_level_delete_context,
				structure_delete_context=self.structure_delete_context,
				atom_mark_delete_context=self.atom_mark_delete_context,
				atom_number_context=self.atom_number_context,
				atom_mark_revision=self.atom_mark_revision,
				template_names=oasa.template_placement.system_template_names(),
				template_action=self.submit_system_template,
				biomolecule_catalog=(
					oasa.biomolecule_template_placement.biomolecule_template_catalog()
				),
				biotemplate_action=self.submit_biomolecule_template,
				user_template_catalog=self._user_template_mode_descriptors,
				user_template_action=self.submit_user_template,
				graphics_retirement_reaper=self._projection_retirement_reaper,
			)
			# The backend imported-load baseline is empty, so this projection starts
			# visibly dirty before it becomes a live session.  Qt reflects that
			# backend fact; it does not create an independent local mutation.
			if prepared_imported_cdml is not None:
				self._document.mark_dirty()
			self._document.setParent(self)
			self._document.modified_changed.connect(self._on_modified_changed)
			self._document_modified_connected = True
			self._document.persistent_mutated.connect(self._on_persistent_mutated)
			self._document_persistent_mutation_connected = True
			self._projected_backend_snapshot = self._backend_session.snapshot()
			self._projected_persistent_generation = self._document.persistent_generation
			self._backend_projection_synchronized = True
			if prepared_native_cdml is not None:
				prepared_native_cdml._finalize()
			if prepared_imported_cdml is not None:
				prepared_imported_cdml._finalize()
		except Exception:
			self._dispose_failed_construction(staged_document)
			raise

	# ------------------------------------------------------------------
	# Backend CDML authority staging
	# ------------------------------------------------------------------

	#============================================
	@property
	def backend_snapshot(self) -> oasa.cdml_document.CDMLSnapshot:
		"""Return the current immutable, backend-owned complete CDML snapshot."""
		return self._backend_session.snapshot()

	#============================================
	def paper_catalog(self) -> dict[str, list[float] | None]:
		"""Return the OASA-owned plain paper catalog for this live client session."""
		self._require_live_persistent_operation()
		return self._backend_session.paper_catalog()

	#============================================
	def paper_properties_context(self) -> dict[str, object]:
		"""Return OASA's plain editable-paper observation for this session."""
		return self._backend_session.paper_properties_context()

	#============================================
	def drawing_standard(self) -> oasa.cdml_standard.CDMLDrawingStandardObservation:
		"""Return drawing defaults from this synchronized backend revision."""
		self._require_live_persistent_operation()
		if not self.can_write_authoritative_snapshot:
			raise BackendProjectionOutOfSyncError("Cannot edit drawing style from a stale Qt projection")
		return self._backend_session.drawing_standard(
			oasa.cdml_standard.CDMLDrawingStandardQuery(self.backend_snapshot.revision),
		)

	#============================================
	def query_molecule_summary(
			self, expected_revision: int, molecule_ids: tuple[str, ...],
			) -> object:
		"""Observe selected authoritative molecules without changing the session."""
		self._require_live_persistent_operation()
		if not self.can_write_authoritative_snapshot:
			raise BackendProjectionOutOfSyncError("Cannot summarize molecules from a stale Qt projection")
		return self._backend_session.molecule_summary(
			oasa.cdml_molecule_summary.CDMLMoleculeSummaryQuery(expected_revision, molecule_ids),
		)

	#============================================
	def query_molecule_smiles(
			self, expected_revision: int, molecule_id: str,
			) -> oasa.cdml_document.CDMLMoleculeSmilesResult:
		"""Observe one synchronized direct-root molecule through OASA CDML."""
		self._require_live_persistent_operation()
		if not self.can_write_authoritative_snapshot:
			raise BackendProjectionOutOfSyncError(
				"Cannot query molecule SMILES while the Qt projection is not a "
				"current authoritative projection",
			)
		request = oasa.cdml_document.CDMLMoleculeSmilesQuery(
			expected_revision=expected_revision,
			molecule_id=molecule_id,
		)
		return self._backend_session.query_molecule_smiles(request)

	#============================================
	def observe_atom_chemistry_facts(
			self, expected_revision: int,
			) -> oasa.cdml_document.CDMLAtomChemistryFactsObservation:
		"""Return one read-only OASA chemistry observation for this projection."""
		self._require_live_persistent_operation()
		if not self.can_write_authoritative_snapshot:
			raise BackendProjectionOutOfSyncError(
				"Cannot observe atom chemistry while the Qt projection is not a "
				"current authoritative projection",
			)
		return self._backend_session.atom_chemistry_facts(
			oasa.cdml_document.CDMLAtomChemistryFactsQuery(expected_revision),
		)

	#============================================
	def atom_number_context(self) -> tuple[int, int]:
		"""Return revision and next transient candidate from backend molecule facts.

		The returned scalar is compatibility presentation state. Hidden numbers
		participate, while Qt never reparses the authoritative CDML snapshot.
		"""
		snapshot = self.backend_snapshot
		observation = self._backend_session.molecule_core_observation(
			oasa.cdml_document.CDMLMoleculeCoreObservationQuery(snapshot.revision),
		)
		highest = max((
			atom.number
			for molecule in observation.records for atom in molecule.atoms
			if molecule.renderable and atom.renderable
			and atom.number is not None and atom.number > 0
		), default=0)
		return observation.revision, highest + 1

	#============================================
	def atom_mark_revision(self) -> int:
		"""Return the exact current backend revision for one MarkMode gesture."""
		self._require_live_persistent_operation()
		return self.backend_snapshot.revision

	#============================================
	def capture_visual_render_request(
			self, format_name: str, scope: str = "page",
			) -> oasa.cdml_render.CDMLRenderRequest | oasa.cdml_render.CDMLRenderFailure:
		"""Capture one exact backend snapshot and durable Qt selection keys.

		The resulting request contains no live Qt object.  Page and content output
		remain available while a projection is stale because the backend snapshot is
		the only persistent render source.  Selection has one additional Qt-only
		capture step and reports a typed outcome when no live projection exists.
		"""
		if self._disposed or self._backend_session is None:
			return oasa.cdml_render.CDMLRenderFailure(
				"session-unavailable", "Visual export requires a live backend session",
			)
		try:
			snapshot = self._backend_session.snapshot()
		except Exception:
			return oasa.cdml_render.CDMLRenderFailure(
				"session-unavailable", "Visual export requires a readable backend snapshot",
			)
		selection_keys = ()
		if scope == "selection":
			if not self._selection_projection_matches_snapshot(snapshot):
				return oasa.cdml_render.CDMLRenderFailure(
					"selection-unavailable",
					"Selection export requires the current Qt projection", snapshot.revision,
				)
			try:
				items = bkchem_qt.canvas.graphics_retirement.selected_items_from_captured_scene(
					self._scene,
				)
				if not items:
					return oasa.cdml_render.CDMLRenderFailure(
						"selection-unavailable", "Selection export requires a durable selection",
						snapshot.revision,
					)
				seen = set()
				captured = []
				for item in items:
					if not self._document.is_current_projection_item(item):
						return oasa.cdml_render.CDMLRenderFailure(
							"selection-unavailable",
							"Selection export requires current projection items",
							snapshot.revision,
						)
					key = bkchem_qt.canvas.document_projection.persistent_selection_key(item)
					if key is None:
						return oasa.cdml_render.CDMLRenderFailure(
							"selection-unavailable",
							"Selection export requires durable selection IDs",
							snapshot.revision,
						)
					if key in seen:
						continue
					seen.add(key)
					captured.append(oasa.cdml_render.CDMLRenderSelectionKey(*key))
				selection_keys = tuple(captured)
			except Exception:
				return oasa.cdml_render.CDMLRenderFailure(
					"selection-unavailable", "Could not capture durable selection IDs",
					snapshot.revision,
				)
		try:
			return oasa.cdml_render.CDMLRenderRequest(
				snapshot=snapshot, format_name=format_name, scope=scope,
				selection_keys=selection_keys,
			)
		except (TypeError, ValueError) as exc:
			return oasa.cdml_render.CDMLRenderFailure(
				"invalid-render-request", str(exc), snapshot.revision,
			)

	#============================================
	def _selection_projection_matches_snapshot(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> bool:
		"""Return whether one captured snapshot has its installed Qt projection.

		Selection is frontend interaction state, unlike page/content export.  Its
		durable keys are meaningful only while the registered projection still
		represents this exact immutable backend snapshot.  This check deliberately
		uses the snapshot already captured for the render request rather than
		reading the backend a second time.
		"""
		return (
			not self._disposed
			and not self._projection_replacing
			and self._projection_error is None
			and self._backend_projection_synchronized
			and self._document is not None
			and self._scene is not None
			and self._view is not None
			and self._projected_backend_snapshot == snapshot
			and self._document._scene is self._scene
			and self._view.document is self._document
		)

	#============================================
	@property
	def backend_projection_synchronized(self) -> bool:
		"""Return whether the live Qt document matches the backend snapshot."""
		return self._backend_projection_synchronized

	#============================================
	@property
	def projection_error(self) -> Exception | None:
		"""Return the diagnostic from an unrecoverable projection replacement."""
		return self._projection_error

	#============================================
	def commit_complete_candidate(
			self, complete_cdml: str,
			) -> oasa.cdml_document.CDMLCommit:
		"""Accept a complete CDML candidate without changing the Qt projection."""
		self._require_live_persistent_operation()
		commit = self._backend_session.commit(
			expected_revision=self._backend_session.revision,
			complete_cdml=complete_cdml,
		)
		self._backend_projection_synchronized = False
		return commit

	#============================================
	@property
	def projection_lifecycle_generation(self) -> int:
		"""Return the generation that invalidates stale lifecycle delivery."""
		return self._projection_lifecycle_generation

	#============================================
	def install_projection_lifecycle_port(
			self, port: bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort,
			) -> None:
		"""Install one explicitly session-bound projection delivery port."""
		if self._disposed or not port.is_bound_to(self):
			raise ValueError("A live session requires its own projection lifecycle port")
		self._projection_lifecycle_port = port

	#============================================
	def owns_projection_lifecycle_port(self, port: object) -> bool:
		"""Return whether a delivery port is this live session's current owner."""
		return not self._disposed and self._projection_lifecycle_port is port

	#============================================
	def clear_projection_lifecycle_port(self) -> None:
		"""Invalidate and remove this session's projection delivery port."""
		self._projection_lifecycle_generation += 1
		self._projection_lifecycle_port = None

	#============================================
	@property
	def legacy_isolated(self) -> bool:
		"""Return whether Qt-local persistent edits block backend actions."""
		return self._legacy_isolated

	#============================================
	@property
	def can_commit_persistent_action(self) -> bool:
		"""Return whether a persistent backend action can start safely now."""
		available = (
			self._projection_lifecycle_port is not None
			and not self._legacy_isolated
			and self.can_write_authoritative_snapshot
		)
		return available

	#============================================
	def replace_user_template_catalog(
			self,
			entries: tuple[bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry, ...],
			) -> None:
		"""Atomically replace this session's frozen saved-template delivery data."""
		if self._disposed:
			raise RuntimeError("Cannot replace a disposed session's user template catalog")
		frozen_entries, by_key, descriptors = _freeze_user_template_catalog(entries)
		mode = self._mode_manager.mode("usertemplate")
		set_catalog = getattr(mode, "set_catalog", None)
		if not callable(set_catalog):
			raise RuntimeError("User template mode is unavailable")
		previous_entries = self._user_template_entries
		previous_by_key = self._user_templates_by_key
		previous_descriptors = self._user_template_mode_descriptors
		try:
			set_catalog(descriptors)
			self._user_template_entries = frozen_entries
			self._user_templates_by_key = by_key
			self._user_template_mode_descriptors = descriptors
		except Exception:
			set_catalog(previous_descriptors)
			self._user_template_entries = previous_entries
			self._user_templates_by_key = previous_by_key
			self._user_template_mode_descriptors = previous_descriptors
			raise

	#============================================
	def atom_translate_drag_authority(self) -> str:
		"""Return the current frontend-only authority for an EditMode atom drag.

		The installed translation callback alone cannot distinguish a normal
		backend session from a legacy-isolated projection: every session installs
		the callback so keyboard nudging has one narrow interface.  This query
		keeps that distinction at the session boundary without carrying Qt
		objects across the backend-facing request boundary.
		"""
		return self._edit_drag_authority()

	#============================================
	def presentation_translate_drag_authority(self) -> str:
		"""Return the current frontend-only authority for a presentation drag.

		Presentation-only EditMode drags use the same session/projection provenance
		gate as atom drags.  The separate public name keeps the mode's two durable
		request grammars explicit while this session owns their common lifecycle
		state.
		"""
		return self._edit_drag_authority()

	#============================================
	def presentation_translate_drag_context(self) -> tuple[str, int | None]:
		"""Return one immutable authority/revision pair for an EditMode drag."""
		authority = self.presentation_translate_drag_authority()
		if authority == "backend":
			return authority, self.backend_snapshot.revision
		return authority, None


	#============================================
	def selection_translate_drag_context(self) -> tuple[str, int | None]:
		"""Return one immutable authority/revision pair for a mixed EditMode drag."""
		authority = self._edit_drag_authority()
		if authority == "backend":
			return authority, self.backend_snapshot.revision
		return authority, None

	#============================================
	def top_level_delete_authority(self) -> str:
		"""Return the current frontend-only authority for complete-root Delete.

		Complete-root Delete shares the session/projection provenance gate used by
		EditMode drags.  The public name makes its local transitional route and
		unavailable synchronized outcome explicit at the interaction boundary.
		"""
		return self._edit_drag_authority()

	#============================================
	def top_level_delete_context(self) -> tuple[str, int | None]:
		"""Return one immutable authority/revision pair for complete-root Delete."""
		authority = self.top_level_delete_authority()
		if authority == "backend":
			return authority, self.backend_snapshot.revision
		return authority, None

	#============================================
	def structure_delete_authority(self) -> str:
		"""Return the current frontend-only authority for partial structure Delete."""
		return self._edit_drag_authority()

	#============================================
	def structure_delete_context(self) -> tuple[str, int | None]:
		"""Return one immutable authority/revision pair for partial structure Delete."""
		authority = self.structure_delete_authority()
		if authority == "backend":
			return authority, self.backend_snapshot.revision
		return authority, None

	#============================================
	def atom_mark_delete_context(self) -> tuple[str, int | None]:
		"""Return one immutable authority/revision pair for selected-mark Delete."""
		authority = self._edit_drag_authority()
		if authority == "backend":
			return authority, self.backend_snapshot.revision
		return authority, None

	#============================================
	def _edit_drag_authority(self) -> str:
		"""Classify one in-flight EditMode gesture without exposing Qt state."""
		if (
				self._disposed
				or self._projection_replacing
				or self._projection_error is not None
				or self._backend_session is None
				or self._document is None
				or self._scene is None
				or self._view is None
				or self._projection_lifecycle_port is None
			):
			return "unavailable"
		if self._legacy_isolated:
			return "local"
		if self.can_commit_persistent_action:
			return "backend"
		return "unavailable"

	#============================================
	@property
	def can_undo_backend(self) -> bool:
		"""Return whether the preceding logical backend entry is available."""
		available = self.can_commit_persistent_action and self._backend_history.can_undo
		return available

	#============================================
	@property
	def has_backend_navigation(self) -> bool:
		"""Return whether this session owns generic backend history entries."""
		return self._backend_history is not None

	#============================================
	@property
	def can_redo_backend(self) -> bool:
		"""Return whether the succeeding logical backend entry is available."""
		available = (
			self.can_commit_persistent_action
			and self._backend_history.can_redo
		)
		return available

	#============================================
	def _next_arrow_provisional_id(self, revision: int) -> str:
		"""Allocate a frontend-only correlation token for one candidate arrow."""
		self._provisional_action_sequence += 1
		token = "__bkchem_new__arrow-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return token

	#============================================
	def _next_text_provisional_id(self, revision: int) -> str:
		"""Allocate a frontend-only correlation token for one candidate text."""
		self._provisional_action_sequence += 1
		token = "__bkchem_new__text-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return token

	#============================================
	def _next_plus_provisional_id(self, revision: int) -> str:
		"""Allocate a frontend-only correlation token for one candidate Plus."""
		self._provisional_action_sequence += 1
		token = "__bkchem_new__plus-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return token

	#============================================
	def _next_vector_provisional_id(self, revision: int) -> str:
		"""Allocate a frontend-only correlation token for one candidate Vector."""
		self._provisional_action_sequence += 1
		token = "__bkchem_new__vector-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return token

	#============================================
	def _next_bracket_provisional_ids(self, revision: int) -> tuple[str, str]:
		"""Allocate two distinct frontend-only tokens for one bracket pair."""
		self._provisional_action_sequence += 1
		stem = "__bkchem_new__bracket-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return stem + "-left", stem + "-right"

	#============================================
	def _next_wavy_provisional_id(self, revision: int) -> str:
		"""Allocate a frontend-only correlation token for one candidate Wavy."""
		self._provisional_action_sequence += 1
		token = "__bkchem_new__wavy-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return token

	#============================================
	def _next_template_token_stem(self, revision: int) -> str:
		"""Allocate one session-local provisional stem for OASA template preparation."""
		self._provisional_action_sequence += 1
		token_stem = "template-r%s-%s" % (
			revision, self._provisional_action_sequence,
		)
		return token_stem

	#============================================
	def _next_biomolecule_token_stem(self, revision: int) -> str:
		"""Allocate one session-local provisional stem for biomolecule placement."""
		self._provisional_action_sequence += 1
		return "biomolecule-r%s-%s" % (revision, self._provisional_action_sequence)

	#============================================
	def commit_arrow(
			self, start: tuple[float, float], end: tuple[float, float],
			) -> PersistentActionOutcome:
		"""Adapt the established Arrow route to the generic request boundary."""
		request = PersistentOperationRequest(
			"arrow.add", "Arrow",
			(("start", tuple(start)), ("end", tuple(end))),
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_atom_align(
			self, axis: str, targets: tuple[tuple[str, str], ...],
			) -> PersistentActionOutcome:
		"""Submit durable atom alignment using this live session's snapshot."""
		self._require_live_persistent_operation()
		if not isinstance(targets, tuple):
			raise TypeError("Atom alignment targets must be an immutable tuple")
		request = build_atom_align_request(self.backend_snapshot.revision, axis, targets)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_top_level_transform(
			self, expected_revision: int, mode: str,
			root_keys: tuple[tuple[str, str], ...],
			scale_x: float | None = None, scale_y: float | None = None,
			delta: tuple[float, float] | None = None,
			) -> PersistentActionOutcome:
		"""Submit one durable mixed top-level transform through this session."""
		self._require_live_persistent_operation()
		request = build_top_level_transform_request(
			expected_revision, mode, root_keys, scale_x, scale_y, delta,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_atom_translate(
			self, targets: tuple[tuple[str, str], ...], delta: tuple[float, float],
			) -> PersistentActionOutcome:
		"""Submit one durable atom nudge using this live session's snapshot."""
		self._require_live_persistent_operation()
		if not isinstance(targets, tuple) or not isinstance(delta, tuple):
			raise TypeError("Atom translation targets and delta must be immutable tuples")
		request = build_atom_translate_request(self.backend_snapshot.revision, targets, delta)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_biomolecule_template(
			self, catalog_key: str, anchor: tuple[float, float],
			) -> PersistentActionOutcome:
		"""Submit one current revision-bound packaged biomolecule placement."""
		if self._disposed:
			return PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		self._require_live_persistent_operation()
		request = PersistentOperationRequest(
			"biotemplate.insert", "Place Biomolecule Template",
			(
				("expected_revision", self.backend_snapshot.revision),
				("catalog_key", catalog_key),
				("anchor", anchor),
			),
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_user_template(
			self, catalog_key: str, anchor: tuple[float, float],
			) -> PersistentActionOutcome:
		"""Submit one current revision-bound session-delivered saved template."""
		if self._disposed:
			return PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		self._require_live_persistent_operation()
		try:
			request = build_user_template_insert_request(
				self.backend_snapshot.revision, catalog_key, anchor,
			)
		except (TypeError, ValueError) as exc:
			return PersistentActionOutcome(
				"rejected", str(exc), None, False, None, "validation",
			)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_system_template(
			self, template_name: str, anchor: tuple[float, float],
			) -> PersistentActionOutcome:
		"""Submit one current revision-bound OASA system-template placement."""
		if self._disposed:
			return PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		self._require_live_persistent_operation()
		request = PersistentOperationRequest(
			"template.insert", "Place Template",
			(
				("expected_revision", self.backend_snapshot.revision),
				("template_name", template_name),
				("anchor", anchor),
			),
		)
		return self.submit_persistent_operation(request)


	#============================================
	def submit_selection_translate(
			self, expected_revision: int, atom_targets: tuple[tuple[str, str], ...],
			presentation_root_keys: tuple[tuple[str, str], ...], delta: tuple[float, float],
			) -> PersistentActionOutcome:
		"""Submit one press-revision-bound mixed selection translation."""
		self._require_live_persistent_operation()
		request = build_selection_translate_request(
			expected_revision, atom_targets, presentation_root_keys, delta,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_atom_rotate(
			self, targets: tuple[tuple[str, str], ...], center: tuple[float, float],
			angle_radians: float,
			) -> PersistentActionOutcome:
		"""Submit one durable 2D atom rotation using this live session snapshot."""
		self._require_live_persistent_operation()
		if not isinstance(targets, tuple) or not isinstance(center, tuple):
			raise TypeError("Atom rotation targets and center must be immutable tuples")
		request = build_atom_rotate_request(
			self.backend_snapshot.revision, targets, center, angle_radians,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_bond_order(
			self, molecule_id: str, bond_id: str, order: int,
			) -> PersistentActionOutcome:
		"""Submit one exact durable bond-order edit through this live session."""
		self._require_live_persistent_operation()
		request = build_bond_order_request(
			self.backend_snapshot.revision, molecule_id, bond_id, order,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_bond_type(
			self, molecule_id: str, bond_id: str, bond_type: str,
			) -> PersistentActionOutcome:
		"""Submit one exact durable bond-type edit through this live session."""
		self._require_live_persistent_operation()
		request = build_bond_type_request(
			self.backend_snapshot.revision, molecule_id, bond_id, bond_type,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_bond_properties_patch(
			self, expected_revision: int, molecule_id: str, bond_id: str,
			changes: tuple[tuple[str, object], ...],
			) -> PersistentActionOutcome:
		"""Submit one revision-bound durable bond-properties patch through this session."""
		self._require_live_persistent_operation()
		request = build_bond_properties_patch_request(
			expected_revision, molecule_id, bond_id, changes,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_atom_properties_patch(
			self, expected_revision: int, molecule_id: str, atom_id: str,
			changes: tuple[tuple[str, object], ...],
			) -> PersistentActionOutcome:
		"""Submit one revision-bound durable atom-properties patch through this session."""
		self._require_live_persistent_operation()
		request = build_atom_properties_patch_request(
			expected_revision, molecule_id, atom_id, changes,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_text_properties_patch(
			self, expected_revision: int, text_id: str,
			changes: tuple[tuple[str, object], ...],
			) -> PersistentActionOutcome:
		"""Submit one revision-bound durable plain Text patch through this session."""
		self._require_live_persistent_operation()
		request = build_text_properties_patch_request(
			expected_revision, text_id, changes,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_rich_text_patch(
			self, expected_revision: int, text_id: str,
			runs: tuple[tuple[str, tuple[str, ...]], ...],
			changes: tuple[tuple[str, object], ...] = (),
			) -> PersistentActionOutcome:
		"""Submit one revision-bound durable rich Text run patch through this session."""
		self._require_live_persistent_operation()
		request = build_rich_text_patch_request(expected_revision, text_id, runs, changes)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_plus_properties_patch(
			self, expected_revision: int, plus_id: str,
			changes: tuple[tuple[str, object], ...],
			) -> PersistentActionOutcome:
		"""Submit one revision-bound durable plain Plus patch through this session."""
		self._require_live_persistent_operation()
		request = build_plus_properties_patch_request(
			expected_revision, plus_id, changes,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_wavy_properties_patch(
			self, expected_revision: int, wavy_id: str,
			changes: tuple[tuple[str, object], ...],
			) -> PersistentActionOutcome:
		"""Submit one revision-bound durable plain Wavy patch through this session."""
		self._require_live_persistent_operation()
		request = build_wavy_properties_patch_request(
			expected_revision, wavy_id, changes,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_fragment_create(
			self, expected_revision: int, molecule_id: str, name: str,
			fragment_type: str, atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
			) -> PersistentActionOutcome:
		"""Submit one ordinary fragment metadata creation through this session."""
		self._require_live_persistent_operation()
		request = build_fragment_create_request(
			expected_revision, molecule_id, name, fragment_type, atom_ids, bond_ids,
		)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_fragment_delete(
			self, expected_revision: int, molecule_id: str, fragment_id: str,
			) -> PersistentActionOutcome:
		"""Submit one ordinary fragment metadata deletion through this session."""
		self._require_live_persistent_operation()
		request = build_fragment_delete_request(expected_revision, molecule_id, fragment_id)
		return self.submit_persistent_operation(request)

	#============================================
	def submit_implicit_group_expand(
			self, expected_revision: int, molecule_id: str, group_id: str,
			) -> PersistentActionOutcome:
		"""Submit one backend-authoritative implicit-group expansion."""
		self._require_live_persistent_operation()
		return self.submit_persistent_operation(build_implicit_group_expand_request(
			expected_revision, molecule_id, group_id,
		))

	#============================================
	def submit_linear_form_convert(
			self, expected_revision: int, molecule_id: str, atom_ids: tuple[str, ...],
			) -> PersistentActionOutcome:
		"""Submit one durable atom-path linear-form conversion."""
		self._require_live_persistent_operation()
		return self.submit_persistent_operation(build_linear_form_convert_request(
			expected_revision, molecule_id, atom_ids,
		))

	#============================================
	def submit_persistent_operation(
			self, request: PersistentOperationRequest,
			) -> PersistentActionOutcome:
		"""Dispatch, commit, record, and project one immutable plain request."""
		if not isinstance(request, PersistentOperationRequest):
			raise TypeError("Persistent operations require PersistentOperationRequest")
		if not self.can_commit_persistent_action:
			return PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		builder = self._operation_dispatcher.get(request.operation_key)
		if builder is None:
			return PersistentActionOutcome(
				"rejected", "Unsupported persistent operation: %s" % request.operation_key,
				None, False,
			)
		snapshot = self.backend_snapshot
		try:
			prepared = builder(snapshot, request)
			if (
					prepared.executor_key == "complete-candidate"
					and prepared.value == snapshot.cdml
				):
				return PersistentActionOutcome(
					"accepted", "%s made no persistent change" % request.label,
					None, True,
				)
			executor = self._operation_commit_executors[prepared.executor_key]
			execution_result = executor(prepared)
		except oasa.cdml_document.CDMLRevisionConflictError as exc:
			return PersistentActionOutcome(
				"rejected", str(exc), None, False, None, "revision-conflict",
			)
		except oasa.cdml_document.CDMLDocumentError as exc:
			return PersistentActionOutcome(
				"rejected", str(exc), None, False, None, "validation",
			)
		except ValueError as exc:
			return PersistentActionOutcome(
				"rejected", str(exc), None, False, None, "validation",
			)
		structural_result = None
		if isinstance(
				execution_result,
				(
					oasa.cdml_document.CDMLGeometryRepairResult,
					oasa.cdml_document.CDMLAtomAlignResult,
					oasa.cdml_document.CDMLAtomTranslateResult,
					oasa.cdml_document.CDMLSelectionTranslateResult,
					oasa.cdml_document.CDMLAtomRotateResult,
					oasa.cdml_document.CDMLBondOrderEditResult,
					oasa.cdml_document.CDMLBondTypeEditResult,
					oasa.cdml_document.CDMLBondPropertiesPatchResult,
					oasa.cdml_document.CDMLAtomPropertiesPatchResult,
					oasa.cdml_document.CDMLTextPropertiesPatchResult,
					oasa.cdml_document.CDMLRichTextPatchResult,
					oasa.cdml_document.CDMLPlusPropertiesPatchResult,
					oasa.cdml_document.CDMLWavyPropertiesPatchResult,
					oasa.cdml_document.CDMLAtomMarkOperationResult,
					oasa.cdml_document.CDMLTopLevelTransformResult,
					oasa.cdml_document.CDMLLinearFormConvertResult,
				),
			):
			if not execution_result.changed:
				return PersistentActionOutcome(
					"accepted", "%s made no persistent change" % request.label,
					None, True,
				)
			commit = execution_result.commit
			if commit is None:
				raise RuntimeError("Changed persistent operation requires an accepted commit")
		elif type(execution_result) is oasa.cdml_document.CDMLStructureDeleteResult:
			commit = execution_result.commit
		elif type(execution_result) in (
				oasa.cdml_document.CDMLFragmentCreateResult,
				oasa.cdml_document.CDMLFragmentDeleteResult,
				oasa.cdml_document.CDMLImplicitGroupExpandResult,
		):
			commit = execution_result.commit
		elif isinstance(execution_result, oasa.cdml_document.CDMLStructuralEditResult):
			commit = execution_result.commit
			structural_result = execution_result
		else:
			commit = execution_result
		if _is_unchanged_authoritative_snapshot(snapshot, commit.snapshot):
			return PersistentActionOutcome(
				"accepted", f"{request.label} made no persistent change",
				None, True, structural_result,
			)
		self._record_accepted_history(request.label, commit.snapshot.revision)
		if prepared.preserve_existing_selection:
			selection_keys, selection_error = None, None
		elif type(execution_result) is oasa.cdml_document.CDMLImplicitGroupExpandResult:
			selection_keys, selection_error = frozenset({
				("atom", execution_result.replacement_atom_id),
			}), None
		else:
			selection_keys, selection_error = self._durable_selection_keys(prepared, commit)
		return self._project_accepted_commit(
			commit, "%s accepted" % request.label, structural_result, selection_keys,
			selection_error,
		)

	#============================================
	def extract_structure_fragment(
			self, expected_revision: int, molecule_id: str,
			atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
			) -> oasa.cdml_document.CDMLStructureFragmentExtractionResult:
		"""Read one backend-authoritative structural clipboard fragment."""
		self._require_live_persistent_operation()
		query = build_structure_fragment_extraction_query(
			expected_revision, molecule_id, atom_ids, bond_ids,
		)
		try:
			return self._backend_session.extract_structure_fragment(query)
		except oasa.cdml_document.CDMLDocumentError as exc:
			raise BackendFragmentExtractionError(str(exc)) from exc

	#============================================
	def extract_top_level_fragment(
			self, expected_revision: int, root_ids: tuple[str, ...],
			) -> oasa.cdml_document.CDMLTopLevelFragmentExtractionResult:
		"""Read one authoritative direct-root clipboard fragment."""
		self._require_live_persistent_operation()
		query = build_top_level_fragment_extraction_query(expected_revision, root_ids)
		try:
			return self._backend_session.extract_top_level_fragment(query)
		except oasa.cdml_document.CDMLDocumentError as exc:
			raise BackendFragmentExtractionError(str(exc)) from exc

	#============================================
	def submit_clipboard_fragment(self, fragment_cdml: str) -> PersistentActionOutcome:
		"""Commit one raw complete clipboard fragment through the OASA boundary."""
		if not self.can_commit_persistent_action:
			return PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		snapshot = self.backend_snapshot
		request = oasa.cdml_document.CDMLTopLevelInsertionRequest(
			expected_revision=snapshot.revision,
			fragment_cdml=fragment_cdml,
			translation=(20.0, 20.0),
			label="Paste",
		)
		try:
			commit = self._backend_session.insert_top_level(request)
		except oasa.cdml_document.CDMLDocumentError as exc:
			return PersistentActionOutcome("rejected", str(exc), None, False)
		except ValueError as exc:
			return PersistentActionOutcome("rejected", str(exc), None, False)
		self._record_accepted_history("Paste", commit.snapshot.revision)
		return self._project_accepted_commit(commit, "Pasted")

	#============================================
	def _build_arrow_candidate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
		) -> _PreparedPersistentOperation:
		"""Build the complete CDML candidate owned by the Arrow dispatcher key."""
		payload = dict(request.payload)
		start = payload["start"]
		end = payload["end"]
		if not isinstance(start, tuple) or not isinstance(end, tuple):
			raise ValueError("Arrow coordinates must be immutable coordinate tuples")
		candidate = bkchem_qt.io.cdml_candidate.append_arrow_candidate(
			snapshot.cdml, self._next_arrow_provisional_id(snapshot.revision),
			start, end, self.drawing_standard(),
		)
		return self._prepare_complete_candidate(snapshot.revision, candidate)

	#============================================
	def _build_text_candidate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
		) -> _PreparedPersistentOperation:
		"""Build the complete CDML candidate owned by the Text dispatcher key."""
		payload = dict(request.payload)
		if set(payload) != {"text", "position"}:
			raise ValueError("Text payload must contain exactly text and position")
		text = payload["text"]
		position = payload["position"]
		if not isinstance(text, str) or not text or text != text.strip():
			raise ValueError("Text must be a nonblank stripped string")
		if not isinstance(position, tuple) or len(position) != 2:
			raise ValueError("Text position must be a two-coordinate immutable tuple")
		if any(
				isinstance(value, bool)
				or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in position
				):
			raise ValueError("Text position coordinates must be finite real numbers")
		candidate = bkchem_qt.io.cdml_candidate.append_text_candidate(
			snapshot.cdml, self._next_text_provisional_id(snapshot.revision),
			position, text, self.drawing_standard(),
		)
		return self._prepare_complete_candidate(snapshot.revision, candidate)

	#============================================
	def _build_plus_candidate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
		) -> _PreparedPersistentOperation:
		"""Build the complete CDML candidate owned by the Plus dispatcher key."""
		payload = dict(request.payload)
		if set(payload) != {"position"}:
			raise ValueError("Plus payload must contain exactly position")
		position = payload["position"]
		if not isinstance(position, tuple) or len(position) != 2:
			raise ValueError("Plus position must be a two-coordinate immutable tuple")
		if any(
				isinstance(value, bool)
				or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in position
				):
			raise ValueError("Plus position coordinates must be finite real numbers")
		candidate = bkchem_qt.io.cdml_candidate.append_plus_candidate(
			snapshot.cdml, self._next_plus_provisional_id(snapshot.revision),
			position, self.drawing_standard(),
		)
		return self._prepare_complete_candidate(snapshot.revision, candidate)

	#============================================
	def _build_vector_candidate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
		) -> _PreparedPersistentOperation:
		"""Build one validated complete-CDML candidate for a Vector gesture."""
		if request.target_keys:
			raise ValueError("Vector creation does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"shape", "start", "end"}:
			raise ValueError("Vector payload must contain exactly shape, start, and end")
		shape = payload["shape"]
		start = payload["start"]
		end = payload["end"]
		if shape not in {"rect", "oval", "polyline"}:
			raise ValueError("Vector shape is unsupported")
		for name, point in (("start", start), ("end", end)):
			if type(point) is not tuple or len(point) != 2:
				raise ValueError("Vector %s must be a two-coordinate immutable tuple" % name)
			if any(
					isinstance(value, bool)
					or not isinstance(value, numbers.Real)
					or not math.isfinite(value)
					for value in point
				):
				raise ValueError("Vector %s coordinates must be finite real numbers" % name)
		provisional_id = self._next_vector_provisional_id(snapshot.revision)
		candidate = bkchem_qt.io.cdml_candidate.append_vector_candidate(
			snapshot.cdml, provisional_id, shape, start, end, self.drawing_standard(),
		)
		return self._prepare_complete_candidate(snapshot.revision, candidate)

	#============================================
	def _build_bracket_candidate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
		) -> _PreparedPersistentOperation:
		"""Build one atomic complete-CDML rectangular bracket candidate."""
		if request.target_keys:
			raise ValueError("Bracket creation does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"bounds"}:
			raise ValueError("Bracket payload must contain exactly bounds")
		bounds = payload["bounds"]
		if type(bounds) is not tuple or len(bounds) != 4:
			raise ValueError("Bracket bounds must be an immutable four-coordinate tuple")
		if any(
				isinstance(value, bool)
				or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in bounds
			):
			raise ValueError("Bracket bounds must contain finite real numbers")
		left, top, right, bottom = bounds
		if not left < right or not top < bottom:
			raise ValueError("Bracket bounds must have strict left-right and top-bottom order")
		candidate = bkchem_qt.io.cdml_candidate.append_rectangular_bracket_candidate(
			snapshot.cdml, self._next_bracket_provisional_ids(snapshot.revision),
			bounds, self.drawing_standard(),
		)
		prepared = self._prepare_complete_candidate(snapshot.revision, candidate)
		return dataclasses.replace(prepared, preserve_existing_selection=True)

	#============================================
	def _build_wavy_candidate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
		) -> _PreparedPersistentOperation:
		"""Build one validated complete-CDML candidate for a Wavy gesture."""
		if request.target_keys:
			raise ValueError("Wavy creation does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"start", "end"}:
			raise ValueError("Wavy payload must contain exactly start and end")
		start = payload["start"]
		end = payload["end"]
		points = bkchem_qt.wavy_geometry.wavy_points(start, end)
		if len(points) < 2:
			raise ValueError("Wavy gesture must have nonzero length")
		candidate = bkchem_qt.io.cdml_candidate.append_wavy_candidate(
			snapshot.cdml, self._next_wavy_provisional_id(snapshot.revision),
			points, self.drawing_standard(),
		)
		return self._prepare_complete_candidate(snapshot.revision, candidate)

	#============================================
	def _build_paper_properties_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Delegate paper intent to the frontend-neutral header adapter."""
		return bkchem_qt.models.document_header_operations.prepare_paper_properties(
			snapshot, request, _PreparedPersistentOperation,
		)

	#============================================
	def _build_drawing_standard_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Delegate drawing-style intent to the backend header adapter."""
		return bkchem_qt.models.document_header_operations.prepare_drawing_standard(
			snapshot, request, _PreparedPersistentOperation,
		)

	#============================================
	def _prepare_complete_candidate(
			self, expected_revision: int, candidate: str,
			) -> _PreparedPersistentOperation:
		"""Bind a complete candidate to the shared complete-CDML executor."""
		prepared = _PreparedPersistentOperation(
			"complete-candidate", expected_revision, candidate,
		)
		return prepared

	#============================================
	def _build_presentation_stack_reorder(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Validate a revision-bound presentation-only root reorder candidate."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "mode", "root_ids"}:
			raise ValueError("Presentation stack payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		mode = payload["mode"]
		root_ids = payload["root_ids"]
		if type(expected_revision) is not int:
			raise ValueError("Presentation stack expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Presentation stack expected revision does not match the current snapshot",
			)
		if mode not in {"bring-to-front", "send-back", "swap-at-slots"}:
			raise ValueError("Presentation stack mode is unsupported")
		if not isinstance(root_ids, tuple) or not root_ids:
			raise ValueError("Presentation stack root_ids must be a nonempty immutable tuple")
		if any(
				not isinstance(identifier, str) or not identifier.strip()
				for identifier in root_ids
			):
			raise ValueError("Presentation stack root IDs must be nonblank strings")
		if len(set(root_ids)) != len(root_ids):
			raise ValueError("Presentation stack root IDs must be unique")
		if mode == "swap-at-slots" and len(root_ids) < 2:
			raise ValueError("Presentation stack swap requires at least two roots")
		expected_targets = frozenset(
			("presentation", identifier) for identifier in root_ids
		)
		if request.target_keys != expected_targets:
			raise ValueError("Presentation stack target keys must match root IDs")
		candidate = bkchem_qt.io.cdml_candidate.reorder_presentation_roots_candidate(
			snapshot.cdml, root_ids, mode,
		)
		return self._prepare_complete_candidate(expected_revision, candidate)

	#============================================
	def _build_molecule_insertion(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Validate an immutable molecule-only proposal without revising it."""
		if request.target_keys:
			raise ValueError("Molecule insertion does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "proposal_cdml"}:
			raise ValueError(
				"Molecule insertion payload must contain expected_revision and proposal_cdml",
			)
		expected_revision = payload["expected_revision"]
		proposal_cdml = payload["proposal_cdml"]
		if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
			raise ValueError("Molecule insertion revision must be an integer")
		if not isinstance(proposal_cdml, str) or not proposal_cdml:
			raise ValueError("Molecule insertion proposal must be a nonempty string")
		insertion_request = oasa.cdml_document.CDMLMoleculeInsertionRequest(
			expected_revision=expected_revision,
			proposal_cdml=proposal_cdml,
			label=request.label,
		)
		prepared = _PreparedPersistentOperation(
			"molecule-insertion", expected_revision, insertion_request,
		)
		return prepared

	#============================================
	def _build_template_insertion(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Prepare one detached template proposal in OASA for normal insertion."""
		if request.target_keys:
			raise ValueError("Template insertion does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "template_name", "anchor"}:
			raise ValueError(
				"Template insertion payload must contain expected_revision, template_name, and anchor",
			)
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Template insertion expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Template insertion expected revision does not match the current snapshot",
			)
		template_name = payload["template_name"]
		if not isinstance(template_name, str) or not template_name:
			raise ValueError("Template insertion template_name must be a nonempty string")
		anchor = payload["anchor"]
		if (
				type(anchor) is not tuple
				or len(anchor) != 2
				or any(
					isinstance(value, bool)
					or not isinstance(value, numbers.Real)
					or not math.isfinite(value)
					for value in anchor
				)
			):
			raise ValueError(
				"Template insertion anchor must be a finite two-value immutable tuple",
			)
		prepared_template = oasa.template_placement.prepare_template_molecule_insertion(
			oasa.template_placement.CDMLTemplatePlacementRequest(
				template_name=template_name,
				anchor=anchor,
				token_stem=self._next_template_token_stem(snapshot.revision),
			),
		)
		if not isinstance(
				prepared_template,
				oasa.template_placement.CDMLPreparedMoleculeInsertion,
			):
			raise ValueError("Template preparation returned an invalid detached proposal")
		insertion_request = oasa.cdml_document.CDMLMoleculeInsertionRequest(
			expected_revision=expected_revision,
			proposal_cdml=prepared_template.proposal_cdml,
			label=request.label,
		)
		return _PreparedPersistentOperation(
			"molecule-insertion", expected_revision, insertion_request,
			frozenset(
				("molecule", identifier)
				for identifier in prepared_template.root_provisional_molecule_ids
			),
		)

	#============================================
	def _build_biomolecule_template_insertion(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Prepare one OASA-owned packaged biomolecule through molecule insertion."""
		if request.target_keys:
			raise ValueError("Biomolecule insertion does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "catalog_key", "anchor"}:
			raise ValueError("Biomolecule insertion payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Biomolecule insertion expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Biomolecule insertion expected revision does not match the current snapshot",
			)
		prepared = oasa.biomolecule_template_placement.prepare_biomolecule_template_insertion(
			oasa.biomolecule_template_placement.BiomoleculeTemplatePlacementRequest(
				catalog_key=payload["catalog_key"], anchor=payload["anchor"],
				token_stem=self._next_biomolecule_token_stem(snapshot.revision),
			),
		)
		if type(prepared) is not oasa.template_placement.CDMLPreparedMoleculeInsertion:
			raise ValueError("Biomolecule preparation returned an invalid detached proposal")
		insertion_request = oasa.cdml_document.CDMLMoleculeInsertionRequest(
			expected_revision, prepared.proposal_cdml, request.label,
		)
		return _PreparedPersistentOperation(
			"molecule-insertion", expected_revision, insertion_request,
			frozenset(("molecule", identifier) for identifier in prepared.root_provisional_molecule_ids),
		)

	#============================================
	def _build_user_template_insertion(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one session-frozen saved template to OASA's insertion request."""
		if request.target_keys:
			raise ValueError("User template insertion does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "catalog_key", "anchor"}:
			raise ValueError("User template insertion payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("User template insertion expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"User template insertion expected revision does not match the current snapshot",
			)
		catalog_key = payload["catalog_key"]
		if type(catalog_key) is not str or not catalog_key.strip():
			raise ValueError("User template insertion catalog_key must be nonblank")
		anchor = payload["anchor"]
		if (
			type(anchor) is not tuple or len(anchor) != 2
			or any(
				isinstance(value, bool) or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in anchor
			)
		):
			raise ValueError("User template insertion anchor must be a finite point tuple")
		if catalog_key not in self._user_templates_by_key:
			raise ValueError("User template catalog key is unavailable")
		entry = self._user_templates_by_key[catalog_key]
		insertion_request = oasa.cdml_document.CDMLUserTemplateInsertionRequest(
			expected_revision=expected_revision,
			template_cdml=entry.template_cdml,
			anchor=(float(anchor[0]), float(anchor[1])),
			label=entry.label,
		)
		return _PreparedPersistentOperation(
			"user-template-insertion", expected_revision, insertion_request,
		)

	#============================================
	def _build_geometry_repair(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one plain geometry-repair request to the OASA executor."""
		payload = dict(request.payload)
		if set(payload) != {
			"expected_revision", "molecule_ids", "kind", "target_spacing_pt",
		}:
			raise ValueError("Geometry repair payload has unsupported fields")
		molecule_ids = payload["molecule_ids"]
		if not isinstance(molecule_ids, tuple):
			raise ValueError("Geometry repair molecule_ids must be an immutable tuple")
		if request.target_keys != frozenset(("molecule", identifier) for identifier in molecule_ids):
			raise ValueError("Geometry repair target keys must match molecule IDs")
		repair_request = oasa.cdml_document.CDMLGeometryRepairRequest(
			expected_revision=payload["expected_revision"],
			molecule_ids=molecule_ids,
			kind=payload["kind"],
			target_spacing_pt=payload["target_spacing_pt"],
		)
		return _PreparedPersistentOperation(
			"geometry-repair", repair_request.expected_revision, repair_request,
			preserve_existing_selection=True,
		)

	#============================================
	def _build_atom_align(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one direct atom selection to OASA's narrow alignment operation."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "axis", "targets"}:
			raise ValueError("Atom alignment payload has unsupported fields")
		targets = payload["targets"]
		if not isinstance(targets, tuple):
			raise ValueError("Atom alignment targets must be an immutable tuple")
		if request.target_keys != (
				frozenset(("molecule", molecule_id) for molecule_id, _atom_id in targets)
				| frozenset(("atom", atom_id) for _molecule_id, atom_id in targets)
			):
			raise ValueError("Atom alignment target keys must match atom targets")
		align_request = oasa.cdml_document.CDMLAtomAlignRequest(
			expected_revision=payload["expected_revision"], axis=payload["axis"], targets=targets,
		)
		return _PreparedPersistentOperation(
			"atom-align", align_request.expected_revision, align_request,
			frozenset(("atom", atom_id) for _molecule_id, atom_id in targets),
		)

	#============================================
	def _build_atom_translate(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one direct atom nudge to OASA's atomic translation operation."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "targets", "delta"}:
			raise ValueError("Atom translation payload has unsupported fields")
		targets = payload["targets"]
		delta = payload["delta"]
		if not isinstance(targets, tuple) or not isinstance(delta, tuple):
			raise ValueError("Atom translation targets and delta must be immutable tuples")
		if request.target_keys != (
				frozenset(("molecule", molecule_id) for molecule_id, _atom_id in targets)
				| frozenset(("atom", atom_id) for _molecule_id, atom_id in targets)
			):
			raise ValueError("Atom translation target keys must match atom targets")
		translate_request = oasa.cdml_document.CDMLAtomTranslateRequest(
			expected_revision=payload["expected_revision"], targets=targets, delta=delta,
		)
		return _PreparedPersistentOperation(
			"atom-translate", translate_request.expected_revision, translate_request,
			frozenset(("atom", atom_id) for _molecule_id, atom_id in targets),
		)

	#============================================
	def _build_selection_translate(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one mixed durable selection to OASA's atomic translation operation."""
		payload = dict(request.payload)
		if set(payload) != {
				"expected_revision", "atom_targets", "presentation_root_ids", "delta",
			}:
			raise ValueError("Selection translation payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		atom_targets = payload["atom_targets"]
		presentation_root_ids = payload["presentation_root_ids"]
		delta = payload["delta"]
		if type(expected_revision) is not int:
			raise ValueError("Selection translation expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Selection translation expected revision does not match the current snapshot",
			)
		if type(atom_targets) is not tuple or type(presentation_root_ids) is not tuple:
			raise ValueError("Selection translation targets must be immutable tuples")
		if type(delta) is not tuple:
			raise ValueError("Selection translation delta must be an immutable tuple")
		if not atom_targets:
			raise ValueError("Selection translation requires durable atom targets")
		if not presentation_root_ids:
			raise ValueError("Selection translation requires durable presentation roots")
		if any(
				type(target) is not tuple or len(target) != 2
				or type(target[0]) is not str or not target[0].strip()
				or type(target[1]) is not str or not target[1].strip()
				for target in atom_targets
			):
			raise ValueError("Selection translation atom targets must be durable ID pairs")
		if any(type(identifier) is not str or not identifier.strip() for identifier in presentation_root_ids):
			raise ValueError("Selection translation presentation IDs must be nonblank strings")
		expected_target_keys = (
			frozenset(("molecule", molecule_id) for molecule_id, _atom_id in atom_targets)
			| frozenset(("atom", atom_id) for _molecule_id, atom_id in atom_targets)
			| frozenset(("presentation", identifier) for identifier in presentation_root_ids)
		)
		if request.target_keys != expected_target_keys:
			raise ValueError("Selection translation target keys must match durable targets")
		translate_request = oasa.cdml_document.CDMLSelectionTranslateRequest(
			expected_revision=expected_revision,
			atom_targets=atom_targets,
			presentation_root_ids=presentation_root_ids,
			delta=delta,
		)
		selection_keys = (
			frozenset(("atom", atom_id) for _molecule_id, atom_id in atom_targets)
			| frozenset(("presentation", identifier) for identifier in presentation_root_ids)
		)
		return _PreparedPersistentOperation(
			"selection-translate", expected_revision, translate_request, selection_keys,
		)

	#============================================
	def _build_atom_rotate(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one direct atom rotation to OASA's atomic operation."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "targets", "center", "angle_radians"}:
			raise ValueError("Atom rotation payload has unsupported fields")
		targets = payload["targets"]
		center = payload["center"]
		if not isinstance(targets, tuple) or not isinstance(center, tuple):
			raise ValueError("Atom rotation targets and center must be immutable tuples")
		if request.target_keys != (
				frozenset(("molecule", molecule_id) for molecule_id, _atom_id in targets)
				| frozenset(("atom", atom_id) for _molecule_id, atom_id in targets)
			):
			raise ValueError("Atom rotation target keys must match atom targets")
		rotate_request = oasa.cdml_document.CDMLAtomRotateRequest(
			expected_revision=payload["expected_revision"], targets=targets,
			center=center, angle_radians=payload["angle_radians"],
		)
		return _PreparedPersistentOperation(
			"atom-rotate", rotate_request.expected_revision, rotate_request,
			frozenset(("atom", atom_id) for _molecule_id, atom_id in targets),
		)

	#============================================
	def _build_bond_order_edit(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact context-menu bond order request to OASA."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "bond_id", "order"}:
			raise ValueError("Bond order payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Bond order expected_revision must be an integer")
		for field_name in ("molecule_id", "bond_id"):
			value = payload[field_name]
			if not isinstance(value, str) or not value:
				raise ValueError("Bond order %s must be a nonempty string" % field_name)
		if type(payload["order"]) is not int or payload["order"] not in (1, 2, 3):
			raise ValueError("Bond order must be 1, 2, or 3")
		molecule_id = payload["molecule_id"]
		bond_id = payload["bond_id"]
		if request.target_keys != frozenset({("molecule", molecule_id), ("bond", bond_id)}):
			raise ValueError("Bond order target keys must match durable edit targets")
		bond_order_request = oasa.cdml_document.CDMLBondOrderEditRequest(**payload)
		return _PreparedPersistentOperation(
			"bond-order-edit", bond_order_request.expected_revision, bond_order_request,
			frozenset({("bond", bond_id)}),
		)

	#============================================
	def _build_bond_type_edit(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact context-menu bond type request to OASA."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "bond_id", "bond_type"}:
			raise ValueError("Bond type payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Bond type expected_revision must be an integer")
		for field_name in ("molecule_id", "bond_id"):
			value = payload[field_name]
			if not isinstance(value, str) or not value:
				raise ValueError("Bond type %s must be a nonempty string" % field_name)
		if payload["bond_type"] not in ("n", "w", "h", "a", "b", "d", "o", "s"):
			raise ValueError("Bond type must be an ordinary type character")
		molecule_id = payload["molecule_id"]
		bond_id = payload["bond_id"]
		if request.target_keys != frozenset({("molecule", molecule_id), ("bond", bond_id)}):
			raise ValueError("Bond type target keys must match durable edit targets")
		bond_type_request = oasa.cdml_document.CDMLBondTypeEditRequest(**payload)
		return _PreparedPersistentOperation(
			"bond-type-edit", bond_type_request.expected_revision, bond_type_request,
			frozenset({("bond", bond_id)}),
		)

	#============================================
	def _build_bond_properties_patch(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one immutable direct-core bond-properties patch to OASA."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "bond_id", "changes"}:
			raise ValueError("Bond properties payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Bond properties expected_revision must be an integer")
		if payload["expected_revision"] != _snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Bond properties expected revision does not match the current snapshot",
			)
		for field_name in ("molecule_id", "bond_id"):
			value = payload[field_name]
			if not isinstance(value, str) or not value:
				raise ValueError("Bond properties %s must be a nonempty string" % field_name)
		if type(payload["changes"]) is not tuple:
			raise ValueError("Bond properties changes must be an immutable tuple")
		molecule_id = payload["molecule_id"]
		bond_id = payload["bond_id"]
		if request.target_keys != frozenset({("molecule", molecule_id), ("bond", bond_id)}):
			raise ValueError("Bond properties target keys must match durable edit targets")
		patch = oasa.cdml_document.CDMLBondPropertiesPatch(**payload)
		return _PreparedPersistentOperation(
			"bond-properties-patch", patch.expected_revision, patch,
			frozenset({("bond", bond_id)}),
		)

	#============================================
	def _build_structural_edit(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact plain Draw-mode operation to the OASA structural grammar."""
		payload = dict(request.payload)
		if "kind" not in payload:
			raise ValueError("Draw structure kind must be a string")
		kind = payload["kind"]
		if not isinstance(kind, str):
			raise ValueError("Draw structure kind must be a string")
		fields_by_kind = {
			"create-bonded-pair": {
				"expected_revision", "kind", "source_position", "target_position",
				"element", "bond_type", "bond_order", "simple_double",
			},
			"extend-atom": {
				"expected_revision", "kind", "molecule_id", "source_atom_id",
				"target_position", "element", "bond_type", "bond_order", "simple_double",
			},
			"join-atoms": {
				"expected_revision", "kind", "molecule_id", "source_atom_id",
				"target_atom_id", "bond_type", "bond_order", "simple_double",
			},
			"apply-bond-tool": {
				"expected_revision", "kind", "molecule_id", "bond_id", "bond_type",
				"bond_order", "simple_double",
			},
		}
		expected_fields = fields_by_kind.get(kind)
		if expected_fields is None or set(payload) != expected_fields:
			raise ValueError("Draw structure payload does not match its operation kind")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Draw structure expected_revision must be an integer")
		for position_name in ("source_position", "target_position"):
			if position_name not in payload:
				continue
			position = payload[position_name]
			if (
					type(position) is not tuple
					or len(position) != 2
					or any(
						isinstance(value, bool)
						or not isinstance(value, numbers.Real)
						or not math.isfinite(value)
						for value in position
					)
				):
				raise ValueError(
					"Draw structure positions must be finite two-value immutable tuples",
				)
		for identifier_name in (
				"molecule_id", "source_atom_id", "target_atom_id", "bond_id",
			):
			if identifier_name not in payload:
				continue
			identifier = payload[identifier_name]
			if not isinstance(identifier, str) or not identifier:
				raise ValueError(
					"Draw structure %s must be a nonempty durable ID" % identifier_name,
				)
		if "element" in payload and not isinstance(payload["element"], str):
			raise ValueError("Draw structure element must be a string")
		if "bond_type" not in payload or not isinstance(payload["bond_type"], str):
			raise ValueError("Draw structure bond_type must be a string")
		if type(payload["bond_order"]) is not int:
			raise ValueError("Draw structure bond_order must be an integer")
		if type(payload["simple_double"]) is not bool:
			raise ValueError("Draw structure simple_double must be a bool")
		expected_target_keys = self._structural_target_keys(kind, payload)
		if request.target_keys != expected_target_keys:
			raise ValueError("Draw structure target keys must match durable edit targets")
		structural_request = oasa.cdml_document.CDMLStructuralEditRequest(**payload)
		return _PreparedPersistentOperation(
			"structural-edit", structural_request.expected_revision, structural_request,
		)

	#============================================
	def _build_atom_element_edit(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact AtomMode element substitution to the OASA request."""
		payload = dict(request.payload)
		if set(payload) != {
				"expected_revision", "molecule_id", "atom_id", "element",
			}:
			raise ValueError("Atom element payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Atom element expected_revision must be an integer")
		for field_name in ("molecule_id", "atom_id", "element"):
			value = payload[field_name]
			if not isinstance(value, str) or not value:
				raise ValueError("Atom element %s must be a nonempty string" % field_name)
		molecule_id = payload["molecule_id"]
		atom_id = payload["atom_id"]
		expected_target_keys = frozenset({
			("molecule", molecule_id), ("atom", atom_id),
		})
		if request.target_keys != expected_target_keys:
			raise ValueError("Atom element target keys must match durable edit targets")
		atom_element_request = oasa.cdml_document.CDMLAtomElementEditRequest(
			expected_revision=expected_revision,
			molecule_id=molecule_id,
			atom_id=atom_id,
			element=payload["element"],
		)
		return _PreparedPersistentOperation(
			"atom-element-edit", atom_element_request.expected_revision,
			atom_element_request,
		)

	#============================================
	def _build_atom_properties_patch(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact atom dialog intent to the OASA patch request."""
		payload = dict(request.payload)
		if set(payload) != {
				"expected_revision", "molecule_id", "atom_id", "changes",
			}:
			raise ValueError("Atom properties payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Atom properties expected_revision must be an integer")
		if payload["expected_revision"] != _snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Atom properties expected revision does not match the current snapshot",
			)
		for field_name in ("molecule_id", "atom_id"):
			if not isinstance(payload[field_name], str) or not payload[field_name]:
				raise ValueError("Atom properties %s must be a nonempty string" % field_name)
		if type(payload["changes"]) is not tuple:
			raise ValueError("Atom properties changes must be an immutable tuple")
		molecule_id = payload["molecule_id"]
		atom_id = payload["atom_id"]
		if request.target_keys != frozenset({("molecule", molecule_id), ("atom", atom_id)}):
			raise ValueError("Atom properties target keys must match durable edit targets")
		atom_request = oasa.cdml_document.CDMLAtomPropertiesPatch(**payload)
		return _PreparedPersistentOperation(
			"atom-properties-patch", atom_request.expected_revision, atom_request,
			frozenset({("atom", atom_id)}),
		)

	#============================================
	def _build_text_properties_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact plain Text dialog intent to OASA's direct-root patch."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "text_id", "changes"}:
			raise ValueError("Text properties payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Text properties expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Text properties expected revision does not match the current snapshot",
			)
		text_id = payload["text_id"]
		if type(text_id) is not str or not text_id.strip():
			raise ValueError("Text properties text_id must contain a non-whitespace character")
		if type(payload["changes"]) is not tuple:
			raise ValueError("Text properties changes must be an immutable tuple")
		if request.target_keys != frozenset({("presentation", text_id)}):
			raise ValueError("Text properties target keys must match the durable Text target")
		text_request = oasa.cdml_document.CDMLTextPropertiesPatch(**payload)
		return _PreparedPersistentOperation(
			"text-properties-patch", text_request.expected_revision, text_request,
			frozenset({("presentation", text_id)}),
		)

	#============================================
	def _build_rich_text_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind plain frontend runs to one OASA-only rich Text patch adapter."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "text_id", "runs", "changes"}:
			raise ValueError("Rich Text payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Rich Text expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Rich Text expected revision does not match the current snapshot",
			)
		text_id = payload["text_id"]
		if type(text_id) is not str or not text_id.strip():
			raise ValueError("Rich Text text_id must contain a non-whitespace character")
		if request.target_keys != frozenset({("presentation", text_id)}):
			raise ValueError("Rich Text target keys must match the durable Text target")
		patch = rich_text_patch_from_plain_runs(
			expected_revision, text_id, payload["runs"], payload["changes"],
		)
		return _PreparedPersistentOperation(
			"rich-text-patch", patch.expected_revision, patch,
			frozenset({("presentation", text_id)}),
		)

	#============================================
	def _build_plus_properties_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact plain Plus dialog intent to OASA's root patch."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "plus_id", "changes"}:
			raise ValueError("Plus properties payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Plus properties expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Plus properties expected revision does not match the current snapshot",
			)
		plus_id = payload["plus_id"]
		if type(plus_id) is not str or not plus_id.strip():
			raise ValueError("Plus properties plus_id must contain a non-whitespace character")
		if type(payload["changes"]) is not tuple:
			raise ValueError("Plus properties changes must be an immutable tuple")
		if request.target_keys != frozenset({("presentation", plus_id)}):
			raise ValueError("Plus properties target keys must match the durable Plus target")
		plus_request = oasa.cdml_document.CDMLPlusPropertiesPatch(**payload)
		return _PreparedPersistentOperation(
			"plus-properties-patch", plus_request.expected_revision, plus_request,
			frozenset({("presentation", plus_id)}),
		)

	#============================================
	def _build_wavy_properties_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact plain Wavy dialog intent to OASA's root patch."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "wavy_id", "changes"}:
			raise ValueError("Wavy properties payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Wavy properties expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Wavy properties expected revision does not match the current snapshot",
			)
		wavy_id = payload["wavy_id"]
		if type(wavy_id) is not str or not wavy_id.strip():
			raise ValueError("Wavy properties wavy_id must contain a non-whitespace character")
		if type(payload["changes"]) is not tuple:
			raise ValueError("Wavy properties changes must be an immutable tuple")
		if request.target_keys != frozenset({("presentation", wavy_id)}):
			raise ValueError("Wavy properties target keys must match the durable Wavy target")
		wavy_request = oasa.cdml_document.CDMLWavyPropertiesPatch(**payload)
		return _PreparedPersistentOperation(
			"wavy-properties-patch", wavy_request.expected_revision, wavy_request,
			frozenset({("presentation", wavy_id)}),
		)

	#============================================
	def _build_fragment_create(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one selected molecule fragment intent to the OASA operation."""
		payload = dict(request.payload)
		if set(payload) != {
				"expected_revision", "molecule_id", "name", "fragment_type",
				"atom_ids", "bond_ids",
			}:
			raise ValueError("Fragment creation payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Fragment creation expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Fragment creation expected revision does not match the current snapshot",
			)
		for field_name in ("molecule_id", "name", "fragment_type"):
			if type(payload[field_name]) is not str:
				raise ValueError("Fragment creation %s must be a string" % field_name)
		for field_name in ("atom_ids", "bond_ids"):
			if type(payload[field_name]) is not tuple:
				raise ValueError("Fragment creation %s must be an immutable tuple" % field_name)
		molecule_id = payload["molecule_id"]
		atom_ids = payload["atom_ids"]
		bond_ids = payload["bond_ids"]
		expected_targets = frozenset({("molecule", molecule_id)}) | frozenset(
			("atom", atom_id) for atom_id in atom_ids
		) | frozenset(("bond", bond_id) for bond_id in bond_ids)
		if request.target_keys != expected_targets:
			raise ValueError("Fragment creation target keys must match durable selection")
		fragment_request = oasa.cdml_document.CDMLFragmentCreateRequest(**payload)
		return _PreparedPersistentOperation(
			"fragment-create", fragment_request.expected_revision, fragment_request,
			frozenset({("molecule", molecule_id)}),
		)

	#============================================
	def _build_fragment_delete(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one immutable ordinary fragment deletion target to OASA."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "fragment_id"}:
			raise ValueError("Fragment deletion payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Fragment deletion expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Fragment deletion expected revision does not match the current snapshot",
			)
		molecule_id = payload["molecule_id"]
		fragment_id = payload["fragment_id"]
		if type(molecule_id) is not str or type(fragment_id) is not str:
			raise ValueError("Fragment deletion targets must be strings")
		if request.target_keys != frozenset({("molecule", molecule_id)}):
			raise ValueError("Fragment deletion target keys must match durable molecule")
		fragment_request = oasa.cdml_document.CDMLFragmentDeleteRequest(**payload)
		return _PreparedPersistentOperation(
			"fragment-delete", fragment_request.expected_revision, fragment_request,
			frozenset({("molecule", molecule_id)}),
		)

	#============================================
	def _build_implicit_group_expand(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one direct implicit-group target to the OASA transaction."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "group_id"}:
			raise ValueError("Implicit group expansion payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Implicit group expansion expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Implicit group expansion expected revision does not match the current snapshot",
			)
		for field_name in ("molecule_id", "group_id"):
			if type(payload[field_name]) is not str or not payload[field_name]:
				raise ValueError("Implicit group expansion %s must be a durable ID" % field_name)
		molecule_id = payload["molecule_id"]
		group_id = payload["group_id"]
		if request.target_keys != frozenset({("molecule", molecule_id), ("group", group_id)}):
			raise ValueError("Implicit group expansion target keys must match durable targets")
		expand_request = oasa.cdml_document.CDMLImplicitGroupExpandRequest(**payload)
		return _PreparedPersistentOperation(
			"implicit-group-expand", expand_request.expected_revision, expand_request,
		)

	#============================================
	def _build_linear_form_convert(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one durable path intent to OASA's closed linear-form grammar."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "atom_ids"}:
			raise ValueError("Linear form payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Linear form expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Linear form expected revision does not match the current snapshot",
			)
		molecule_id = payload["molecule_id"]
		atom_ids = payload["atom_ids"]
		if type(molecule_id) is not str or not molecule_id or type(atom_ids) is not tuple:
			raise ValueError("Linear form requires a durable molecule and immutable atom IDs")
		expected_targets = frozenset({("molecule", molecule_id)}) | frozenset(
			("atom", atom_id) for atom_id in atom_ids
		)
		if request.target_keys != expected_targets:
			raise ValueError("Linear form target keys must match durable selection")
		linear_request = oasa.cdml_document.CDMLLinearFormConvertRequest(**payload)
		return _PreparedPersistentOperation(
			"linear-form-convert", linear_request.expected_revision, linear_request,
			frozenset(("atom", atom_id) for atom_id in atom_ids),
		)

	#============================================
	def _build_atom_mark_operation(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact MarkMode intent to OASA's atom-mark operation."""
		payload = dict(request.payload)
		if set(payload) not in (
				{"expected_revision", "molecule_id", "atom_id", "action", "mark_type"},
				{
					"expected_revision", "molecule_id", "atom_id", "action", "mark_type",
					"matching_mark_index",
				},
			):
			raise ValueError("Atom mark payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Atom mark expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Atom mark expected revision does not match the current snapshot",
			)
		for field_name in ("molecule_id", "atom_id", "action", "mark_type"):
			value = payload[field_name]
			if not isinstance(value, str) or not value:
				raise ValueError("Atom mark %s must be a nonempty string" % field_name)
		molecule_id = payload["molecule_id"]
		atom_id = payload["atom_id"]
		if request.target_keys != frozenset({
				("molecule", molecule_id), ("atom", atom_id),
			}):
			raise ValueError("Atom mark target keys must match durable edit targets")
		mark_request = oasa.cdml_document.CDMLAtomMarkOperationRequest(**payload)
		return _PreparedPersistentOperation(
			"atom-mark-operation", mark_request.expected_revision, mark_request,
			frozenset({("atom", atom_id)}),
		)

	#============================================
	def _build_atom_number_edit(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact MiscMode number assignment or clear to OASA."""
		payload = dict(request.payload)
		if set(payload) != {
				"expected_revision", "molecule_id", "atom_id", "number", "show_number",
			}:
			raise ValueError("Atom number payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Atom number expected_revision must be an integer")
		for field_name in ("molecule_id", "atom_id"):
			value = payload[field_name]
			if not isinstance(value, str) or not value:
				raise ValueError("Atom number %s must be a nonempty string" % field_name)
		number = payload["number"]
		show_number = payload["show_number"]
		if number is None and show_number is None:
			pass
		elif type(number) is int and number > 0 and type(show_number) is bool:
			pass
		else:
			raise ValueError(
				"Atom number requires a positive integer and bool, or an exact clear pair",
			)
		molecule_id = payload["molecule_id"]
		atom_id = payload["atom_id"]
		expected_target_keys = frozenset({
			("molecule", molecule_id), ("atom", atom_id),
		})
		if request.target_keys != expected_target_keys:
			raise ValueError("Atom number target keys must match durable edit targets")
		atom_number_request = oasa.cdml_document.CDMLAtomNumberEditRequest(
			expected_revision=expected_revision,
			molecule_id=molecule_id,
			atom_id=atom_id,
			number=number,
			show_number=show_number,
		)
		return _PreparedPersistentOperation(
			"atom-number-edit", atom_number_request.expected_revision,
			atom_number_request,
		)

	#============================================
	def _build_molecule_name_edit(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact direct-root molecule display-name edit to OASA."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "molecule_id", "name"}:
			raise ValueError("Molecule name payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		molecule_id = payload["molecule_id"]
		name = payload["name"]
		if type(expected_revision) is not int:
			raise ValueError("Molecule name expected_revision must be an integer")
		if not isinstance(molecule_id, str) or not molecule_id:
			raise ValueError("Molecule name molecule_id must be a nonempty string")
		if not isinstance(name, str):
			raise ValueError("Molecule name name must be a string")
		if request.target_keys != frozenset({("molecule", molecule_id)}):
			raise ValueError("Molecule name target keys must match durable root target")
		name_request = oasa.cdml_document.CDMLMoleculeNameEditRequest(
			expected_revision=expected_revision, molecule_id=molecule_id, name=name,
		)
		return _PreparedPersistentOperation(
			"molecule-name-edit", name_request.expected_revision, name_request,
		)

	#============================================
	def _structural_target_keys(
			self, kind: str, payload: dict[str, object],
			) -> frozenset[tuple[str, str]]:
		"""Return durable target identities for one exact structural operation."""
		if kind == "create-bonded-pair":
			return frozenset()
		molecule_id = payload["molecule_id"]
		if not isinstance(molecule_id, str):
			raise ValueError("Draw structure molecule_id must be a nonempty durable ID")
		target_keys = {("molecule", molecule_id)}
		if kind == "apply-bond-tool":
			bond_id = payload["bond_id"]
			if not isinstance(bond_id, str):
				raise ValueError("Draw structure bond_id must be a nonempty durable ID")
			target_keys.add(("bond", bond_id))
		else:
			source_atom_id = payload["source_atom_id"]
			if not isinstance(source_atom_id, str):
				raise ValueError("Draw structure source_atom_id must be a nonempty durable ID")
			target_keys.add(("atom", source_atom_id))
			if kind == "join-atoms":
				target_atom_id = payload["target_atom_id"]
				if not isinstance(target_atom_id, str):
					raise ValueError(
						"Draw structure target_atom_id must be a nonempty durable ID",
					)
				target_keys.add(("atom", target_atom_id))
		return frozenset(target_keys)

	#============================================
	def _build_top_level_delete(
			self, _snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind a plain direct-root deletion request to the OASA executor."""
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "root_ids"}:
			raise ValueError("Top-level Delete payload has unsupported fields")
		root_ids = payload["root_ids"]
		if not isinstance(root_ids, tuple):
			raise ValueError("Top-level Delete root_ids must be an immutable tuple")
		if request.target_keys != frozenset(
			("molecule", identifier) for identifier in root_ids
		) and request.target_keys != frozenset(
			("presentation", identifier) for identifier in root_ids
		):
			# Mixed root families are represented by their durable IDs; require each
			# key to be one of the two direct-root families without leaking Qt types.
			if {
				identifier for _kind, identifier in request.target_keys
			} != set(root_ids) or any(
				kind not in {"molecule", "presentation"}
				for kind, _identifier in request.target_keys
			):
				raise ValueError("Top-level Delete target keys must match root IDs")
		delete_request = oasa.cdml_document.CDMLTopLevelDeleteRequest(
			expected_revision=payload["expected_revision"],
			root_ids=root_ids,
			label=request.label,
		)
		return _PreparedPersistentOperation(
			"top-level-delete", delete_request.expected_revision, delete_request,
		)

	#============================================
	def _build_structure_delete(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact partial atom/bond deletion to the OASA executor."""
		payload = dict(request.payload)
		if set(payload) != {
				"expected_revision", "molecule_id", "atom_ids", "bond_ids",
			}:
			raise ValueError("Structure Delete payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		molecule_id = payload["molecule_id"]
		atom_ids = payload["atom_ids"]
		bond_ids = payload["bond_ids"]
		if type(expected_revision) is not int:
			raise ValueError("Structure Delete expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Structure Delete expected revision does not match the current snapshot",
			)
		if type(molecule_id) is not str or not molecule_id.strip():
			raise ValueError("Structure Delete molecule_id must be a nonblank durable ID")
		for identifiers in (atom_ids, bond_ids):
			if type(identifiers) is not tuple:
				raise ValueError("Structure Delete target IDs must be immutable tuples")
			if any(
				type(identifier) is not str or not identifier.strip()
				for identifier in identifiers
			):
				raise ValueError("Structure Delete target IDs must be nonblank strings")
			if len(set(identifiers)) != len(identifiers):
				raise ValueError("Structure Delete target IDs must be unique")
		if not atom_ids and not bond_ids:
			raise ValueError("Structure Delete requires at least one atom or bond")
		if set(atom_ids).intersection(bond_ids):
			raise ValueError("Structure Delete atom and bond IDs must be distinct")
		expected_targets = (
			frozenset({("molecule", molecule_id)})
			| frozenset(("atom", identifier) for identifier in atom_ids)
			| frozenset(("bond", identifier) for identifier in bond_ids)
		)
		if request.target_keys != expected_targets:
			raise ValueError("Structure Delete target keys must match its durable targets")
		delete_request = oasa.cdml_document.CDMLStructureDeleteRequest(
			expected_revision=expected_revision,
			molecule_id=molecule_id,
			atom_ids=atom_ids,
			bond_ids=bond_ids,
			label=request.label,
		)
		return _PreparedPersistentOperation(
			"structure-delete", expected_revision, delete_request,
		)

	#============================================
	def _build_top_level_transform(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind one exact durable-root transform request to OASA."""
		payload = dict(request.payload)
		expected_fields = {
			"expected_revision", "mode", "root_ids", "scale_x", "scale_y", "delta",
		}
		if set(payload) != expected_fields:
			raise ValueError("Top-level transform payload has unsupported fields")
		if type(payload["expected_revision"]) is not int:
			raise ValueError("Top-level transform expected_revision must be an integer")
		if payload["expected_revision"] != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Top-level transform expected revision does not match the current snapshot",
			)
		root_ids = payload["root_ids"]
		if (
			type(root_ids) is not tuple or not root_ids
			or any(type(identifier) is not str or not identifier for identifier in root_ids)
			or len(set(root_ids)) != len(root_ids)
		):
			raise ValueError("Top-level transform root_ids must be unique nonempty strings")
		if request.target_keys != frozenset(
			(kind, identifier)
			for kind, identifier in request.target_keys
			if kind in {"molecule", "presentation"} and identifier in root_ids
		) or {identifier for _kind, identifier in request.target_keys} != set(root_ids):
			raise ValueError("Top-level transform target keys must match root IDs")
		canonical_document = oasa.cdml_document.CDMLDocument.parse(
			snapshot.cdml, validation="compat",
		)
		presentation_names = {
			"arrow", "text", "plus", "rect", "square", "oval", "circle",
			"polygon", "polyline",
		}
		canonical_root_keys = frozenset(
			("molecule", record.identifier)
			if record.local_name == "molecule"
			else ("presentation", record.identifier)
			for record in canonical_document.objects()
			if record.identifier is not None and (
				record.local_name == "molecule"
				or record.local_name in presentation_names
			)
		)
		if request.target_keys - canonical_root_keys:
			raise ValueError(
				"Top-level transform target keys must match authoritative root kinds",
			)
		transform_request = oasa.cdml_document.CDMLTopLevelTransformRequest(**payload)
		return _PreparedPersistentOperation(
			"top-level-transform", transform_request.expected_revision, transform_request,
			request.target_keys,
		)

	#============================================
	def _commit_complete_candidate(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one validated complete-CDML operation through OASA."""
		if not isinstance(prepared.value, str):
			raise ValueError("Complete CDML operation requires a string candidate")
		commit = self._backend_session.commit(
			expected_revision=prepared.expected_revision,
			complete_cdml=prepared.value,
		)
		return commit

	#============================================
	def _commit_molecule_insertion(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one validated molecule proposal through OASA composition."""
		if not isinstance(
				prepared.value, oasa.cdml_document.CDMLMoleculeInsertionRequest,
			):
			raise ValueError("Molecule insertion requires a molecule insertion request")
		commit = self._backend_session.insert_molecules(prepared.value)
		return commit

	#============================================
	def _commit_user_template_insertion(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Submit one prepared serialized user-template insertion to OASA."""
		if type(prepared.value) is not oasa.cdml_document.CDMLUserTemplateInsertionRequest:
			raise ValueError("User template insertion requires an exact insertion request")
		return self._backend_session.insert_user_template(prepared.value)

	#============================================
	def _commit_geometry_repair(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLGeometryRepairResult:
		"""Execute one backend-owned geometry repair without a Qt candidate."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLGeometryRepairRequest):
			raise ValueError("Geometry repair requires a geometry repair request")
		return self._backend_session.repair_geometry(prepared.value)

	#============================================
	def _commit_atom_align(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomAlignResult:
		"""Execute one backend-owned direct atom alignment."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomAlignRequest):
			raise ValueError("Atom alignment requires an atom alignment request")
		return self._backend_session.align_atoms(prepared.value)

	#============================================
	def _commit_atom_translate(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomTranslateResult:
		"""Execute one backend-owned direct atom translation."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomTranslateRequest):
			raise ValueError("Atom translation requires an atom translation request")
		return self._backend_session.translate_atoms(prepared.value)

	#============================================
	def _commit_selection_translate(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLSelectionTranslateResult:
		"""Execute one backend-owned mixed atom/presentation translation."""
		if type(prepared.value) is not oasa.cdml_document.CDMLSelectionTranslateRequest:
			raise ValueError("Selection translation requires an exact translation request")
		return self._backend_session.translate_selection(prepared.value)

	#============================================
	def _commit_atom_rotate(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomRotateResult:
		"""Execute one backend-owned direct atom rotation."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomRotateRequest):
			raise ValueError("Atom rotation requires an atom rotation request")
		return self._backend_session.rotate_atoms(prepared.value)

	#============================================
	def _commit_bond_order_edit(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLBondOrderEditResult:
		"""Execute one backend-owned exact bond-order edit."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLBondOrderEditRequest):
			raise ValueError("Bond order requires a bond order edit request")
		return self._backend_session.set_bond_order(prepared.value)

	#============================================
	def _commit_bond_type_edit(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLBondTypeEditResult:
		"""Execute one backend-owned exact bond-type edit."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLBondTypeEditRequest):
			raise ValueError("Bond type requires a bond type edit request")
		return self._backend_session.set_bond_type(prepared.value)

	#============================================
	def _commit_bond_properties_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLBondPropertiesPatchResult:
		"""Execute one backend-owned explicit bond-properties patch."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLBondPropertiesPatch):
			raise ValueError("Bond properties requires a bond properties patch")
		return self._backend_session.patch_bond_properties(prepared.value)

	#============================================
	def _commit_structural_edit(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLStructuralEditResult:
		"""Execute one backend-owned Draw-mode operation without a CDML candidate."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLStructuralEditRequest):
			raise ValueError("Draw structure requires a structural edit request")
		return self._backend_session.edit_structure(prepared.value)

	#============================================
	def _commit_atom_element_edit(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one backend-owned AtomMode element substitution."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomElementEditRequest):
			raise ValueError("Atom element requires an element edit request")
		return self._backend_session.set_atom_element(prepared.value)

	#============================================
	def _commit_atom_properties_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomPropertiesPatchResult:
		"""Execute one backend-owned explicit atom-properties patch."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomPropertiesPatch):
			raise ValueError("Atom properties requires an atom properties patch")
		return self._backend_session.patch_atom_properties(prepared.value)

	#============================================
	def _commit_text_properties_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLTextPropertiesPatchResult:
		"""Execute one backend-owned explicit plain Text-properties patch."""
		if type(prepared.value) is not oasa.cdml_document.CDMLTextPropertiesPatch:
			raise ValueError("Text properties requires an exact Text properties patch")
		return self._backend_session.patch_text_properties(prepared.value)

	#============================================
	def _commit_rich_text_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLRichTextPatchResult:
		"""Execute one backend-owned authored rich Text patch."""
		if type(prepared.value) is not oasa.cdml_document.CDMLRichTextPatch:
			raise ValueError("Rich Text requires an exact rich Text patch")
		return self._backend_session.patch_rich_text(prepared.value)

	#============================================
	def _commit_plus_properties_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLPlusPropertiesPatchResult:
		"""Execute one backend-owned explicit plain Plus-properties patch."""
		if type(prepared.value) is not oasa.cdml_document.CDMLPlusPropertiesPatch:
			raise ValueError("Plus properties requires an exact Plus properties patch")
		return self._backend_session.patch_plus_properties(prepared.value)

	#============================================
	def _commit_wavy_properties_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLWavyPropertiesPatchResult:
		"""Execute one backend-owned explicit plain Wavy-properties patch."""
		if type(prepared.value) is not oasa.cdml_document.CDMLWavyPropertiesPatch:
			raise ValueError("Wavy properties requires an exact Wavy properties patch")
		return self._backend_session.patch_wavy_properties(prepared.value)

	#============================================
	def _commit_fragment_create(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLFragmentCreateResult:
		"""Execute one backend-owned ordinary fragment creation."""
		if type(prepared.value) is not oasa.cdml_document.CDMLFragmentCreateRequest:
			raise ValueError("Fragment creation requires an exact fragment request")
		return self._backend_session.create_fragment(prepared.value)

	#============================================
	def _commit_fragment_delete(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLFragmentDeleteResult:
		"""Execute one backend-owned ordinary fragment deletion."""
		if type(prepared.value) is not oasa.cdml_document.CDMLFragmentDeleteRequest:
			raise ValueError("Fragment deletion requires an exact fragment request")
		return self._backend_session.delete_fragment(prepared.value)

	#============================================
	def _commit_implicit_group_expand(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLImplicitGroupExpandResult:
		"""Execute one backend-owned implicit-group expansion."""
		if type(prepared.value) is not oasa.cdml_document.CDMLImplicitGroupExpandRequest:
			raise ValueError("Implicit group expansion requires an exact request")
		return self._backend_session.expand_implicit_group(prepared.value)

	#============================================
	def _commit_linear_form_convert(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLLinearFormConvertResult:
		"""Execute one backend-owned atom-path linear-form conversion."""
		if type(prepared.value) is not oasa.cdml_document.CDMLLinearFormConvertRequest:
			raise ValueError("Linear form requires an exact conversion request")
		return self._backend_session.convert_linear_form(prepared.value)

	#============================================
	def _commit_atom_mark_operation(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomMarkOperationResult:
		"""Execute one backend-owned atom-mark add or removal."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomMarkOperationRequest):
			raise ValueError("Atom mark requires an atom-mark operation request")
		return self._backend_session.apply_atom_mark(prepared.value)

	#============================================
	def _commit_atom_number_edit(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one backend-owned atom-number assignment or clear."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLAtomNumberEditRequest):
			raise ValueError("Atom number requires an atom number edit request")
		return self._backend_session.set_atom_number(prepared.value)

	#============================================
	def _commit_molecule_name_edit(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one backend-owned direct-root molecule display-name edit."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLMoleculeNameEditRequest):
			raise ValueError("Molecule name requires a molecule name edit request")
		return self._backend_session.set_molecule_name(prepared.value)

	#============================================
	def _commit_paper_properties_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Apply one backend-owned explicit paper-properties patch."""
		return bkchem_qt.models.document_header_operations.commit_paper_properties(
			self._backend_session, prepared,
		)

	#============================================
	def _commit_drawing_standard_patch(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Apply one backend-owned explicit drawing-standard patch."""
		return bkchem_qt.models.document_header_operations.commit_drawing_standard(
			self._backend_session, prepared,
		)

	#============================================
	def _commit_top_level_delete(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one backend-owned direct-root deletion."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLTopLevelDeleteRequest):
			raise ValueError("Top-level Delete requires a deletion request")
		return self._backend_session.delete_top_level(prepared.value)

	#============================================
	def _commit_structure_delete(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLStructureDeleteResult:
		"""Execute one backend-owned partial atom/bond deletion."""
		if type(prepared.value) is not oasa.cdml_document.CDMLStructureDeleteRequest:
			raise ValueError("Structure Delete requires an exact deletion request")
		result = self._backend_session.delete_structure(prepared.value)
		if type(result) is not oasa.cdml_document.CDMLStructureDeleteResult:
			raise ValueError("Structure Delete requires an exact deletion result")
		return result

	#============================================
	def _commit_top_level_transform(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLTopLevelTransformResult:
		"""Execute one backend-owned durable-root affine transform."""
		if type(prepared.value) is not oasa.cdml_document.CDMLTopLevelTransformRequest:
			raise ValueError("Top-level transform requires a transform request")
		return self._backend_session.apply_top_level_transform(prepared.value)

	#============================================
	def _record_accepted_history(self, label: str, revision: int) -> None:
		"""Append an accepted edit after dropping logical redo entries."""
		self._backend_history = self._backend_history.append_accepted(label, revision)

	#============================================
	def _durable_selection_keys(
			self, prepared: _PreparedPersistentOperation,
			commit: oasa.cdml_document.CDMLCommit,
			) -> tuple[frozenset[tuple[str, str]], str | None]:
		"""Translate optional proposal tokens only to accepted direct-root records."""
		if not prepared.provisional_selection_keys:
			return frozenset(), None
		if prepared.executor_key in (
			"atom-align", "atom-translate", "selection-translate", "atom-rotate", "bond-order-edit", "bond-type-edit",
			"bond-properties-patch", "atom-properties-patch", "text-properties-patch",
			"rich-text-patch",
			"plus-properties-patch",
			"wavy-properties-patch",
			"atom-mark-operation",
			"fragment-create", "fragment-delete",
			"linear-form-convert",
			"top-level-transform",
			):
			# These direct-core edits preserve durable IDs; retain only their immutable
			# target selections across the replacement projection.
			return prepared.provisional_selection_keys, None
		canonical_document = oasa.cdml_document.CDMLDocument.parse(
			commit.snapshot.cdml, validation="compat",
		)
		direct_root_keys = frozenset(
			(record.local_name, record.identifier)
			for record in canonical_document.objects()
			if record.identifier is not None
		)
		selection_keys = []
		for kind, identifier in prepared.provisional_selection_keys:
			if identifier not in commit.id_map:
				return frozenset(), (
					"Persistent edit was accepted but selection correlation is unavailable"
				)
			durable_identifier = commit.id_map[identifier]
			if not isinstance(durable_identifier, str) or not durable_identifier:
				return frozenset(), (
					"Persistent edit was accepted but selection correlation is unavailable"
				)
			if (kind, durable_identifier) not in direct_root_keys:
				return frozenset(), (
					"Persistent edit was accepted but selection correlation is unavailable"
				)
			selection_keys.append((kind, durable_identifier))
		return frozenset(selection_keys), None

	#============================================
	def _project_accepted_commit(
			self, commit: oasa.cdml_document.CDMLCommit, success_message: str,
			structural_result: oasa.cdml_document.CDMLStructuralEditResult | None = None,
			selection_keys: frozenset[tuple[str, str]] | None = None,
			selection_error: str | None = None,
			) -> PersistentActionOutcome:
		"""Project accepted backend state without ever rolling it back."""
		self._backend_projection_synchronized = False
		if selection_keys is not None:
			self._accepted_projection_selection = (
				commit.snapshot.revision, selection_keys,
			)
		port = self._projection_lifecycle_port
		if port is None:
			projected = bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.SESSION,
			)
		else:
			projected = port.project(commit.snapshot)
		if projected.installed:
			self._clear_accepted_projection_selection(commit.snapshot)
			if selection_error is not None:
				return PersistentActionOutcome(
					"selection-unavailable", selection_error, commit, True, structural_result,
				)
			return PersistentActionOutcome(
				"accepted", success_message, commit, True, structural_result,
			)
		return PersistentActionOutcome(
			"unavailable",
			"Persistent edit was accepted but its projection is unavailable; retry or reopen",
			commit, True, structural_result,
		)

	#============================================
	def _clear_accepted_projection_selection(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> None:
		"""Drop a one-shot durable selection intent after its snapshot is projected."""
		selection = self._accepted_projection_selection
		if selection is not None and selection[0] == snapshot.revision:
			self._accepted_projection_selection = None

	#============================================
	def retry_current_backend_projection(self) -> PersistentActionOutcome:
		"""Rebuild exactly the current backend snapshot after a failed projection."""
		if self._legacy_isolated:
			return PersistentActionOutcome(
				"unavailable",
				"Qt-local edits are isolated; discard them before backend reprojection",
				None,
			)
		return self._retry_current_backend_projection()

	#============================================
	def _discard_legacy_and_retry_projection(self) -> PersistentActionOutcome:
		"""Rebuild from backend after a frontend has confirmed Qt-edit discard."""
		return self._retry_current_backend_projection()

	#============================================
	def _retry_current_backend_projection(self) -> PersistentActionOutcome:
		"""Run one exact snapshot reprojection after an explicit safe recovery."""
		if self._disposed or self._projection_lifecycle_port is None:
			return PersistentActionOutcome(
				"unavailable", "Document projection retry is unavailable", None,
			)
		snapshot = self.backend_snapshot
		projected = self._projection_lifecycle_port.project(snapshot)
		if not projected.installed:
			return PersistentActionOutcome(
				"unavailable", "Document projection retry is unavailable", None,
			)
		self._legacy_isolated = False
		self._clear_accepted_projection_selection(snapshot)
		return PersistentActionOutcome("accepted", "Backend projection restored", None)

	#============================================
	def undo_backend(self) -> PersistentActionOutcome:
		"""Restore the predecessor logical history entry through OASA."""
		return self._restore_backend_navigation("undo")

	#============================================
	def redo_backend(self) -> PersistentActionOutcome:
		"""Restore the successor logical history entry through OASA."""
		return self._restore_backend_navigation("redo")

	#============================================
	def _restore_backend_navigation(self, direction: str) -> PersistentActionOutcome:
		"""Restore one adjacent entry and replace only its physical revision."""
		if not self.can_commit_persistent_action:
			return PersistentActionOutcome(
				"unavailable", "Backend %s is unavailable" % direction, None,
			)
		target = self._backend_history.adjacent_target(direction)
		if target is None:
			return PersistentActionOutcome(
				"unavailable", "Backend %s is unavailable" % direction, None,
			)
		destination, entry = target
		before_revision = self.backend_snapshot.revision
		try:
			commit = self._backend_session.restore(
				target_revision=entry.revision, expected_revision=before_revision,
			)
		except oasa.cdml_document.CDMLRevisionUnavailableError as exc:
			return PersistentActionOutcome("unavailable", str(exc), None)
		except oasa.cdml_document.CDMLDocumentError as exc:
			return PersistentActionOutcome("rejected", str(exc), None)
		self._backend_history = self._backend_history.record_restored(
			destination, commit.snapshot.revision,
		)
		success_message = "%s %s" % (
			entry.label,
			"undone" if direction == "undo" else "redone",
		)
		return self._project_accepted_commit(commit, success_message)

	#============================================
	def replace_projection_from_backend_snapshot(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
		"""Replace this Qt projection from one exact current backend snapshot.

		Only a snapshot returned by this session's current backend authority can
		be installed.  The requested current snapshot is prepared before any live
		Qt projection is retired; an accepted backend revision is never rolled back
		to an older displayed projection after a Qt failure.
		"""
		if (
				self._disposed
				or self._projection_replacing
				or snapshot != self.backend_snapshot
			):
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.SESSION,
			)
		from bkchem_qt.io import cdml_document_io
		try:
			projection_snapshot = self._backend_session.projection_snapshot()
			if projection_snapshot.snapshot != snapshot:
				raise ValueError("backend projection envelope does not match the requested snapshot")
			candidate = cdml_document_io.prepare_synchronized_projection(
				projection_snapshot, self._projection_retirement_reaper,
			)
		except Exception as exc:
			self._backend_projection_synchronized = False
			self._projection_error = ProjectionReplacementError(
				"Could not prepare the current backend CDML projection",
			)
			self._projection_error.__cause__ = exc
			self.title_changed.emit(self.title)
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
				self._projection_error,
			)

		self._projection_replacing = True
		retirement_started = False
		result = None
		try:
			file_path = self._origin_path
			selected_keys = self._accepted_selection_keys_for_snapshot(snapshot)
			if self._document is not None:
				file_path = self._document.file_path
				# Validate immediately before both native selection boundaries.
				if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(self._scene):
					raise ProjectionReplacementError("Current projection scene is unavailable")
				if selected_keys is None:
					selected_keys = frozenset(
						key for key in (
							bkchem_qt.canvas.document_projection.persistent_selection_key(item)
							for item in self._scene.selectedItems()
						) if key is not None
					)
			if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(self._scene):
				raise ProjectionReplacementError("Current projection scene is unavailable")
			self._scene.clearSelection()
			if selected_keys is None:
				selected_keys = frozenset()
			retirement_started = self._document is not None
			if retirement_started:
				self._dispose_current_projection()
			self._install_prepared_projection(candidate, selected_keys, file_path, snapshot)
			self._projected_backend_snapshot = snapshot
			self._backend_projection_synchronized = True
			self._projection_error = None
			result = bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLED,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.COMPLETE,
			)
		except Exception as exc:
			try:
				self._dispose_prepared_projection(candidate)
			except Exception as cleanup_exc:
				# The failed candidate remains terminal frontend-only state.  Keep its
				# cleanup diagnostic without allowing it to replace the failure that
				# caused projection replacement to fail.
				self._teardown_diagnostics.append(cleanup_exc)
			self._backend_projection_synchronized = False
			phase = (
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION
				if retirement_started
				else bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.RETIREMENT
			)
			status = (
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED
				if retirement_started
				else bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE
			)
			message = (
				"Current backend projection installation failed after retirement"
				if retirement_started else "Current projection replacement could not begin"
			)
			self._projection_error = ProjectionReplacementError(message)
			self._projection_error.__cause__ = exc
			if retirement_started:
				self._document = None
			self.title_changed.emit(self.title)
			result = bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				status, phase, self._projection_error,
			)
		finally:
			self._projection_replacing = False
		return result

	#============================================
	def _accepted_selection_keys_for_snapshot(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> frozenset[tuple[str, str]] | None:
		"""Return a pending accepted selection only for its exact backend snapshot."""
		selection = self._accepted_projection_selection
		if selection is None or selection[0] != snapshot.revision:
			return None
		return selection[1]

	#============================================
	def _dispose_current_projection(self) -> None:
		"""Terminally detach the current generation without scene furniture.

		This is deliberately a cleanup transaction, rather than an all-or-nothing
		series of calls.  Once replacement starts, no part of the old Qt document
		may remain available for recovery: recovery is always reconstructed from a
		backend snapshot.  Continue every independent teardown step after a
		callback failure, then re-raise the original diagnostic for the caller to
		record as a failed replacement.
		"""
		old_document = self._document
		if old_document is None:
			return
		first_error = None
		if self._document_modified_connected:
			try:
				old_document.modified_changed.disconnect(self._on_modified_changed)
			except Exception as exc:
				first_error = exc
			self._document_modified_connected = False
		if self._document_persistent_mutation_connected:
			try:
				old_document.persistent_mutated.disconnect(self._on_persistent_mutated)
			except Exception as exc:
				if first_error is None:
					first_error = exc
			self._document_persistent_mutation_connected = False
		try:
			old_document._dispose_document_graphics(self._projection_retirement_reaper)
		except Exception as exc:
			if first_error is None:
				first_error = exc
		try:
			old_document.undo_stack.clear()
		except Exception as exc:
			if first_error is None:
				first_error = exc
		try:
			old_document.set_scene(None)
		except Exception as exc:
			if first_error is None:
				first_error = exc
		try:
			self._view.set_document(None)
		except Exception as exc:
			if first_error is None:
				first_error = exc
		try:
			old_document.clear()
		except Exception as exc:
			if first_error is None:
				first_error = exc
		finally:
			# Never leave a partially cleared document parented to the session.
			# Deleting it later is safer than allowing a second projection to share
			# its models, callbacks, or QGraphicsItem wrappers.
			try:
				old_document.setParent(None)
			except Exception as exc:
				if first_error is None:
					first_error = exc
			try:
				old_document.deleteLater()
			except Exception as exc:
				if first_error is None:
					first_error = exc
			self._document = None
		if first_error is not None:
			raise ProjectionReplacementError(
				"Old Qt projection was detached after a disposal failure",
			) from first_error

	#============================================
	def _install_prepared_projection(
			self, prepared: object, selected_keys: frozenset[tuple[str, str]],
			file_path: str | None, projected_snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> None:
		"""Install one fully prepared projection without decoding or serialization."""
		document = prepared.document
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(document):
			raise ProjectionReplacementError("Prepared Document wrapper is unavailable")
		document.file_path = file_path
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(document):
			raise ProjectionReplacementError("Prepared Document wrapper is unavailable")
		document.set_graphics_retirement_reaper(
			self._projection_retirement_reaper,
		)
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(document):
			raise ProjectionReplacementError("Prepared Document wrapper is unavailable")
		document.setParent(self)
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(document):
			raise ProjectionReplacementError("Prepared Document wrapper is unavailable")
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(self._scene):
			raise ProjectionReplacementError("Projection scene is unavailable")
		document.set_scene(self._scene)
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(self._view):
			raise ProjectionReplacementError("Projection view is unavailable")
		self._view.set_document(document)
		def add_scene_root(item: object, role: str) -> None:
			"""Cross one checked native scene-add boundary for a prepared root."""
			if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(self._scene):
				raise ProjectionReplacementError("Projection scene is unavailable")
			if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(item):
				raise ProjectionReplacementError("Prepared %s wrapper is unavailable" % role)
			self._scene.addItem(item)
		for _molecule, items in prepared.molecule_projections:
			for item in items:
				add_scene_root(item, "molecule")
		for item in prepared.presentation_items:
			add_scene_root(item, "presentation")
		for atom_item, mark_items in prepared.mark_parent_items:
			if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(atom_item):
				raise ProjectionReplacementError("Prepared mark parent wrapper is unavailable")
			for item in mark_items:
				if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(item):
					raise ProjectionReplacementError("Prepared mark wrapper is unavailable")
				if item.parentItem() is not atom_item:
					raise ProjectionReplacementError("Prepared mark lost atom-parent ownership")
		projection_items = tuple(
			item
			for _molecule, items in prepared.molecule_projections
			for item in items
		) + tuple(prepared.presentation_items) + tuple(prepared.mark_items)
		document.register_current_projection_items(projection_items)
		if hasattr(self._scene, "apply_paper_model"):
			self._scene.apply_paper_model(document.paper)
		bkchem_qt.canvas.document_projection.synchronize_document_stack_z_order(
			document, self._scene,
		)
		bkchem_qt.canvas.document_projection.select_projected_persistent_keys(
			self._scene, selected_keys,
		)
		if projected_snapshot.is_dirty:
			document.mark_dirty()
		else:
			document.mark_clean()
		self._document = document
		document.modified_changed.connect(self._on_modified_changed)
		self._document_modified_connected = True
		document.persistent_mutated.connect(self._on_persistent_mutated)
		self._document_persistent_mutation_connected = True
		self._projected_backend_snapshot = projected_snapshot
		self._projected_persistent_generation = document.persistent_generation
		self._backend_projection_synchronized = True
		# Dirty state was established before this connection so backend-derived
		# dirtiness cannot invalidate the synchronization latch.  Publish the
		# replacement afterwards so registered tabs receive one title refresh.
		self.title_changed.emit(self.title)

	#============================================
	def _dispose_prepared_projection(self, prepared: object) -> None:
		"""Release an uninstalled or partially installed frontend-only bundle."""
		from bkchem_qt.io import cdml_document_io
		document = prepared.document
		if self._document_modified_connected and document is self._document:
			try:
				document.modified_changed.disconnect(self._on_modified_changed)
			except (RuntimeError, TypeError):
				pass
			self._document_modified_connected = False
		if self._document_persistent_mutation_connected and document is self._document:
			try:
				document.persistent_mutated.disconnect(self._on_persistent_mutated)
			except (RuntimeError, TypeError):
				pass
			self._document_persistent_mutation_connected = False
		if self._view.document is document:
			self._view.set_document(None)
		try:
			document.set_scene(None)
		except (RuntimeError, TypeError):
			pass
		cdml_document_io.dispose_prepared_projection(
			prepared, self._projection_retirement_reaper,
		)

	#============================================
	def write_backend_snapshot(self, file_path: str) -> oasa.cdml_document.CDMLSnapshot:
		"""Write one exact synchronized backend snapshot, then mark it saved."""
		self._require_live_persistent_operation()
		if not self.can_write_authoritative_snapshot:
			raise BackendProjectionOutOfSyncError(
				"Cannot save backend CDML while the Qt projection is not a current "
				"authoritative projection",
			)
		snapshot = self._backend_session.snapshot()
		if (
				self._projected_backend_snapshot != snapshot
				or self._document.persistent_generation != self._projected_persistent_generation
			):
			raise BackendProjectionOutOfSyncError(
				"Cannot save backend CDML after Qt-local persistent mutation",
			)
		_write_backend_snapshot(file_path, snapshot)
		try:
			saved_snapshot = self._backend_session.mark_saved(
				expected_revision=snapshot.revision,
			)
		except Exception as exc:
			raise BackendSnapshotPublicationError(
				"CDML target was atomically replaced and may contain the canonical "
				"snapshot, but backend saved-state marking failed; this Save attempt "
				"did not change the backend saved baseline",
			) from exc
		self._projected_backend_snapshot = saved_snapshot
		self._projected_persistent_generation = self._document.persistent_generation
		self._backend_projection_synchronized = True
		try:
			self._document.mark_clean()
		except Exception:
			# Publication and the backend saved baseline already succeeded.  Keep a
			# conservative dirty/ineligible projection rather than reporting a
			# completed Save as failed because local presentation cleanup faulted.
			pass
		return saved_snapshot

	#============================================
	@classmethod
	def prepare_native_cdml(cls, cdml_text: str) -> PreparedNativeCDML:
		"""Validate CDML and stage a detached projection without live mutation."""
		backend_session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
		from bkchem_qt.io import cdml_document_io
		projection_snapshot = backend_session.projection_snapshot()
		document = cdml_document_io.hydrate_synchronized_cdml_document(
			projection_snapshot,
		)
		return PreparedNativeCDML(
			factory_token=_PREPARED_NATIVE_FACTORY_TOKEN,
			snapshot=projection_snapshot.snapshot,
			document=document,
		)

	#============================================
	@classmethod
	def prepare_imported_cdml(cls, cdml_text: str) -> PreparedImportedCDML:
		"""Stage imported external content against the backend empty baseline."""
		backend_session = oasa.cdml_document.CDMLDocumentSession.load_imported(cdml_text)
		from bkchem_qt.io import cdml_document_io
		projection_snapshot = backend_session.projection_snapshot()
		document = cdml_document_io.hydrate_synchronized_cdml_document(
			projection_snapshot,
		)
		return PreparedImportedCDML(
			factory_token=_PREPARED_IMPORTED_FACTORY_TOKEN,
			snapshot=projection_snapshot.snapshot,
			document=document,
		)

	# ------------------------------------------------------------------
	# Owned state and tab title
	# ------------------------------------------------------------------

	#============================================
	@property
	def document(self) -> bkchem_qt.models.document.Document | None:
		"""Return this session's live Qt projection and interaction model."""
		return self._document

	#============================================
	@property
	def has_live_projection(self) -> bool:
		"""Return whether this session can serve legacy Qt document operations."""
		return not self._disposed and self._document is not None

	#============================================
	@property
	def can_write_authoritative_snapshot(self) -> bool:
		"""Return whether this Qt projection may publish the backend snapshot.

		The predicate is intentionally total.  It proves controlled projection
		provenance; it never treats a Qt serializer as evidence that a locally
		edited document equals the backend-owned CDML.
		"""
		if (
				self._disposed
				or self._projection_replacing
				or self._projection_error is not None
				or self._backend_session is None
				or self._document is None
				or self._scene is None
				or self._view is None
				or self._projected_backend_snapshot is None
				or self._projected_persistent_generation is None
				or not self._backend_projection_synchronized
			):
			return False
		try:
			current_snapshot = self._backend_session.snapshot()
			return (
				self._view.document is self._document
				and self._document._scene is self._scene
				and self._projected_backend_snapshot == current_snapshot
				and self._document.dirty == current_snapshot.is_dirty
				and self._document.persistent_generation
				== self._projected_persistent_generation
			)
		except Exception:
			return False

	#============================================
	def _current_recovery_snapshot(self) -> oasa.cdml_document.CDMLSnapshot:
		"""Return one current snapshot or reject a terminal/malformed backend."""
		if self._disposed or self._backend_session is None:
			raise RuntimeError("Recovery Export requires a live backend session")
		try:
			snapshot = self._backend_session.snapshot()
		except Exception as exc:
			raise RuntimeError(
				"Recovery Export requires a readable backend snapshot",
			) from exc
		if not isinstance(snapshot, oasa.cdml_document.CDMLSnapshot):
			raise RuntimeError("Recovery Export requires an immutable backend snapshot")
		return snapshot

	#============================================
	@property
	def can_recovery_export(self) -> bool:
		"""Return whether this live session can publish one backend snapshot."""
		try:
			self._current_recovery_snapshot()
		except Exception:
			return False
		return True

	#============================================
	def close_state(self) -> CloseState:
		"""Return document-free facts that govern confirmation before disposal."""
		snapshot = self._current_recovery_snapshot()
		backend_unseen = (
			not self._backend_projection_synchronized
			or self._projected_backend_snapshot != snapshot
		)
		state = CloseState(
			backend_dirty=snapshot.is_dirty,
			backend_unseen=backend_unseen,
			legacy_local_pending=self._legacy_isolated,
			authoritative_save_eligible=self.can_write_authoritative_snapshot,
		)
		return state

	#============================================
	def export_backend_snapshot(self, file_path: str) -> oasa.cdml_document.CDMLSnapshot:
		"""Publish one exact backend snapshot without changing this session."""
		snapshot = self._current_recovery_snapshot()
		_write_backend_snapshot(file_path, snapshot)
		return snapshot

	#============================================
	@property
	def scene(self) -> object:
		"""Return this session's ChemScene."""
		return self._scene

	#============================================
	@property
	def view(self) -> object:
		"""Return the ChemView suitable for direct insertion into a tab."""
		return self._view

	#============================================
	@property
	def mode_manager(self) -> object:
		"""Return the ModeManager that dispatches this view's events."""
		return self._mode_manager

	#============================================
	@property
	def title(self) -> str:
		"""Return the visible tab title, including the unsaved marker."""
		file_path = self._origin_path
		if self._document is not None:
			file_path = self._document.file_path
		base_name = self._display_name
		if not base_name:
			if file_path:
				base_name = os.path.basename(file_path)
			elif self._document is None:
				base_name = "Projection Error"
			else:
				base_name = "Untitled"
		dirty = self._document.dirty if self._document is not None else True
		return base_name + (" *" if dirty else "")

	#============================================
	def set_file_path(self, file_path: str | None) -> None:
		"""Update the native path and notify tab hosts of the new title."""
		if self._document is None:
			raise ProjectionReplacementError(
				"Cannot change a file path while the Qt projection is unavailable",
			)
		self._document.file_path = file_path
		self._display_name = None
		if file_path is not None:
			self._origin_path = file_path
		self.title_changed.emit(self.title)

	#============================================
	@property
	def origin_path(self) -> str | None:
		"""Return the native, imported, or pending source path for deduplication."""
		return self._origin_path

	#============================================
	def set_origin_path(self, origin_path: str | None) -> None:
		"""Set or clear the source path used for duplicate-open detection."""
		self._origin_path = origin_path

	#============================================
	def set_display_name(self, display_name: str | None) -> None:
		"""Set an import/loading label without making it a native save path."""
		self._display_name = display_name
		self.title_changed.emit(self.title)

	#============================================
	@property
	def is_disposed(self) -> bool:
		"""Return whether deterministic teardown has already begun."""
		return self._disposed

	#============================================
	@PySide6.QtCore.Slot(bool)
	def _on_modified_changed(self, _dirty: bool) -> None:
		"""Forward the tab title after a Qt dirty-state transition."""
		self.title_changed.emit(self.title)

	#============================================
	@PySide6.QtCore.Slot(int)
	def _on_persistent_mutated(self, _generation: int) -> None:
		"""Permanently revoke backend-write provenance after a Qt-local edit."""
		self._backend_projection_synchronized = False
		self._legacy_isolated = True

	#============================================
	def _clear_mode_persistent_actions(self) -> None:
		"""Break mode callback references before session-owned Qt teardown."""
		if self._mode_manager is None:
			return
		for mode in self._mode_manager._modes.values():
			installer = getattr(mode, "set_persistent_operation", None)
			if callable(installer):
				installer(None)
			align_installer = getattr(mode, "set_atom_align_operation", None)
			if callable(align_installer):
				align_installer(None)
			translate_installer = getattr(mode, "set_atom_translate_operation", None)
			if callable(translate_installer):
				translate_installer(None)
			translate_authority_installer = getattr(mode, "set_atom_translate_authority", None)
			if callable(translate_authority_installer):
				translate_authority_installer(None)
			presentation_translate_installer = getattr(mode, "set_presentation_translate_operation", None)
			if callable(presentation_translate_installer):
				presentation_translate_installer(None)
			presentation_context_installer = getattr(mode, "set_presentation_translate_context", None)
			if callable(presentation_context_installer):
				presentation_context_installer(None)
			selection_translate_installer = getattr(mode, "set_selection_translate_operation", None)
			if callable(selection_translate_installer):
				selection_translate_installer(None)
			selection_context_installer = getattr(mode, "set_selection_translate_context", None)
			if callable(selection_context_installer):
				selection_context_installer(None)
			delete_context_installer = getattr(mode, "set_top_level_delete_context", None)
			if callable(delete_context_installer):
				delete_context_installer(None)
			structure_delete_installer = getattr(mode, "set_structure_delete_context", None)
			if callable(structure_delete_installer):
				structure_delete_installer(None)
			atom_mark_delete_installer = getattr(mode, "set_atom_mark_delete_context", None)
			if callable(atom_mark_delete_installer):
				atom_mark_delete_installer(None)
			rotate_installer = getattr(mode, "set_atom_rotate_operation", None)
			if callable(rotate_installer):
				rotate_installer(None)
			candidate_installer = getattr(mode, "set_atom_number_context", None)
			if callable(candidate_installer):
				candidate_installer(None)
			mark_revision_installer = getattr(mode, "set_atom_mark_revision", None)
			if callable(mark_revision_installer):
				mark_revision_installer(None)
			template_installer = getattr(mode, "set_template_action", None)
			if callable(template_installer):
				template_installer(None)
			biotemplate_installer = getattr(mode, "set_biotemplate_action", None)
			if callable(biotemplate_installer):
				biotemplate_installer(None)
			user_template_installer = getattr(mode, "set_user_template_action", None)
			if callable(user_template_installer):
				user_template_installer(None)

	#============================================
	def _require_live_persistent_operation(self) -> None:
		"""Reject backend mutation or persistence after this session is terminal."""
		if self._disposed:
			raise RuntimeError("Cannot change or save backend CDML after session disposal")

	#============================================
	def _dispose_failed_construction(
			self, staged_document: bkchem_qt.models.document.Document | None,
			) -> None:
		"""Undo a failed constructor without consuming staged native content.

		The staged document is deliberately restored as detached state instead of
		being cleared or queued for deletion.  That leaves its prepared value
		reusable when canvas or mode setup fails after backend parsing succeeds.
		"""
		self._disposed = True
		self.clear_projection_lifecycle_port()
		self._clear_mode_persistent_actions()
		self.invalidate_import_requests()
		self._stop_import_workers()
		if self._document is not None:
			if self._document_modified_connected:
				try:
					self._document.modified_changed.disconnect(self._on_modified_changed)
				except (RuntimeError, TypeError):
					pass
				self._document_modified_connected = False
			if self._document_persistent_mutation_connected:
				try:
					self._document.persistent_mutated.disconnect(self._on_persistent_mutated)
				except (RuntimeError, TypeError):
					pass
				self._document_persistent_mutation_connected = False
			try:
				self._document.set_scene(None)
			except (RuntimeError, TypeError):
				pass
		if self._view is not None:
			try:
				self._view.set_mode_manager(None)
			except (RuntimeError, TypeError):
				pass
			try:
				self._view.set_document(None)
			except (RuntimeError, TypeError):
				pass
			try:
				self._view.setScene(None)
			except (RuntimeError, TypeError):
				pass
		if self._mode_manager is not None:
			try:
				self._mode_manager.dispose()
			except (RuntimeError, TypeError):
				pass
			try:
				self._mode_manager.setParent(None)
				self._mode_manager.deleteLater()
			except (RuntimeError, TypeError):
				pass
		for child in tuple(self.children()):
			if child in (self._document, self._scene, self._mode_manager):
				continue
			dispose = getattr(child, "dispose", None)
			if callable(dispose):
				try:
					dispose()
				except (RuntimeError, TypeError):
					pass
			try:
				child.setParent(None)
				child.deleteLater()
			except (RuntimeError, TypeError):
				pass
		if self._scene is not None:
			try:
				self._scene.dispose_contents(self._projection_retirement_reaper)
			except (RuntimeError, TypeError):
				pass
			finally:
				# A constructor that never returns has no session-close owner.  Move
				# any explicit native-delete failure into the process reaper rather
				# than allowing its wrapper to reach Python finalization.
				from bkchem_qt.canvas.graphics_retirement import (
					detached_graphics_retirement_reaper,
				)
				detached_graphics_retirement_reaper.retain_graphics_records(
					self._projection_retirement_reaper.take_retained_graphics_records(),
				)
			try:
				self._scene.setParent(None)
				self._scene.deleteLater()
			except (RuntimeError, TypeError):
				pass
		if self._view is not None:
			try:
				self._view.setParent(None)
				self._view.deleteLater()
			except (RuntimeError, TypeError):
				pass
		if self._document is not None:
			try:
				self._document.setParent(None)
			except (RuntimeError, TypeError):
				pass
			if self._document is not staged_document:
				try:
					self._document.deleteLater()
				except (RuntimeError, TypeError):
					pass
		self._document = None
		self._scene = None
		self._view = None
		self._mode_manager = None
		try:
			self.setParent(None)
			self.deleteLater()
		except (RuntimeError, TypeError):
			pass

	# ------------------------------------------------------------------
	# Import request and worker lifetime
	# ------------------------------------------------------------------

	#============================================
	def begin_import_request(self) -> int:
		"""Invalidate earlier imports and return this request's session token."""
		self._import_generation += 1
		return self._import_generation

	#============================================
	def invalidate_import_requests(self) -> None:
		"""Prevent all prior asynchronous callbacks from changing this session."""
		self._import_generation += 1

	#============================================
	def import_request_is_current(self, token: int) -> bool:
		"""Return whether an import result may still be delivered here."""
		return not self._disposed and token == self._import_generation

	#============================================
	def track_import_worker(self, worker: PySide6.QtCore.QThread) -> None:
		"""Retain a live worker until its native thread has finished."""
		if self._disposed:
			worker.requestInterruption()
			_adopt_orphaned_import_worker(worker)
			return
		self._import_workers.add(worker)

	#============================================
	def retire_import_workers(self) -> tuple[PySide6.QtCore.QThread, ...]:
		"""Invalidate delivery and surrender live workers to a retirement owner.

		Interruption is a truthful delivery fence only: opaque OASA, RDKit, and
		transport calls continue until their native call returns.  A live window
		must retain the returned workers and their relays through ``finished``.
		"""
		self.invalidate_import_requests()
		workers = tuple(self._import_workers)
		self._import_workers.clear()
		for worker in workers:
			worker.requestInterruption()
		return workers

	#============================================
	def release_import_worker(self, worker: PySide6.QtCore.QThread) -> None:
		"""Release one stopped worker and schedule its Qt wrapper for deletion."""
		self._import_workers.discard(worker)
		if not worker.isRunning():
			worker.deleteLater()

	# ------------------------------------------------------------------
	# Deterministic teardown
	# ------------------------------------------------------------------

	#============================================
	def dispose(self) -> None:
		"""Disconnect this tab's callbacks before Qt or Python wrappers die.

		This method is idempotent. It intentionally performs callback disposal
		before clearing undo history or the scene, because undone commands may
		be the final Python owners of off-scene graphics items.
		"""
		if self._disposed:
			return
		self._disposed = True
		self.disposed.emit()
		self.clear_projection_lifecycle_port()
		self._clear_mode_persistent_actions()
		self.invalidate_import_requests()
		self._stop_import_workers()

		self._mode_manager.dispose()
		if self._document_modified_connected and self._document is not None:
			try:
				self._document.modified_changed.disconnect(self._on_modified_changed)
			except (RuntimeError, TypeError):
				pass
			self._document_modified_connected = False
		if self._document_persistent_mutation_connected and self._document is not None:
			try:
				self._document.persistent_mutated.disconnect(self._on_persistent_mutated)
			except (RuntimeError, TypeError):
				pass
			self._document_persistent_mutation_connected = False
		self._view.set_mode_manager(None)
		self._view.set_document(None)
		self._view.setScene(None)
		graphics_error = None
		self._merge_retained_detached_graphics(
			self._projection_retirement_reaper.take_retained_detached_graphics(),
		)
		if self._document is not None:
			self._document.set_scene(None)
			try:
				self._dispose_graphics_items()
			except Exception as exc:
				graphics_error = exc
				self._teardown_diagnostics.append(exc)
			self._document.undo_stack.clear()
		self._teardown_phase = "callbacks_detached"
		scene_error = None
		try:
			self._scene.dispose_contents(self._projection_retirement_reaper)
		except Exception as exc:
			# A coordinator-recorded native deletion failure already has a
			# session-owned reaper record.  The remaining scene has crossed its
			# terminal transition, so finish queuing the session and transfer that
			# explicit record to MainWindow.  Other scene failures still stop here:
			# they have no safe terminal ownership proof.
			if not self._projection_retirement_reaper.has_retained_graphics:
				self._teardown_diagnostics.append(exc)
				raise RuntimeError("Session scene retirement did not complete") from exc
			self._merge_retained_detached_graphics(
				self._projection_retirement_reaper.take_retained_detached_graphics(),
			)
			scene_error = exc
			self._teardown_diagnostics.append(exc)
		self._teardown_phase = "scene_retired"
		if self._document is not None:
			# Clear model ownership only after the scene has explicitly retired its
			# graphics. Document.clear() detaches molecule/presentation QObjects so
			# deleting the document cannot move the same parent-cascade hazard there.
			self._document.clear()

		# Python-wrapped QGraphicsScene children can crash Shiboken when they are
		# destroyed recursively by a Python-wrapped QObject parent.  Break that
		# cascade and queue each independent root while its Python wrapper remains
		# retained by this terminal session.  MainWindow queues the now-childless
		# session only after dispose() returns.
		self._mode_manager.setParent(None)
		self._scene.setParent(None)
		self._mode_manager.deleteLater()
		if self._document is not None:
			self._document.setParent(None)
			self._document.deleteLater()
		self._scene.deleteLater()

		# The tab page was normally detached from QTabWidget by MainWindow.
		# Reparent defensively so direct DocumentSession users get the same
		# single-owner teardown contract.
		self._view.setParent(None)
		self._view.deleteLater()
		self._teardown_phase = "roots_queued"
		if graphics_error is not None:
			raise RuntimeError(
				"Session was retired after a graphics callback disposal failure",
			) from graphics_error
		if scene_error is not None:
			raise RuntimeError(
				"Session was retired after a scene graphics retirement failure",
			) from scene_error

	#============================================
	def release_python_references(self) -> None:
		"""Flatten the terminal wrapper graph after a reaper retains its roots.

		Native objects have already been queued for deletion by :meth:`dispose`.
		A caller retains QObject roots and any failed detached-graphics record
		before calling this method.  Scene-owned item sentinels were already
		released by :meth:`ChemScene.dispose_contents`.
		"""
		if self._teardown_phase != "roots_queued":
			raise RuntimeError(
				"Session roots must be queued before releasing Python references",
			)
		self._mode_manager.release_python_references()
		if self._document is not None:
			self._document._undo_stack = None
		self._mode_manager = None
		self._document = None
		self._scene = None
		self._view = None

	#============================================
	def take_retained_detached_graphics(self) -> object:
		"""Transfer failed detached graphics to the MainWindow terminal reaper."""
		self._merge_retained_detached_graphics(
			self._projection_retirement_reaper.take_retained_detached_graphics(),
		)
		retained = self._retained_detached_graphics
		self._retained_detached_graphics = None
		return retained

	#============================================
	def take_retained_graphics_records(self) -> object:
		"""Transfer every terminal graphics record to the MainWindow owner.

		The aggregate keeps failed scene-removal records together with detached
		root failures, so closing a session never changes their ownership to the
		process-level fallback while the MainWindow can still retry them.
		"""
		records = self._projection_retirement_reaper.take_retained_graphics_records()
		self._merge_retained_detached_graphics(records.detached)
		records.detached = self._retained_detached_graphics
		self._retained_detached_graphics = None
		return records

	#============================================
	def _merge_retained_detached_graphics(self, retained: object) -> None:
		"""Keep every failed projection root under this session's terminal owner."""
		if retained is None:
			return
		if self._retained_detached_graphics is None:
			self._retained_detached_graphics = retained
			return
		self._retained_detached_graphics.roots.extend(retained.roots)
		self._retained_detached_graphics.diagnostics.extend(retained.diagnostics)

	#============================================
	def _stop_import_workers(self) -> None:
		"""Invalidate local worker delivery without joining native work.

		This fallback is only safe when no worker was started during failed
		construction.  Registered sessions transfer workers to MainWindow before
		disposal, which remains their terminal Qt owner.
		"""
		for worker in self.retire_import_workers():
			_adopt_orphaned_import_worker(worker)

	#============================================
	def _dispose_graphics_items(self) -> None:
		"""Disconnect live and undo-retained graphics callbacks in order."""
		from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
		coordinator = GraphicsRetirementCoordinator()
		coordinator.prepare_scene_retirement(
			self._scene, self._document.undo_stack,
			destroy_detached_undo_items=True,
			reaper=self._projection_retirement_reaper,
		)
		coordinator.raise_if_callback_failed(
			"Session graphics callbacks were released after a disposal failure",
		)
