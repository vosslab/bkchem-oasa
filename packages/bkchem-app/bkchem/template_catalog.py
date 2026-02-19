#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program
#
#--------------------------------------------------------------------------

"""Template catalog helpers for folder-based template discovery."""

# Standard Library
import dataclasses
import os

# local repo modules
from bkchem import os_support


TEMPLATE_EXTENSIONS = (".cdml", ".cdgz")
BIOMOLECULE_TEMPLATE_SUBDIR = "biomolecules"


#============================================
@dataclasses.dataclass(frozen=True)
class TemplateEntry:
	path: str
	name: str
	category: str
	subcategory: str | None


#============================================
def scan_template_tree(root_dir, include_root_files=False):
	"""
	Scan a template directory tree and return TemplateEntry items.

	Args:
		root_dir: Root directory to scan.
		include_root_files: Include files directly under the root directory.

	Returns:
		list[TemplateEntry]: Sorted template entries.
	"""
	if not root_dir or not os.path.isdir(root_dir):
		return []
	entries = []
	for current_root, _dirs, files in os.walk(root_dir):
		for filename in sorted(files):
			if not _has_template_extension(filename):
				continue
			full_path = os.path.join(current_root, filename)
			rel_path = os.path.relpath(full_path, root_dir)
			parts = rel_path.split(os.sep)
			if len(parts) == 1 and not include_root_files:
				continue
			category, subcategory = _category_from_parts(parts)
			if not category:
				continue
			name = os.path.splitext(filename)[0]
			entries.append(
				TemplateEntry(
					path=full_path,
					name=name,
					category=category,
					subcategory=subcategory,
				)
			)
	return _sorted_entries(entries)


#============================================
def scan_template_dirs(template_dirs, include_root_files=False):
	"""
	Scan multiple template directories and merge the results.

	Args:
		template_dirs: Iterable of directories to scan.
		include_root_files: Include files directly under root directories.

	Returns:
		list[TemplateEntry]: Sorted template entries.
	"""
	entries = []
	for root_dir in template_dirs or []:
		entries.extend(scan_template_tree(root_dir, include_root_files=include_root_files))
	return _sorted_entries(entries)


#============================================
def discover_template_dirs():
	"""
	Return template directories from the configured search paths.

	Returns:
		list[str]: Existing template directories.
	"""
	dirs = []
	for root_dir in os_support.get_dirs("template"):
		if root_dir and os.path.isdir(root_dir):
			dirs.append(root_dir)
	return dirs


#============================================
def discover_biomolecule_template_dirs(subdir=BIOMOLECULE_TEMPLATE_SUBDIR):
	"""
	Return biomolecule template directories from configured template paths.

	Args:
		subdir: Subdirectory name containing biomolecule templates.

	Returns:
		list[str]: Existing biomolecule template directories.
	"""
	dirs = []
	seen = set()
	for root_dir in discover_template_dirs():
		candidate = os.path.abspath(os.path.join(root_dir, subdir))
		if os.path.isdir(candidate) and candidate not in seen:
			seen.add(candidate)
			dirs.append(candidate)
	return dirs


#============================================
def build_category_map(entries):
	"""
	Build a nested map of categories and subcategories.

	Args:
		entries: TemplateEntry list.

	Returns:
		dict: {category: {subcategory: [TemplateEntry, ...]}}.
	"""
	catalog = {}
	for entry in entries:
		category = entry.category
		subcategory = entry.subcategory or ""
		if category not in catalog:
			catalog[category] = {}
		if subcategory not in catalog[category]:
			catalog[category][subcategory] = []
		catalog[category][subcategory].append(entry)
	for category, subcats in catalog.items():
		for subcategory, items in subcats.items():
			subcats[subcategory] = _sorted_entries(items)
	return catalog


#============================================
def format_entry_label(entry):
	"""
	Format a TemplateEntry into a human-readable label.

	Args:
		entry: TemplateEntry to format.

	Returns:
		str: Display label for UI selection.
	"""
	parts = []
	if entry.category:
		parts.append(_format_label_part(entry.category))
	if entry.subcategory:
		parts.append(_format_label_part(entry.subcategory))
	name = entry.name
	if entry.subcategory and entry.name == entry.subcategory:
		name = ""
	if name:
		parts.append(_format_label_part(name))
	return " / ".join(parts)


#============================================
def _has_template_extension(filename):
	return filename.lower().endswith(TEMPLATE_EXTENSIONS)


#============================================
def _category_from_parts(parts):
	if not parts:
		return None, None
	if len(parts) == 1:
		return "uncategorized", None
	category = parts[0]
	subcategory = None
	if len(parts) > 2:
		subcategory = parts[1]
	elif len(parts) == 2:
		subcategory = ""
	return category, subcategory


#============================================
def _sorted_entries(entries):
	return sorted(entries, key=lambda entry: (entry.category, entry.subcategory or "", entry.name))


#============================================
def _format_label_part(value):
	return value.replace("_", " ").strip()
