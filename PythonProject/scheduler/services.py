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