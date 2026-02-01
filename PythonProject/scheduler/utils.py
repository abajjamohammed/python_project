from .models import ScheduledSession, TeacherUnavailability, Room, Course, Filiere, ReservationRequest

class TimetableAlgorithm:
    def __init__(self):
        # ✅ FIX: Use English Day names to match your Views
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        hours = [(8, 10), (10, 12), (14, 16), (16, 18)]
        self.timeslots = [(d, h[0], h[1]) for d in days for h in hours]

    def check_conflict(self, day, start, end, room=None, teacher=None, filiere=None, group=None):
        # 1. Base query: sessions overlapping this time
        conflicts = ScheduledSession.objects.filter(
            day=day,
            start_hour__lt=end,
            end_hour__gt=start
        )

        # 2. Check Room
        if room:
            if conflicts.filter(room=room).exists():
                return True
            # Check if room is reserved manually
            if ReservationRequest.objects.filter(room=room, day=day, start_hour__lt=end, end_hour__gt=start, status='APPROVED').exists():
                return True

        # 3. Check Teacher
        if teacher:
            if conflicts.filter(course__teacher=teacher).exists():
                return True
            if TeacherUnavailability.objects.filter(teacher=teacher, day=day, start_hour__lt=end, end_hour__gt=start).exists():
                return True

        # 4. Check Filière (Prevent stacking CMs)
        if filiere:
            # If ANY course for this Filière exists at this time, return True
            if conflicts.filter(course__filiere=filiere).exists():
                return True

        # 5. Check Group (For TDs)
        if group:
            if conflicts.filter(course__group=group).exists():
                return True
            # Also check if the Filière is busy with a CM
            if conflicts.filter(course__filiere=group.filiere, course__group__isnull=True).exists():
                return True

        return False

    def generate_timetable(self):
        ScheduledSession.objects.all().delete()
        
        # Prioritize Master courses, then Licence
        courses = Course.objects.all().order_by('-filiere__level', 'name')
        
        unscheduled = []

        for course in courses:
            placed = False
            
            # Smart Room Selection: Filter rooms big enough
            rooms = Room.objects.filter(capacity__gte=course.student_count).order_by('capacity')
            
            for day, start, end in self.timeslots:
                # CHECK CONFLICTS
                # We pass 'group' if it's a TD, or 'filiere' if it's a CM
                if self.check_conflict(day, start, end, 
                                     teacher=course.teacher, 
                                     filiere=course.filiere if course.session_type == 'CM' else None,
                                     group=course.group):
                    continue

                # FIND ROOM
                for room in rooms:
                    if not self.check_conflict(day, start, end, room=room):
                        ScheduledSession.objects.create(
                            course=course, room=room, day=day, 
                            start_hour=start, end_hour=end
                        )
                        placed = True
                        break
                if placed: break
            
            if not placed:
                unscheduled.append(course.name)
        
        return unscheduled