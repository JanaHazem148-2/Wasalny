"""
main.py
Cairo Transportation Network -- Task 1: Full System Demo

Covers all three deliverables of Task 1:
  1. Weighted graph representation  (models/)
  2. Temporal traffic data store     (simulation/traffic_data.py)
  3. Simulation framework            (simulation/framework.py)

Run:
    python main.py

"""

from models.graph            import Graph
from models.edge             import TimePeriod, CongestionLevel
from simulation.traffic_data import TrafficDataStore
from simulation.framework    import SimulationFramework


# ============================================================
# Display helpers
# ============================================================

def header(title: str) -> None:
    W = 70
    print()
    print("=" * W)
    print(f"  {title}")
    print("=" * W)


def sub(title: str) -> None:
    print(f"\n  {'─' * 60}")
    print(f"  {title}")
    print(f"  {'─' * 60}")


# ============================================================
# Section 1 -- Graph structure verification
# ============================================================

def demo_graph(graph: Graph) -> None:
    header("PART 1 -- Weighted Graph Representation")
    graph.print_summary()

    sub("All 25 Nodes")
    print(f"  {'ID':<6}  {'Name':<35}  {'Type':<14}  {'Population':>12}  Critical")
    print(f"  {'──':<6}  {'────':<35}  {'────':<14}  {'──────────':>12}  ────────")
    for node in sorted(graph.nodes.values(), key=lambda n: n.node_id):
        pop  = f"{node.population:,}" if node.population > 0 else "  —"
        flag = "*** YES ***" if node.is_critical else ""
        print(f"  {node.node_id:<6}  {node.name:<35}  {node.node_type.name:<14}"
              f"  {pop:>12}  {flag}")

    sub("Existing Road Network -- 33 edges")
    edges = sorted(graph.get_existing_edges(), key=lambda e: e.key)
    print(f"  {'Road':<12}  {'Dist':>7}  {'Cap':>8}  {'Cond':>6}  "
          f"{'Maint £':>9}  {'Priority':>9}")
    print(f"  {'────':<12}  {'────':>7}  {'───':>8}  {'────':>6}  "
          f"{'───────':>9}  {'────────':>9}")
    for e in edges:
        print(f"  {e.key:<12}  {e.distance:>5.1f}km  "
              f"{e.capacity:>6}v/h  {e.condition:>4}/10  "
              f"{e.maint_cost:>7.1f}M  {e.maint_priority:>7}/5")
    total_dist = sum(e.distance for e in edges)
    print(f"\n  Total road network length: {total_dist:.1f} km")

    sub("Proposed New Roads -- 15 candidates (for MST evaluation)")
    pot = sorted(graph.get_potential_edges(), key=lambda e: e.cost_millions)
    print(f"  {'Road':<12}  {'Dist':>7}  {'Cap':>8}  {'Cost (MEGP)':>12}")
    print(f"  {'────':<12}  {'────':>7}  {'───':>8}  {'───────────':>12}")
    for e in pot:
        print(f"  {e.key:<12}  {e.distance:>5.1f}km  "
              f"{e.capacity:>6}v/h  {e.cost_millions:>10.0f}M")

    sub("Adjacency List -- Spot Check (critical nodes)")
    for nid in ["3", "F9", "F10", "13", "7"]:
        nbrs = graph.get_neighbours(nid)
        node = graph.get_node(nid)
        print(f"\n  [{nid}] {node.name}  ({len(nbrs)} neighbours)")
        for nbr, edge in sorted(nbrs, key=lambda t: t[0].node_id):
            wm = edge.get_weight(TimePeriod.MORNING_PEAK)
            wn = edge.get_weight(TimePeriod.NIGHT)
            print(f"       -> [{nbr.node_id}] {nbr.name:<30}  "
                  f"{edge.distance:.1f}km  "
                  f"peak={wm:.1f}min  night={wn:.1f}min")

    sub("Edge Lookup + Road Closure Simulation")
    e35 = graph.get_edge("3", "5")
    print(f"  get_edge('3','5')         -> {e35}")
    print(f"  get_edge('5','3')         -> {graph.get_edge('5','3')}")
    print(f"  Bidirectional same edge?  -> {e35 == graph.get_edge('5','3')}")

    print("\n  [Simulating accident: removing road 3-5 ...]")
    removed = graph.remove_edge("3", "5")
    print(f"  get_edge('3','5') after   -> {graph.get_edge('3','5')}  (None = removed)")
    nbrs_3 = [n.node_id for n, _ in graph.get_neighbours("3")]
    print(f"  Node 3 neighbours now     -> {nbrs_3}")
    graph.restore_edge(removed)
    print(f"  get_edge('3','5') restored-> {graph.get_edge('3','5')}")

    sub("A* Heuristic -- Aerial Distances")
    pairs = [
        ("7",  "F9",  "6th October -> Qasr El Aini Hospital"),
        ("13", "F9",  "New Capital -> Qasr El Aini Hospital"),
        ("12", "F10", "Helwan -> Maadi Military Hospital"),
        ("4",  "3",   "New Cairo -> Downtown Cairo"),
        ("7",  "8",   "6th October -> Giza"),
    ]
    print(f"  {'Route':<52}  {'Aerial km':>10}")
    print(f"  {'─────':<52}  {'─────────':>10}")
    for a, b, lbl in pairs:
        dist = graph.get_node(a).euclidean_distance_to(graph.get_node(b))
        print(f"  {lbl:<52}  {dist:>10.2f}")


