"""Smoke tests for sugar-code parser curated cases."""

# Standard Library
import os

# Local repo modules
import conftest

import oasa.sugar_code as sugar_code


#============================================
def _fixture_path() -> str:
	return os.path.join(
		conftest.repo_root(),
		"tests",
		"fixtures",
		"smoke_sugar_codes.txt",
	)


#============================================
def _load_cases(path: str) -> list[tuple[str, str, int]]:
	cases = []
	with open(path, "r", encoding="utf-8") as handle:
		for line_number, line in enumerate(handle, start=1):
			text = line.strip()
			if not text:
				continue
			if text.startswith("#"):
				continue
			if "|" not in text:
				raise ValueError(f"Invalid smoke fixture line {line_number}: {text}")
			status, code = [part.strip() for part in text.split("|", 1)]
			state = status.lower()
			if state not in ("valid", "invalid"):
				raise ValueError(
					f"Invalid smoke fixture status '{status}' at line {line_number}"
				)
			cases.append((state, code, line_number))
	return cases


#============================================
def test_sugar_code_smoke():
	cases = _load_cases(_fixture_path())
	assert cases
	for state, code, line_number in cases:
		if state == "valid":
			parsed = sugar_code.parse(code)
			assert parsed.sugar_code_raw == code
			if "[" in code:
				assert parsed.sugar_code_raw.startswith(parsed.sugar_code)
			else:
				assert parsed.sugar_code_raw == parsed.sugar_code
			continue
		try:
			sugar_code.parse(code)
		except ValueError:
			continue
		raise AssertionError(
			f"Expected ValueError for invalid smoke case line {line_number}: {code}"
		)
