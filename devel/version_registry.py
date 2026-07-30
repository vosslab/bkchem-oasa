"""Read and update the monorepo's canonical VERSION assignment."""

# Standard Library
import os
import re


VERSION_ASSIGNMENT_PATTERN = re.compile(
	r"^(?P<prefix>\s*version\s*=\s*)(?P<version>[^\s#]+)"
	r"(?P<suffix>\s*(?:#.*)?)$"
)
VERSION_START_PATTERN = re.compile(r"^\s*version\s*=")
PEP440ISH_PATTERN = re.compile(
	r"^\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?"
	r"(?:\+[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)?$"
)


#============================================
def validate_version(version: str) -> str:
	"""Validate and return a nonempty PEP 440-shaped release version."""
	if not PEP440ISH_PATTERN.fullmatch(version):
		raise ValueError(f"Invalid VERSION value: {version!r}")
	return version


#============================================
def parse_version_text(text: str) -> str:
	"""Extract one strict ``version = value`` assignment from registry text."""
	versions: list[str] = []
	for line in text.splitlines():
		if not VERSION_START_PATTERN.match(line):
			continue
		match = VERSION_ASSIGNMENT_PATTERN.fullmatch(line)
		if not match:
			raise ValueError(f"Malformed VERSION assignment: {line!r}")
		versions.append(validate_version(match.group("version")))
	if len(versions) != 1:
		raise ValueError("VERSION must contain exactly one version assignment")
	return versions[0]


#============================================
def update_version_text(text: str, version: str) -> tuple[str, bool]:
	"""Replace the registry value while preserving its assignment and comments."""
	new_version = validate_version(version)
	lines = text.splitlines(keepends=True)
	updated_lines: list[str] = []
	found = False
	changed = False
	for line in lines:
		line_text = line.rstrip("\r\n")
		line_ending = line[len(line_text):]
		if not VERSION_START_PATTERN.match(line_text):
			updated_lines.append(line)
			continue
		match = VERSION_ASSIGNMENT_PATTERN.fullmatch(line_text)
		if not match:
			raise ValueError(f"Malformed VERSION assignment: {line_text!r}")
		if found:
			raise ValueError("VERSION must contain exactly one version assignment")
		found = True
		current_version = validate_version(match.group("version"))
		updated_line = f"{match.group('prefix')}{new_version}{match.group('suffix')}"
		updated_lines.append(updated_line + line_ending)
		changed = current_version != new_version
	if not found:
		raise ValueError("VERSION must contain exactly one version assignment")
	updated_text = "".join(updated_lines)
	return updated_text, changed


#============================================
def create_version_text(version: str) -> str:
	"""Create canonical registry text for a previously missing VERSION file."""
	new_version = validate_version(version)
	text = f"version = {new_version}\n"
	return text


#============================================
def read_version_file(path: str) -> str:
	"""Read and strictly parse a canonical VERSION registry file."""
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	version = parse_version_text(text)
	return version


#============================================
def update_version_file(path: str, version: str) -> bool:
	"""Update a registry file in place while retaining its non-version content."""
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	updated_text, changed = update_version_text(text, version)
	if changed:
		with open(path, "w", encoding="utf-8") as handle:
			handle.write(updated_text)
	return changed


#============================================
def repository_root(start_path: str) -> str | None:
	"""Return the nearest ancestor recognized as a Git worktree root."""
	current_path = os.path.abspath(start_path)
	if os.path.isfile(current_path):
		current_path = os.path.dirname(current_path)
	while True:
		if os.path.exists(os.path.join(current_path, ".git")):
			return current_path
		parent_path = os.path.dirname(current_path)
		if parent_path == current_path:
			return None
		current_path = parent_path


#============================================
def resolve_version_path(start_path: str) -> str:
	"""Resolve the canonical VERSION from Git root or generic project ancestry."""
	root_path = repository_root(start_path)
	if root_path is not None:
		version_path = os.path.join(root_path, "VERSION")
		return version_path

	current_path = os.path.abspath(start_path)
	if os.path.isfile(current_path):
		current_path = os.path.dirname(current_path)
	start_directory = current_path
	while True:
		version_path = os.path.join(current_path, "VERSION")
		if os.path.isfile(version_path):
			return version_path
		parent_path = os.path.dirname(current_path)
		if parent_path == current_path:
			fallback_path = os.path.join(start_directory, "VERSION")
			return fallback_path
		current_path = parent_path
