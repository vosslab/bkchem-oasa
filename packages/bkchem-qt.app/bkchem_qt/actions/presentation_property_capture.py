"""Revision-bound presentation-property submissions for live Qt sessions."""

# Standard Library
from collections.abc import Collection, Callable

# local repo modules
import bkchem_qt.models.document_session


PresentationPropertiesSubmit = Callable[
	[int, str, tuple[tuple[str, object], ...]],
	bkchem_qt.models.document_session.PersistentActionOutcome,
]


#============================================
def capture_presentation_properties(
		session: bkchem_qt.models.document_session.DocumentSession | None,
		live_sessions: Collection[bkchem_qt.models.document_session.DocumentSession],
		identifier: str, kind: str,
		) -> tuple[int, PresentationPropertiesSubmit] | None:
	"""Capture a presentation patch that cannot retarget a different tab."""
	if (
		session is None or session.is_disposed or session not in live_sessions
		or session.document is None or not session.can_commit_persistent_action
		or not isinstance(identifier, str) or not identifier
	):
		return None
	submitters = {
		"plus": session.submit_plus_properties_patch,
		"wavy": session.submit_wavy_properties_patch,
		"arrow": session.submit_arrow_properties_patch,
		"geometric": session.submit_geometric_properties_patch,
	}
	if kind not in submitters:
		raise ValueError("Presentation properties kind is unsupported")
	submitter = submitters[kind]
	def submit(
			expected_revision: int, captured_identifier: str,
			changes: tuple[tuple[str, object], ...],
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Submit only while the session captured by the dialog remains live."""
		if session.is_disposed or session not in live_sessions:
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		return submitter(expected_revision, captured_identifier, changes)
	return session.backend_snapshot.revision, submit


#============================================
def capture_bracket_properties(
		session: bkchem_qt.models.document_session.DocumentSession | None,
		live_sessions: Collection[bkchem_qt.models.document_session.DocumentSession],
		pair_id: str,
		) -> tuple[int, PresentationPropertiesSubmit] | None:
	"""Capture one atomic bracket-pair patch for the exact current tab."""
	if (
		session is None or session.is_disposed or session not in live_sessions
		or session.document is None or not session.can_commit_persistent_action
		or not isinstance(pair_id, str) or not pair_id
	):
		return None
	def submit(
			expected_revision: int, captured_pair_id: str,
			changes: tuple[tuple[str, object], ...],
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Submit only while the session captured by the dialog remains live."""
		if session.is_disposed or session not in live_sessions:
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"unavailable", "Document cannot accept a persistent edit", None, False,
			)
		return session.submit_bracket_properties_patch(
			expected_revision, captured_pair_id, changes,
		)
	return session.backend_snapshot.revision, submit
