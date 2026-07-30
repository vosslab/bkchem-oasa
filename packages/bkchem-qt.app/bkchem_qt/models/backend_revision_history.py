"""Immutable logical revision history for backend-authoritative operations."""

# Standard Library
import dataclasses


#============================================
@dataclasses.dataclass(frozen=True)
class BackendHistoryEntry:
	"""One logical entry and its currently retained physical revision."""

	label: str
	revision: int


#============================================
@dataclasses.dataclass(frozen=True)
class BackendRevisionHistory:
	"""Plain-Python navigation state for backend revisions.

	This value owns no backend session, Qt object, projection, or callback.
	Its adapter obtains an adjacent target revision, asks the backend to restore
	it, and records the resulting physical revision only after that succeeds.
	"""

	entries: tuple[BackendHistoryEntry, ...]
	cursor: int

	#============================================
	@classmethod
	def baseline(cls, label: str, revision: int) -> "BackendRevisionHistory":
		"""Create a one-entry history for the initial backend snapshot."""
		history = cls((BackendHistoryEntry(label, revision),), 0)
		return history

	#============================================
	@property
	def can_undo(self) -> bool:
		"""Return whether the preceding logical entry exists."""
		return self.cursor > 0

	#============================================
	@property
	def can_redo(self) -> bool:
		"""Return whether the succeeding logical entry exists."""
		return self.cursor + 1 < len(self.entries)

	#============================================
	def append_accepted(self, label: str, revision: int) -> "BackendRevisionHistory":
		"""Append an accepted edit after truncating its logical redo branch."""
		entries = self.entries[:self.cursor + 1] + (BackendHistoryEntry(label, revision),)
		history = BackendRevisionHistory(entries, len(entries) - 1)
		return history

	#============================================
	def adjacent_target(self, direction: str) -> tuple[int, BackendHistoryEntry] | None:
		"""Return the adjacent logical target without changing this value."""
		if direction == "undo":
			destination = self.cursor - 1
		elif direction == "redo":
			destination = self.cursor + 1
		else:
			raise ValueError("Backend history direction must be undo or redo")
		if destination < 0 or destination >= len(self.entries):
			return None
		target = (destination, self.entries[destination])
		return target

	#============================================
	def record_restored(
			self, destination: int, revision: int,
			) -> "BackendRevisionHistory":
		"""Replace one restored destination revision and move the cursor."""
		if destination < 0 or destination >= len(self.entries):
			raise IndexError("Backend history destination is out of range")
		entries = list(self.entries)
		entry = entries[destination]
		entries[destination] = BackendHistoryEntry(entry.label, revision)
		history = BackendRevisionHistory(tuple(entries), destination)
		return history
