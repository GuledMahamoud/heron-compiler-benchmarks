"""Stand-in for qiskit.synthesis.linear.linear_matrix_utils, which Qiskit 2.x no longer ships.

qiskit-ibm-transpiler 0.18 (the newest that installs next to torch 2.2.2 on Intel macOS) imports
random_invertible_binary_matrix from here.  It is only used to make random test matrices, not to compile.
"""
try:  # still exported by the package on some Qiskit versions
    from qiskit.synthesis.linear import random_invertible_binary_matrix  # noqa: F401
except ImportError:
    import numpy as np

    def _rank_gf2(m) -> int:
        m = m.copy().astype(np.uint8)
        rows, cols = m.shape
        r = 0
        for c in range(cols):
            piv = next((i for i in range(r, rows) if m[i, c]), None)
            if piv is None:
                continue
            m[[r, piv]] = m[[piv, r]]
            for i in range(rows):
                if i != r and m[i, c]:
                    m[i] ^= m[r]
            r += 1
        return r

    def random_invertible_binary_matrix(num_qubits: int, seed=None):
        rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
        while True:
            m = rng.integers(0, 2, size=(num_qubits, num_qubits), dtype=np.uint8).astype(bool)
            if _rank_gf2(m) == num_qubits:
                return m
