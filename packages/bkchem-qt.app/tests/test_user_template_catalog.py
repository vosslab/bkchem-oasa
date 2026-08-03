"""Focused delivery checks for the Qt-free saved user-template catalog."""

# Standard Library
import os
import pathlib

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.io.user_template_catalog


_NAMED_TEMPLATE = (
	'<cdml><molecule name="Named molecule"><atom id="atom">'
	'<point x="0cm" y="0cm"/></atom></molecule></cdml>'
)
_UNNAMED_TEMPLATE = (
	'<cdml><molecule><atom id="atom"><point x="0cm" y="0cm"/>'
	'</atom></molecule></cdml>'
)
_RAW_BYTE_FILENAMES_SUPPORTED = (
	os.name == "posix" and os.fsencode(os.fsdecode(b"\xff")) == b"\xff"
)


#============================================
def test_catalog_uses_backend_name_or_filename_and_preserves_exact_payload(
		tmp_path: pathlib.Path,
		) -> None:
	"""Accepted entries expose the backend label or stem with untouched CDML."""
	(tmp_path / "fallback.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	(tmp_path / "named.cdml").write_text(_NAMED_TEMPLATE, encoding="utf-8")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	entries_by_label = {entry.label: entry for entry in snapshot.entries}
	assert entries_by_label["Named molecule"].template_cdml == _NAMED_TEMPLATE
	assert entries_by_label["fallback"].template_cdml == _UNNAMED_TEMPLATE


#============================================
def test_catalog_scan_uses_stable_keys_and_filename_order(tmp_path: pathlib.Path) -> None:
	"""Directory-local filenames determine a repeatable opaque delivery order."""
	(tmp_path / "zeta.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	(tmp_path / "alpha.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	first = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	second = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in first.entries) == ("alpha", "zeta")
	assert tuple(entry.catalog_key for entry in first.entries) == tuple(
		entry.catalog_key for entry in second.entries
	)


#============================================
def test_missing_directory_has_an_empty_catalog_snapshot(tmp_path: pathlib.Path) -> None:
	"""A not-yet-created configured directory is a normal empty user state."""
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(
		tmp_path / "not-created",
	)
	assert snapshot.entries == ()
	assert snapshot.failures == ()


#============================================
def test_bad_file_reports_failure_without_hiding_good_template(tmp_path: pathlib.Path) -> None:
	"""Malformed files are isolated so neighboring eligible templates remain usable."""
	(tmp_path / "broken.cdml").write_text("<cdml>", encoding="utf-8")
	(tmp_path / "usable.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in snapshot.entries) == ("usable",)
	assert snapshot.failures[0].source_name == "broken.cdml"


#============================================
def test_invalid_utf8_content_is_isolated_beside_a_good_template(
		tmp_path: pathlib.Path,
		) -> None:
	"""Unreadable CDML leaves an eligible neighboring template available."""
	(tmp_path / "invalid.cdml").write_bytes(b"\xff")
	(tmp_path / "usable.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in snapshot.entries) == ("usable",)
	assert snapshot.failures and snapshot.failures[0].source_name == "invalid.cdml"


#============================================
def test_regular_file_directory_target_returns_a_scan_failure(tmp_path: pathlib.Path) -> None:
	"""A file passed as the configured directory remains a recoverable scan error."""
	directory_target = tmp_path / "not-a-directory"
	directory_target.write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(directory_target)
	assert snapshot.entries == ()
	assert snapshot.failures


#============================================
def test_nested_non_cdml_and_symlink_candidates_do_not_enter_catalog(
		tmp_path: pathlib.Path,
		) -> None:
	"""Only direct regular lowercase CDML files can become catalog entries."""
	(tmp_path / "usable.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	(tmp_path / "notes.txt").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	nested_directory = tmp_path / "nested"
	nested_directory.mkdir()
	(nested_directory / "nested.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	(tmp_path / "linked.cdml").symlink_to(tmp_path / "usable.cdml")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in snapshot.entries) == ("usable",)


#============================================
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX no-follow admission")
def test_catalog_rejects_candidate_replaced_by_symlink_at_open_boundary(
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A pathname swap cannot turn an admitted template into a symlink target."""
	usable = tmp_path / "usable.cdml"
	swapped = tmp_path / "swapped.cdml"
	usable.write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	swapped.write_text(_NAMED_TEMPLATE, encoding="utf-8")
	original_open = os.open
	replaced = False

	def replace_before_candidate_open(
			path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None,
			) -> int:
		"""Replace only the listed candidate immediately before its descriptor opens."""
		nonlocal replaced
		if path == "swapped.cdml" and dir_fd is not None and not replaced:
			swapped.unlink()
			swapped.symlink_to(usable)
			replaced = True
		file_descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
		return file_descriptor

	monkeypatch.setattr(os, "open", replace_before_candidate_open)
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in snapshot.entries) == ("usable",)
	assert any(failure.source_name == "swapped.cdml" for failure in snapshot.failures)


#============================================
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX fifo support")
def test_catalog_skips_fifo_without_waiting_for_a_writer(tmp_path: pathlib.Path) -> None:
	"""A FIFO candidate is rejected from its nonblocking opened descriptor."""
	usable = tmp_path / "usable.cdml"
	fifo = tmp_path / "stream.cdml"
	usable.write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	try:
		os.mkfifo(fifo)
	except OSError:
		pytest.skip("temporary filesystem rejects FIFO creation")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in snapshot.entries) == ("usable",)
	assert any(failure.source_name == "stream.cdml" for failure in snapshot.failures)


#============================================
def test_whitespace_only_backend_name_falls_back_to_filename_stem(
		tmp_path: pathlib.Path,
		) -> None:
	"""A nonblank label cannot be invented from whitespace-only molecule metadata."""
	template = _UNNAMED_TEMPLATE.replace("<molecule>", '<molecule name=" ">')
	(tmp_path / "fallback.cdml").write_text(template, encoding="utf-8")
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert snapshot.entries[0].label == "fallback"


#============================================
def test_prior_catalog_snapshot_retains_payload_after_file_change(
		tmp_path: pathlib.Path,
		) -> None:
	"""A later explicit rescan cannot mutate an already returned snapshot value."""
	template_path = tmp_path / "saved.cdml"
	template_path.write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	prior_snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	updated_template = _NAMED_TEMPLATE
	template_path.write_text(updated_template, encoding="utf-8")
	current_snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert prior_snapshot.entries[0].template_cdml == _UNNAMED_TEMPLATE
	assert current_snapshot.entries[0].template_cdml == updated_template


@pytest.mark.skipif(not _RAW_BYTE_FILENAMES_SUPPORTED, reason="requires POSIX")
def test_surrogate_cdml_filename_is_a_safe_failure_beside_a_good_template(
		tmp_path: pathlib.Path,
		) -> None:
	"""A non-UTF-8 filename cannot abort neighboring valid catalog admission."""
	(tmp_path / "usable.cdml").write_text(_UNNAMED_TEMPLATE, encoding="utf-8")
	raw_filename = os.path.join(os.fsencode(str(tmp_path)), b"\xff.cdml")
	try:
		file_descriptor = os.open(raw_filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
	except OSError:
		pytest.skip("temporary filesystem rejects raw-byte filenames")
	with os.fdopen(file_descriptor, "wb") as raw_file:
		raw_file.write(_UNNAMED_TEMPLATE.encode("utf-8"))
	snapshot = bkchem_qt.io.user_template_catalog.scan_user_template_catalog(tmp_path)
	assert tuple(entry.label for entry in snapshot.entries) == ("usable",)
	assert any(failure.source_name == "\\xff.cdml" for failure in snapshot.failures)
