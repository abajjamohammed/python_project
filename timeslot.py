# timeslot.py

class TimeSlot:
    def __init__(self, day, start, end):
        self.day = day
        self.start = start
        self.end = end

    def overlaps(self, other):
        return (
            self.day == other.day and
            not (self.end <= other.start or self.start >= other.end)
        )

    def __str__(self):
        return f"{self.day} {self.start}:00 - {self.end}:00"
