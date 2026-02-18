#!/usr/bin/env python3

# Standard Library
import runpy


#============================================
def main() -> None:
	"""Run BKChem as a console script."""
	runpy.run_module("bkchem.bkchem_app", run_name="__main__")


if __name__ == '__main__':
	main()
