"""
algorithms/optimization.py
Cairo Transportation Network — Optimization Analysis Report

Purpose
-------
This module provides a complete analysis of the optimization
techniques, algorithms, and data structures implemented across
the Cairo Transportation Network project.

Unlike the algorithm modules themselves, this file does NOT
implement new routing or graph algorithms.

Instead, it explains:
    • what was optimized
    • how optimization was achieved
    • which data structures improved performance
    • algorithmic complexity
    • transportation-system impact

This acts as the final optimization-analysis layer of the project.
"""

from models.graph import Graph
from models.edge import TimePeriod
from simulation.traffic_data import TrafficDataStore

from algorithms.mst import kruskal_mst
from algorithms.shortest_path import (
    dijkstra,
    astar,
    least_congested_route,
    alternate_route,
)
from algorithms.emergency_response import emergency_response


# ============================================================
# SECTION 1 — GRAPH OPTIMIZATION
# ============================================================

def graph_optimization(graph: Graph) -> None:

    print("\n" + "=" * 72)
    print("  1. GRAPH STRUCTURE OPTIMIZATION")
    print("=" * 72)

    print("""
  Module:
      models/graph.py

  Optimization Techniques
  -----------------------
  • Sparse graph representation using adjacency lists
  • O(1) edge lookup using dictionary hash maps
  • Canonical edge-key normalization
  • Dynamic edge-weight computation

  Why adjacency lists?
  --------------------
  Cairo's transportation network is sparse:
      • 25 nodes
      • 33 existing roads
      • 15 potential roads

  Using adjacency matrices would require:
      O(V²) memory

  Using adjacency lists:
      O(V + E) memory

  Benefits
  --------
  • Faster neighbour traversal
  • Lower memory usage
  • Better scalability
  • Efficient shortest-path traversal

  Dynamic Weight Optimization
  ---------------------------
  Edge weights are NOT stored statically.

  Travel times are dynamically computed using:
      • distance
      • traffic flow
      • speed
      • congestion factor
      • time period

  This allows:
      • adaptive routing
      • congestion-aware navigation
      • real-time simulation
""")

    print(f"  Current graph statistics:")
    print(f"    Nodes                : {len(graph.nodes)}")
    print(f"    Existing roads       : {len(graph.get_existing_edges())}")
    print(f"    Potential roads      : {len(graph.get_potential_edges())}")
    print(f"    Critical nodes       : {len(graph.get_critical_nodes())}")


# ============================================================
# SECTION 2 — TRAFFIC DATA STORE OPTIMIZATION
# ============================================================

def datastore_optimization(store: TrafficDataStore) -> None:

    print("\n" + "=" * 72)
    print("  2. TEMPORAL TRAFFIC DATA OPTIMIZATION")
    print("=" * 72)

    print("""
  Module:
      simulation/traffic_data.py

  Optimization Techniques
  -----------------------
  • O(1) traffic-flow lookup
  • O(1) speed lookup
  • O(1) signal lookup
  • Temporal traffic modeling
  • Surge-event simulation
  • Snapshot/rollback restoration

  Data Structures
  ---------------
  Flow table:
      dict[edge_key -> list[int]]

  Speed table:
      dict[edge_key -> (normal_speed, rush_speed)]

  Signal table:
      dict[intersection_id -> SignalConfig]

  Traffic Period Optimization
  ---------------------------
      1. Morning Peak
      2. Afternoon
      3. Evening Peak
      4. Night

  Congestion Optimization
  -----------------------
  Congestion ratio:
      flow / capacity

  Congestion levels:
      • CLEAR
      • MODERATE
      • SEVERE

  Dynamic weight formula:
      travel_time =
          (distance / speed)
          × congestion_factor

  Benefits
  --------
  • Adaptive traffic-aware routing
  • Realistic congestion simulation
  • Efficient event injection
  • No graph rebuilding required
""")

    print(f"  Signals loaded         : {len(store.get_all_signals())}")
    print(f"  Transit routes loaded  : {len(store.get_all_routes())}")


