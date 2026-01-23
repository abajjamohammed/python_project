# rooms.py

class Room:
    def __init__(self, room_id, name, capacity, equipment):
        self.room_id = room_id
        self.name = name
        self.capacity = capacity
        self.equipment = equipment
        self.bookings = []

    def is_available(self, timeslot):
        for booking in self.bookings:
            if booking.overlaps(timeslot):
                return False
        return True

    def reserve(self, timeslot):
        self.bookings.append(timeslot)

    def __str__(self):
        return f"{self.name} (Capacity: {self.capacity})"
