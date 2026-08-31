"""
app/ — the HTTP surface.

The topmost layer of docs/ARCHITECTURE.md's map, and the thinnest. It loads
committed manifests, calls the interpretation layer, and serializes what comes
back. It computes nothing: there is no arithmetic anywhere in this package,
because a number a surface calculated is a number that never passed the gate.
"""
