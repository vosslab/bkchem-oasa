"""Pure regression coverage for the canonical release-version registry."""

# Standard Library
import pathlib
import sys
import tomllib

# PIP3 modules
import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "devel"))

# local repo modules
import commit_changelog
import bump_version
import submit_to_pypi
import version_registry
import oasa.version_registry as release_version_registry


#============================================
@pytest.mark.parametrize(("display", "distribution", "macos_short"), (
	("26.02a1", "26.2a1", "26.2.0"),
	("26.07", "26.7", "26.7.0"),
	("26.07rc2", "26.7rc2", "26.7.0"),
	("26.07.3", "26.7.3", "26.7.3"),
))
def test_release_profile_projects_display_distribution_and_macos_forms(
		display: str, distribution: str, macos_short: str,
		) -> None:
	"""One checked-in CalVer label has deliberate consumer-specific projections."""
	profile = release_version_registry.release_version_profile(display)

	assert (profile.display, profile.distribution, profile.macos_short_version) == (
		display, distribution, macos_short,
	)


#============================================
@pytest.mark.parametrize(("distribution", "display"), (
	("26.2a1", "26.02a1"),
	("26.7", "26.07"),
	("26.7rc2", "26.07rc2"),
	("26.7.3", "26.07.3"),
))
def test_distribution_metadata_reconstructs_the_exact_display_label(
		distribution: str, display: str,
		) -> None:
	"""Installed metadata restores the repository's zero-padded public spelling."""
	assert release_version_registry.display_from_distribution(distribution) == display


#============================================
@pytest.mark.parametrize("value", ("26.2", "26.13", "26.7.0", "v26.07", "26.7.post1"))
def test_release_profile_rejects_values_outside_the_supported_calver_contract(value: str) -> None:
	"""Release projection refuses ambiguous or unrelated PEP 440 spellings."""
	with pytest.raises(release_version_registry.ReleaseVersionError):
		release_version_registry.release_version_profile(value)


#============================================
@pytest.mark.parametrize("bundle_build", ("1", "26.7", "26.7.1"))
def test_macos_bundle_build_accepts_numeric_dotted_identity(bundle_build: str) -> None:
	"""A distributable build carries an explicit numeric macOS identity."""
	assert release_version_registry.validate_macos_bundle_build(bundle_build) == bundle_build


#============================================
@pytest.mark.parametrize("bundle_build", ("", "26.7a1", "26.7.1.2", "26.x", "26-7"))
def test_macos_bundle_build_rejects_non_numeric_or_overspecified_identity(bundle_build: str) -> None:
	"""macOS bundle-build input remains a bounded numeric dotted value."""
	with pytest.raises(release_version_registry.ReleaseVersionError):
		release_version_registry.validate_macos_bundle_build(bundle_build)


#============================================
def test_registry_parser_ignores_comments() -> None:
	"""Comments do not become part of the release value."""
	text = "# release registry\nversion = 26.02a1 # alpha\n"

	assert version_registry.parse_version_text(text) == "26.02a1"


#============================================
def test_registry_update_preserves_assignment_context() -> None:
	"""Changing a release retains registry comments and assignment syntax."""
	text = "# release registry\nversion = 26.02a1 # alpha\n"
	updated_text, changed = version_registry.update_version_text(text, "26.02b1")

	assert (updated_text, changed) == (
		"# release registry\nversion = 26.02b1 # alpha\n", True,
	)


