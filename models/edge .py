"""
edge.py
-------
Defines the Edge class, which represents a road segment connecting
two nodes in Cairo's transportation network.

The most important responsibility of this class is time-dependent
weight computation. An edge does not have a single fixed cost —
its effective travel time changes across four daily periods based
on measured traffic flow and road capacity. This is what allows
Dijkstra and A* to model real Cairo traffic rather than assuming
a static road network.

The congestion model used here mirrors the BPR (Bureau of Public Roads)
function commonly used in transportation engineering, simplified to
three discrete congestion tiers for clarity and efficiency.

Author : Cairo Transport System — CSE112
"""

from enum import Enum


# ---------------------------------------------------------------------------
# TimePeriod Enum
# ---------------------------------------------------------------------------

class TimePeriod(Enum):
    """
    Represents the four daily traffic periods defined in the dataset.

    Each period carries distinct flow patterns across the road network,
    which directly affects edge weights in Dijkstra and A*.

    Time windows (24-hour):
        MORNING_PEAK  07:00 – 09:00   (rush hour inbound)
        AFTERNOON     09:00 – 16:00   (normal flow)
        EVENING_PEAK  16:00 – 19:00   (rush hour outbound)
        NIGHT         19:00 – 07:00   (light traffic)
    """
    MORNING_PEAK = "Morning Peak"
    AFTERNOON    = "Afternoon"
    EVENING_PEAK = "Evening Peak"
    NIGHT        = "Night"

    def is_peak(self) -> bool:
        """Returns True during rush hours — used to select speed limits."""
        return self in {TimePeriod.MORNING_PEAK, TimePeriod.EVENING_PEAK}

    def label(self) -> str:
        windows = {
            TimePeriod.MORNING_PEAK : "07:00 – 09:00",
            TimePeriod.AFTERNOON    : "09:00 – 16:00",
            TimePeriod.EVENING_PEAK : "16:00 – 19:00",
            TimePeriod.NIGHT        : "19:00 – 07:00",
        }
        return f"{self.value}  ({windows[self]})"


# ---------------------------------------------------------------------------
# Congestion Thresholds
# ---------------------------------------------------------------------------

# These thresholds define how the flow/capacity ratio maps to a time penalty.
# Based on the BPR congestion model, simplified to three tiers:
#   ratio >= 0.90  →  severe   (x3.0)  road is effectively gridlocked
#   ratio >= 0.75  →  moderate (x1.8)  noticeable slowdown
#   ratio <  0.75  →  clear    (x1.0)  free-flowing traffic

SEVERE_CONGESTION_THRESHOLD   = 0.90
MODERATE_CONGESTION_THRESHOLD = 0.75

SEVERE_MULTIPLIER   = 3.0
MODERATE_MULTIPLIER = 1.8
CLEAR_MULTIPLIER    = 1.0


# ---------------------------------------------------------------------------
# Edge Class
# ---------------------------------------------------------------------------

