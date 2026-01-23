# menu.py

from timeslot import TimeSlot


def admin_menu(admin, schedule, courses, rooms, timeslots):
    """
    Console menu for the Administrator
    """
    while True:
        print("\n===== ADMINISTRATOR MENU =====")
        print("1. Generate timetable")
        print("2. View all scheduled sessions")
        print("3. View unscheduled courses")
        print("4. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            schedule.generate(courses, rooms, timeslots)
            print("\nTimetable generated successfully.")

        elif choice == "2":
            print("\n--- ALL SCHEDULED SESSIONS ---")
            if not schedule.sessions:
                print("No sessions scheduled yet.")
            else:
                for s in schedule.sessions:
                    print(f"{s['timeslot']} | {s['course']} | {s['room']}")

        elif choice == "3":
            print("\n--- UNSCHEDULED COURSES ---")
            if not schedule.unscheduled_courses:
                print("All courses were scheduled successfully.")
            else:
                for course in schedule.unscheduled_courses:
                    print(course)

        elif choice == "4":
            print("Exiting administrator menu...")
            break

        else:
            print("Invalid choice. Please try again.")


def teacher_menu(teacher, schedule, rooms):
    """
    Console menu for the Teacher
    """
    while True:
        print(f"\n===== TEACHER MENU ({teacher.name}) =====")
        print("1. View my timetable")
        print("2. Search available rooms")
        print("3. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            schedule.display_for_teacher(teacher)

        elif choice == "2":
            day = input("Enter day (e.g. Monday): ")
            start = int(input("Start hour (e.g. 8): "))
            end = int(input("End hour (e.g. 10): "))

            slot = TimeSlot(day, start, end)

            print("\nAvailable rooms:")
            found = False
            for room in rooms:
                if room.is_available(slot):
                    print(room)
                    found = True

            if not found:
                print("No rooms available for this time slot.")

        elif choice == "3":
            print("Exiting teacher menu...")
            break

        else:
            print("Invalid choice. Please try again.")


def student_menu(student, schedule, rooms):
    """
    Console menu for the Student
    """
    while True:
        print(f"\n===== STUDENT MENU ({student.name}) =====")
        print("1. View my group timetable")
        print("2. Search free rooms")
        print("3. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            schedule.display_for_group(student.group)

        elif choice == "2":
            day = input("Enter day (e.g. Monday): ")
            start = int(input("Start hour (e.g. 8): "))
            end = int(input("End hour (e.g. 10): "))

            slot = TimeSlot(day, start, end)

            print("\nFree rooms:")
            found = False
            for room in rooms:
                if room.is_available(slot):
                    print(room)
                    found = True

            if not found:
                print("No free rooms for this time slot.")

        elif choice == "3":
            print("Exiting student menu...")
            break

        else:
            print("Invalid choice. Please try again.")
