"""Local MaxCut experiment; no accounts, hardware access, or quantum-advantage claim.

Run with the restored openqaoa-core installed: python examples/core_maxcut.py
"""
import itertools
import json
from importlib.metadata import version

import networkx as nx
import numpy as np

from openqaoa import QAOA, create_device
from openqaoa.problems import MaximumCut, QUBO
from openqaoa.utilities import bitstring_energy


def cut_value(graph, bits):
    return sum(1 for u, v in graph.edges if int(bits[u]) != int(bits[v]))


def run():
    graph = nx.Graph()
    graph.add_nodes_from(range(6))
    graph.add_edges_from([(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3),
                          (0, 3), (1, 4), (2, 5)])
    qubo = QUBO.from_dict(json.loads(json.dumps(MaximumCut(graph).qubo.asdict())))
    exact = max(cut_value(graph, bits) for bits in itertools.product((0, 1), repeat=6))
    rng = np.random.default_rng(11)
    random_best = max(cut_value(graph, bits) for bits in rng.integers(0, 2, (64, 6)))
    greedy = [0] * 6
    while True:
        candidates = [greedy[:i] + [1 - greedy[i]] + greedy[i + 1:] for i in range(6)]
        best = max(candidates, key=lambda bits: cut_value(graph, bits))
        if cut_value(graph, best) <= cut_value(graph, greedy):
            break
        greedy = best

    trials = []
    for depth, seed in itertools.product((1, 2), (11, 22, 33)):
        qaoa = QAOA()
        qaoa.set_device(create_device(location="local", name="vectorized"))
        qaoa.set_circuit_properties(p=depth, init_type="rand", seed=seed)
        qaoa.set_classical_optimizer(method="cobyla", maxiter=60)
        qaoa.compile(qubo)
        qaoa.optimize()
        qaoa.variate_params.update_from_raw(qaoa.result.optimized["angles"])
        probabilities = qaoa.backend.probability_dict(qaoa.variate_params)
        expected_cut = sum(prob * cut_value(graph, bits) for bits, prob in probabilities.items())
        expected_energy = sum(prob * bitstring_energy(qubo.hamiltonian, bits)
                              for bits, prob in probabilities.items())
        np.testing.assert_allclose(sum(probabilities.values()), 1, atol=1e-10)
        np.testing.assert_allclose(expected_energy, qaoa.result.optimized["cost"], atol=1e-9)
        np.testing.assert_allclose(expected_energy, graph.number_of_edges() - 2 * expected_cut,
                                   atol=1e-9)
        assert 0 <= expected_cut <= exact + 1e-9
        trials.append({"depth": depth, "seed": seed, "expected_cut": expected_cut,
                       "probability_of_optimum": sum(prob for bits, prob in probabilities.items()
                                                     if cut_value(graph, bits) == exact)})
    return {"openqaoa_core": version("openqaoa-core"), "graph": "triangular prism",
            "vertices": 6, "edges": 9, "exact_optimum": exact,
            "random_best_of_64": random_best, "greedy_cut": cut_value(graph, greedy),
            "optimizer_evaluation_cap_per_trial": 60,
            "validation_statevectors_per_trial": 1, "trials": trials,
            "interpretation": "Statevector simulation, not evidence of quantum advantage. "
                              "Expected QAOA cut and best classical cuts are different statistics; "
                              "their compute budgets are not matched."}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
