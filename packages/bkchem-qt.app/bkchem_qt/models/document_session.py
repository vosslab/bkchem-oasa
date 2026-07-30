"""Per-tab ownership and teardown boundary for BKChem Qt documents."""

# Standard Library
import errno
import collections.abc
import dataclasses
import enum
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
import bkchem_qt.io.cdml_candidate
import bkchem_qt.models.backend_revision_history
import bkchem_qt.models.document
import bkchem_qt.undo.commands
import bkchem_qt.wavy_geometry
import oasa.cdml_document
import oasa.cdml_render
import oasa.cdml_writer
import oasa.safe_xml
import oasa.template_placement


_BLANK_CDML = (
	'<cdml xmlns="%s" version="%s"></cdml>' % (
		oasa.cdml_writer.CDML_NAMESPACE,
		oasa.cdml_writer.DEFAULT_CDML_VERSION,
	)
)


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
def _direct_core_cdml_children(parent: object, local_name: str) -> tuple[object, ...]:
	"""Return direct legacy-or-canonical core children with one exact name."""
	children = []
	for child in parent.childNodes:
		if getattr(child, "nodeType", None) != child.ELEMENT_NODE:
			continue
		child_name = getattr(child, "localName", None) or getattr(child, "tagName", "")
		if ":" in child_name:
			child_name = child_name.rsplit(":", 1)[1]
		if (
				child_name == local_name
				and getattr(child, "namespaceURI", None) in (
					None, "", oasa.cdml_document.CDML_NAMESPACE_URI,
				)
			):
			children.append(child)
	return tuple(children)


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


@dataclasses.dataclass(frozen=True)
class ProjectionLifecycleResult:
	"""One session-bound delivery result for a backend projection request."""

	status: "ProjectionLifecycleStatus"
	phase: "ProjectionLifecyclePhase"
	diagnostic: BaseException | None = None

	#============================================
	def __bool__(self) -> bool:
		"""Preserve the direct replacement truthiness contract for callers."""
		return self.installed

	#============================================
	@property
	def installed(self) -> bool:
		"""Return whether the exact requested snapshot became live."""
		return self.status is ProjectionLifecycleStatus.INSTALLED


class ProjectionLifecycleStatus(enum.StrEnum):
	"""Closed outcomes for one backend snapshot projection delivery."""

	INSTALLED = "installed"
	PREPARATION_UNAVAILABLE = "preparation-unavailable"
	INSTALLATION_FAILED = "installation-failed"
	SESSION_UNAVAILABLE = "session-unavailable"


class ProjectionLifecyclePhase(enum.StrEnum):
	"""The terminal replacement phase that produced a lifecycle outcome."""

	SESSION = "session"
	PREPARATION = "preparation"
	RETIREMENT = "retirement"
	INSTALLATION = "installation"
	COMPLETE = "complete"


