"""Discover one explicit directory of validated user-template CDML files."""

# Standard Library
import dataclasses
import hashlib
import os
import pathlib
import stat

# local repo modules
import bkchem_qt.bridge.user_template_inspection


@dataclasses.dataclass(frozen=True)
class UserTemplateCatalogEntry:
	"""One immutable frontend-owned delivery record for a saved template."""

	catalog_key: str
	label: str
	template_cdml: str


@dataclasses.dataclass(frozen=True)
class UserTemplateScanFailure:
	"""One recoverable filesystem or admission failure from a catalog scan."""

	source_name: str
	message: str


@dataclasses.dataclass(frozen=True)
class UserTemplateCatalogSnapshot:
	"""One explicit immutable result of scanning a configured directory."""

	entries: tuple[UserTemplateCatalogEntry, ...]
	failures: tuple[UserTemplateScanFailure, ...]


#============================================
def scan_user_template_catalog(directory: str | pathlib.Path) -> UserTemplateCatalogSnapshot:
	"""Scan one directory nonrecursively into an immutable catalog snapshot.

	Only regular lowercase ``.cdml`` files participate. A missing directory is
	an empty catalog so the eventual UI can offer an empty state without creating
	user filesystem state. Other per-file failures are recorded while remaining
	eligible entries continue through OASA admission.

	Args:
		directory: The one caller-configured template directory to scan.

	Returns:
		One deterministic immutable catalog snapshot.
	"""
	template_directory = pathlib.Path(directory)
	directory_descriptor = _open_catalog_directory(template_directory)
	if isinstance(directory_descriptor, UserTemplateCatalogSnapshot):
		return directory_descriptor
	try:
		filenames = tuple(os.listdir(directory_descriptor))
		entries = []
		failures = []
		for filename_value in sorted(filenames, key=_raw_filename):
			filename = _validated_utf8_filename(filename_value)
			if isinstance(filename, UserTemplateScanFailure):
				if _raw_filename(filename_value).endswith(b".cdml"):
					failures.append(filename)
				continue
			if not filename.endswith(".cdml"):
				continue
			result = _scan_template_file(directory_descriptor, filename)
			if isinstance(result, UserTemplateCatalogEntry):
				entries.append(result)
			else:
				failures.append(result)
		snapshot = UserTemplateCatalogSnapshot(entries=tuple(entries), failures=tuple(failures))
	except OSError as error:
		failure = UserTemplateScanFailure(
			source_name=_safe_text(str(template_directory)),
			message="Cannot read user template directory: %s" % _safe_text(str(error)),
		)
		snapshot = UserTemplateCatalogSnapshot(entries=(), failures=(failure,))
	finally:
		os.close(directory_descriptor)
	return snapshot


#============================================
def _open_catalog_directory(
		template_directory: pathlib.Path,
		) -> int | UserTemplateCatalogSnapshot:
	"""Open one stable catalog directory descriptor for this scan."""
	directory_flags = os.O_RDONLY
	if hasattr(os, "O_DIRECTORY"):
		directory_flags |= os.O_DIRECTORY
	if hasattr(os, "O_CLOEXEC"):
		directory_flags |= os.O_CLOEXEC
	try:
		directory_descriptor = os.open(template_directory, directory_flags)
	except FileNotFoundError:
		return UserTemplateCatalogSnapshot(entries=(), failures=())
	except OSError as error:
		failure = UserTemplateScanFailure(
			source_name=_safe_text(str(template_directory)),
			message="Cannot read user template directory: %s" % _safe_text(str(error)),
		)
		return UserTemplateCatalogSnapshot(entries=(), failures=(failure,))
	return directory_descriptor


#============================================
def _raw_filename(path: pathlib.Path | str) -> bytes:
	"""Return the directory entry's stable filesystem byte filename."""
	name = path.name if isinstance(path, pathlib.Path) else path
	raw_filename = os.fsencode(name)
	return raw_filename