# ============================================================
# SECTION 3 — SHORTEST PATH OPTIMIZATION
# ============================================================

def shortest_path_optimization(
    graph: Graph,
    store: TrafficDataStore,
) -> None:

    print("\n" + "=" * 72)
    print("  3. SHORTEST PATH OPTIMIZATION")
    print("=" * 72)

    start = "4"
    end   = "3"

    dijkstra_result = dijkstra(
        graph,
        store,
        start,
        end,
        TimePeriod.MORNING_PEAK
    )

    astar_result = astar(
        graph,
        store,
        start,
        end,
        TimePeriod.MORNING_PEAK
    )

    least_result = least_congested_route(
        graph,
        store,
        start,
        end,
        TimePeriod.MORNING_PEAK
    )

    blocked_result = alternate_route(
        graph,
        store,
        start,
        end,
        blocked_edge_keys=["3-5"],
        period=TimePeriod.MORNING_PEAK
    )

    print("""
  Module:
      algorithms/shortest_path.py

  Implemented Algorithms
  ----------------------
  • Dijkstra's Algorithm
  • A* Search Algorithm
  • Time-Varying Dijkstra
  • Alternate Route Routing
  • Least Congested Routing

  Dijkstra Optimization
  ---------------------
  • Min-heap priority queue
  • Early destination exit

  Complexity:
      O((V + E) log V)

  A* Optimization
  ---------------
  Uses heuristic:
      f(n) = g(n) + h(n)

  where:
      g(n) = actual travel cost
      h(n) = Euclidean heuristic estimate

  Benefits
  --------
  • Fewer explored nodes
  • Faster emergency routing
  • Better real-world performance

  Alternate Route Optimization
  ----------------------------
  Supports dynamic road closures and automatic rerouting.

  Least Congested Route
  ---------------------
  Optimizes congestion ratio instead of shortest time.
""")

    print(f"\n  Test route: Node {start} -> Node {end}")

    print(f"\n    Dijkstra")
    print(f"      Time               : {dijkstra_result.total_time_minutes:.2f} min")
    print(f"      Nodes explored     : {dijkstra_result.nodes_visited}")

    print(f"\n    A*")
    print(f"      Time               : {astar_result.total_time_minutes:.2f} min")
    print(f"      Nodes explored     : {astar_result.nodes_visited}")

    print(f"\n    Least Congested")
    print(f"      Time               : {least_result.total_time_minutes:.2f} min")

    print(f"\n    Alternate Route")
    print(f"      Time               : {blocked_result.total_time_minutes:.2f} min")
    print(f"      Blocked road       : 3-5")


# ============================================================
# SECTION 4 — MST OPTIMIZATION
# ============================================================

def mst_optimization(graph: Graph) -> None:

    print("\n" + "=" * 72)
    print("  4. INFRASTRUCTURE OPTIMIZATION (MST)")
    print("=" * 72)

    result = kruskal_mst(
        graph,
        use_cost=True,
        include_potential=True
    )

    print("""
  Module:
      algorithms/mst.py

  Implemented Algorithm
  ---------------------
  • Kruskal's Minimum Spanning Tree

  Optimization Techniques
  -----------------------
  • Edge sorting
  • Union-Find structure
  • Path compression
  • Union by rank
  • Critical-node priority forcing

  Complexity
  ----------
      O(E log E)

  Critical Infrastructure Optimization
  ------------------------------------
  The following nodes are guaranteed connectivity:
      • F9  — Qasr El Aini Hospital
      • F10 — Maadi Hospital
      • F1  — Cairo Airport
      • F2  — Ramses Railway Station
      • 13  — New Administrative Capital

  Cost Optimization Modes
  -----------------------
      1. Distance minimization
      2. Construction-cost minimization

  Infrastructure Goals
  --------------------
  • Minimize road cost
  • Preserve full connectivity
  • Guarantee critical-node access
""")

    print(f"  MST edges selected     : {len(result.edges)}")
    print(f"  Total MST weight       : {result.total_weight:.2f}")
    print(f"  Total distance         : {result.total_distance_km:.1f} km")
    print(f"  Construction cost      : {result.total_cost_megp:.1f} M EGP")
    print(f"  New roads selected     : {len(result.new_roads_selected)}")
    print(f"  Critical forced edges  : {len(result.critical_forced)}")


