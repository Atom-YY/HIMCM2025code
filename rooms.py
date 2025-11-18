from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Literal, Optional
from math import ceil

OccupantType = Literal["adult", "child", "unabled"]
Point = Tuple[float, float]


@dataclass
class OccupantInfo:
    """Counts of each occupant type in a room."""
    adults: int = 0
    children: int = 0
    unabled: int = 0


@dataclass
class Door:
    """Simple door located at a point on the plane."""
    x: float
    y: float

    def position(self) -> Point:
        return (self.x, self.y)


@dataclass
class RoomGeometry:
    """
    Axis-aligned rectangular room on a 2D plane.

    Defined by bottom-left and top-right coordinates.
    """
    bottom_left: Point
    top_right: Point

    @property
    def x_min(self) -> float:
        return self.bottom_left[0]

    @property
    def y_min(self) -> float:
        return self.bottom_left[1]

    @property
    def x_max(self) -> float:
        return self.top_right[0]

    @property
    def y_max(self) -> float:
        return self.top_right[1]

    @property
    def width(self) -> float:
        return self.top_right[0] - self.bottom_left[0]

    @property
    def height(self) -> float:
        return self.top_right[1] - self.bottom_left[1]

    @property
    def center(self) -> Point:
        return (
            (self.bottom_left[0] + self.top_right[0]) / 2.0,
            (self.bottom_left[1] + self.top_right[1]) / 2.0,
        )

    def contains_point(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


# RectRoomShape is just an alias for RoomGeometry so the rest
# of your code can keep using "RectRoomShape".
class RectRoomShape(RoomGeometry):
    pass


@dataclass
class RoomNode:
    """
    Represents a room / node in the evacuation graph.

    Things attached:
      - base_clear_time: time to search/clear the room (not including carrying unabled)
      - occupants: counts of each type
      - shape: geometric obstacle in the plane
      - doors: responder stands at these points when 'in' the room
    """
    id: str
    base_clear_time: float
    occupants: OccupantInfo
    shape: RectRoomShape
    doors: List[Door] = field(default_factory=list)

    @property
    def clearance_time(self) -> float:
        """
        Clearance time for searching the room and moving mobile occupants.

        NOTE:
        - Unabled evac time is handled separately via exit trips
          in the simulation, so they are NOT counted here.
        """
        extra = 5 * self.occupants.children  # +5s per child
        return ceil(self.base_clear_time + extra)

    def add_door(self, door: Door) -> None:
        self.doors.append(door)

    def get_door_positions(self) -> List[Point]:
        return [d.position() for d in self.doors]


@dataclass
class ExitNode:
    """Exit node where unabled occupants must be brought."""
    id: str
    x: float
    y: float

    def position(self) -> Point:
        return (self.x, self.y)


def create_rect_room(
    room_id: str,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    base_clear_time: float,
    n_adults: int = 0,
    n_children: int = 0,
    n_unabled: int = 0,
    doors: Optional[List[Door]] = None,
) -> RoomNode:
    """Helper to quickly build a RoomNode."""
    occupants = OccupantInfo(
        adults=n_adults,
        children=n_children,
        unabled=n_unabled,
    )
    shape = RectRoomShape(bottom_left=(x_min, y_min), top_right=(x_max, y_max))
    room = RoomNode(
        id=room_id,
        base_clear_time=base_clear_time,
        occupants=occupants,
        shape=shape,
        doors=doors or [],
    )
    return room


def create_exit(exit_id: str, x: float, y: float) -> ExitNode:
    """Helper to quickly build an ExitNode."""
    return ExitNode(id=exit_id, x=x, y=y)