#============================================
def _safe_source_name(path: pathlib.Path | str) -> str:
	"""Return a renderable filename without surrogate escape code points."""
	name = path.name if isinstance(path, pathlib.Path) else path
	source_name = _safe_text(name)
	return source_name


#============================================
def _safe_text(value: str) -> str:
	"""Return text with filesystem surrogate escapes made visible."""
	safe_value = os.fsencode(value).decode("utf-8", errors="backslashreplace")
	return safe_value


#============================================
def _validated_utf8_filename(path: pathlib.Path | str) -> str | UserTemplateScanFailure:
	"""Return one filename only when its filesystem bytes are valid UTF-8."""
	try:
		filename = _raw_filename(path).decode("utf-8")
	except UnicodeError:
		return UserTemplateScanFailure(
			source_name=_safe_source_name(path),
			message="User template filename is not valid UTF-8",
		)
	return filename


#============================================
def _scan_template_file(
		directory_descriptor: int, filename: str,
		) -> UserTemplateCatalogEntry | UserTemplateScanFailure:
	"""Admit and read one exact regular descriptor without following a link."""
	file_descriptor = _open_catalog_candidate(directory_descriptor, filename)
	if isinstance(file_descriptor, UserTemplateScanFailure):
		return file_descriptor
	try:
		# The raw descriptor remains this function's one owner.  Keeping it open
		# through the file wrapper without transferring ownership means the
		# finally block also closes it if constructing or reading the wrapper
		# raises before its context manager can run.
		try:
			with os.fdopen(file_descriptor, "rb", closefd=False) as template_file:
				payload = template_file.read()
		finally:
			os.close(file_descriptor)
		template_cdml = payload.decode("utf-8")
	except (OSError, UnicodeError) as error:
		return UserTemplateScanFailure(
			source_name=filename,
			message="Cannot read user template CDML: %s" % _safe_text(str(error)),
		)
	try:
		display_name = bkchem_qt.bridge.user_template_inspection.inspect_user_template_display_name(
			template_cdml,
		)
	except bkchem_qt.bridge.user_template_inspection.UserTemplateInspectionError as error:
		return UserTemplateScanFailure(
			source_name=filename,
			message="User template is not eligible: %s" % error,
		)
	label = display_name if display_name is not None else pathlib.PurePath(filename).stem
	return UserTemplateCatalogEntry(
		catalog_key=_catalog_key(filename), label=label, template_cdml=template_cdml,
	)


#============================================
def _open_catalog_candidate(
		directory_descriptor: int, filename: str,
		) -> int | UserTemplateScanFailure:
	"""Open exactly one directory-local regular candidate without a pathname race."""
	if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
		return UserTemplateScanFailure(
			source_name=filename,
			message="Secure user template admission is unavailable on this platform",
		)
	candidate_flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
	if hasattr(os, "O_CLOEXEC"):
		candidate_flags |= os.O_CLOEXEC
	try:
		file_descriptor = os.open(filename, candidate_flags, dir_fd=directory_descriptor)
	except OSError as error:
		return UserTemplateScanFailure(
			source_name=filename,
			message="Cannot admit user template file: %s" % _safe_text(str(error)),
		)
	try:
		file_status = os.fstat(file_descriptor)
	except OSError as error:
		os.close(file_descriptor)
		return UserTemplateScanFailure(
			source_name=filename,
			message="Cannot inspect admitted user template file: %s" % _safe_text(str(error)),
		)
	if not stat.S_ISREG(file_status.st_mode):
		os.close(file_descriptor)
		return UserTemplateScanFailure(
			source_name=filename,
			message="User template must be a regular CDML file",
		)
	return file_descriptor


#============================================
def _catalog_key(filename: str) -> str:
	"""Derive a stable opaque catalog key from one directory-local filename."""
	digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()
	return "user-template:" + digest
