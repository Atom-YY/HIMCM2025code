from dataclasses import dataclass
from typing import List, Tuple, Optional
from math import hypot

from rooms import RoomNode, ExitNode

Point = Tuple[float, float]


@dataclass
class ResponderState:
    # state is one of: "idle", "moving", "clearing", "evacuating_unabled"
    state: str
    time_remaining: float
    position: Point
    target_room: Optional[RoomNode] = None
    target_door: Optional[Point] = None


def _distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def _choose_nearest_room(
    responder: ResponderState,
    rooms_left: List[RoomNode],
    speed: float,
):
    """
    Pick the nearest uncleared room (and door) for this responder.

    Returns (room, door_position, travel_time).
    If there are no rooms_left, returns (None, None, 0.0).
    """
    if not rooms_left:
        return None, None, 0.0

    best_room: Optional[RoomNode] = None
    best_door: Optional[Point] = None
    best_dist: float = float("inf")

    for room in rooms_left:
        # If no explicit doors, use the room center as a stand-in.
        door_positions = room.get_door_positions() or [room.shape.center]
        for d in door_positions:
            dist = _distance(responder.position, d)
            if dist < best_dist:
                best_dist = dist
                best_room = room
                best_door = d

    if best_room is None:
        return None, None, 0.0

    travel_time = best_dist / speed if speed > 0 else 0.0
    return best_room, best_door, travel_time


def _nearest_exit(source: Point, exits: List[ExitNode]):
    """
    Return (exit_node, distance) for the nearest exit to 'source'.
    """
    if not exits:
        return None, 0.0

    best_exit: Optional[ExitNode] = None
    best_dist: float = float("inf")

    for ex in exits:
        pos = ex.position()
        dist = _distance(source, pos)
        if dist < best_dist:
            best_dist = dist
            best_exit = ex

    return best_exit, best_dist


def _unabled_evac_time(
    num_unabled: int,
    door_position: Point,
    exits: List[ExitNode],
    responder_speed: float,
) -> Tuple[float, Optional[Point]]:
    """
    Compute total extra time to evacuate all unabled occupants from this room
    to the nearest exit, assuming:

      - One unabled person per trip
      - Carrying speed = responder_speed / 2
      - Normal speed when not carrying
      - For all but the last evac, responder returns to the door
      - After the last evac, responder stays at the exit

    Returns (extra_time, final_position_of_responder)
    """
    if num_unabled <= 0 or responder_speed <= 0 or not exits:
        return 0.0, door_position

    exit_node, dist = _nearest_exit(door_position, exits)
    if exit_node is None:
        return 0.0, door_position

    d = dist
    s = responder_speed

    # Carrying speed is half
    # Time to carry one unabled from door to exit: d / (s/2) = 2d / s
    # Time to return empty: d / s

    if num_unabled == 1:
        extra_time = 2 * d / s
    else:
        # (U - 1) full cycles (carry + return) + final carry
        # cycle = 2d/s (carry) + d/s (return) = 3d/s
        # total = (U - 1) * 3d/s + 2d/s = (3U - 1) * d/s
        extra_time = (3 * num_unabled - 1) * d / s

    final_position = exit_node.position()
    return extra_time, final_position


def find_fastest_evacuation(
    n_responders: int,
    rooms: List[RoomNode],
    exits: List[ExitNode],
    responder_speed: float = 1.0,
    start_position: Point = (0.0, 0.0),
) -> float:
    if responder_speed <= 0:
        raise ValueError("responder_speed must be > 0")

    remaining_rooms: List[RoomNode] = list(rooms)

    responders: List[ResponderState] = [
        ResponderState(
            state="idle",
            time_remaining=0.0,
            position=start_position,
            target_room=None,
            target_door=None,
        )
        for _ in range(n_responders)
    ]

    current_time: float = 0.0

    while remaining_rooms or any(r.state != "idle" for r in responders):
        # 1) Assign idle responders to new rooms (if any left).
        already_taken: List[RoomNode] = [
            r.target_room
            for r in responders
            if r.state in ("moving", "clearing", "evacuating_unabled")
            and r.target_room is not None
        ]  # type: ignore[arg-type]

        available_rooms: List[RoomNode] = [
            room for room in remaining_rooms if room not in already_taken
        ]

        for r in responders:
            if r.state == "idle" and available_rooms:
                room, door, travel_time = _choose_nearest_room(
                    r, available_rooms, responder_speed
                )
                if room is None:
                    continue

                r.state = "moving"
                r.target_room = room
                r.target_door = door
                r.time_remaining = travel_time

                # Mark this room as taken so we don't give it to another responder
                available_rooms = [rm for rm in available_rooms if rm is not room]

        # 2) Find the next event (who finishes first?)
        active = [
            r for r in responders
            if r.state in ("moving", "clearing", "evacuating_unabled")
        ]
        if not active:
            # Nobody is doing anything but there are still rooms left:
            # in this simple model that means they're unreachable.
            break

        dt = min(r.time_remaining for r in active)
        current_time += dt

        # 3) Advance all active responders by dt
        for r in active:
            r.time_remaining -= dt

        # 4) Process responders who just finished an action
        for r in responders:
            if r.time_remaining > 1e-9:
                continue  # still busy

            elif r.state == "moving":
                # Arrived at the target room's door: start clearing
                r.position = r.target_door  # type: ignore[arg-type]
                print(f"Responder arrived at room {r.target_room.id} door.")
                r.state = "clearing"
                r.time_remaining = r.target_room.clearance_time  # type: ignore[union-attr]

            elif r.state == "clearing":
                # Just finished clearing the room itself
                room = r.target_room
                if room is None:
                    # Shouldn't happen, but just be safe
                    r.state = "idle"
                    continue

                num_unabled = room.occupants.unabled

                if num_unabled > 0 and exits:
                    # Compute extra time to evacuate all unabled to the nearest exit
                    extra_time, final_pos = _unabled_evac_time(
                        num_unabled=num_unabled,
                        door_position=r.position,
                        exits=exits,
                        responder_speed=responder_speed,
                    )
                    # Mark them as evacuated so we don't do it again
                    room.occupants.unabled = 0

                    r.position = final_pos
                    r.state = "evacuating_unabled"
                    r.time_remaining = extra_time
                else:
                    # No unabled or no exits configured: room is now done
                    if room in remaining_rooms:
                        remaining_rooms.remove(room)
                    r.state = "idle"
                    r.time_remaining = 0.0
                    r.target_room = None
                    r.target_door = None

            elif r.state == "evacuating_unabled":
                # Finished all trips for unabled occupants in this room
                room = r.target_room
                if room in remaining_rooms:
                    remaining_rooms.remove(room)  # type: ignore[arg-type]
                r.state = "idle"
                r.time_remaining = 0.0
                r.target_room = None
                r.target_door = None

    return current_time
