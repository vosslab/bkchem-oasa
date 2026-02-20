#!/usr/bin/env python3
"""Benchmark comparing OASA graph algorithms vs rustworkx equivalents.

Runs timing comparisons on real molecule graphs parsed from SMILES strings.
Verifies result parity between the two implementations and prints speedup
ratios in a summary table.
"""

# Standard Library
import sys
import time
import argparse

# PIP3 modules
import numpy
import rustworkx

# ensure OASA package is importable from the repo tree
sys.path.insert(0, "packages/oasa")

# local repo modules
import oasa.smiles_lib


# ============================================
# Molecule definitions
# ============================================

MOLECULES = {
	"benzene": "c1ccccc1",
	"naphthalene": "c1ccc2ccccc2c1",
	"cholesterol": (
		"C(CCCCCCCC)C(CC)C(CCC(C(CC1)CC(O)C1)C)C=C(CC2)C2(C)CC3C=4CCC3C4C"
	),
}


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Benchmark OASA vs rustworkx graph algorithms"
	)
	parser.add_argument(
		'-n', '--iterations', dest='num_iterations',
		type=int, default=500,
		help="Number of timing iterations per algorithm (default: 500)",
	)
	parser.add_argument(
		'-v', '--verbose', dest='verbose',
		action='store_true',
		help="Print detailed per-algorithm output",
	)
	args = parser.parse_args()
	return args


#============================================
def smiles_to_oasa_mol(smiles: str):
	"""Parse a SMILES string into an OASA molecule object.

	Args:
		smiles: SMILES string for the molecule.

	Returns:
		An oasa.molecule instance with zero-order bonds removed.
	"""
	mol = oasa.smiles_lib.text_to_mol(smiles, calc_coords=0)
	mol.remove_zero_order_bonds()
	return mol


#============================================
def oasa_mol_to_rustworkx(mol) -> tuple:
	"""Build a rustworkx PyGraph from an OASA molecule.

	Args:
		mol: An oasa.molecule instance.

	Returns:
		Tuple of (rx_graph, vertex_to_index, index_to_vertex) where
		vertex_to_index maps OASA vertex objects to rustworkx node indices
		and index_to_vertex maps indices back.
	"""
	rx_graph = rustworkx.PyGraph(multigraph=False)
	vertex_to_index = {}
	index_to_vertex = {}

	# add all vertices as nodes
	for vertex in mol.vertices:
		idx = rx_graph.add_node(vertex)
		vertex_to_index[vertex] = idx
		index_to_vertex[idx] = vertex

	# add all edges
	for edge in mol.edges:
		v1, v2 = edge.vertices
		rx_graph.add_edge(
			vertex_to_index[v1],
			vertex_to_index[v2],
			edge,
		)

	return rx_graph, vertex_to_index, index_to_vertex


#============================================
def time_function(func, num_iterations: int) -> float:
	"""Time a function over multiple iterations.

	Args:
		func: Callable taking no arguments.
		num_iterations: Number of times to call func.

	Returns:
		Average time per call in microseconds.
	"""
	start = time.perf_counter()
	for _ in range(num_iterations):
		func()
	elapsed = time.perf_counter() - start
	avg_us = (elapsed / num_iterations) * 1_000_000
	return avg_us


#============================================
def verify_connected_components(mol, rx_graph, v_to_i) -> str:
	"""Check that both backends agree on number of connected components.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	oasa_components = list(mol.get_connected_components())
	rx_components = rustworkx.connected_components(rx_graph)
	if len(oasa_components) == len(rx_components):
		return "MATCH"
	return "MISMATCH"


#============================================
def verify_is_connected(mol, rx_graph) -> str:
	"""Check that both backends agree on connectivity.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	oasa_result = mol.is_connected()
	rx_result = rustworkx.is_connected(rx_graph)
	if oasa_result == rx_result:
		return "MATCH"
	return "MISMATCH"


#============================================
def verify_path_exists(mol, rx_graph, v_to_i) -> str:
	"""Check path_exists parity between start and end vertices.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	v_start = mol.vertices[0]
	v_end = mol.vertices[-1]
	oasa_result = mol.path_exists(v_start, v_end)
	rx_result = rustworkx.has_path(
		rx_graph, v_to_i[v_start], v_to_i[v_end]
	)
	if oasa_result == rx_result:
		return "MATCH"
	return "MISMATCH"


#============================================
def verify_diameter(mol, rx_graph) -> str:
	"""Check diameter parity between OASA and rustworkx.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	oasa_diameter = mol.get_diameter()
	# rustworkx: compute distance matrix, take max finite value
	dist_matrix = rustworkx.distance_matrix(rx_graph)
	rx_diameter = int(numpy.max(dist_matrix))
	if oasa_diameter == rx_diameter:
		return "MATCH"
	return "MISMATCH"


