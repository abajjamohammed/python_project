# reservations.py

class ReservationRequest:
    def __init__(self, request_id, teacher, room, timeslot):
        self.request_id = request_id
        self.teacher = teacher
        self.room = room
        self.timeslot = timeslot
        self.status = "Pending"

    def approve(self):
        self.status = "Approved"
        self.room.reserve(self.timeslot)
        print("Reservation approved.")

    def reject(self):
        self.status = "Rejected"
        print("Reservation rejected.")
