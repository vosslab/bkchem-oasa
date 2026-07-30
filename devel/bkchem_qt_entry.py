#!/usr/bin/env python3

"""Stable PyInstaller entry point for the Qt BKChem frontend."""

# local repo modules
import bkchem_qt.cli


#============================================
def main() -> None:
	"""Launch the Qt frontend through its supported command-line interface."""
	bkchem_qt.cli.main()


#============================================

if __name__ == "__main__":
	main()
