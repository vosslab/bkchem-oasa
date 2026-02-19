"""Backward-compat shim -- real code lives in oasa.haworth.spec."""

from oasa.haworth import spec as _spec

HaworthSpec = _spec.HaworthSpec
generate = _spec.generate