# ============================================================
# SECTION 5 — GREEDY OPTIMIZATION
# ============================================================

def greedy_optimization(
    graph: Graph,
    store: TrafficDataStore,
) -> None:

    print("\n" + "=" * 72)
    print("  5. GREEDY EMERGENCY OPTIMIZATION")
    print("=" * 72)

    result = emergency_response(
        graph,
        store,
        origin_id="7",
        period=TimePeriod.MORNING_PEAK
    )

    print("""
  Module:
      algorithms/emergency_response.py

  Implemented Optimization
  ------------------------
  • Greedy Signal Preemption

  Combined Algorithms
  -------------------
  • A* shortest-path routing
  • Greedy traffic-signal clearing

  Greedy Strategy
  ---------------
  Traffic signals are processed in encounter order:
      always clear the NEXT signal first

  Characteristics
  ---------------
  • Local optimization strategy
  • No backtracking
  • No global search
  • Fast real-time decision making

  Optimization Goal
  -----------------
  Reduce emergency-vehicle waiting time at
  signalized intersections.

  Emergency Benefits
  ------------------
  • Faster ambulance routing
  • Reduced hospital response time
  • Dynamic emergency corridor creation
""")

    print(f"  Origin node            : {result.origin_id}")
    print(f"  Selected hospital      : {result.hospital_name}")
    print(f"  Original response time : {result.total_time_without_min:.2f} min")
    print(f"  Optimized response     : {result.total_time_with_min:.2f} min")
    print(f"  Time saved             : {result.time_saved_min:.2f} min")
    print(f"  Improvement            : {result.improvement_pct:.1f}%")


# ============================================================
# SECTION 6 — DYNAMIC PROGRAMMING OPTIMIZATION
# ============================================================

def dp_optimization() -> None:

    print("\n" + "=" * 72)
    print("  6. DYNAMIC PROGRAMMING OPTIMIZATION")
    print("=" * 72)

    print("""
  Module:
      algorithms/dp.py

  Implemented Optimization
  ------------------------
  • Knapsack-style dynamic programming
  • Memoization
  • Resource allocation optimization
  • Transit scheduling optimization

  DP Optimization Goals
  ---------------------
  • Maximize passenger coverage
  • Minimize transportation inefficiency
  • Optimize limited transportation resources

  Memoization Optimization
  ------------------------
  Previously computed subproblems are reused,
  avoiding redundant recalculation.

  Benefits
  --------
  • Faster scheduling computation
  • Better fleet utilization
  • Reduced computation overhead
  • Improved transportation efficiency
""")


# ============================================================
# FINAL REPORT
# ============================================================

def run_optimization_report() -> None:

    graph = Graph()
    store = TrafficDataStore()

    print("\n" + "=" * 72)
    print("  CAIRO TRANSPORTATION NETWORK — OPTIMIZATION ANALYSIS")
    print("=" * 72)

    graph_optimization(graph)

    datastore_optimization(store)

    shortest_path_optimization(graph, store)

    mst_optimization(graph)

    greedy_optimization(graph, store)

    dp_optimization()

    print("\n" + "=" * 72)
    print("  FINAL OPTIMIZATION SUMMARY")
    print("=" * 72)

    print("""
  ✓ Sparse graph optimized using adjacency lists
  ✓ O(1) traffic-data retrieval implemented
  ✓ Dynamic congestion-aware routing operational
  ✓ A* heuristic optimization reduces explored nodes
  ✓ Kruskal MST minimizes infrastructure cost
  ✓ Critical infrastructure guaranteed connectivity
  ✓ Greedy signal preemption reduces ambulance delay
  ✓ Dynamic programming optimizes transit resources
  ✓ Integrated optimization framework completed
""")

    print("=" * 72)