# ============================================================
# Section 2 -- Traffic data store verification
# ============================================================

def demo_store(graph: Graph, store: TrafficDataStore) -> None:
    header("PART 2 -- Temporal Traffic Data Store")

    sub("O(1) Flow Lookup -- Key Roads Across All Periods")
    sample_keys = ["3-5", "2-4", "7-8", "3-F9", "13-4"]
    periods     = list(TimePeriod)
    period_lbls = ["Morning", "Afternoon", "Evening", "Night"]

    for key in sample_keys:
        edge = graph.edges.get(key)
        if edge is None:
            continue
        print(f"\n  Road {key}  (cap={edge.capacity})")
        print(f"  {'Period':<12}  {'Flow':>7}  {'Ratio':>7}  {'Level':<10}  {'Weight (min)':>13}")
        print(f"  {'──────':<12}  {'────':>7}  {'─────':>7}  {'─────':<10}  {'────────────':>13}")
        for p, lbl in zip(periods, period_lbls):
            flow  = store.get_flow(key, p)
            ratio = store.get_congestion_ratio(key, edge.capacity, p)
            level = store.get_congestion_level(key, edge.capacity, p)
            w     = store.get_weight(key, edge.capacity, edge.distance, p)
            print(f"  {lbl:<12}  {flow:>7}  {ratio:>7.3f}  {level.name:<10}  {w:>13.2f}")

    sub("Congestion Report -- Morning Peak (top 10 most congested roads)")
    existing = graph.get_existing_edges()
    report   = store.congestion_report(existing, TimePeriod.MORNING_PEAK)
    print(f"  {'Road':<12}  {'Flow':>7}  {'Cap':>7}  {'Ratio':>7}  {'Level':<10}  {'Time(min)':>10}")
    print(f"  {'────':<12}  {'────':>7}  {'───':>7}  {'─────':>7}  {'─────':<10}  {'─────────':>10}")
    for row in report[:10]:
        print(f"  {row['edge']:<12}  {row['flow']:>7}  {row['cap']:>7}  "
              f"{row['ratio']:>7.3f}  {row['level'].name:<10}  {row['weight']:>10.2f}")

    sub("Surge Event Simulation -- Injecting +40% flow on road 3-5")
    edge_35 = graph.get_edge("3", "5")
    period  = TimePeriod.MORNING_PEAK
    before  = store.get_weight("3-5", edge_35.capacity, edge_35.distance, period)
    ratio_b = store.get_congestion_ratio("3-5", edge_35.capacity, period)

    snap    = store.apply_surge("3-5", period, 1.4)
    after   = store.get_weight("3-5", edge_35.capacity, edge_35.distance, period)
    ratio_a = store.get_congestion_ratio("3-5", edge_35.capacity, period)

    print(f"  Before surge: flow ratio={ratio_b:.3f}  weight={before:.2f} min")
    print(f"  After  surge: flow ratio={ratio_a:.3f}  weight={after:.2f} min")
    print(f"  Impact: +{after - before:.2f} min travel time (+{(after/before - 1)*100:.0f}%)")
    store.restore_flow("3-5", snap)
    restored = store.get_weight("3-5", edge_35.capacity, edge_35.distance, period)
    print(f"  Restored:     weight={restored:.2f} min  (snapshot rollback OK)")

    sub("Signal Configurations -- 10 Intersections")
    print(f"  {'ID':<5}  {'Name':<28}  {'Cycle':>6}  {'Preempt':>8}  {'Roads'}")
    print(f"  {'──':<5}  {'────':<28}  {'─────':>6}  {'───────':>8}  {'─────'}")
    for sig in store.get_all_signals():
        roads = ", ".join(sig.connected_roads)
        print(f"  {sig.intersection_id:<5}  {sig.name:<28}  "
              f"{sig.normal_cycle_sec:>5}s  {sig.preempt_hold_sec:>6}s  {roads}")

    sub("Transit Routes -- Fleet and Demand Summary")
    routes  = store.get_all_routes()
    bus_r   = [r for r in routes if r.route_type == "bus"]
    metro_r = [r for r in routes if r.route_type == "metro"]
    print(f"  Metro lines  : {len(metro_r)}  "
          f"(daily passengers: {sum(r.daily_passengers for r in metro_r):,})")
    print(f"  Bus routes   : {len(bus_r)}  "
          f"(daily passengers: {sum(r.daily_passengers for r in bus_r):,})")
    print()
    print(f"  Fleet availability per period:")
    for p in TimePeriod:
        buses, trains = store.get_fleet(p)
        print(f"    {p.name:<16}  {buses:>4} buses  |  {trains:>3} trains")
    total_demand = sum(store.get_all_od_demands().values())
    print(f"\n  OD demand pairs : {len(store.get_all_od_demands())}  "
          f"(total: {total_demand:,} passengers/day)")


