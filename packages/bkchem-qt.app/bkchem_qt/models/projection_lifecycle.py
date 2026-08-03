"""Dependency-light delivery values for disposable frontend projections."""

# Standard Library
import collections.abc
import dataclasses
import enum


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


@dataclasses.dataclass(frozen=True)
class ProjectionLifecycleResult:
	"""One session-bound delivery result for a backend projection request."""

	status: ProjectionLifecycleStatus
	phase: ProjectionLifecyclePhase
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


class SessionProjectionLifecyclePort:
	"""Deliver projection work only to the live session that registered it.

	The port is deliberately narrow: a frontend shell owns transient aliases and
	UI wiring, while its document session retains backend state and the replacement
	transaction. Its generation latch makes queued or retained stale delivery inert
	after session disposal or port replacement.
	"""

	#============================================
	def __init__(
			self, session: object,
			deliver: collections.abc.Callable[[object], ProjectionLifecycleResult],
			notice_consumer: collections.abc.Callable[
				[object, ProjectionLifecycleResult], None,
			] | None = None,
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
	def _is_current_owner(self) -> bool:
		"""Return whether the target session still grants this port delivery."""
		return (
			self.is_bound_to(self._session)
			and self._session.owns_projection_lifecycle_port(self)
		)

	#============================================
	def project(self, snapshot: object) -> ProjectionLifecycleResult:
		"""Deliver one exact snapshot or report a typed inert/failure outcome."""
		if not self._is_current_owner():
			return ProjectionLifecycleResult(
				ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				ProjectionLifecyclePhase.SESSION,
			)
		try:
			result = self._deliver(snapshot)
		except Exception as error:
			result = ProjectionLifecycleResult(
				ProjectionLifecycleStatus.INSTALLATION_FAILED,
				ProjectionLifecyclePhase.INSTALLATION,
				error,
			)
		else:
			if not isinstance(result, ProjectionLifecycleResult):
				raise TypeError(
					"Projection lifecycle delivery must return ProjectionLifecycleResult",
				)
		# Delivery can synchronously close this tab or replace its port. A retained
		# notice cannot retarget frontend aliases after that ownership boundary.
		if not self._is_current_owner():
			return result
		if self._notice_consumer is not None:
			self._notice_consumer(self._session, result)
		return result
