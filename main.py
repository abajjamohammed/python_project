# main.py

from users import Administrator, Teacher, Student
from rooms import Room
from timeslot import TimeSlot
from courses import Course
from schedule import Schedule
from menu import admin_menu, teacher_menu, student_menu

# -------------------------
# Step 1: Initialize Users
# -------------------------
admin = Administrator(1, "Admin", "admin@uni.com")

teacher1 = Teacher(2, "Dr Smith", "smith@uni.com")
teacher2 = Teacher(3, "Dr Jane", "jane@uni.com")

student1 = Student(4, "Alice", "alice@uni.com", "CS", "G1")
student2 = Student(5, "Bob", "bob@uni.com", "CS", "G2")
teacher1 = Teacher(2, "Pr. Sanae KHALI ISSA", "sanae@uni.com")
teacher2 = Teacher(3, "Pr. Ezziyyani Mostafa", "mostafa@uni.com")
teacher3 = Teacher(4, "Pr. JEBARI", "jebari@uni.com")

student1 = Student(5, "Fatima", "fatima@uni.com", "CS", "G1")
student2 = Student(6, "Hamza", "hamza@uni.com", "CS", "G2")

# -------------------------
# Step 2: Initialize Rooms
# -------------------------
rooms = [
    Room(1, "Room A", 30, ["Projector"]),
    Room(2, "Room B", 60, ["Projector"]),
    Room(3, "Lab 1", 25, ["Computers"]),
    Room(1, "Amphi 1", 30, ["Projector"]),
    Room(2, "Amphi 6", 60, ["Projector"]),
    Room(3, "Salle E15", 25, ["Computers"])
]

# -------------------------
# Step 3: Initialize TimeSlots
# -------------------------
timeslots = [
    TimeSlot("Monday", 8, 10),
    TimeSlot("Monday", 10, 12),
    TimeSlot("Tuesday", 8, 10),
    TimeSlot("Tuesday", 10, 12),
    TimeSlot("Wednesday", 8, 10),
]

# -------------------------
# Step 4: Initialize Courses
# -------------------------
courses = [
    Course(1, "Algorithms", teacher1, "G1", 28, ["Projector"]),
    Course(2, "Databases", teacher1, "G2", 55, ["Projector"]),
    Course(3, "Programming Lab", teacher2, "G1", 20, ["Computers"]),
    Course(1, "Machine Learning", teacher1, "G1", 28, ["Projector"]),
    Course(2, "Databases", teacher2, "G2", 55, ["Projector"]),
    Course(3, "Python Programming", teacher3, "G1", 20, ["Computers"]),
    Course(4, "Data Structures", teacher2, "G2", 25, ["Projector"])
]

# -------------------------
# Step 5: Create Schedule
# -------------------------
schedule = Schedule()

# -------------------------
# Step 6: Main Console Loop
# -------------------------
while True:
    print("\n===== UNIVERSITY TIMETABLE SYSTEM =====")
    print("1. Administrator")
    print("2. Teacher")
    print("3. Student")
    print("4. Exit")

    role = input("Select your role: ")

    if role == "1":
        admin_menu(admin, schedule, courses, rooms, timeslots)

    elif role == "2":
        # For simplicity, we select teacher1 for demo
        print("\nSelect teacher:")
        print("1. Dr Smith")
        print("2. Dr Jane")
        t_choice = input("Enter choice: ")
        print("\nSelect teacher:")
        print("1. Pr. Sanae KHALI ISSA")
        print("2. Pr. Ezziyyani Mostafa")
        print("3. Pr. JEBARI")

        t_choice = input("Enter choice: ")

        if t_choice == "1":
            teacher_menu(teacher1, schedule, rooms)
        elif t_choice == "2":
            teacher_menu(teacher2, schedule, rooms)
        elif t_choice == "3":
            teacher_menu(teacher3, schedule, rooms)
        else:
            print("Invalid choice.")

    elif role == "3":
        # For simplicity, we select student1 or student2
        print("\nSelect student:")
        print("1. Alice (G1)")
        print("2. Bob (G2)")
        s_choice = input("Enter choice: ")
        print("\nSelect student:")
        print("1. Fatima (G1)")
        print("2. Hamza (G2)")

        s_choice = input("Enter choice: ")

        if s_choice == "1":
            student_menu(student1, schedule, rooms)
        elif s_choice == "2":
            student_menu(student2, schedule, rooms)
        else:
            print("Invalid choice.")

    elif role == "4":
        print("Goodbye! Exiting the system...")
        break

    else:
        print("Invalid choice. Please try again.")