# ============================================================
# Section 3 -- Simulation framework
# ============================================================

def demo_simulation(graph: Graph, store: TrafficDataStore) -> None:
    header("PART 3 -- Simulation Framework (All 7 Scenarios)")
    print("  Algorithms will be integrated in Tasks 2-5.")
    print("  The framework runs all scenarios now and shows pre-computed")
    print("  reference data from the graph and store for each one.")

    sim     = SimulationFramework(graph, store)
    results = sim.run_all()
    sim.print_report(results)


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    print("\n  [Loading Cairo network ...]")
    graph = Graph()
    print("  [Loading traffic data store ...]")
    store = TrafficDataStore()
    print("  [Ready.]\n")

    demo_graph(graph)
    demo_store(graph, store)
    demo_simulation(graph, store)

    header("TASK 1 COMPLETE")
    print("  Graph model       : 25 nodes, 33 existing + 15 potential edges")
    print("  Traffic data store: O(1) flow/speed/weight queries, all 4 periods")
    print("  Simulation engine : 7 scenario families, algorithm hooks ready")
    print("  All Tasks 2-5 modules can now plug in via:")
    print("    sim.register_algorithm('dijkstra', my_fn)")
    print("    sim.register_algorithm('a_star',   my_fn)")
    print("    sim.register_algorithm('mst',      my_fn)")
    print("    sim.register_algorithm('greedy',   my_fn)")
    print("    sim.register_algorithm('dp_sched', my_fn)")
    print("    sim.register_algorithm('dp_maint', my_fn)")
    print()
