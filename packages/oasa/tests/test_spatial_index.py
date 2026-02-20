"""Tests for the 2D spatial index (KD-tree radius queries).

Validates query_radius and query_pairs against brute-force oracles.
Uses scipy.spatial.cKDTree as a cross-check when available.
"""

import random

import pytest

import oasa.graph.spatial_index as spatial_index
from oasa.graph.spatial_index import SpatialIndex


#============================================
# helper: brute-force oracle for pairs
#============================================
def _brute_force_pairs(points: list, r: float) -> set:
	"""Brute-force all-pairs within radius, returns set of (i,j) with i<j."""
	pairs = set()
	r2 = r * r
	n = len(points)
	for i in range(n):
		xi, yi = points[i]
		for j in range(i + 1, n):
			xj, yj = points[j]
			dx = xi - xj
			dy = yi - yj
			if dx * dx + dy * dy <= r2:
				pairs.add((i, j))
	return pairs


#============================================
# helper: brute-force oracle for radius query
#============================================
def _brute_force_radius(points: list, x: float, y: float, r: float) -> set:
	"""Brute-force radius query, returns set of indices."""
	result = set()
	r2 = r * r
	for i in range(len(points)):
		px, py = points[i]
		dx = px - x
		dy = py - y
		if dx * dx + dy * dy <= r2:
			result.add(i)
	return result