#============================================
def test_commit_changelog_reads_assignment_value(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""Commit freshness receives the parsed registry value, not comments."""
	(tmp_path / "VERSION").write_text("# release\nversion = 26.02a1\n", encoding="utf-8")
	monkeypatch.setattr(commit_changelog.changelog_lib, "get_git_root", lambda: str(tmp_path))

	assert commit_changelog.read_version_file() == "26.02a1"


#============================================
def test_package_directory_resolves_git_root_registry(tmp_path: pathlib.Path) -> None:
	"""Package tooling finds the monorepo registry rather than a child path."""
	(tmp_path / ".git").mkdir()
	(tmp_path / "VERSION").write_text("version = 26.02a1\n", encoding="utf-8")
	package_dir = tmp_path / "packages" / "bkchem-app"
	package_dir.mkdir(parents=True)

	assert submit_to_pypi.read_version_file(str(package_dir)) == "26.02a1"


#============================================
def test_bump_discovery_uses_assignment_registry(tmp_path: pathlib.Path) -> None:
	"""Bump discovery keeps the root registry as an assignment-backed source."""
	(tmp_path / ".git").mkdir()
	(tmp_path / "VERSION").write_text("# release\nversion = 26.02a1\n", encoding="utf-8")

	entries = bump_version.parse_versions(str(tmp_path), max_depth=1)

	assert (entries[0]["kind"], entries[0]["version"]) == (
		"version_registry", "26.02a1",
	)


#============================================
def test_pypi_update_from_package_directory_updates_all_release_metadata(
		tmp_path: pathlib.Path,
		) -> None:
	"""PyPI release updates delegate to the monorepo-wide metadata updater."""
	(tmp_path / ".git").mkdir()
	(tmp_path / "VERSION").write_text("version = 26.02a1\n", encoding="utf-8")
	oasa_dir = tmp_path / "packages" / "oasa"
	bkchem_dir = tmp_path / "packages" / "bkchem-app"
	qt_dir = tmp_path / "packages" / "bkchem-qt.app"
	oasa_dir.mkdir(parents=True)
	bkchem_dir.mkdir()
	qt_dir.mkdir()
	oasa_dir.joinpath("pyproject.toml").write_text(
		"[project]\nname = \"oasa\"\nversion = \"26.02a1\"\n",
		encoding="utf-8",
	)
	bkchem_dir.joinpath("pyproject.toml").write_text(
		"[project]\nname = \"bkchem\"\nversion = \"26.02a1\"\n"
		"dependencies = [\"oasa>=26.02a1\"]\n",
		encoding="utf-8",
	)
	qt_dir.joinpath("pyproject.toml").write_text(
		"[project]\nname = \"bkchem-qt\"\nversion = \"26.02a1\"\n"
		"dependencies = [\"oasa>=26.02a1\"]\n",
		encoding="utf-8",
	)

	submit_to_pypi.update_version_files(str(bkchem_dir), "26.03a1")
	project_data = tuple(
		tomllib.loads(path.joinpath("pyproject.toml").read_text(encoding="utf-8"))["project"]
		for path in (oasa_dir, bkchem_dir, qt_dir)
	)
	versions = tuple(project["version"] for project in project_data)
	requirements = tuple(project.get("dependencies", []) for project in project_data)

	assert (version_registry.read_version_file(str(tmp_path / "VERSION")), versions, requirements) == (
		"26.03a1",
		("26.03a1", "26.03a1", "26.03a1"),
		([], ["oasa>=26.03a1"], ["oasa>=26.03a1"]),
	)


#============================================
def test_oasa_lower_bound_update_preserves_requirement_remainder() -> None:
	"""Only the OASA lower-bound token changes in a constrained requirement."""
	text = (
		"[project]\nversion = \"26.02a1\"\n"
		"dependencies = [\"oasa[rdkit] >= 26.02a1, <27; python_version >= '3.10'\"]\n"
	)
	updated_text, changed = bump_version.update_pyproject(text, ["project"], "26.03a1")

	assert (updated_text, changed) == (
		"[project]\nversion = \"26.03a1\"\n"
		"dependencies = [\"oasa[rdkit] >= 26.03a1, <27; python_version >= '3.10'\"]\n",
		True,
	)


#============================================
def test_release_update_keeps_generic_repository_scope(tmp_path: pathlib.Path) -> None:
	"""A non-monorepo project updates only its own package metadata."""
	(tmp_path / ".git").mkdir()
	(tmp_path / "VERSION").write_text("version = 26.02a1\n", encoding="utf-8")
	project_dir = tmp_path / "single-project"
	project_dir.mkdir()
	project_dir.joinpath("pyproject.toml").write_text(
		"[project]\nname = \"single-project\"\nversion = \"26.02a1\"\n",
		encoding="utf-8",
	)

	submit_to_pypi.update_version_files(str(project_dir), "26.03a1")
	project_data = tomllib.loads(
		project_dir.joinpath("pyproject.toml").read_text(encoding="utf-8")
	)

	assert (version_registry.read_version_file(str(tmp_path / "VERSION")),
		project_data["project"]["version"]) == ("26.03a1", "26.03a1")
