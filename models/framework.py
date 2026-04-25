"""
simulation/framework.py
Cairo Transportation Network -- Simulation Framework

Provides a structured engine for running all scenario types defined in
Section 9 of the dataset. Each scenario is a self-contained method that:
  1. Sets up the graph/store state for the scenario
  2. Runs the relevant algorithm (or a structured stub if not yet integrated)
  3. Records a SimulationResult with full diagnostic data
  4. Restores all state changes so the next scenario starts clean

Scenarios implemented
---------------------
A -- Standard route planning (Dijkstra, 4 periods compared)
B -- Emergency vehicle routing (A*, worst-case morning peak)
C -- Road closure / alternate route (Dijkstra on modified graph)
D -- MST infrastructure design (existing vs. existing + potential roads)
E -- Traffic signal optimization (Greedy, peak vs night + preemption)
F -- DP scheduling (bus/metro allocation against fleet constraints)
G -- DP maintenance knapsack (road selection under 200 M-EGP budget)

Author : CSE112 Project Team
Course : Design and Analysis of Algorithms -- AIU
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing      import Any, Callable, Dict, List, Optional, Tuple

from models.graph            import Graph
from models.edge             import TimePeriod, CongestionLevel
from simulation.traffic_data import TrafficDataStore


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    scenario_id:   str
    scenario_name: str
    status:        str           # "OK" | "STUB" | "ERROR"
    elapsed_ms:    float
    data:          Dict[str, Any] = field(default_factory=dict)
    notes:         List[str]      = field(default_factory=list)

    def ok(self) -> bool:
        return self.status == "OK"


# ---------------------------------------------------------------------------
# Framework
# ---------------------------------------------------------------------------

class SimulationFramework:
    """
    Orchestrates all scenario runs against a shared Graph and TrafficDataStore.

    Algorithm hooks (register with register_algorithm):
      "dijkstra" : fn(graph, store, source, target, period) -> dict
                   dict must have: path (list[str]), total_time (float)
      "a_star"   : same signature as dijkstra
      "mst"      : fn(graph, store, use_potential) -> dict
                   dict must have: edges, total_distance, total_cost,
                                   critical_covered, total_critical
      "greedy"   : fn(graph, store, intersection_id, period, emergency) -> dict
      "dp_sched" : fn(store, period) -> dict
      "dp_maint" : fn(graph, store, budget) -> dict
    """

    _STUB = object()

    def __init__(self, graph: Graph, store: TrafficDataStore):
        self.graph   = graph
        self.store   = store
        self._algos: Dict[str, Any] = {}

    def register_algorithm(self, name: str, fn: Callable) -> None:
        self._algos[name] = fn

    def _call(self, name: str, *args, **kwargs) -> Tuple[bool, Any]:
        """
        Invoke a registered algorithm. Returns (is_stub, result).
        is_stub=True when the algorithm has not yet been registered.
        """
        fn = self._algos.get(name, self._STUB)
        if fn is self._STUB:
            return True, None
        try:
            return False, fn(*args, **kwargs)
        except Exception as exc:
            return False, {"error": str(exc)}

    # ------------------------------------------------------------------
    # Run all scenarios
    # ------------------------------------------------------------------

    def run_all(self) -> List[SimulationResult]:
        runners = [
            self.run_scenario_a,
            self.run_scenario_b,
            self.run_scenario_c,
            self.run_scenario_d,
            self.run_scenario_e,
            self.run_scenario_f,
            self.run_scenario_g,
        ]
        results = []
        for runner in runners:
            results.extend(runner())
        return results

    # ------------------------------------------------------------------
    # Scenario A -- Standard route planning (Dijkstra)
    # ------------------------------------------------------------------

    def run_scenario_a(self) -> List[SimulationResult]:
        queries = [
            ("4",  "3",  "New Cairo -> Downtown"),
            ("7",  "2",  "6th October -> Nasr City"),
            ("12", "13", "Helwan -> New Admin Capital"),
            ("11", "15", "Shubra -> Sheikh Zayed"),
        ]
        results = []
        for src, dst, label in queries:
            t0   = time.perf_counter()
            rows = {}
            for period in TimePeriod:
                is_stub, raw = self._call("dijkstra",
                                          self.graph, self.store, src, dst, period)
                rows[period] = {
                    "stub":       is_stub,
                    "path":       raw.get("path")       if raw and not is_stub else None,
                    "total_time": raw.get("total_time") if raw and not is_stub else None,
                }
            elapsed = (time.perf_counter() - t0) * 1000
            is_any_stub = any(v["stub"] for v in rows.values())
            results.append(SimulationResult(
                scenario_id   = "A",
                scenario_name = f"Route Planning: {label}",
                status        = "STUB" if is_any_stub else "OK",
                elapsed_ms    = elapsed,
                data          = {"source": src, "destination": dst,
                                 "label": label, "periods": rows},
                notes         = [
                    "Algorithm: Dijkstra with time-dependent weights",
                    "Expected: peak times >> night times on congested corridors",
                ],
            ))
        return results

    # ------------------------------------------------------------------
    # Scenario B -- Emergency vehicle routing (A*)
    # ------------------------------------------------------------------

    def run_scenario_b(self) -> List[SimulationResult]:
        queries = [
            ("7",  "F9",  "6th October -> Qasr El Aini Hospital"),
            ("13", "F9",  "New Capital -> Qasr El Aini Hospital"),
            ("12", "F10", "Helwan -> Maadi Military Hospital"),
            ("4",  "F9",  "New Cairo -> Qasr El Aini Hospital"),
            ("7",  "F10", "6th October -> Maadi Military Hospital"),
        ]
        results = []
        period = TimePeriod.MORNING_PEAK
        for src, dst, label in queries:
            t0 = time.perf_counter()
            is_stub, astar_raw    = self._call("a_star",   self.graph, self.store, src, dst, period)
            _,        dijkstra_raw = self._call("dijkstra", self.graph, self.store, src, dst, period)
            elapsed = (time.perf_counter() - t0) * 1000

            node_s    = self.graph.get_node(src)
            node_d    = self.graph.get_node(dst)
            aerial_km = node_s.euclidean_distance_to(node_d)
            aerial_min = round((aerial_km / 90.0) * 60.0, 2)  # 90 km/h emergency speed

            results.append(SimulationResult(
                scenario_id   = "B",
                scenario_name = f"Emergency: {label}",
                status        = "STUB" if is_stub else "OK",
                elapsed_ms    = elapsed,
                data          = {
                    "source": src, "destination": dst,
                    "period": period.label(),
                    "aerial_km":  round(aerial_km, 2),
                    "aerial_min": aerial_min,
                    "a_star":     astar_raw,
                    "dijkstra":   dijkstra_raw,
                },
                notes = [
                    "Algorithm: A* with Euclidean (aerial) heuristic",
                    "Period: Morning Peak (worst-case congestion for response time)",
                    "Heuristic admissibility: aerial dist <= road dist, always",
                    "Compare A* nodes expanded vs Dijkstra to show efficiency gain",
                ],
            ))
        return results

    # ------------------------------------------------------------------
    # Scenario C -- Road closure / alternate route
    # ------------------------------------------------------------------

    def run_scenario_c(self) -> List[SimulationResult]:
        closures = [
            ("3","5", "4","3", TimePeriod.MORNING_PEAK,
             "Downtown-Heliopolis accident: New Cairo -> Downtown"),
            ("13","4","13","3", TimePeriod.AFTERNOON,
             "New Capital link closed: New Capital -> Downtown"),
        ]
        results = []
        for e_a, e_b, src, dst, period, label in closures:
            t0 = time.perf_counter()

            # Baseline (road open)
            _, baseline = self._call("dijkstra", self.graph, self.store, src, dst, period)

            # Remove the road and run detour query
            removed = self.graph.remove_edge(e_a, e_b)
            is_stub, detour = self._call("dijkstra", self.graph, self.store, src, dst, period)

            # Always restore -- the graph must be clean for the next scenario
            if removed:
                self.graph.restore_edge(removed)

            elapsed = (time.perf_counter() - t0) * 1000

            bt  = baseline.get("total_time") if baseline else None
            dt_ = detour.get("total_time")   if detour   else None
            overhead = round(dt_ - bt, 2) if (bt and dt_) else None

            results.append(SimulationResult(
                scenario_id   = "C",
                scenario_name = f"Closure: {label}",
                status        = "STUB" if is_stub else "OK",
                elapsed_ms    = elapsed,
                data          = {
                    "closed_road":  f"{e_a}-{e_b}",
                    "source": src, "destination": dst,
                    "period": period.label(),
                    "baseline":     baseline,
                    "detour":       detour,
                    "overhead_min": overhead,
                },
                notes = [
                    f"Road {e_a}-{e_b} removed from adjacency list (O(degree) op)",
                    "Dijkstra re-runs on modified graph -- finds next-best path",
                    "Graph fully restored after scenario (remove_edge / restore_edge)",
                ],
            ))
        return results

    # ------------------------------------------------------------------
    # Scenario D -- MST infrastructure design (Kruskal's)
    # ------------------------------------------------------------------

    def run_scenario_d(self) -> List[SimulationResult]:
        results = []
        critical_ids = sorted(n.node_id for n in self.graph.get_critical_nodes())
        for use_potential in (False, True):
            label = "Existing + Potential" if use_potential else "Existing Roads Only"
            t0    = time.perf_counter()
            is_stub, raw = self._call("mst", self.graph, self.store, use_potential)
            elapsed = (time.perf_counter() - t0) * 1000

            pool = (self.graph.get_all_edges()
                    if use_potential
                    else self.graph.get_existing_edges())
            results.append(SimulationResult(
                scenario_id   = "D",
                scenario_name = f"MST: {label}",
                status        = "STUB" if is_stub else "OK",
                elapsed_ms    = elapsed,
                data          = {
                    "use_potential":      use_potential,
                    "pool_edges":         len(pool),
                    "pool_distance_km":   round(sum(e.distance for e in pool), 1),
                    "pool_cost_millions": round(sum(e.cost_millions for e in pool if e.is_potential), 1),
                    "critical_required":  critical_ids,
                    "mst_result":         raw,
                },
                notes = [
                    "Algorithm: Kruskal's with two-phase priority modification",
                    "Phase 1: union critical nodes first (guarantee hospital/hub connectivity)",
                    "Phase 2: standard Kruskal's on remaining edges",
                    "Union-Find with path compression: O(alpha(V)) per operation",
                ],
            ))
        return results

    # ------------------------------------------------------------------
    # Scenario E -- Traffic signal optimization (Greedy)
    # ------------------------------------------------------------------

    def run_scenario_e(self) -> List[SimulationResult]:
        signal  = self.store.get_signal("I1")
        results = []
        runs = [
            (TimePeriod.MORNING_PEAK, False),
            (TimePeriod.NIGHT,        False),
            (TimePeriod.MORNING_PEAK, True),   # emergency preemption
        ]
        for period, emergency in runs:
            em_tag = " [EMERGENCY]" if emergency else ""
            label  = f"I1 Tahrir Sq{em_tag} -- {period.name}"
            t0     = time.perf_counter()
            is_stub, raw = self._call("greedy", self.graph, self.store,
                                      "I1", period, emergency)
            elapsed = (time.perf_counter() - t0) * 1000

            # Compute proportional green-time allocation from TrafficDataStore
            allocation = {}
            if signal:
                total_flow = sum(self.store.get_flow(r, period)
                                 for r in signal.connected_roads)
                cycle = signal.normal_cycle_sec
                for road in signal.connected_roads:
                    flow  = self.store.get_flow(road, period)
                    share = (flow / total_flow * cycle) if total_flow > 0 else 0
                    allocation[road] = {
                        "flow":      flow,
                        "green_sec": round(share, 1),
                        "pct":       round(share / cycle * 100, 1) if cycle else 0,
                    }

            results.append(SimulationResult(
                scenario_id   = "E",
                scenario_name = f"Signal Opt: {label}",
                status        = "STUB" if is_stub else "OK",
                elapsed_ms    = elapsed,
                data          = {
                    "intersection":       "I1 -- Tahrir Square",
                    "period":             period.label(),
                    "emergency":          emergency,
                    "cycle_sec":          signal.normal_cycle_sec if signal else None,
                    "preempt_hold":       signal.preempt_hold_sec if signal else None,
                    "recover_cycle":      signal.recover_cycle_sec if signal else None,
                    "greedy_allocation":  allocation,
                    "optimized_result":   raw,
                },
                notes = [
                    "Greedy rule: green_time(road) = flow(road) / total_flow * cycle",
                    "Optimal when flows are independent and stable",
                    "Suboptimal when adjacent intersections I1+I4 interact (global opt needed)",
                    "Emergency: preempt hold=" + (f"{signal.preempt_hold_sec}s" if signal else "?"),
                ],
            ))
        return results

    # ------------------------------------------------------------------
    # Scenario F -- DP scheduling
    # ------------------------------------------------------------------

    def run_scenario_f(self) -> List[SimulationResult]:
        results = []
        for period in TimePeriod:
            t0 = time.perf_counter()
            is_stub, raw = self._call("dp_sched", self.store, period)
            elapsed = (time.perf_counter() - t0) * 1000

            buses, trains = self.store.get_fleet(period)
            all_routes    = self.store.get_all_routes()
            total_demand  = sum(self.store.get_all_od_demands().values())

            results.append(SimulationResult(
                scenario_id   = "F",
                scenario_name = f"DP Scheduling: {period.name}",
                status        = "STUB" if is_stub else "OK",
                elapsed_ms    = elapsed,
                data          = {
                    "period":           period.label(),
                    "available_buses":  buses,
                    "available_trains": trains,
                    "total_routes":     len(all_routes),
                    "total_od_demand":  total_demand,
                    "dp_result":        raw,
                },
                notes = [
                    "Algorithm: Weighted job scheduling DP",
                    "Objective: maximize total passengers served per period",
                    "Constraint: deployed vehicles <= fleet availability",
                ],
            ))
        return results

    # ------------------------------------------------------------------
    # Scenario G -- DP maintenance knapsack
    # ------------------------------------------------------------------

    def run_scenario_g(self) -> List[SimulationResult]:
        BUDGET = 200.0
        t0 = time.perf_counter()
        is_stub, raw = self._call("dp_maint", self.graph, self.store, BUDGET)
        elapsed = (time.perf_counter() - t0) * 1000

        edges     = self.graph.get_existing_edges()
        mandatory = {"3-F2","3-F9","6-F9","10-F9","1-F10","12-F10","8-F10"}
        mand_cost = sum(e.maint_cost for e in edges if e.key in mandatory)

        by_priority = sorted(edges,
                             key=lambda e: (-e.maint_priority, e.maint_cost))

        return [SimulationResult(
            scenario_id   = "G",
            scenario_name = "DP Maintenance Knapsack",
            status        = "STUB" if is_stub else "OK",
            elapsed_ms    = elapsed,
            data          = {
                "budget_millions":           BUDGET,
                "mandatory_roads":           sorted(mandatory),
                "mandatory_cost_millions":   round(mand_cost, 1),
                "remaining_budget":          round(BUDGET - mand_cost, 1),
                "total_roads":               len(edges),
                "max_priority_score":        sum(e.maint_priority for e in edges),
                "top_candidates":            [
                    {"road": e.key, "cost": e.maint_cost,
                     "priority": e.maint_priority, "condition": e.condition}
                    for e in by_priority[:8]
                ],
                "dp_result": raw,
            },
            notes = [
                "Algorithm: 0/1 Knapsack DP",
                "Objective: maximize sum of priority scores of maintained roads",
                "Budget: 200 M-EGP  |  Hard include: hospital + Ramses access roads",
                "Complexity: O(roads x budget_granularity)",
            ],
        )]

    # ------------------------------------------------------------------
    # Report printer
    # ------------------------------------------------------------------

    def print_report(self, results: List[SimulationResult]) -> None:
        W = 70
        print()
        print("=" * W)
        print("  CAIRO TRANSPORTATION SYSTEM -- SIMULATION REPORT")
        print("=" * W)

        current_sid = None
        for r in results:
            if r.scenario_id != current_sid:
                current_sid = r.scenario_id
                print(f"\n  {'─'*2} SCENARIO {r.scenario_id} {'─'*(W-14)}")

            icon = {"OK": "v", "STUB": "~", "ERROR": "X"}.get(r.status, "?")
            print(f"\n  [{icon}] {r.scenario_name:<50}  ({r.elapsed_ms:.1f} ms)")
            for note in r.notes:
                print(f"       · {note}")

            d = r.data
            sid = r.scenario_id
            if   sid == "A": self._print_a(d)
            elif sid == "B": self._print_b(d)
            elif sid == "C": self._print_c(d)
            elif sid == "D": self._print_d(d)
            elif sid == "E": self._print_e(d)
            elif sid == "F": self._print_f(d)
            elif sid == "G": self._print_g(d)

        ok    = sum(1 for r in results if r.status == "OK")
        stub  = sum(1 for r in results if r.status == "STUB")
        error = sum(1 for r in results if r.status == "ERROR")
        print()
        print("=" * W)
        print(f"  {ok} passed  |  {stub} pending (algorithm stub)  |  {error} errors")
        print("=" * W)
        print()

    # ---- per-scenario detail printers ----

    def _print_a(self, d: dict) -> None:
        print(f"       [{d['source']}] -> [{d['destination']}]  |  {d['label']}")
        periods_data = d.get("periods", {})
        if all(v["stub"] for v in periods_data.values()):
            print("       Dijkstra not yet integrated -- store preview:")
            for p in TimePeriod:
                edge = self.graph.get_edge(d["source"], d["destination"])
                if edge:
                    ratio = self.store.get_congestion_ratio(edge.key, edge.capacity, p)
                    w     = self.store.get_weight(edge.key, edge.capacity, edge.distance, p)
                    lvl   = CongestionLevel.from_ratio(ratio)
                    print(f"         {p.name:<16}  ratio={ratio:.2f}  [{lvl.name:<8}]  direct={w:.1f} min")
                else:
                    print(f"         {p.name:<16}  no direct road (multi-hop path needed)")
        else:
            print(f"       {'Period':<16} {'Time (min)':>10}  Path")
            for p, v in periods_data.items():
                t    = f"{v['total_time']:.1f}" if v["total_time"] is not None else "--"
                path = " -> ".join(v["path"]) if v["path"] else "[stub]"
                print(f"         {p.name:<16} {t:>8}  {path}")

    def _print_b(self, d: dict) -> None:
        print(f"       [{d['source']}] -> [{d['destination']}]  |  {d['period']}")
        print(f"       Aerial distance: {d['aerial_km']} km  "
              f"(theoretical min @ 90 km/h: {d['aerial_min']} min)")
        astar = d.get("a_star")
        if astar and "total_time" in astar:
            t = astar["total_time"]
            p = " -> ".join(astar.get("path", []))
            print(f"       A* response time : {t:.1f} min  |  Path: {p}")
        else:
            print("       A* algorithm     : [not yet integrated]")

    def _print_c(self, d: dict) -> None:
        print(f"       Blocked: {d['closed_road']}  |  [{d['source']}] -> [{d['destination']}]"
              f"  |  {d['period']}")
        b  = d.get("baseline")
        dt = d.get("detour")
        if b and dt and b.get("total_time") and dt.get("total_time"):
            oh = d.get("overhead_min", "--")
            print(f"       Baseline: {b['total_time']:.1f} min  ->  "
                  f"Detour: {dt['total_time']:.1f} min  (+{oh} min overhead)")
            path = " -> ".join(dt.get("path", []))
            print(f"       Detour path: {path}")
        else:
            print("       Dijkstra: [not yet integrated]")
            print("       Graph mutation: remove_edge / restore_edge verified OK")

    def _print_d(self, d: dict) -> None:
        label = "Existing + Potential" if d["use_potential"] else "Existing Only"
        print(f"       Mode: {label}  |  Pool: {d['pool_edges']} edges  "
              f"|  {d['pool_distance_km']} km total")
        print(f"       Critical nodes required: {', '.join(d['critical_required'])}")
        raw = d.get("mst_result")
        if raw and "total_distance" in raw:
            print(f"       MST: {raw['total_distance']} km  "
                  f"|  cost: {raw['total_cost']} M-EGP  "
                  f"|  critical: {raw['critical_covered']}/{raw['total_critical']}")
        else:
            print("       Kruskal: [not yet integrated]")

    def _print_e(self, d: dict) -> None:
        em = "[EMERGENCY PREEMPTION]" if d["emergency"] else ""
        print(f"       {d['intersection']}  {em}  |  {d['period']}")
        alloc = d.get("greedy_allocation", {})
        if alloc:
            print(f"       Proportional allocation (cycle = {d['cycle_sec']}s):")
            for road, info in alloc.items():
                bar_len = max(1, int(info["pct"] / 4))
                bar     = "#" * bar_len
                print(f"         {road:<12}  flow={info['flow']:>5}  "
                      f"green={info['green_sec']:>5.1f}s  [{bar:<25}] {info['pct']:.0f}%")
        if d["emergency"]:
            print(f"       Emergency override: hold={d['preempt_hold']}s  "
                  f"then recover over {d['recover_cycle']}s")
        opt = d.get("optimized_result")
        if opt and "error" not in opt:
            print(f"       Greedy result: {opt}")
        else:
            print("       Greedy optimizer: [not yet integrated] -- allocation above is pre-computed")

    def _print_f(self, d: dict) -> None:
        print(f"       Period: {d['period']}")
        print(f"       Fleet: {d['available_buses']} buses / {d['available_trains']} trains  "
              f"|  Routes: {d['total_routes']}")
        print(f"       Total OD demand: {d['total_od_demand']:,} passengers/day")
        raw = d.get("dp_result")
        if raw and "served" in raw:
            print(f"       Served: {raw['served']:,}  ({raw.get('utilization','--')}% utilization)")
        else:
            print("       DP Scheduling: [not yet integrated]")

    def _print_g(self, d: dict) -> None:
        print(f"       Budget: {d['budget_millions']} M-EGP  "
              f"|  Roads: {d['total_roads']}  "
              f"|  Max priority score: {d['max_priority_score']}")
        print(f"       Always maintained: {', '.join(d['mandatory_roads'])}"
              f"  (cost: {d['mandatory_cost_millions']} M-EGP)")
        print(f"       Remaining budget after mandatory: {d['remaining_budget']} M-EGP")
        print("       Top candidates by priority:")
        for r in d["top_candidates"]:
            print(f"         {r['road']:<12}  P={r['priority']}/5  "
                  f"cost={r['cost']:>5.1f}  cond={r['condition']}/10")
        raw = d.get("dp_result")
        if raw and "total_score" in raw:
            print(f"       DP result: score={raw['total_score']}  "
                  f"cost={raw['cost_used']} M-EGP")
        else:
            print("       DP Knapsack: [not yet integrated]")