#============================================
# basic tests
#============================================
class TestSpatialIndexBasic:
	"""Basic functionality tests."""

	def test_empty_points(self):
		"""Empty point list returns no pairs."""
		idx = SpatialIndex.build([])
		assert idx.query_pairs(1.0) == []
		assert idx.query_radius(0.0, 0.0, 1.0) == []

	def test_single_point(self):
		"""Single point: no pairs, radius finds itself."""
		idx = SpatialIndex.build([(0.0, 0.0)])
		assert idx.query_pairs(1.0) == []
		result = idx.query_radius(0.0, 0.0, 1.0)
		assert result == [0]

	def test_two_points_within_radius(self):
		"""Two points within radius form a pair."""
		points = [(0.0, 0.0), (0.5, 0.0)]
		idx = SpatialIndex.build(points)
		pairs = idx.query_pairs(1.0)
		assert set(pairs) == {(0, 1)}

	def test_two_points_outside_radius(self):
		"""Two points outside radius form no pair."""
		points = [(0.0, 0.0), (2.0, 0.0)]
		idx = SpatialIndex.build(points)
		pairs = idx.query_pairs(1.0)
		assert pairs == []

	def test_two_identical_points(self):
		"""Two identical points: distance is 0, always within any positive radius."""
		points = [(1.0, 1.0), (1.0, 1.0)]
		idx = SpatialIndex.build(points)
		pairs = idx.query_pairs(0.001)
		assert set(pairs) == {(0, 1)}

	def test_radius_zero(self):
		"""r=0 only finds exact overlapping points."""
		points = [(0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
		idx = SpatialIndex.build(points)
		pairs = idx.query_pairs(0.0)
		# only the overlapping pair
		assert set(pairs) == {(0, 1)}


#============================================
# boundary tests
#============================================
class TestSpatialIndexBoundary:
	"""Boundary condition tests for exact-distance pairs."""

	def test_exact_distance_included(self):
		"""Points at exactly radius distance are included (<= comparison)."""
		r = 1.0
		points = [(0.0, 0.0), (1.0, 0.0)]
		idx = SpatialIndex.build(points)
		pairs = idx.query_pairs(r)
		assert set(pairs) == {(0, 1)}

	def test_exact_distance_radius_query(self):
		"""query_radius includes points at exactly the radius distance."""
		r = 1.0
		points = [(0.0, 0.0), (1.0, 0.0), (1.5, 0.0)]
		idx = SpatialIndex.build(points)
		result = set(idx.query_radius(0.0, 0.0, r))
		assert 0 in result
		assert 1 in result
		assert 2 not in result

	def test_huge_radius_returns_all_pairs(self):
		"""Very large radius returns all possible pairs."""
		points = [(float(i), float(j)) for i in range(5) for j in range(5)]
		n = len(points)
		idx = SpatialIndex.build(points)
		pairs = idx.query_pairs(1e6)
		expected_count = n * (n - 1) // 2
		assert len(pairs) == expected_count


#============================================
# degenerate geometry tests
#============================================
class TestSpatialIndexDegenerate:
	"""Degenerate point distribution tests."""

	def test_all_same_location(self):
		"""All points at the same location."""
		points = [(5.0, 5.0)] * 10
		idx = SpatialIndex.build(points)
		pairs = set(idx.query_pairs(0.001))
		expected = _brute_force_pairs(points, 0.001)
		assert pairs == expected

	def test_points_on_line_x(self):
		"""All points on a horizontal line (degenerate y-axis split)."""
		points = [(float(i), 0.0) for i in range(30)]
		idx = SpatialIndex.build(points)
		pairs = set(idx.query_pairs(1.5))
		expected = _brute_force_pairs(points, 1.5)
		assert pairs == expected

	def test_points_on_line_y(self):
		"""All points on a vertical line (degenerate x-axis split)."""
		points = [(0.0, float(i)) for i in range(30)]
		idx = SpatialIndex.build(points)
		pairs = set(idx.query_pairs(1.5))
		expected = _brute_force_pairs(points, 1.5)
		assert pairs == expected

	def test_points_on_diagonal(self):
		"""All points on a diagonal line."""
		points = [(float(i), float(i)) for i in range(30)]
		idx = SpatialIndex.build(points)
		r = 1.5
		pairs = set(idx.query_pairs(r))
		expected = _brute_force_pairs(points, r)
		assert pairs == expected


#============================================
# property tests with random point clouds
#============================================
class TestSpatialIndexRandom:
	"""Random point cloud property tests against brute-force oracle."""

	@pytest.mark.parametrize("n_points", [10, 50, 100, 200, 500])
	def test_query_pairs_matches_brute_force(self, n_points: int):
		"""query_pairs matches brute-force for random point clouds."""
		rng = random.Random(42 + n_points)
		points = [(rng.uniform(-10, 10), rng.uniform(-10, 10))
			for _ in range(n_points)]
		r = 2.0
		idx = SpatialIndex.build(points)
		kd_pairs = set(idx.query_pairs(r))
		bf_pairs = _brute_force_pairs(points, r)
		assert kd_pairs == bf_pairs

	@pytest.mark.parametrize("n_points", [10, 50, 100, 200, 500])
	def test_query_radius_matches_brute_force(self, n_points: int):
		"""query_radius matches brute-force for random query points."""
		rng = random.Random(123 + n_points)
		points = [(rng.uniform(-10, 10), rng.uniform(-10, 10))
			for _ in range(n_points)]
		idx = SpatialIndex.build(points)
		# test several query points
		for _ in range(10):
			qx = rng.uniform(-12, 12)
			qy = rng.uniform(-12, 12)
			r = rng.uniform(0.5, 5.0)
			kd_result = set(idx.query_radius(qx, qy, r))
			bf_result = _brute_force_radius(points, qx, qy, r)
			assert kd_result == bf_result

	def test_large_cloud_pairs(self):
		"""1000-point cloud: pairs match brute force."""
		rng = random.Random(999)
		points = [(rng.uniform(-50, 50), rng.uniform(-50, 50))
			for _ in range(1000)]
		r = 3.0
		idx = SpatialIndex.build(points)
		kd_pairs = set(idx.query_pairs(r))
		bf_pairs = _brute_force_pairs(points, r)
		assert kd_pairs == bf_pairs


#============================================
# determinism test
#============================================
class TestSpatialIndexDeterminism:
	"""Same input produces same output."""

	def test_deterministic_pairs(self):
		"""Building and querying twice gives identical results."""
		rng = random.Random(777)
		points = [(rng.uniform(-5, 5), rng.uniform(-5, 5))
			for _ in range(100)]
		r = 2.0
		pairs1 = set(SpatialIndex.build(points).query_pairs(r))
		pairs2 = set(SpatialIndex.build(points).query_pairs(r))
		assert pairs1 == pairs2


#============================================
# brute_force_pairs / brute_force_radius module functions
#============================================
class TestBruteForceHelpers:
	"""Test the exported brute-force helper functions."""

	def test_brute_force_pairs_function(self):
		"""spatial_index.brute_force_pairs matches local oracle."""
		rng = random.Random(55)
		points = [(rng.uniform(-5, 5), rng.uniform(-5, 5))
			for _ in range(50)]
		r = 2.0
		result = set(spatial_index.brute_force_pairs(points, r))
		expected = _brute_force_pairs(points, r)
		assert result == expected

	def test_brute_force_radius_function(self):
		"""spatial_index.brute_force_radius matches local oracle."""
		rng = random.Random(66)
		points = [(rng.uniform(-5, 5), rng.uniform(-5, 5))
			for _ in range(50)]
		result = set(spatial_index.brute_force_radius(points, 0.0, 0.0, 3.0))
		expected = _brute_force_radius(points, 0.0, 0.0, 3.0)
		assert result == expected


#============================================
# scipy cross-check (optional)
#============================================
class TestSpatialIndexScipy:
	"""Cross-check against scipy.spatial.cKDTree when available."""

	@pytest.fixture(autouse=True)
	def _skip_without_scipy(self):
		"""Skip tests if scipy is not installed."""
		pytest.importorskip("scipy")

	def test_query_pairs_matches_scipy(self):
		"""query_pairs matches scipy cKDTree.query_pairs."""
		import scipy.spatial
		rng = random.Random(314)
		points = [(rng.uniform(-10, 10), rng.uniform(-10, 10))
			for _ in range(200)]
		r = 2.5
		# our index
		idx = SpatialIndex.build(points)
		our_pairs = set(idx.query_pairs(r))
		# scipy
		tree = scipy.spatial.cKDTree(points)
		scipy_pairs = tree.query_pairs(r)
		# scipy returns set of (i,j) with i<j
		assert our_pairs == scipy_pairs

	def test_query_pairs_matches_scipy_large(self):
		"""query_pairs matches scipy on a larger cloud."""
		import scipy.spatial
		rng = random.Random(271)
		points = [(rng.uniform(-50, 50), rng.uniform(-50, 50))
			for _ in range(500)]
		r = 4.0
		idx = SpatialIndex.build(points)
		our_pairs = set(idx.query_pairs(r))
		tree = scipy.spatial.cKDTree(points)
		scipy_pairs = tree.query_pairs(r)
		assert our_pairs == scipy_pairs
