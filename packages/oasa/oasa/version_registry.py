"""Strict parser for the source-tree release VERSION registry."""

# Standard Library
import dataclasses
import re


VERSION_ASSIGNMENT_PATTERN = re.compile(
	r"^(?P<prefix>\s*version\s*=\s*)(?P<version>[^\s#]+)"
	r"(?P<suffix>\s*(?:#.*)?)$"
)
VERSION_START_PATTERN = re.compile(r"^\s*version\s*=")
PEP440_SUBSET_PATTERN = re.compile(
	r"^\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?"
	r"(?:\+[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)?$"
)
_DISPLAY_CALVER_PATTERN = re.compile(
	r"^(?P<year>\d{2})\.(?P<month>0[1-9]|1[0-2])"
	r"(?:\.(?P<patch>[1-9]\d*))?"
	r"(?:(?P<pre>a|b|rc)(?P<pre_number>[1-9]\d*))?$"
)
_DISTRIBUTION_CALVER_PATTERN = re.compile(
	r"^(?P<year>\d{2})\.(?P<month>[1-9]|1[0-2])"
	r"(?:\.(?P<patch>[1-9]\d*))?"
	r"(?:(?P<pre>a|b|rc)(?P<pre_number>[1-9]\d*))?$"
)
_NUMERIC_DOTTED_PATTERN = re.compile(r"^\d+(?:\.\d+){0,2}$")


class ReleaseVersionError(ValueError):
	"""Report a release value outside BKChem's supported CalVer profile."""


@dataclasses.dataclass(frozen=True)
class ReleaseVersion:
	"""One release identity projected into display, packaging, and macOS forms."""

	display: str
	distribution: str
	macos_short_version: str


#============================================
def _profile_from_match(match: re.Match[str], *, display: str) -> ReleaseVersion:
	"""Build one release profile from an already-validated CalVer match."""
	year = match.group("year")
	month = match.group("month")
	patch = match.group("patch")
	pre = match.group("pre")
	pre_number = match.group("pre_number")
	distribution = f"{int(year)}.{int(month)}"
	if patch is not None:
		distribution += f".{int(patch)}"
	if pre is not None:
		distribution += f"{pre}{int(pre_number)}"
	return ReleaseVersion(
		display=display,
		distribution=distribution,
		macos_short_version=f"{int(year)}.{int(month)}.{int(patch or '0')}",
	)


#============================================
def release_version_profile(display: str) -> ReleaseVersion:
	"""Return the supported CalVer projections for an exact registry display value.

	The root registry retains its zero-padded display spelling.  Distribution
	metadata and macOS standard keys use their deliberately different grammars.
	"""
	match = _DISPLAY_CALVER_PATTERN.fullmatch(display)
	if match is None:
		raise ReleaseVersionError(f"Unsupported BKChem CalVer display value: {display!r}")
	return _profile_from_match(match, display=display)


#============================================
def display_from_distribution(distribution: str) -> str:
	"""Reconstruct the exact supported display spelling from normalized metadata."""
	match = _DISTRIBUTION_CALVER_PATTERN.fullmatch(distribution)
	if match is None:
		raise ReleaseVersionError(
			f"Unsupported normalized BKChem distribution version: {distribution!r}"
		)
	profile = _profile_from_match(match, display="")
	if profile.distribution != distribution:
		raise ReleaseVersionError(
			"BKChem distribution version must use normalized numeric spelling: "
			f"{distribution!r}; expected {profile.distribution!r}"
		)
	year = match.group("year")
	month = match.group("month")
	patch = match.group("patch")
	pre = match.group("pre")
	pre_number = match.group("pre_number")
	display = f"{int(year):02d}.{int(month):02d}"
	if patch is not None:
		display += f".{int(patch)}"
	if pre is not None:
		display += f"{pre}{int(pre_number)}"
	return display


#============================================
def validate_macos_bundle_build(bundle_build: str) -> str:
	"""Validate one explicit numeric macOS bundle-build identity."""
	if not _NUMERIC_DOTTED_PATTERN.fullmatch(bundle_build):
		raise ReleaseVersionError(
			"macOS bundle build must contain one to three numeric dotted components: "
			f"{bundle_build!r}"
		)
	return bundle_build


#============================================
def parse_version_text(text: str) -> str:
	"""Return one canonical release value from strict registry text."""
	versions: list[str] = []
	for line in text.splitlines():
		if not VERSION_START_PATTERN.match(line):
			continue
		match = VERSION_ASSIGNMENT_PATTERN.fullmatch(line)
		if not match:
			raise ValueError(f"Malformed VERSION assignment: {line!r}")
		version = match.group("version")
		if not PEP440_SUBSET_PATTERN.fullmatch(version):
			raise ValueError(f"Invalid VERSION value: {version!r}")
		versions.append(version)
	if len(versions) != 1:
		raise ValueError("VERSION must contain exactly one version assignment")
	return versions[0]


#============================================
def read_version_file(path: str) -> str:
	"""Read and parse a source-tree VERSION registry file."""
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	version = parse_version_text(text)
	return version
