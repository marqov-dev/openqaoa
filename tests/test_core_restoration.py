"""Provider-free regression coverage for the Marqov core restoration."""
import itertools
import json
import os
import subprocess
import sys

import networkx as nx
import numpy as np
import pytest

from openqaoa import QAOA, create_device
from openqaoa.algorithms.qaoa.qaoa_benchmark import QAOABenchmark
from openqaoa.backends.wrapper import ZNEWrapper
from openqaoa.problems import MaximumCut, QUBO
from openqaoa.utilities import bitstring_energy


def test_core_import_never_attempts_optional_provider_or_mitigation_imports():
    code = '''
import importlib.abc
import sys
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'mitiq', 'qiskit', 'openqaoa_qiskit'}:
            raise AssertionError('Unexpected optional import: ' + fullname)
sys.meta_path.insert(0, BlockOptional())
from openqaoa import QAOA, RQAOA, create_device
assert create_device(location='local', name='vectorized').check_connection()
assert create_device(location='local', name='analytical_simulator').check_connection()
'''
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ, timeout=60)


def test_optional_zne_dependency_error_is_actionable(monkeypatch):
    monkeypatch.setitem(sys.modules, "mitiq", None)
    with pytest.raises(ImportError, match="Zero-noise extrapolation requires compatible Mitiq"):
        ZNEWrapper(object(), "Richardson", "fold_gates_at_random", [1, 2], 1, 3)


def test_weighted_maxcut_preserves_zero_and_negative_weights_and_serialization():
    graph = nx.Graph()
    graph.add_edge(0, 1, weight=0.0)
    graph.add_edge(1, 2, weight=2.5)
    graph.add_edge(0, 2, weight=-1.0)
    graph.add_edge(2, 3)  # Unspecified weight means one; zero does not.
    problem = MaximumCut(graph)
    qubo = QUBO.from_dict(json.loads(json.dumps(problem.qubo.asdict())))
    for bits in itertools.product((0, 1), repeat=4):
        cut = sum(data.get("weight", 1.0) for u, v, data in graph.edges(data=True)
                  if bits[u] != bits[v])
        total_weight = sum(data.get("weight", 1.0) for _, _, data in graph.edges(data=True))
        assert bitstring_energy(qubo.hamiltonian, bits) == pytest.approx(total_weight - 2 * cut)


@pytest.mark.parametrize("seed", [0, 11, 33])
def test_builtin_simulators_agree_for_weighted_maxcut(seed):
    graph = nx.cycle_graph(5)
    nx.set_edge_attributes(graph, {edge: i / 2 for i, edge in enumerate(graph.edges())}, "weight")
    energies = []
    for backend in ("vectorized", "analytical_simulator"):
        qaoa = QAOA()
        qaoa.set_device(create_device(location="local", name=backend))
        qaoa.set_circuit_properties(p=1, param_type="standard", init_type="rand", seed=seed)
        qaoa.compile(MaximumCut(graph).qubo)
        energies.append(qaoa.backend.expectation(qaoa.variate_params))
    np.testing.assert_allclose(energies[0], energies[1], atol=1e-10)


def test_benchmark_plot_keeps_sample_centers_and_all_values():
    import matplotlib.pyplot as plt

    qaoa = QAOA()
    qaoa.compile(MaximumCut(nx.cycle_graph(4)).qubo)
    benchmark = QAOABenchmark(qaoa)
    benchmark.run(n_points_axis=4, ranges=[(0, 1), (-1, 1)],
                  run_reference=False, verbose=False)
    figure, axis = benchmark.plot()
    try:
        figure.canvas.draw()
        mesh = axis.collections[0]
        np.testing.assert_allclose(np.asarray(mesh.get_array()).reshape(4, 4), benchmark.values)
        coordinates = mesh.get_coordinates()
        np.testing.assert_allclose((coordinates[0, :-1, 0] + coordinates[0, 1:, 0]) / 2,
                                   np.linspace(0, 1, 4))
        np.testing.assert_allclose((coordinates[:-1, 0, 1] + coordinates[1:, 0, 1]) / 2,
                                   np.linspace(-1, 1, 4))
    finally:
        plt.close(figure)
