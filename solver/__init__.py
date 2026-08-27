"""
solver/__init__.py — public surface of the solver package.

Exposes: solve, grid, validate
Nothing outside the package calls Lambert directly or touches raw frames
(CONVENTIONS.md: Public surface).

Imports are deferred so the package can be partially used during construction
(e.g. fetch.py and constants.py work before solve/grid/validate are written).
"""

def solve(*args, **kwargs):
    from solver.solve import solve as _solve
    return _solve(*args, **kwargs)


def grid(*args, **kwargs):
    from solver.grid import grid as _grid
    return _grid(*args, **kwargs)


def validate(*args, **kwargs):
    from solver.validate import validate as _validate
    return _validate(*args, **kwargs)


__all__ = ["solve", "grid", "validate"]
