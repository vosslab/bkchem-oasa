#!/usr/bin/env python3

"""Check translation files for formatting consistency."""

# Standard Library
import os
import subprocess


#============================================
def get_repo_root() -> object:
	"""Get repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


#============================================
def check_translation_file(filename: object) -> object:
	"""Print printf-placeholder count mismatches for one .po file."""
	msgid = ""
	line_index = 0
	with open(filename, "r", encoding="utf-8") as handle:
		for line in handle:
			if line.startswith("msgid"):
				msgid = line
			elif line.startswith("msgstr"):
				msgstr = line
				# msgstr == 'msgstr ""' means untranslated; skip those.
				if msgstr != 'msgstr ""\n' and msgid.count("%") != msgstr.count("%"):
					print("!! line %d: %s vs. %s" % (line_index, msgid, msgstr))
			line_index += 1


#============================================
def main() -> None:
	"""Run translation checks for all locale files."""
	repo_root = get_repo_root()
	locale_dir = os.path.join(repo_root, "packages", "bkchem", "bkchem_data", "locale")
	if not os.path.isdir(locale_dir):
		raise FileNotFoundError("Locale directory not found: %s" % locale_dir)
	for lang in sorted(os.listdir(locale_dir)):
		filename = os.path.join(locale_dir, lang, "BKChem.po")
		if not os.path.isfile(filename):
			continue
		print("-- language:", lang)
		check_translation_file(filename)


if __name__ == "__main__":
	main()