#============================================
def verify_cycle_basis(mol, rx_graph) -> str:
	"""Check cycle count parity between OASA and rustworkx.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	oasa_cycles = mol.get_smallest_independent_cycles()
	rx_cycles = rustworkx.cycle_basis(rx_graph)
	if len(oasa_cycles) == len(rx_cycles):
		return "MATCH"
	return "MISMATCH"


#============================================
def verify_find_path(mol, rx_graph, v_to_i) -> str:
	"""Check that both backends find a path of the same length.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	v_start = mol.vertices[0]
	v_end = mol.vertices[-1]
	oasa_path = mol.find_path_between(v_start, v_end)
	rx_paths = rustworkx.dijkstra_shortest_paths(
		rx_graph, v_to_i[v_start], v_to_i[v_end]
	)
	if oasa_path is None and v_to_i[v_end] not in rx_paths:
		return "MATCH"
	if oasa_path is not None and v_to_i[v_end] in rx_paths:
		# both found a path; compare lengths (both include endpoints)
		oasa_len = len(oasa_path)
		rx_len = len(rx_paths[v_to_i[v_end]])
		if oasa_len == rx_len:
			return "MATCH"
	return "MISMATCH"


#============================================
def verify_distance_from(mol, rx_graph, v_to_i) -> str:
	"""Check BFS distance parity from vertex 0.

	Returns:
		'MATCH' or 'MISMATCH'.
	"""
	v_start = mol.vertices[0]
	# OASA sets d on each vertex property
	mol.mark_vertices_with_distance_from(v_start)
	oasa_distances = {}
	for v in mol.vertices:
		if 'd' in v.properties_:
			oasa_distances[v] = v.properties_['d']

	# rustworkx distance matrix row for start vertex
	dist_matrix = rustworkx.distance_matrix(rx_graph)
	start_idx = v_to_i[v_start]

	all_match = True
	for v in mol.vertices:
		oasa_d = oasa_distances.get(v)
		rx_d = int(dist_matrix[start_idx, v_to_i[v]])
		if oasa_d != rx_d:
			all_match = False
			break

	if all_match:
		return "MATCH"
	return "MISMATCH"