class SessionProjectionLifecyclePort:
	"""Deliver projection work only to the live session that registered it.

	The port is deliberately narrow: MainWindow owns transient aliases and UI
	wiring, while DocumentSession retains backend state and the replacement
	transaction.  Its generation latch makes queued or retained stale delivery
	inert after tab disposal or port replacement.
	"""

	#============================================
	def __init__(
			self, session: object,
			deliver: collections.abc.Callable[[object], ProjectionLifecycleResult],
			notice_consumer: collections.abc.Callable[[object, ProjectionLifecycleResult], None] | None = None,
			) -> None:
		"""Bind one typed delivery seam to one currently live session."""
		self._session = session
		self._generation = session.projection_lifecycle_generation
		self._deliver = deliver
		self._notice_consumer = notice_consumer

	#============================================
	def is_bound_to(self, session: object) -> bool:
		"""Return whether this port still targets its original live session."""
		return (
			session is self._session
			and not session.is_disposed
			and session.projection_lifecycle_generation == self._generation
		)

	#============================================
	def project(self, snapshot: object) -> ProjectionLifecycleResult:
		"""Deliver one exact snapshot or report a typed inert/failure outcome."""
		if (
			not self.is_bound_to(self._session)
			or self._session._projection_lifecycle_port is not self
		):
			return ProjectionLifecycleResult(
				ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				ProjectionLifecyclePhase.SESSION,
			)
		else:
			try:
				result = self._deliver(snapshot)
			except Exception as exc:
				result = ProjectionLifecycleResult(
					ProjectionLifecycleStatus.INSTALLATION_FAILED,
					ProjectionLifecyclePhase.INSTALLATION, exc,
				)
			else:
				if not isinstance(result, ProjectionLifecycleResult):
					raise TypeError("Projection lifecycle delivery must return ProjectionLifecycleResult")
		# Delivery can synchronously close this tab or replace its port.  A
		# retained notice must not retarget MainWindow aliases after that boundary.
		if (
			not self.is_bound_to(self._session)
			or self._session._projection_lifecycle_port is not self
		):
			return result
		if self._notice_consumer is not None:
			self._notice_consumer(self._session, result)
		return result


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
		changes: tuple[tuple[str, object], ...],
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
		changes: tuple[tuple[str, object], ...],
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
		(
			("expected_revision", expected_revision),
			("changes", changes),
		),
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
		document: Optional existing Document to adopt.
		file_path: Optional native document path for the initial title.
		display_name: Optional non-native label for loading/imported content.
		origin_path: Optional source path used for duplicate-open detection.
		prepared_native_cdml: One-use native staging result from
			:meth:`prepare_native_cdml`.  Its canonical CDML is parsed into this
			session's independently owned backend authority.
	"""

	title_changed = PySide6.QtCore.Signal(str)
	disposed = PySide6.QtCore.Signal()

	#============================================
	def __init__(
			self, parent: PySide6.QtCore.QObject, theme_manager: object,
		prefs: object, mode_host: object,
		view_parent: PySide6.QtWidgets.QWidget | None = None,
		document: bkchem_qt.models.document.Document | None = None,
		file_path: str | None = None, display_name: str | None = None,
		origin_path: str | None = None,
		prepared_native_cdml: PreparedNativeCDML | None = None,
		prepared_imported_cdml: PreparedImportedCDML | None = None,
		) -> None:
		"""Create a clean, independently owned document session."""
		super().__init__(parent)
		if document is not None and (
				prepared_native_cdml is not None or prepared_imported_cdml is not None
			):
			raise ValueError(
				"A supplied Qt document cannot accompany prepared native CDML",
			)
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
		self._operation_dispatcher = {
			"arrow.add": self._build_arrow_candidate,
			"text.add": self._build_text_candidate,
			"plus.add": self._build_plus_candidate,
			"vector.add": self._build_vector_candidate,
			"bracket.add": self._build_bracket_candidate,
			"wavy.add": self._build_wavy_candidate,
			"molecule.insert": self._build_molecule_insertion,
			"template.insert": self._build_template_insertion,
			"geometry.repair": self._build_geometry_repair,
			"atom.align": self._build_atom_align,
			"atom.translate": self._build_atom_translate,
			"atom.rotate": self._build_atom_rotate,
			"bond.order.set": self._build_bond_order_edit,
			"bond.type.set": self._build_bond_type_edit,
			"bond.properties.patch": self._build_bond_properties_patch,
			"atom.properties.patch": self._build_atom_properties_patch,
			"draw.structure": self._build_structural_edit,
			"atom.element.set": self._build_atom_element_edit,
			"atom.number.set": self._build_atom_number_edit,
			"molecule.name.set": self._build_molecule_name_edit,
			"paper.properties.set": self._build_paper_properties_patch,
			"presentation.stack.reorder": self._build_presentation_stack_reorder,
			"top-level.delete": self._build_top_level_delete,
		}
		self._operation_commit_executors = {
			"complete-candidate": self._commit_complete_candidate,
			"molecule-insertion": self._commit_molecule_insertion,
			"geometry-repair": self._commit_geometry_repair,
			"atom-align": self._commit_atom_align,
			"atom-translate": self._commit_atom_translate,
			"atom-rotate": self._commit_atom_rotate,
			"bond-order-edit": self._commit_bond_order_edit,
			"bond-type-edit": self._commit_bond_type_edit,
			"bond-properties-patch": self._commit_bond_properties_patch,
			"atom-properties-patch": self._commit_atom_properties_patch,
			"structural-edit": self._commit_structural_edit,
			"atom-element-edit": self._commit_atom_element_edit,
			"atom-number-edit": self._commit_atom_number_edit,
			"molecule-name-edit": self._commit_molecule_name_edit,
			"paper-properties-patch": self._commit_paper_properties_patch,
			"top-level-delete": self._commit_top_level_delete,
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
			bootstrap_backend_projection = document is None
			if prepared_native_cdml is None and prepared_imported_cdml is None:
				self._backend_session = oasa.cdml_document.CDMLDocumentSession.load(
					_BLANK_CDML,
				)
			elif prepared_native_cdml is not None:
				canonical_cdml, staged_document = prepared_native_cdml._peek()
				self._backend_session = oasa.cdml_document.CDMLDocumentSession.load(
					canonical_cdml,
				)
				bootstrap_backend_projection = True
				# Keep this document detached until every new session root is viable.
				document = staged_document
			else:
				canonical_cdml, staged_document = prepared_imported_cdml._peek()
				self._backend_session = oasa.cdml_document.CDMLDocumentSession.load_imported(
					canonical_cdml,
				)
				bootstrap_backend_projection = True
				document = staged_document
			self._document = (
				document
				if document is not None
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
				atom_number_context=self.atom_number_context,
				template_names=oasa.template_placement.system_template_names(),
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
			if bootstrap_backend_projection:
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
	def query_molecule_smiles(
			self, expected_revision: int, molecule_id: str,
			) -> oasa.cdml_document.CDMLMoleculeSmilesResult:
		"""Observe one synchronized direct-root molecule through OASA CDML.

		The Qt session supplies only immutable scalar revision and durable-ID
		data.  This query creates no candidate, history entry, dirty transition,
		or projection replacement.
		"""
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
	def atom_number_context(self) -> tuple[int, int]:
		"""Return revision and next transient candidate from backend CDML.

		The returned scalar is compatibility presentation state.  The canonical
		snapshot remains the sole persistent source, including hidden numbers.
		"""
		snapshot = self.backend_snapshot
		# Accept the complete document at the CDML boundary before compatibility
		# DOM inspection identifies direct core molecule/atom records.
		oasa.cdml_document.CDMLDocument.parse(snapshot.cdml, validation="compat")
		document = oasa.safe_xml.parse_dom_from_string(snapshot.cdml)
		highest_number = 0
		root = document.documentElement
		for molecule in _direct_core_cdml_children(root, "molecule"):
			for atom in _direct_core_cdml_children(molecule, "atom"):
				number_text = atom.getAttribute("number")
				if not number_text.isdecimal():
					continue
				number = int(number_text)
				if number > highest_number:
					highest_number = number
		next_number = highest_number + 1
		context = (snapshot.revision, next_number)
		return context

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
			if self._scene is None or self._document is None:
				return oasa.cdml_render.CDMLRenderFailure(
					"selection-unavailable",
					"Selection export requires a live Qt projection", snapshot.revision,
				)
			try:
				seen = set()
				captured = []
				for item in self._scene.selectedItems():
					key = bkchem_qt.canvas.document_projection.persistent_selection_key(item)
					if key is None or key in seen:
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
			self, port: SessionProjectionLifecyclePort,
			) -> None:
		"""Install one explicitly session-bound projection delivery port."""
		if self._disposed or not port.is_bound_to(self):
			raise ValueError("A live session requires its own projection lifecycle port")
		self._projection_lifecycle_port = port

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
	def atom_translate_drag_authority(self) -> str:
		"""Return the current frontend-only authority for an EditMode atom drag.

		The installed translation callback alone cannot distinguish a normal
		backend session from a legacy-isolated projection: every session installs
		the callback so keyboard nudging has one narrow interface.  This query
		keeps that distinction at the session boundary without carrying Qt
		objects across the backend-facing request boundary.
		"""
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
					oasa.cdml_document.CDMLAtomRotateResult,
					oasa.cdml_document.CDMLBondOrderEditResult,
					oasa.cdml_document.CDMLBondTypeEditResult,
					oasa.cdml_document.CDMLBondPropertiesPatchResult,
					oasa.cdml_document.CDMLAtomPropertiesPatchResult,
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
		else:
			selection_keys, selection_error = self._durable_selection_keys(prepared, commit)
		return self._project_accepted_commit(
			commit, "%s accepted" % request.label, structural_result, selection_keys,
			selection_error,
		)

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
			snapshot.cdml, self._next_arrow_provisional_id(snapshot.revision), start, end,
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
			position, text,
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
			snapshot.cdml, self._next_plus_provisional_id(snapshot.revision), position,
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
			snapshot.cdml, provisional_id, shape, start, end,
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
			snapshot.cdml, self._next_bracket_provisional_ids(snapshot.revision), bounds,
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
			snapshot.cdml, self._next_wavy_provisional_id(snapshot.revision), points,
		)
		return self._prepare_complete_candidate(snapshot.revision, candidate)

	#============================================
	def _build_paper_properties_patch(
			self, snapshot: oasa.cdml_document.CDMLSnapshot,
			request: PersistentOperationRequest,
			) -> _PreparedPersistentOperation:
		"""Bind explicit dialog intent to OASA's paper-properties patch API."""
		if request.target_keys:
			raise ValueError("Paper properties does not accept persistent targets")
		payload = dict(request.payload)
		if set(payload) != {"expected_revision", "changes"}:
			raise ValueError("Paper properties payload has unsupported fields")
		expected_revision = payload["expected_revision"]
		if type(expected_revision) is not int:
			raise ValueError("Paper properties expected_revision must be an integer")
		if expected_revision != snapshot.revision:
			raise oasa.cdml_document.CDMLRevisionConflictError(
				"Paper properties expected revision does not match the current snapshot",
			)
		changes = payload["changes"]
		if type(changes) is not tuple:
			raise ValueError("Paper properties changes must be an immutable tuple")
		paper_patch = oasa.cdml_document.CDMLPaperPropertiesPatch(
			expected_revision=expected_revision,
			changes=changes,
		)
		return _PreparedPersistentOperation(
			"paper-properties-patch", expected_revision, paper_patch,
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
		if not isinstance(prepared.value, oasa.cdml_document.CDMLPaperPropertiesPatch):
			raise ValueError("Paper properties requires a paper properties patch")
		return self._backend_session.patch_paper_properties(prepared.value)

	#============================================
	def _commit_top_level_delete(
			self, prepared: _PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLCommit:
		"""Execute one backend-owned direct-root deletion."""
		if not isinstance(prepared.value, oasa.cdml_document.CDMLTopLevelDeleteRequest):
			raise ValueError("Top-level Delete requires a deletion request")
		return self._backend_session.delete_top_level(prepared.value)

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
				"atom-align", "atom-translate", "atom-rotate", "bond-order-edit", "bond-type-edit",
				"bond-properties-patch", "atom-properties-patch",
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
			projected = ProjectionLifecycleResult(
				ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				ProjectionLifecyclePhase.SESSION,
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
			) -> ProjectionLifecycleResult:
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
			return ProjectionLifecycleResult(
				ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				ProjectionLifecyclePhase.SESSION,
			)
		from bkchem_qt.io import cdml_document_io
		try:
			candidate = cdml_document_io.prepare_projection_from_cdml(
				snapshot.cdml, self._projection_retirement_reaper,
			)
		except Exception as exc:
			self._backend_projection_synchronized = False
			self._projection_error = ProjectionReplacementError(
				"Could not prepare the current backend CDML projection",
			)
			self._projection_error.__cause__ = exc
			self.title_changed.emit(self.title)
			return ProjectionLifecycleResult(
				ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
				ProjectionLifecyclePhase.PREPARATION, self._projection_error,
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
			result = ProjectionLifecycleResult(
				ProjectionLifecycleStatus.INSTALLED, ProjectionLifecyclePhase.COMPLETE,
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
				ProjectionLifecyclePhase.INSTALLATION if retirement_started
				else ProjectionLifecyclePhase.RETIREMENT
			)
			status = (
				ProjectionLifecycleStatus.INSTALLATION_FAILED if retirement_started
				else ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE
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
			result = ProjectionLifecycleResult(status, phase, self._projection_error)
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
		snapshot = backend_session.snapshot()
		document = cdml_document_io.load_cdml_document_string(snapshot.cdml)
		return PreparedNativeCDML(
			factory_token=_PREPARED_NATIVE_FACTORY_TOKEN,
			snapshot=snapshot,
			document=document,
		)

	#============================================
	@classmethod
	def prepare_imported_cdml(cls, cdml_text: str) -> PreparedImportedCDML:
		"""Stage imported external content against the backend empty baseline."""
		backend_session = oasa.cdml_document.CDMLDocumentSession.load_imported(cdml_text)
		from bkchem_qt.io import cdml_document_io
		snapshot = backend_session.snapshot()
		document = cdml_document_io.load_cdml_document_string(snapshot.cdml)
		return PreparedImportedCDML(
			factory_token=_PREPARED_IMPORTED_FACTORY_TOKEN,
			snapshot=snapshot,
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
			rotate_installer = getattr(mode, "set_atom_rotate_operation", None)
			if callable(rotate_installer):
				rotate_installer(None)
			candidate_installer = getattr(mode, "set_atom_number_context", None)
			if callable(candidate_installer):
				candidate_installer(None)

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
			return
		self._import_workers.add(worker)

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
		"""Interrupt, join, and disconnect every session-owned import worker."""
		workers = tuple(self._import_workers)
		for worker in workers:
			worker.requestInterruption()
		for worker in workers:
			if worker.isRunning():
				worker.wait()
			for signal in (worker.result, worker.error, worker.finished):
				try:
					signal.disconnect()
				except (RuntimeError, TypeError):
					pass
			relay = getattr(worker, "_result_relay", None)
			if relay is not None:
				relay.deleteLater()
				worker._result_relay = None
			self._import_workers.discard(worker)
			worker.deleteLater()

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