class Edge:
    """
    Represents a directed road segment from one node to another.

    Since all roads in Cairo's dataset are bidirectional, the Graph class
    creates two Edge objects per road (forward and backward), each carrying
    the same data but with from_node and to_node swapped.

    Parameters
    ----------
    from_node         : Origin Node
    to_node           : Destination Node
    distance          : Road length in kilometers
    capacity          : Maximum flow in vehicles per hour
    condition         : Road surface quality from 1 (poor) to 10 (perfect)
    is_existing       : True for current roads, False for potential new ones
    construction_cost : Capital cost in million EGP (for potential roads only)
    """

    def __init__(
        self,
        from_node,
        to_node,
        distance          : float,
        capacity          : int,
        condition         : int,
        is_existing       : bool  = True,
        construction_cost : float = 0.0,
    ):
        self.from_node         = from_node
        self.to_node           = to_node
        self.distance          = distance
        self.capacity          = capacity
        self.condition         = condition
        self.is_existing       = is_existing
        self.construction_cost = construction_cost

        # Traffic flow per period — loaded after construction via set_traffic_flow()
        self._flow = {
            TimePeriod.MORNING_PEAK : 0,
            TimePeriod.AFTERNOON    : 0,
            TimePeriod.EVENING_PEAK : 0,
            TimePeriod.NIGHT        : 0,
        }

        # Speed limits — loaded after construction via set_speed_limits()
        self._normal_speed    = 60.0   # km/h  (default for unset roads)
        self._rush_hour_speed = 30.0   # km/h

        # Maintenance data — loaded after construction via set_maintenance_data()
        self.maintenance_cost = 0.0
        self.priority         = 1      # 1 (low) to 5 (critical)

    # ------------------------------------------------------------------
    # Core Weight Engine
    # ------------------------------------------------------------------

    def get_weight(self, period: TimePeriod) -> float:
        """
        Computes the effective travel time for this road segment in minutes,
        accounting for the current time period and observed congestion level.

        This is the value Dijkstra and A* use as the edge weight.

        Formula
        -------
          base_time     = (distance / speed) * 60
          congestion    = flow / capacity
          travel_time   = base_time * congestion_multiplier(congestion)

        Parameters
        ----------
        period : TimePeriod — the time window being queried

        Returns
        -------
        float : Travel time in minutes (always positive)
        """
        speed     = self._rush_hour_speed if period.is_peak() else self._normal_speed
        base_time = (self.distance / speed) * 60.0

        ratio = self._congestion_ratio(period)

        if ratio >= SEVERE_CONGESTION_THRESHOLD:
            return round(base_time * SEVERE_MULTIPLIER, 3)
        elif ratio >= MODERATE_CONGESTION_THRESHOLD:
            return round(base_time * MODERATE_MULTIPLIER, 3)
        else:
            return round(base_time * CLEAR_MULTIPLIER, 3)

    def get_mst_weight(self) -> float:
        """
        Weight used by Kruskal's MST algorithm.

        Rather than raw distance, this applies a condition penalty:
        a road in poor condition costs more to incorporate into the
        network because it will require immediate maintenance investment.

          mst_weight = distance * condition_penalty
          condition_penalty = (11 - condition) / 10

        A road with condition=10 (perfect) has penalty 0.1 → low weight.
        A road with condition=1  (failed)  has penalty 1.0 → high weight.
        """
        condition_penalty = (11 - self.condition) / 10.0
        return round(self.distance * condition_penalty, 4)

    # ------------------------------------------------------------------
    # Congestion Analysis
    # ------------------------------------------------------------------

    def congestion_ratio(self, period: TimePeriod) -> float:
        """Returns the flow-to-capacity ratio for the given period."""
        return self._congestion_ratio(period)

    def congestion_level(self, period: TimePeriod) -> str:
        """Returns a human-readable congestion label for the given period."""
        ratio = self._congestion_ratio(period)
        if ratio >= SEVERE_CONGESTION_THRESHOLD:
            return "SEVERE"
        elif ratio >= MODERATE_CONGESTION_THRESHOLD:
            return "MODERATE"
        else:
            return "CLEAR"

    def is_congested(self, period: TimePeriod) -> bool:
        """True if the road is at or above moderate congestion threshold."""
        return self._congestion_ratio(period) >= MODERATE_CONGESTION_THRESHOLD

    def _congestion_ratio(self, period: TimePeriod) -> float:
        if self.capacity == 0:
            return 0.0
        return self._flow[period] / self.capacity

    # ------------------------------------------------------------------
    # Setters — called by Graph during data loading
    # ------------------------------------------------------------------

    def set_traffic_flow(
        self,
        morning   : int,
        afternoon : int,
        evening   : int,
        night     : int,
    ) -> None:
        """Loads the four-period traffic flow measurements for this road."""
        self._flow[TimePeriod.MORNING_PEAK] = morning
        self._flow[TimePeriod.AFTERNOON]    = afternoon
        self._flow[TimePeriod.EVENING_PEAK] = evening
        self._flow[TimePeriod.NIGHT]        = night

    def set_speed_limits(self, normal: float, rush_hour: float) -> None:
        """Sets normal and rush-hour speed limits in km/h."""
        self._normal_speed    = normal
        self._rush_hour_speed = rush_hour

    def set_maintenance_data(self, cost: float, priority: int) -> None:
        """
        Attaches maintenance metadata used by the DP resource allocation
        algorithm to select which roads to repair within budget.
        """
        self.maintenance_cost = cost
        self.priority         = priority

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def flow(self, period: TimePeriod) -> int:
        """Returns the measured traffic flow for the given period."""
        return self._flow[period]

    def speed(self, period: TimePeriod) -> float:
        """Returns the applicable speed limit for the given period."""
        return self._rush_hour_speed if period.is_peak() else self._normal_speed

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        tag = "existing" if self.is_existing else f"potential | cost={self.construction_cost}M EGP"
        return (
            f"Edge({self.from_node.name} → {self.to_node.name} | "
            f"{self.distance} km | cond={self.condition}/10 | {tag})"
        )
