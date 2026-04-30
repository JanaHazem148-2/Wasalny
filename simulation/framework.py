"""
Cairo Transportation Network — Simulation Framework
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing      import Callable, Dict, List, Optional, Any

from models.graph            import Graph
from models.edge             import TimePeriod
from simulation.traffic_data import TrafficDataStore


@dataclass
class Scenario:
    scenario_id:   str
    name:          str
    description:   str
    algorithm_key: str
    params:        Dict[str, Any] = field(default_factory=dict)
    result:        Any             = None


class SimulationFramework:
    def __init__(self, graph: Graph, store: TrafficDataStore):
        self.graph  = graph
        self.store  = store
        self._algorithms: Dict[str, Callable] = {}
        self._scenarios: List[Scenario] = self._build_scenarios()

    def register_algorithm(self, key: str, func: Callable) -> None:
        """Register an algorithm implementation."""
        self._algorithms[key] = func

    def run_all(self) -> List[Scenario]:
        """Run all registered scenarios using the registered algorithms."""
        for scenario in self._scenarios:
            algo = self._algorithms.get(scenario.algorithm_key)
            if algo is None:
                scenario.result = f"No algorithm registered for '{scenario.algorithm_key}'"
                continue
            try:
                # Each algorithm function receives (graph, store, **params)
                scenario.result = algo(self.graph, self.store, **scenario.params)
            except Exception as e:
                scenario.result = f"ERROR: {e}"
        return self._scenarios

    def print_report(self, results: List[Scenario]) -> None:
        """Print a formatted report of all scenario results."""
        print("\n" + "=" * 70)
        print("  SIMULATION FRAMEWORK — SCENARIO REPORT")
        print("=" * 70)
        for s in results:
            print(f"\n[{s.scenario_id}] {s.name}")
            print(f"    {s.description}")
            if isinstance(s.result, str):
                print(f"    → {s.result}")
            elif hasattr(s.result, 'summary'):
                # For MST results, use the built-in summary
                print(s.result.summary())
            else:
                print(f"    → {s.result}")

    def _build_scenarios(self) -> List[Scenario]:
        """
        Define all simulation scenarios (only Kruskal's MST).
        """
        scenarios = [
            # ── Task 2: MST (Kruskal only) ───────────────────────────
            Scenario(
                scenario_id   = "MST-1",
                name          = "Min-cost network (existing roads)",
                description   = "Kruskal on existing 33 edges, weight=distance",
                algorithm_key = "mst",
                params        = {"use_cost": False, "include_potential": False},
            ),
            Scenario(
                scenario_id   = "MST-2",
                name          = "Expansion plan (+ proposed roads)",
                description   = "Kruskal including 15 potential roads, weight=cost",
                algorithm_key = "mst",
                params        = {"use_cost": True, "include_potential": True},
            ),
        ]
        return scenarios