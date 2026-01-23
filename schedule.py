# schedule.py

class Schedule:
    def __init__(self):
        self.sessions = []
        self.unscheduled_courses = []

    def add_session(self, course, room, timeslot):
        self.sessions.append({
            "course": course,
            "room": room,
            "timeslot": timeslot
        })
        room.reserve(timeslot)

    def teacher_available(self, teacher, timeslot):
        for s in self.sessions:
            if s["course"].teacher == teacher:
                if s["timeslot"].overlaps(timeslot):
                    return False
        return True
    def group_available(self, group, timeslot):
        for s in self.sessions:
            if s["course"].group == group:
                if s["timeslot"].overlaps(timeslot):
                 return False
        return True

    def room_available(self, room, timeslot):
        return room.is_available(timeslot)
    def get_statistics(self, rooms, all_timeslots):
        total_slots = len(rooms) * len(all_timeslots)
        occupied_slots = len(self.sessions)
        occupancy_rate = (occupied_slots / total_slots) * 100
        print(f"Current Occupancy Rate: {occupancy_rate:.2f}%")

    def find_best_room(self, course, rooms, timeslot):
        suitable_rooms = []

        for room in rooms:
            if (
                room.capacity >= course.students_count and
                all(eq in room.equipment for eq in course.equipment_needed) and
                self.room_available(room, timeslot)
            ):
                suitable_rooms.append(room)

        if not suitable_rooms:
            return None

        # INTELLIGENT CHOICE: smallest suitable room
        suitable_rooms.sort(key=lambda r: r.capacity)
        return suitable_rooms[0]
    
    def generate(self, courses, rooms, timeslots):
        """
        Intelligent timetable generation
        """
        courses.sort(key=lambda x: x.students_count, reverse=True) #Ensures that large classes are handled first
        self.sessions = []
        self.unscheduled_courses = []
        for room in rooms:
            room.bookings = []
        for course in courses:
            scheduled = False

            for timeslot in timeslots:
                if not self.teacher_available(course.teacher, timeslot):
                    continue
                if not self.group_available(course.group, timeslot): continue
                best_room = self.find_best_room(course, rooms, timeslot)

                if best_room:
                    self.add_session(course, best_room, timeslot)
                    scheduled = True
                    break

            if not scheduled:
                self.unscheduled_courses.append(course)

    def display_for_teacher(self, teacher):
        print(f"\nTimetable for {teacher.name}")
        for s in self.sessions:
            if s["course"].teacher == teacher:
                print(f"{s['timeslot']} | {s['course']} | {s['room']}")

    def display_for_group(self, group):
        print(f"\nTimetable for group {group}")
        for s in self.sessions:
            if s["course"].group == group:
                print(f"{s['timeslot']} | {s['course']} | {s['room']}")
