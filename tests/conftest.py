# Exclude both end-to-end tiers from pytest collection. tests/playwright/
# holds browser-driven tests (Playwright), and tests/e2e/ holds heavier
# shell/Python whole-system runners. Both run outside pytest -- see
# docs/PLAYWRIGHT_USAGE.md and docs/E2E_TESTS.md.
collect_ignore = ["e2e", "playwright"]

# Standard Library
import os
import sys


def pytest_addoption(parser):
	parser.addoption(
		"--save",
		action="store_true",
		default=False,
		help="Save rendered outputs to the current working directory",
	)


def repo_root():
	root = _find_repo_root(os.getcwd())
	if not root:
		raise RuntimeError("repo root could not be resolved from current working directory")
	return root


#============================================
def tests_root():
	return os.path.join(repo_root(), "tests")


#============================================
def tests_path(*parts):
	return os.path.join(tests_root(), *parts)


#============================================
def _find_repo_root(start_dir):
	current = os.path.abspath(start_dir)
	while True:
		if _looks_like_repo_root(current):
			return current
		parent = os.path.dirname(current)
		if parent == current:
			return ""
		current = parent


#============================================
def _looks_like_repo_root(path):
	if not path:
		return False
	if not os.path.isdir(path):
		return False
	if not os.path.isfile(os.path.join(path, "AGENTS.md")):
		return False
	if not os.path.isfile(os.path.join(path, "docs", "REPO_STYLE.md")):
		return False
	return True


def add_repo_root_to_sys_path():
	root = repo_root()
	if root not in sys.path:
		sys.path.insert(0, root)
	return root


def add_bkchem_to_sys_path():
	root = add_repo_root_to_sys_path()
	bkchem_dir = os.path.join(root, "packages", "bkchem")
	if bkchem_dir not in sys.path:
		sys.path.insert(0, bkchem_dir)
	bkchem_module_dir = os.path.join(bkchem_dir, "bkchem")
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)
	return root


def add_oasa_to_sys_path():
	root = add_repo_root_to_sys_path()
	oasa_dir = os.path.join(root, "packages", "oasa")
	if oasa_dir not in sys.path:
		sys.path.insert(0, oasa_dir)
	return root
