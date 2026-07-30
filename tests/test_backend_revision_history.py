"""Fast plain-Python checks for logical backend revision history."""

# local repo modules
import bkchem_qt.models.backend_revision_history


#============================================
class FakeRevisionBackend:
	"""Minimal retained-revision backend used only by the history value tests."""

	#============================================
	def __init__(self) -> None:
		"""Start with one retained baseline revision."""
		self.revision = 0
		self.value = "baseline"
		self._retained = {0: self.value}

	#============================================
	def commit_candidate(self, candidate: str) -> int:
		"""Accept one candidate and retain its immutable logical content."""
		self.revision += 1
		self.value = candidate
		self._retained[self.revision] = candidate
		return self.revision

	#============================================
	def restore(self, target_revision: int) -> int:
		"""Restore a retained target into a new physical revision."""
		if target_revision not in self._retained:
			raise LookupError("revision is unavailable")
		self.revision += 1
		self.value = self._retained[target_revision]
		self._retained[self.revision] = self.value
		return self.revision

	#============================================
	def evict(self, revision: int) -> None:
		"""Model retention eviction of one non-current revision."""
		del self._retained[revision]


#============================================
def _accept(
		history: bkchem_qt.models.backend_revision_history.BackendRevisionHistory,
		backend: FakeRevisionBackend, label: str, candidate: str,
		) -> bkchem_qt.models.backend_revision_history.BackendRevisionHistory:
	"""Model the adapter recording a backend-accepted candidate."""
	revision = backend.commit_candidate(candidate)
	updated = history.append_accepted(label, revision)
	return updated


#============================================
def _restore(
		history: bkchem_qt.models.backend_revision_history.BackendRevisionHistory,
		backend: FakeRevisionBackend, direction: str,
		) -> tuple[
		bkchem_qt.models.backend_revision_history.BackendRevisionHistory, bool,
		]:
	"""Model the adapter updating history only after a successful restore."""
	target = history.adjacent_target(direction)
	if target is None:
		return history, False
	destination, entry = target
	try:
		revision = backend.restore(entry.revision)
	except LookupError:
		return history, False
	updated = history.record_restored(destination, revision)
	return updated, True


#============================================
def test_fake_backend_history_restores_multiple_undo_and_redo_entries() -> None:
	"""Adjacent logical targets survive repeated restore-based navigation."""
	backend = FakeRevisionBackend()
	history = bkchem_qt.models.backend_revision_history.BackendRevisionHistory.baseline(
		"Document", backend.revision,
	)
	history = _accept(history, backend, "First", "first")
	history = _accept(history, backend, "Second", "second")
	history, _ = _restore(history, backend, "undo")
	history, _ = _restore(history, backend, "undo")
	history, _ = _restore(history, backend, "redo")
	history, _ = _restore(history, backend, "redo")

	assert backend.value == "second"
	assert history.cursor == 2


#============================================
def test_accepted_edit_after_undo_truncates_the_logical_redo_branch() -> None:
	"""A new accepted candidate removes only its abandoned redo branch."""
	backend = FakeRevisionBackend()
	history = bkchem_qt.models.backend_revision_history.BackendRevisionHistory.baseline(
		"Document", backend.revision,
	)
	history = _accept(history, backend, "First", "first")
	history = _accept(history, backend, "Second", "second")
	history, _ = _restore(history, backend, "undo")
	history = _accept(history, backend, "Replacement", "replacement")

	assert history.adjacent_target("redo") is None
	assert backend.value == "replacement"


#============================================
def test_unavailable_restore_leaves_the_history_value_unchanged() -> None:
	"""Eviction changes neither the logical cursor nor its retained entries."""
	backend = FakeRevisionBackend()
	history = bkchem_qt.models.backend_revision_history.BackendRevisionHistory.baseline(
		"Document", backend.revision,
	)
	history = _accept(history, backend, "First", "first")
	backend.evict(0)
	updated, restored = _restore(history, backend, "undo")

	assert not restored
	assert updated is history
