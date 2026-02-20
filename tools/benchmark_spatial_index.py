#!/usr/bin/env python3
"""Benchmark spatial index vs brute-force for OASA coordinate generation.

Measures wall-clock time for coordinate generation on molecules of
increasing size, comparing the spatial index acceleration against
the brute-force baseline. Prints a summary table.
"""

import time
import statistics

import oasa.smiles_lib
import oasa.coords_gen.calculate as coords_calc
from oasa.graph.spatial_index import SpatialIndex, brute_force_pairs


# test molecules ordered by approximate atom count
TEST_MOLECULES = [
	("methane", "C", 1),
	("ethanol", "CCO", 3),
	("benzene", "c1ccccc1", 6),
	("naphthalene", "c1ccc2ccccc2c1", 10),
	("caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", 14),
	("cholesterol",
		"CC(C)CCCC(C)C1CCC2C1(CCC3C2CC=C4C3(CCC(C4)O)C)C",
		27),
	("chain_50", "C" * 50, 50),
	("chain_100", "C" * 100, 100),
]


#============================================
def _parse_smiles(smiles_str: str):
	"""Parse a SMILES string and return the OASA molecule."""
	mol = oasa.smiles_lib.text_to_mol(smiles_str, calc_coords=False)
	return mol


#============================================
def _benchmark_coord_gen(smiles_str: str, repeats: int = 3) -> float:
	"""Benchmark coordinate generation for a SMILES string.

	Args:
		smiles_str: SMILES string to benchmark.
		repeats: number of repetitions for averaging.

	Returns:
		Median wall-clock time in milliseconds.
	"""
	times = []
	for _ in range(repeats):
		mol = oasa.smiles_lib.text_to_mol(smiles_str, calc_coords=False)
		start = time.perf_counter()
		coords_calc.calculate_coords(mol, bond_length=1.0, force=True)
		elapsed = time.perf_counter() - start
		times.append(elapsed * 1000)  # convert to ms
	median_ms = statistics.median(times)
	return median_ms


#============================================
def _benchmark_spatial_index_standalone(n_points: int,
	radius: float, repeats: int = 5) -> tuple:
	"""Benchmark spatial index build + query_pairs vs brute force.

	Args:
		n_points: number of random points.
		radius: search radius.
		repeats: number of repetitions for averaging.

	Returns:
		Tuple of (brute_force_ms, spatial_index_ms) medians.
	"""
	import random
	rng = random.Random(42)
	points = [(rng.uniform(-50, 50), rng.uniform(-50, 50))
		for _ in range(n_points)]

	# brute force timing
	bf_times = []
	for _ in range(repeats):
		start = time.perf_counter()
		brute_force_pairs(points, radius)
		elapsed = time.perf_counter() - start
		bf_times.append(elapsed * 1000)

	# spatial index timing (includes build + query)
	si_times = []
	for _ in range(repeats):
		start = time.perf_counter()
		idx = SpatialIndex.build(points)
		idx.query_pairs(radius)
		elapsed = time.perf_counter() - start
		si_times.append(elapsed * 1000)

	return statistics.median(bf_times), statistics.median(si_times)


#============================================
def main():
	"""Run benchmarks and print results."""
	print("=" * 70)
	print("OASA Coordinate Generation Benchmark (with spatial index)")
	print("=" * 70)

	# part 1: full coord gen pipeline
	print("\n--- Coordinate Generation Pipeline ---")
	print(f"{'Molecule':<20} {'Atoms':>6} {'Time (ms)':>12}")
	print("-" * 42)
	for name, smiles, approx_atoms in TEST_MOLECULES:
		median_ms = _benchmark_coord_gen(smiles)
		print(f"{name:<20} {approx_atoms:>6} {median_ms:>12.2f}")

	# part 2: standalone spatial index vs brute force
	print("\n--- Spatial Index vs Brute Force (standalone) ---")
	print(f"{'N points':>10} {'Brute (ms)':>12} {'KD-tree (ms)':>14} {'Speedup':>10}")
	print("-" * 50)
	# use radius proportional to point spread to get meaningful pair counts
	for n in [20, 50, 100, 200, 500, 1000]:
		radius = 5.0
		bf_ms, si_ms = _benchmark_spatial_index_standalone(n, radius)
		speedup = bf_ms / si_ms if si_ms > 0 else float('inf')
		print(f"{n:>10} {bf_ms:>12.3f} {si_ms:>14.3f} {speedup:>9.1f}x")

	print("\n" + "=" * 70)
	print("Done.")


#============================================
if __name__ == '__main__':
	main()
