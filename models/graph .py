"""
graph.py
--------
The central data structure of the Cairo Transportation System.

This module builds and maintains an undirected weighted graph that models
the Greater Cairo metropolitan road network. Every node is a real district
or facility drawn from the project dataset. Every edge is a real road with
measured capacity, condition, traffic flow across four daily periods, speed
limits, and maintenance metadata.

Design choice : Adjacency List
    With 25 nodes and 34 existing edges the graph is sparse
    (density ≈ 11%). An adjacency list costs O(V + E) in space
    and gives O(degree) neighbor lookup, which is exactly what
    Dijkstra and A* need in their inner loop. An adjacency matrix
    would waste O(V²) space and offer no benefit here.

Design choice : Bidirectional edges
    All roads in the dataset are bidirectional. The graph stores
    two Edge objects per road (forward + backward) so that every
    algorithm can treat neighbor traversal uniformly without
    needing to check both directions manually.

"""

from collections import defaultdict
from models.node import Node, NodeType
from models.edge import Edge, TimePeriod


class Graph:
    """
    Undirected weighted graph representing Cairo's road network.

    Public attributes
    -----------------
    nodes           : dict[str, Node]       — all 25 locations by ID
    adjacency_list  : dict[str, list[Edge]] — neighbor edges per node
    existing_edges  : list[Edge]            — 34 current road segments
    potential_edges : list[Edge]            — 15 candidate new roads
    """

    def __init__(self):
        self.nodes           = {}
        self.adjacency_list  = defaultdict(list)
        self.existing_edges  = []
        self.potential_edges = []

        # Internal lookup: (from_id, to_id) → Edge (forward direction only)
        self._edge_map: dict[tuple, Edge] = {}

        self._build()

    # ==================================================================
    # BUILD PIPELINE
    # ==================================================================

    def _build(self) -> None:
        """
        Executes the full data loading pipeline in dependency order.
        Nodes must exist before edges; edges must exist before flow/speed/
        maintenance data can be attached to them.
        """
        self._load_nodes()
        self._load_existing_roads()
        self._load_potential_roads()
        self._load_traffic_flow()
        self._load_speed_limits()
        self._load_maintenance_data()

    # ------------------------------------------------------------------
    # Step 1 — Nodes
    # ------------------------------------------------------------------

    def _load_nodes(self) -> None:
        districts = [
            # ID    Name                          Population  Type                    Lon    Lat
            ("1",   "Maadi",                       250_000, NodeType.RESIDENTIAL,  31.25, 29.96),
            ("2",   "Nasr City",                   500_000, NodeType.MIXED,        31.34, 30.06),
            ("3",   "Downtown Cairo",              100_000, NodeType.BUSINESS,     31.24, 30.04),
            ("4",   "New Cairo",                   300_000, NodeType.RESIDENTIAL,  31.47, 30.03),
            ("5",   "Heliopolis",                  200_000, NodeType.MIXED,        31.32, 30.09),
            ("6",   "Zamalek",                      50_000, NodeType.RESIDENTIAL,  31.22, 30.06),
            ("7",   "6th October City",            400_000, NodeType.MIXED,        30.98, 29.93),
            ("8",   "Giza",                        550_000, NodeType.MIXED,        31.21, 29.99),
            ("9",   "Mohandessin",                 180_000, NodeType.BUSINESS,     31.20, 30.05),
            ("10",  "Dokki",                       220_000, NodeType.MIXED,        31.21, 30.03),
            ("11",  "Shubra",                      450_000, NodeType.RESIDENTIAL,  31.24, 30.11),
            ("12",  "Helwan",                      350_000, NodeType.INDUSTRIAL,   31.33, 29.85),
            ("13",  "New Administrative Capital",   50_000, NodeType.GOVERNMENT,   31.80, 30.02),
            ("14",  "Al Rehab",                    120_000, NodeType.RESIDENTIAL,  31.49, 30.06),
            ("15",  "Sheikh Zayed",                150_000, NodeType.RESIDENTIAL,  30.94, 30.01),
        ]

        facilities = [
            # ID    Name                           Pop   Type                   Lon    Lat
            ("F1",  "Cairo International Airport",  0, NodeType.AIRPORT,      31.41, 30.11),
            ("F2",  "Ramses Railway Station",       0, NodeType.TRANSIT_HUB,  31.25, 30.06),
            ("F3",  "Cairo University",             0, NodeType.EDUCATION,    31.21, 30.03),
            ("F4",  "Al-Azhar University",          0, NodeType.EDUCATION,    31.26, 30.05),
            ("F5",  "Egyptian Museum",              0, NodeType.TOURISM,      31.23, 30.05),
            ("F6",  "Cairo International Stadium",  0, NodeType.SPORTS,       31.30, 30.07),
            ("F7",  "Smart Village",                0, NodeType.COMMERCIAL,   30.97, 30.07),
            ("F8",  "Cairo Festival City",          0, NodeType.COMMERCIAL,   31.40, 30.03),
            ("F9",  "Qasr El Aini Hospital",        0, NodeType.MEDICAL,      31.23, 30.03),
            ("F10", "Maadi Military Hospital",      0, NodeType.MEDICAL,      31.25, 29.95),
        ]

        for data in districts + facilities:
            self._add_node(Node(*data))

    # ------------------------------------------------------------------
    # Step 2 — Existing Roads
    # ------------------------------------------------------------------

    def _load_existing_roads(self) -> None:
        """
        Loads the 28 roads from the original dataset plus 6 hospital
        access roads that were added to make F9 and F10 reachable.
        All roads are stored bidirectionally.
        """
        original_roads = [
            # From   To   Dist    Cap   Cond
            ("1",   "3",   8.5,  3000,   7),
            ("1",   "8",   6.2,  2500,   6),
            ("2",   "3",   5.9,  2800,   8),
            ("2",   "5",   4.0,  3200,   9),
            ("3",   "5",   6.1,  3500,   7),
            ("3",   "6",   3.2,  2000,   8),
            ("3",   "9",   4.5,  2600,   6),
            ("3",   "10",  3.8,  2400,   7),
            ("4",   "2",  15.2,  3800,   9),
            ("4",   "14",  5.3,  3000,  10),
            ("5",   "11",  7.9,  3100,   7),
            ("6",   "9",   2.2,  1800,   8),
            ("7",   "8",  24.5,  3500,   8),
            ("7",   "15",  9.8,  3000,   9),
            ("8",   "10",  3.3,  2200,   7),
            ("8",   "12", 14.8,  2600,   5),
            ("9",   "10",  2.1,  1900,   7),
            ("10",  "11",  8.7,  2400,   6),
            ("11",  "F2",  3.6,  2200,   7),
            ("12",  "1",  12.7,  2800,   6),
            ("13",  "4",  45.0,  4000,  10),
            ("14",  "13", 35.5,  3800,   9),
            ("15",  "7",   9.8,  3000,   9),
            ("F1",  "5",   7.5,  3500,   9),
            ("F1",  "2",   9.2,  3200,   8),
            ("F2",  "3",   2.5,  2000,   7),
            ("F7",  "15",  8.3,  2800,   8),
            ("F8",  "4",   6.1,  3000,   9),
        ]

        # Hospital access roads (added — see Section 2B of data file)
        hospital_roads = [
            ("F9",  "3",   1.2,  1500,  9),
            ("F9",  "6",   2.1,  1200,  8),
            ("F9",  "10",  2.5,  1300,  8),
            ("F10", "1",   1.8,  1400,  9),
            ("F10", "12",  3.2,  1200,  7),
            ("F10", "8",   5.1,  1500,  8),
        ]

        for f, t, d, c, cond in original_roads + hospital_roads:
            self._add_edge(f, t, d, c, cond, is_existing=True)

    # ------------------------------------------------------------------
    # Step 3 — Potential New Roads
    # ------------------------------------------------------------------

    def _load_potential_roads(self) -> None:
        """
        Stores candidate roads not yet built. These are passed to
        Kruskal's MST to evaluate which new roads offer the best
        cost-to-connectivity return.
        """
        candidates = [
            # From   To   Dist    Cap   Cost(M EGP)
            ("1",   "4",   22.8, 4000,  450),
            ("1",   "14",  25.3, 3800,  500),
            ("2",   "13",  48.2, 4500,  950),
            ("3",   "13",  56.7, 4500, 1100),
            ("5",   "4",   16.8, 3500,  320),
            ("6",   "8",    7.5, 2500,  150),
            ("7",   "13",  82.3, 4000, 1600),
            ("9",   "11",   6.9, 2800,  140),
            ("10",  "F7",  27.4, 3200,  550),
            ("11",  "13",  62.1, 4200, 1250),
            ("12",  "14",  30.5, 3600,  610),
            ("14",  "5",   18.2, 3300,  360),
            ("15",  "9",   22.7, 3000,  450),
            ("F1",  "13",  40.2, 4000,  800),
            ("F7",  "9",   26.8, 3200,  540),
        ]

        for f, t, d, c, cost in candidates:
            edge = Edge(
                self.nodes[f], self.nodes[t],
                d, c, condition=10,
                is_existing=False,
                construction_cost=cost,
            )
            self.potential_edges.append(edge)

    # ------------------------------------------------------------------
    # Step 4 — Traffic Flow
    # ------------------------------------------------------------------

    def _load_traffic_flow(self) -> None:
        """
        Attaches four-period flow measurements to every existing edge.
        Without this data, get_weight() would compute uncongested times
        only — missing the entire point of time-dependent routing.
        """
        # Format: (from, to, morning, afternoon, evening, night)
        flows = [
            ("1",  "3",   2800, 1500, 2600,  800),
            ("1",  "8",   2200, 1200, 2100,  600),
            ("2",  "3",   2700, 1400, 2500,  700),
            ("2",  "5",   3000, 1600, 2800,  650),
            ("3",  "5",   3200, 1700, 3100,  800),
            ("3",  "6",   1800, 1400, 1900,  500),
            ("3",  "9",   2400, 1300, 2200,  550),
            ("3",  "10",  2300, 1200, 2100,  500),
            ("4",  "2",   3600, 1800, 3300,  750),
            ("4",  "14",  2800, 1600, 2600,  600),
            ("5",  "11",  2900, 1500, 2700,  650),
            ("6",  "9",   1700, 1300, 1800,  450),
            ("7",  "8",   3200, 1700, 3000,  700),
            ("7",  "15",  2800, 1500, 2600,  600),
            ("8",  "10",  2000, 1100, 1900,  450),
            ("8",  "12",  2400, 1300, 2200,  500),
            ("9",  "10",  1800, 1200, 1700,  400),
            ("10", "11",  2200, 1300, 2100,  500),
            ("11", "F2",  2100, 1200, 2000,  450),
            ("12", "1",   2600, 1400, 2400,  550),
            ("13", "4",   3800, 2000, 3500,  800),
            ("14", "13",  3600, 1900, 3300,  750),
            ("15", "7",   2800, 1500, 2600,  600),
            ("F1", "5",   3300, 2200, 3100, 1200),
            ("F1", "2",   3000, 2000, 2800, 1100),
            ("F2", "3",   1900, 1600, 1800,  900),
            ("F7", "15",  2600, 1500, 2400,  550),
            ("F8", "4",   2800, 1600, 2600,  600),
            # Hospital access roads
            ("F9",  "3",    800,  600,  750,  200),
            ("F9",  "6",    600,  450,  580,  150),
            ("F9",  "10",   700,  500,  650,  180),
            ("F10", "1",    700,  520,  670,  190),
            ("F10", "12",   550,  400,  520,  140),
            ("F10", "8",    750,  550,  700,  200),
        ]

        for f, t, m, a, e, n in flows:
            edge = self._get_edge(f, t)
            if edge:
                edge.set_traffic_flow(m, a, e, n)
            rev = self._get_edge(t, f)
            if rev:
                rev.set_traffic_flow(m, a, e, n)

    # ------------------------------------------------------------------
    # Step 5 — Speed Limits
    # ------------------------------------------------------------------

    def _load_speed_limits(self) -> None:
        # Format: (from, to, normal_km/h, rush_hour_km/h)
        speeds = [
            ("1",  "3",   60, 30), ("1",  "8",  70, 35),
            ("2",  "3",   60, 25), ("2",  "5",  80, 40),
            ("3",  "5",   60, 25), ("3",  "6",  50, 20),
            ("3",  "9",   60, 25), ("3",  "10", 60, 25),
            ("4",  "2",  100, 60), ("4",  "14", 90, 55),
            ("5",  "11",  70, 35), ("6",  "9",  50, 20),
            ("7",  "8",  100, 60), ("7",  "15", 90, 55),
            ("8",  "10",  60, 30), ("8",  "12", 80, 45),
            ("9",  "10",  50, 20), ("10", "11", 60, 30),
            ("11", "F2",  60, 30), ("12", "1",  80, 45),
            ("13", "4",  120, 80), ("14", "13",110, 75),
            ("15", "7",   90, 55), ("F1", "5",  90, 55),
            ("F1", "2",   90, 55), ("F2", "3",  50, 20),
            ("F7", "15",  80, 50), ("F8", "4",  90, 55),
            ("F9",  "3",  50, 30), ("F9",  "6",  50, 30),
            ("F9",  "10", 50, 30), ("F10", "1",  60, 35),
            ("F10", "12", 60, 35), ("F10", "8",  70, 40),
        ]

        for f, t, ns, rs in speeds:
            for edge in [self._get_edge(f, t), self._get_edge(t, f)]:
                if edge:
                    edge.set_speed_limits(ns, rs)

    # ------------------------------------------------------------------
    # Step 6 — Maintenance Data
    # ------------------------------------------------------------------

    def _load_maintenance_data(self) -> None:
        # Format: (from, to, cost Million EGP, priority 1-5)
        maintenance = [
            ("1",  "3",  12.5, 3), ("1",  "8",  18.0, 3),
            ("2",  "3",   8.5, 3), ("2",  "5",   6.0, 2),
            ("3",  "5",   9.0, 4), ("3",  "6",   5.0, 2),
            ("3",  "9",  14.0, 4), ("3",  "10", 10.5, 3),
            ("4",  "2",  20.0, 3), ("4",  "14",  4.0, 2),
            ("5",  "11", 11.0, 3), ("6",  "9",   4.0, 2),
            ("7",  "8",  30.0, 4), ("7",  "15", 12.0, 3),
            ("8",  "10",  6.0, 3), ("8",  "12", 35.0, 5),
            ("9",  "10",  4.0, 2), ("10", "11", 18.0, 3),
            ("11", "F2",  7.0, 3), ("12", "1",  22.0, 4),
            ("13", "4",  50.0, 4), ("14", "13", 40.0, 3),
            ("15", "7",  12.0, 3), ("F1", "5",   9.0, 4),
            ("F1", "2",  11.0, 4), ("F2", "3",   4.0, 5),
            ("F7", "15", 10.0, 3), ("F8", "4",   7.0, 3),
            ("F9",  "3",  2.0, 5), ("F9",  "6",  3.5, 5),
            ("F9",  "10", 4.0, 5), ("F10", "1",  2.5, 5),
            ("F10", "12", 5.0, 5), ("F10", "8",  7.0, 5),
        ]

        for f, t, cost, priority in maintenance:
            for edge in [self._get_edge(f, t), self._get_edge(t, f)]:
                if edge:
                    edge.set_maintenance_data(cost, priority)

    # ==================================================================
    # GRAPH OPERATIONS
    # ==================================================================

    def _add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def _add_edge(
        self,
        from_id    : str,
        to_id      : str,
        distance   : float,
        capacity   : int,
        condition  : int,
        is_existing: bool = True,
    ) -> None:
        """
        Adds a bidirectional road. Two Edge objects are created —
        one in each direction — and registered in the adjacency list
        and the internal edge map.
        """
        a = self.nodes[from_id]
        b = self.nodes[to_id]

        forward  = Edge(a, b, distance, capacity, condition, is_existing)
        backward = Edge(b, a, distance, capacity, condition, is_existing)

        self.adjacency_list[from_id].append(forward)
        self.adjacency_list[to_id].append(backward)

        self.existing_edges.append(forward)

        self._edge_map[(from_id, to_id)] = forward
        self._edge_map[(to_id, from_id)] = backward

    def _get_edge(self, from_id: str, to_id: str):
        """Returns the Edge between two nodes, or None if it does not exist."""
        return self._edge_map.get((from_id, to_id))

    # ------------------------------------------------------------------
    # Public Query Interface
    # ------------------------------------------------------------------

    def get_neighbors(self, node_id: str) -> list:
        """Returns all outgoing edges from the given node."""
        return self.adjacency_list.get(node_id, [])

    def get_node(self, node_id: str) -> Node:
        """Returns the Node object for the given ID."""
        return self.nodes.get(node_id)

    def get_edge(self, from_id: str, to_id: str):
        """Public access to a specific road segment."""
        return self._get_edge(from_id, to_id)

    def get_medical_nodes(self) -> list:
        """Returns all hospital and healthcare facility nodes."""
        return [n for n in self.nodes.values() if n.is_medical()]

    def get_critical_nodes(self) -> list:
        """Returns all nodes classified as critical infrastructure."""
        return [n for n in self.nodes.values() if n.is_critical()]

    def get_nodes_by_type(self, node_type: NodeType) -> list:
        """Returns all nodes matching the given NodeType."""
        return [n for n in self.nodes.values() if n.type == node_type]

    def total_population(self) -> int:
        """Returns the sum of population across all residential nodes."""
        return sum(n.population for n in self.nodes.values())

    def remove_edge(self, from_id: str, to_id: str) -> bool:
        """
        Temporarily removes a road from the graph.
        Used in Scenario C (road closure / alternate route simulation).
        Returns True if the edge was found and removed.
        """
        removed = False
        for direction in [(from_id, to_id), (to_id, from_id)]:
            f, t = direction
            if (f, t) in self._edge_map:
                edge = self._edge_map.pop((f, t))
                if edge in self.adjacency_list[f]:
                    self.adjacency_list[f].remove(edge)
                    removed = True
        return removed

    def restore_edge(self, from_id: str, to_id: str) -> None:
        """
        Restores a previously removed road.
        Rebuilds both directions from the existing_edges list.
        """
        for edge in self.existing_edges:
            if edge.from_node.id == from_id and edge.to_node.id == to_id:
                self.adjacency_list[from_id].append(edge)
                self._edge_map[(from_id, to_id)] = edge
            elif edge.from_node.id == to_id and edge.to_node.id == from_id:
                self.adjacency_list[to_id].append(edge)
                self._edge_map[(to_id, from_id)] = edge

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Returns a structured summary of the graph for reporting."""
        return {
            "total_nodes"       : len(self.nodes),
            "total_edges"       : len(self.existing_edges),
            "potential_edges"   : len(self.potential_edges),
            "medical_nodes"     : len(self.get_medical_nodes()),
            "critical_nodes"    : len(self.get_critical_nodes()),
            "total_population"  : self.total_population(),
        }

    def print_summary(self) -> None:
        s = self.summary()
        width = 52
        print()
        print("=" * width)
        print("  Cairo Transportation Network  —  Graph Summary")
        print("=" * width)
        print(f"  {'Nodes (locations)':<30} {s['total_nodes']:>6}")
        print(f"  {'Edges (existing roads)':<30} {s['total_edges']:>6}")
        print(f"  {'Candidate new roads':<30} {s['potential_edges']:>6}")
        print(f"  {'Medical facilities':<30} {s['medical_nodes']:>6}")
        print(f"  {'Critical infrastructure nodes':<30} {s['critical_nodes']:>6}")
        print(f"  {'Total network population':<30} {s['total_population']:>6,}")
        print("=" * width)
        print()
