from rooms import create_rect_room, create_exit, Door
from shitty_simulation import find_fastest_evacuation

# Rooms
room1 = create_rect_room("A", 0, 1, 3, 3, base_clear_time=15, n_unabled=2)
room1.add_door(Door(2, 1))

room2 = create_rect_room("D", 0, -3, 3, -1, base_clear_time=15, n_unabled=3)
room2.add_door(Door(2, -1))

room3 = create_rect_room("C", 3, 1, 6, 3, base_clear_time=15, n_unabled=4)
room3.add_door(Door(5, 1))

room4 = create_rect_room("B", 3, -3, 6, -1, base_clear_time=15, n_unabled=2)
room4.add_door(Door(5, -1))

room5 = create_rect_room("E", 6, 1, 9, 3, base_clear_time=15, n_unabled=1)
room5.add_door(Door(8, 1))

room6 = create_rect_room("F", 6, -3, 9, -1, base_clear_time=15, n_unabled=0)
room6.add_door(Door(8, -1))
# Exits
exit1 = create_exit("E1", 0, -2)
exit2 = create_exit("E2", 8, 1)

total_time = find_fastest_evacuation(
    n_responders=3,
    rooms=[room1, room2, room4, room3, room5, room6],
    exits=[exit1, exit2],
    responder_speed=1.0, #due to limitations of time, we were not able to implement all factors that affect speed
    start_position=(0.0, 0.0),
)

print("Total evacuation time:", total_time)