#============================================
def benchmark_molecule(
	name: str,
	smiles: str,
	num_iterations: int,
	verbose: bool,
) -> list:
	"""Run all benchmarks for a single molecule.

	Args:
		name: Human-readable molecule name.
		smiles: SMILES string.
		num_iterations: Number of timing iterations.
		verbose: Whether to print detailed output.

	Returns:
		List of result dicts with keys: algorithm, oasa_us, rx_us,
		speedup, parity.
	"""
	# parse molecule and build rustworkx graph
	mol = smiles_to_oasa_mol(smiles)
	rx_graph, v_to_i, i_to_v = oasa_mol_to_rustworkx(mol)

	num_atoms = len(mol.vertices)
	num_bonds = len(mol.edges)
	print(f"\n{'='*65}")
	print(f"Molecule: {name} ({num_atoms} atoms, {num_bonds} bonds)")
	print(f"SMILES: {smiles}")
	print(f"Iterations: {num_iterations}")
	print(f"{'='*65}")

	results = []

	# pick start/end vertices for path algorithms
	v_start = mol.vertices[0]
	v_end = mol.vertices[-1]
	start_idx = v_to_i[v_start]
	end_idx = v_to_i[v_end]

	# --- connected_components ---
	oasa_us = time_function(
		lambda: list(mol.get_connected_components()),
		num_iterations,
	)
	rx_us = time_function(
		lambda: rustworkx.connected_components(rx_graph),
		num_iterations,
	)
	parity = verify_connected_components(mol, rx_graph, v_to_i)
	results.append({
		"algorithm": "connected_components",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- is_connected ---
	oasa_us = time_function(
		lambda: mol.is_connected(),
		num_iterations,
	)
	rx_us = time_function(
		lambda: rustworkx.is_connected(rx_graph),
		num_iterations,
	)
	parity = verify_is_connected(mol, rx_graph)
	results.append({
		"algorithm": "is_connected",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- path_exists ---
	oasa_us = time_function(
		lambda: mol.path_exists(v_start, v_end),
		num_iterations,
	)
	rx_us = time_function(
		lambda: rustworkx.has_path(rx_graph, start_idx, end_idx),
		num_iterations,
	)
	parity = verify_path_exists(mol, rx_graph, v_to_i)
	results.append({
		"algorithm": "path_exists",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- distance_from ---
	oasa_us = time_function(
		lambda: mol.mark_vertices_with_distance_from(v_start),
		num_iterations,
	)
	rx_us = time_function(
		lambda: rustworkx.distance_matrix(rx_graph),
		num_iterations,
	)
	parity = verify_distance_from(mol, rx_graph, v_to_i)
	results.append({
		"algorithm": "distance_from",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- diameter ---
	# flush OASA cache so each iteration recomputes
	oasa_us = time_function(
		lambda: (mol._flush_cache(), mol.get_diameter())[1],
		num_iterations,
	)
	rx_us = time_function(
		lambda: int(numpy.max(rustworkx.distance_matrix(rx_graph))),
		num_iterations,
	)
	parity = verify_diameter(mol, rx_graph)
	results.append({
		"algorithm": "diameter",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- cycle_basis ---
	oasa_us = time_function(
		lambda: mol.get_smallest_independent_cycles(),
		num_iterations,
	)
	rx_us = time_function(
		lambda: rustworkx.cycle_basis(rx_graph),
		num_iterations,
	)
	parity = verify_cycle_basis(mol, rx_graph)
	results.append({
		"algorithm": "cycle_basis",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- find_path ---
	oasa_us = time_function(
		lambda: mol.find_path_between(v_start, v_end),
		num_iterations,
	)
	rx_us = time_function(
		lambda: rustworkx.dijkstra_shortest_paths(
			rx_graph, start_idx, end_idx
		),
		num_iterations,
	)
	parity = verify_find_path(mol, rx_graph, v_to_i)
	results.append({
		"algorithm": "find_path",
		"oasa_us": oasa_us, "rx_us": rx_us,
		"speedup": oasa_us / rx_us if rx_us > 0 else float("inf"),
		"parity": parity,
	})

	# --- rustworkx-only algorithms ---
	rx_bridges_us = time_function(
		lambda: rustworkx.bridges(rx_graph),
		num_iterations,
	)
	results.append({
		"algorithm": "bridges (rx only)",
		"oasa_us": None, "rx_us": rx_bridges_us,
		"speedup": None, "parity": "N/A",
	})

	rx_artic_us = time_function(
		lambda: rustworkx.articulation_points(rx_graph),
		num_iterations,
	)
	results.append({
		"algorithm": "articulation_pts (rx only)",
		"oasa_us": None, "rx_us": rx_artic_us,
		"speedup": None, "parity": "N/A",
	})

	rx_match_us = time_function(
		lambda: rustworkx.max_weight_matching(rx_graph),
		num_iterations,
	)
	results.append({
		"algorithm": "max_weight_match (rx only)",
		"oasa_us": None, "rx_us": rx_match_us,
		"speedup": None, "parity": "N/A",
	})

	# print table for this molecule
	print_molecule_table(results, verbose)
	return results


#============================================
def print_molecule_table(results: list, verbose: bool) -> None:
	"""Print a formatted comparison table for one molecule.

	Args:
		results: List of result dicts from benchmark_molecule.
		verbose: Whether to print extra detail.
	"""
	# header
	header = (
		f"{'Algorithm':<28s} "
		f"{'OASA (us)':>10s} "
		f"{'RX (us)':>10s} "
		f"{'Speedup':>10s} "
		f"{'Parity':>8s}"
	)
	print(f"\n{header}")
	print("-" * len(header))

	for row in results:
		alg = row["algorithm"]
		oasa_str = f"{row['oasa_us']:.1f}" if row["oasa_us"] is not None else "--"
		rx_str = f"{row['rx_us']:.1f}"
		if row["speedup"] is not None:
			spd_str = f"{row['speedup']:.1f}x"
		else:
			spd_str = "--"
		parity = row["parity"]
		line = (
			f"{alg:<28s} "
			f"{oasa_str:>10s} "
			f"{rx_str:>10s} "
			f"{spd_str:>10s} "
			f"{parity:>8s}"
		)
		print(line)


#============================================
def print_summary(all_results: dict) -> None:
	"""Print a final summary table across all molecules.

	Args:
		all_results: Dict mapping molecule name to list of result dicts.
	"""
	print(f"\n{'='*65}")
	print("SUMMARY: Speedup ratios (OASA time / rustworkx time)")
	print(f"{'='*65}")

	# collect algorithm names from first molecule
	first_key = list(all_results.keys())[0]
	algorithms = [r["algorithm"] for r in all_results[first_key]]
	mol_names = list(all_results.keys())

	# header
	header = f"{'Algorithm':<28s}"
	for mol_name in mol_names:
		header += f" {mol_name:>14s}"
	print(f"\n{header}")
	print("-" * len(header))

	for alg in algorithms:
		line = f"{alg:<28s}"
		for mol_name in mol_names:
			# find matching result
			row = None
			for r in all_results[mol_name]:
				if r["algorithm"] == alg:
					row = r
					break
			if row and row["speedup"] is not None:
				line += f" {row['speedup']:>13.1f}x"
			elif row:
				line += f" {row['rx_us']:>10.1f}us*"
			else:
				line += f" {'--':>14s}"
		print(line)

	# footnote for rx-only
	print("\n* = rustworkx-only algorithm (time in microseconds)")

	# parity summary
	print("\nParity check results:")
	all_match = True
	for mol_name, results in all_results.items():
		for row in results:
			if row["parity"] == "MISMATCH":
				print(f"  MISMATCH: {mol_name} / {row['algorithm']}")
				all_match = False
	if all_match:
		print("  All parity checks passed.")


#============================================
def main() -> None:
	"""Run graph algorithm benchmarks on test molecules."""
	args = parse_args()

	print("OASA vs rustworkx graph algorithm benchmark")
	print(f"rustworkx version: {rustworkx.__version__}")

	all_results = {}
	for mol_name, smiles in MOLECULES.items():
		results = benchmark_molecule(
			mol_name, smiles,
			args.num_iterations, args.verbose,
		)
		all_results[mol_name] = results

	# final summary
	print_summary(all_results)


#============================================
if __name__ == '__main__':
	main()
