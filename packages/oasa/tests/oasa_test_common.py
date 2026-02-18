#!/usr/bin/env python3

import oasa.common as common


#============================================
def main():
	print("Running test_common checks...")
	result = common.is_uniquely_sorted([1, 2, 3])
	assert result is True

	result = common.is_uniquely_sorted([1, 2, 2, 3])
	assert result is False
	print("test_common passed.")


if __name__ == '__main__':
	main()
