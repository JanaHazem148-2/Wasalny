"""
node.py
-------
Defines the Node class used to represent any physical location
in the Greater Cairo transportation network  whether that is a
residential district, a hospital, an airport, or a metro station.

Each node carries geographic coordinates (real GPS data), a
population count, and a type classification that drives
priority decisions in the MST and emergency routing algorithms.


"""

import math
from enum import Enum


# ---------------------------------------------------------------------------
# NodeType Enum
# ---------------------------------------------------------------------------

class NodeType(Enum):
    """
    Classifies every node in the network by its real-world function.

    This classification is not cosmetic — it directly controls algorithm
    behavior. Medical and critical types receive priority treatment in
    Kruskal's MST (guaranteed connectivity) and A* (preferred destinations
    in emergency routing).
    """
    RESIDENTIAL = "Residential"    # Purely residential district
    BUSINESS    = "Business"       # Commercial or business-dominated area
    MIXED       = "Mixed"          # Residential + commercial mix
    INDUSTRIAL  = "Industrial"     # Industrial or manufacturing zone
    GOVERNMENT  = "Government"     # Administrative / government center
    MEDICAL     = "Medical"        # Hospital or healthcare facility  ← A* priority
    AIRPORT     = "Airport"        # International or domestic airport
    TRANSIT_HUB = "Transit Hub"    # Major railway or bus terminus
    EDUCATION   = "Education"      # University or academic institution
    TOURISM     = "Tourism"        # Museum, landmark, or tourist site
    SPORTS      = "Sports"         # Stadium or sports complex
    COMMERCIAL  = "Commercial"     # Shopping center or commercial hub

    def is_critical(self) -> bool:
        """
        Returns True if this type qualifies as a critical infrastructure
        node — meaning it must be connected first during MST construction
        and reachable at all times for emergency services.
        """
        return self in {
            NodeType.MEDICAL,
            NodeType.AIRPORT,
            NodeType.TRANSIT_HUB,
            NodeType.GOVERNMENT,
        }


# ---------------------------------------------------------------------------
# Node Class
# ---------------------------------------------------------------------------

class Node:
    """
    Represents a single location in Cairo's transportation network.

    Attributes
    ----------
    node_id    : Unique string identifier  (e.g. "3", "F9", "F1")
    name       : Human-readable place name (e.g. "Downtown Cairo")
    population : Resident or user count — 0 for non-residential facilities
    node_type  : NodeType enum value
    x          : Longitude coordinate (used for A* heuristic distance)
    y          : Latitude  coordinate (used for A* heuristic distance)
    """

    def __init__(
        self,
        node_id    : str,
        name       : str,
        population : int,
        node_type  : NodeType,
        x          : float,
        y          : float,
    ):
        self.id         = node_id
        self.name       = name
        self.population = population
        self.type       = node_type
        self.x          = x
        self.y          = y

    # ------------------------------------------------------------------
    # Geographic Calculations
    # ------------------------------------------------------------------

    def haversine_distance(self, other: "Node") -> float:
        """
        Computes the straight-line (aerial) distance between this node
        and another in kilometers using the Haversine formula.

        This is the heuristic function h(n) used by the A* algorithm.
        It is admissible by definition — aerial distance never exceeds
        actual road distance — which guarantees A* returns an optimal path.

        Parameters
        ----------
        other : The destination Node

        Returns
        -------
        float : Aerial distance in kilometers
        """
        R  = 6371.0  # Earth's mean radius in km

        lat1 = math.radians(self.y)
        lat2 = math.radians(other.y)
        dlat = math.radians(other.y - self.y)
        dlon = math.radians(other.x - self.x)

        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)

        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ------------------------------------------------------------------
    # Classification Helpers
    # ------------------------------------------------------------------

    def is_medical(self) -> bool:
        """True if this node is a hospital or healthcare facility."""
        return self.type == NodeType.MEDICAL

    def is_critical(self) -> bool:
        """
        True if this node is classified as critical infrastructure.
        Critical nodes receive guaranteed connectivity in the MST phase
        and are preferred endpoints in emergency routing queries.
        """
        return self.type.is_critical()

    def is_residential(self) -> bool:
        """True if this node primarily serves a residential population."""
        return self.type in {NodeType.RESIDENTIAL, NodeType.MIXED}

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        pop = f", pop={self.population:,}" if self.population > 0 else ""
        return f"Node({self.id} | {self.name} | {self.type.value}{pop})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Node) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
