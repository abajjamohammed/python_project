# users.py

class User:
    """
    Base class for all users
    """
    def __init__(self, user_id, name, email):
        self.user_id = user_id
        self.name = name
        self.email = email

    def login(self):
        print(f"{self.name} has logged in.")

    def logout(self):
        print(f"{self.name} has logged out.")


class Administrator(User):
    """
    Administrator role: manages schedule, rooms, approvals
    """
    def __init__(self, user_id, name, email):
        super().__init__(user_id, name, email)

    def generate_timetable(self, schedule, courses, rooms, timeslots):
        """
        Generate timetable using intelligent algorithm
        """
        schedule.generate(courses, rooms, timeslots)
        print("Timetable generated successfully.")

    def approve_reservation(self, reservation):
        reservation.approve()

    def reject_reservation(self, reservation):
        reservation.reject()


class Teacher(User):
    """
    Teacher role: can view timetable, request rooms, declare unavailability
    """
    def __init__(self, user_id, name, email):
        super().__init__(user_id, name, email)
        self.availability = []         # List of unavailable TimeSlots
        self.assigned_courses = []     # List of courses assigned

    def declare_unavailability(self, timeslot):
        self.availability.append(timeslot)
        print(f"{self.name} is unavailable on {timeslot}")

    def view_timetable(self, schedule):
        schedule.display_for_teacher(self)


class Student(User):
    """
    Student role: can view group timetable, search free rooms
    """
    def __init__(self, user_id, name, email, department, group):
        super().__init__(user_id, name, email)
        self.department = department
        self.group = group

    def view_timetable(self, schedule):
        schedule.display_for_group(self.group)
