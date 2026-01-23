# courses.py

class Course:
    def __init__(self, course_id, name, teacher, group, students_count, equipment_needed):
        self.course_id = course_id
        self.name = name
        self.teacher = teacher
        self.group = group
        self.students_count = students_count
        self.equipment_needed = equipment_needed

    def __str__(self):
        return f"{self.name} ({self.group})"
