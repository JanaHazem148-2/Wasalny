# Wasalny
### Cairo Transportation Management System


---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Setup and Usage](#setup-and-usage)
4. [Data Overview](#data-overview)
5. [Algorithm Design](#algorithm-design)
6. [Complexity Analysis](#complexity-analysis)
7. [Key Design Decisions](#key-design-decisions)
8. [Test Cases](#test-cases)
9. [Team Task Division](#team-task-division)
10. [Important Notes](#important-notes)

---

## Project Overview

This system implements a transportation management solution for the Greater Cairo metropolitan area. It integrates multiple algorithmic techniques covered in CSE112, including graph algorithms, dynamic programming, greedy approaches, and complexity analysis, applied to a real-world urban transportation dataset.

The system is built in pure Python with no external dependencies, structured around a core graph model and a set of independent algorithm modules.

---

## Project Structure

```
cairo_transport/
│
├── main.py                    # Entry point — runs and demonstrates all algorithms
│
├── models/                    # Core data model (Task 1) — DO NOT MODIFY
│   ├── node.py                # Node class: represents a location (district or facility)
│   ├── edge.py                # Edge class: represents a road with time-dependent weights
│   └── graph.py               # Graph class: full Cairo network with all data loaded
│
└── algorithms/                # Algorithm implementations
    ├── mst.py                 # Kruskal's MST with critical facility constraints (Task 2)
    ├── shortest_path.py       # Dijkstra + A* with time-dependent traffic (Task 3 and 4)
    ├── dp.py                  # Dynamic programming for scheduling and maintenance (Task 5)
    └── emergency_response.py  # A* routing + Greedy signal preemption (Task 4)
```

---

## Setup and Usage

### Requirements

Python 3.8 or higher. No external libraries required.

### Running the System

```bash
python main.py
```

### Using Individual Algorithms

```python
from models.graph import Graph
from models.edge import TimePeriod
from algorithms.mst import MST
from algorithms.shortest_path import ShortestPath

# Load the Cairo network
graph = Graph()

# MST: Design optimal road network
mst    = MST(graph)
result = mst.kruskal(use_potential=True)
mst.print_results(result)

# Dijkstra: Standard route planning
sp     = ShortestPath(graph)
result = sp.dijkstra("1", "13", period=TimePeriod.MORNING_PEAK)
sp.print_results(result)

# A*: Emergency vehicle routing
result = sp.a_star("7", "F9", period=TimePeriod.MORNING_PEAK)
sp.print_results(result)
```

---

## Data Overview

### Nodes — 25 Total

| Category | Count | Examples |
|----------|-------|---------|
| Residential and Mixed Districts | 15 | Maadi, Nasr City, Giza, Heliopolis |
| Medical Facilities | 2 | Qasr El Aini Hospital (F9), Maadi Military Hospital (F10) |
| Transport Hubs | 2 | Cairo Airport (F1), Ramses Station (F2) |
| Other Facilities | 6 | Universities, Smart Village, Cairo Festival City |

### Edges

| Category | Count | Details |
|----------|-------|---------|
| Existing Roads | 34 | Distance, capacity, condition, traffic flow per time period |
| Potential New Roads | 15 | Distance, capacity, construction cost in million EGP |

### Time Periods

| Period | Hours | Traffic Condition |
|--------|-------|------------------|
| Morning Peak | 07:00 - 09:00 | Heavy congestion |
| Afternoon | 09:00 - 16:00 | Normal flow |
| Evening Peak | 16:00 - 19:00 | Heavy congestion |
| Night | 19:00 - 07:00 | Light traffic |

### Additional Data Added to Original Dataset

The following data was added to support all required algorithms.

**Hospital road connections.** F9 and F10 were isolated in the original dataset with no connecting roads. Six roads were added to integrate them into the network, which is required for the A* emergency routing algorithm to function.

**Speed limits.** Normal and rush-hour speeds were added for every road. These are necessary to compute accurate travel times in Dijkstra and A*, since the original dataset only provides distances and not time.

**Traffic signal data.** Ten major intersections were defined with signal cycle times and emergency preemption configuration, required for the Greedy signal optimization algorithm.

**Maintenance data.** A maintenance cost and priority level were added per road, required for the Dynamic Programming resource allocation problem.

**Transportation schedules.** Bus and metro schedules including frequency per time period and vehicle capacity were added, required for the DP scheduling problem.

---

## Algorithm Design

### Task 2 — Minimum Spanning Tree (mst.py)

**Algorithm:** Kruskal's algorithm with a critical facility constraint modification.

Standard Kruskal's is modified to run in two phases. In the first phase, all edges connected to critical nodes (hospitals, airport, government centers, transit hubs) are processed first using Union-Find, ensuring these facilities always have guaranteed network connectivity. In the second phase, standard Kruskal's continues on the remaining edges to complete the spanning tree at minimum total cost.

```
Input  : All existing roads, with option to include potential new roads
Output : Minimum cost road network that connects all nodes in Cairo
```

The key modification over standard Kruskal's is that critical facility connectivity is guaranteed before cost optimization begins. Standard MST does not make this guarantee.

---

### Task 3 — Dijkstra with Time-Dependent Traffic (shortest_path.py)

**Algorithm:** Dijkstra's algorithm with dynamic edge weights.

Edge weights are not fixed values. Each call to `get_weight(period)` computes the travel time in minutes based on the road's distance, its speed limit for the given time period, and a congestion multiplier derived from the traffic flow-to-capacity ratio.

```
Congestion ratio >= 0.90  ->  travel time multiplied by 3.0  (severe congestion)
Congestion ratio >= 0.75  ->  travel time multiplied by 1.8  (moderate congestion)
Congestion ratio <  0.75  ->  travel time multiplied by 1.0  (clear road)
```

```
Input  : source node ID, destination node ID, TimePeriod
Output : shortest path, total travel time, roads taken, and congestion status per road
```

---

### Task 4 — A* Emergency Routing and Greedy Signal Optimization

**A* Algorithm (shortest_path.py)**

A* extends Dijkstra by adding a heuristic function that guides the search toward the destination, avoiding unnecessary exploration. The heuristic used is the aerial (Euclidean) distance between two nodes computed from their real GPS coordinates. This heuristic is admissible — it never overestimates the actual travel distance — which guarantees A* returns the optimal path.

```
f(n) = g(n) + h(n)

g(n) = actual travel time from source to node n
h(n) = aerial distance from node n to the destination
```

A* is significantly faster than Dijkstra for emergency routing because it focuses the search toward the destination rather than expanding in all directions.

**Greedy Signal Optimization (greedy.py)**

At each intersection, the greedy algorithm allocates green signal time proportionally to the incoming traffic volume on each connected road, prioritizing the most congested direction at each step. For emergency vehicles, a preemption override immediately clears the intersection and holds the green signal regardless of the current cycle state.

---

### Task 5 — Dynamic Programming (dp.py)

**DP Scheduling — Bus and Metro Allocation**

The scheduling problem is modeled as a variant of the weighted job scheduling problem. Given the number of available vehicles per time period and the passenger demand between each origin-destination pair, the DP table assigns vehicles to routes to maximize the total number of passengers served across the network.

**DP Maintenance — Road Resource Allocation**

The maintenance problem is modeled as a 0/1 Knapsack problem. Given a total annual maintenance budget of 200 million EGP, the algorithm selects which subset of roads to maintain in order to maximize the total priority score, where priority is determined by road condition rating and proximity to critical facilities.

**Memoization**

Route planning computations use memoization to cache previously computed shortest paths. When the same source-destination pair is queried more than once under the same time period, the cached result is returned immediately without re-running the algorithm.

---

## Complexity Analysis

| Component | Time Complexity | Space Complexity |
|-----------|----------------|-----------------|
| Graph construction | O(V + E) | O(V + E) |
| Kruskal's MST | O(E log E) | O(V) |
| Union-Find per operation | O(alpha(V)) | O(V) |
| Dijkstra with binary heap | O((V + E) log V) | O(V) |
| A* | O((V + E) log V) | O(V) |
| DP Scheduling | O(n x W) | O(n x W) |
| DP Maintenance (Knapsack) | O(n x B) | O(n x B) |
| Greedy Signal Optimization | O(E log E) | O(E) |

V = number of nodes, E = number of edges, n = number of routes or roads,
W = demand range, B = budget granularity, alpha = inverse Ackermann function (effectively constant).

---

## Key Design Decisions

**Undirected Graph.**
All roads are represented as bidirectional. The dataset does not specify direction, and Cairo's road network is predominantly two-way.

**Adjacency List over Adjacency Matrix.**
With 25 nodes and 34 edges the graph is sparse. An adjacency list requires O(V + E) space compared to O(V^2) for a matrix, and provides faster neighbor traversal which Dijkstra and A* rely on heavily.

**On-Demand Weight Computation.**
Edge weights are computed at query time rather than stored statically. This allows the same graph instance to answer queries for any time period without rebuilding or copying any data structure.

**Two-Phase Kruskal's.**
Standard Kruskal's optimizes for minimum total cost only and makes no guarantee about which nodes are connected first. The two-phase modification ensures critical infrastructure is always reachable, which is a hard requirement for any transportation network serving hospitals and emergency services.

**Aerial Distance as A* Heuristic.**
Using actual GPS coordinates to compute the heuristic ensures it remains admissible under all conditions. An inadmissible heuristic would cause A* to return suboptimal paths, which is unacceptable for emergency routing.

---

## Test Cases

```python
from models.graph import Graph
from models.edge import TimePeriod
from algorithms.mst import MST
from algorithms.shortest_path import ShortestPath

graph = Graph()
sp    = ShortestPath(graph)
mst   = MST(graph)

# Test 1: Rush hour vs. night travel time comparison
morning = sp.dijkstra("4", "3", TimePeriod.MORNING_PEAK)
night   = sp.dijkstra("4", "3", TimePeriod.NIGHT)
print(f"New Cairo to Downtown  |  Morning: {morning['total_time']:.1f} min  |  Night: {night['total_time']:.1f} min")

# Test 2: Emergency vehicle routing to nearest hospital
emergency = sp.a_star("7", "F9", TimePeriod.MORNING_PEAK)
print(f"6th October to Qasr El Aini  |  Response Time: {emergency['total_time']:.1f} min")

# Test 3: MST with potential new roads included
result = mst.kruskal(use_potential=True)
print(f"MST Total Distance      : {result['total_distance']} km")
print(f"MST Construction Cost   : {result['total_cost']} M EGP")
print(f"Critical Nodes Covered  : {result['critical_covered']} / {result['total_critical']}")

# Test 4: Route with and without a blocked road
# Remove an edge temporarily, run Dijkstra, then restore it to simulate an accident scenario
```

---

## Team Task Division

| Task | Algorithm | File | Status |
|------|-----------|------|--------|
| Task 1 | Graph Setup | `models/` | Complete |
| Task 2 | Kruskal's MST | `algorithms/mst.py` | Member 1 |
| Task 3 | Dijkstra + Time-Dependent Weights | `algorithms/shortest_path.py` | Member 2 |
| Task 4 | A* + Greedy Signal Optimization | `algorithms/shortest_path.py` + `emergency_response.py` | Member 3 |
| Task 5 | Dynamic Programming | `algorithms/dp.py` | Member 4 |
| Task 6 | Integration + Technical Report | `main.py` + all files | All members |

---

## Important Notes

- Do not modify any file inside the `models/` directory. The graph data model is finalized and all algorithms depend on its current interface.
- Every algorithm function must return a dictionary containing the result and all relevant metadata (path, cost, time, congestion status, etc.) so that `main.py` can display and compare outputs in a consistent format.
- All algorithms that involve routing must accept a `TimePeriod` parameter and pass it through to the edge weight computation.
- Implement and test each algorithm in isolation before integrating it into `main.py`.
- The `Graph` class in `graph.py` loads all data internally on initialization. No external files are read at runtime.

---

*CSE112 — Design and Analysis of Algorithms*
*Alamein International University — Faculty of Computer Science and Engineering*
