"""Pytest plugin providing a hard wall-clock deadline for test processes."""

# Standard Library
import faulthandler
import os
import sys
import threading


_TIMER = None


#============================================
def pytest_addoption(parser: object) -> None:
	"""Register the opt-in hard process deadline."""
	group = parser.getgroup("terminal reporting")
	group.addoption(
		"--kill-after",
		action="store",
		type=float,
		default=0.0,
		metavar="SECONDS",
		help=(
			"Force the pytest process to exit after this many wall-clock "
			"seconds; disabled by default."
		),
	)


#============================================
def _cancel_timer(config: object) -> None:
	"""Cancel and forget the deadline timer attached to a pytest config."""
	global _TIMER
	timer = getattr(config, "_bkchem_kill_after_timer", None)
	if timer is not None:
		timer.cancel()
		config._bkchem_kill_after_timer = None
	if timer is _TIMER:
		_TIMER = None


#============================================
def pytest_configure(config: object) -> None:
	"""Start the requested wall-clock deadline after pytest is configured."""
	global _TIMER
	seconds = float(config.getoption("kill_after"))
	if seconds <= 0.0:
		return

	def _terminate() -> None:
		"""Print live thread stacks, then terminate without teardown hangs."""
		sys.stderr.write(
			"\n--kill-after deadline reached after %.3f seconds\n" % seconds
		)
		sys.stderr.flush()
		faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
		os._exit(124)

	timer = threading.Timer(seconds, _terminate)
	timer.daemon = True
	config._bkchem_kill_after_timer = timer
	_TIMER = timer
	timer.start()


#============================================
def pytest_sessionfinish(session: object, exitstatus: object) -> None:
	"""Cancel the deadline once all tests and fixture teardowns have finished."""
	_cancel_timer(session.config)


#============================================
def pytest_unconfigure(config: object) -> None:
	"""Cancel the deadline during early or ordinary pytest shutdown."""
	_cancel_timer(config)
