from django.core.management.base import BaseCommand
from scheduler.models import Filiere, StudentGroup, Course, Room, User, ScheduledSession
from django.db import transaction

class Command(BaseCommand):
    help = 'Populates Rooms, Teachers, and Courses without deleting Groups'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Populating Curriculum into existing structure...")

        with transaction.atomic():
            # 1. CLEANUP ONLY COURSES/SESSIONS/ROOMS (Keep Groups & Filières safe)
            self.stdout.write("   Clearing old schedule data (Courses, Rooms, Sessions)...")
            ScheduledSession.objects.all().delete()
            Course.objects.all().delete()
            Room.objects.all().delete()
            # Remove old teachers to avoid duplicates
            User.objects.filter(role='T').delete()

            # 2. CREATE ROOMS
            self.stdout.write("   Creating Rooms...")
            rooms = []
            # Amphis (Big capacity for CM)
            for i in range(1, 5):
                rooms.append(Room(name=f"Amphi {i}", capacity=150, building="Bloc A"))
            # Salles de cours (Standard capacity for TD)
            for i in range(1, 20):
                rooms.append(Room(name=f"Salle {i}", capacity=40, building="Bloc B"))
            Room.objects.bulk_create(rooms)

            # 3. DEFINE CURRICULUM
            # Dictionary maps Filiere CODE to Module List
            curriculum = {
                # --- LICENCE ---
                'AD': ["Python Programming", "Probability & Statistics", "Data Structures", "Databases (SQL)", "Machine Learning", "LC"],
                'IDAI': ["Web Development", "OOP (Java/C++)", "Operating Systems", "UML & Software Eng", "Databases", "LC"],
                'SSD': ["Descriptive Statistics", "Probability Theory", "Data Analysis", "Databases", "Optimization Methods", "LC"],
                'MIDS': ["Linear Algebra", "Optimization Models", "Algorithms", "Databases", "Programming (Python)", "LC"],
                'GI': ["Programming (C)", "Data Structures", "Computer Architecture", "Operating Systems", "Computer Networks", "LC"],
                'GIND': ["Operations Research", "Production Management", "Quality Management", "Supply Chain Basics", "Project Management", "LC"],
                
                # --- MASTER ---
               'MBD': ["Big Data Analytics", "Distributed Systems", "Data Mining", "Cloud Computing", "Research Project"],
               'SIM': ["Adv. Software Arch.", "Mobile App Dev", "Network Security", "Embedded Systems", "Final Project"],
               'AISD': ["Machine Learning & Deep Learning", "Data Mining & Big Data Analytics", "Statistical Learning & Optimization", "Artificial Intelligence (Search, Reasoning, NLP)", "Final Project"],
                'GC': ["Adv. Structural Design", "Earthquake Engineering", "Construction Mgmt", "Finite Element Methods", "Final Project"],
                'GENE': ["Renewable Energy", "Energy Optimization", "Heat Transfer", "Smart Grids", "Final Project"],
            }

            # 4. CREATE COURSES & TEACHERS
            self.stdout.write("   Linking Modules to your existing Filières...")
            
            for filiere_code, modules in curriculum.items():
                # Find the existing Filiere you created manually
                try:
                    filiere = Filiere.objects.get(code=filiere_code)
                except Filiere.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Skipping {filiere_code}: Filiere not found in your manual data."))
                    continue

                # Get the groups you created for this filiere
                groups = StudentGroup.objects.filter(filiere=filiere)
                if not groups.exists():
                     self.stdout.write(self.style.WARNING(f"   ⚠️ No groups found for {filiere_code}."))

                for mod_name in modules:
                    # A. Create a Teacher
                    teacher_username = f"prof_{filiere_code.lower()}_{mod_name.split()[0].lower()}"[:20]
                    teacher, created = User.objects.get_or_create(
                        username=teacher_username,
                        defaults={
                            'role': 'T', 
                            'email': f"{teacher_username}@fstt.ac.ma",
                            'first_name': "Prof.",
                            'last_name': mod_name.split()[0]
                        }
                    )
                    if created:
                        teacher.set_password('pass123')
                        teacher.save()

                    # B. Create CM (Cours Magistral) - Linked to Filière (All groups)
                    Course.objects.create(
                        name=f"{mod_name} (CM)",
                        code=f"{filiere_code}-{mod_name[:3].upper()}",
                        teacher=teacher,
                        filiere=filiere,
                        group=None, # None means it is for the whole Filiere
                        session_type='CM',
                        credits=3
                    )

                    # C. Create TD (Travaux Dirigés) - Linked to EACH Group
                    # We create a specific TD course for G1, G2, etc.
                    # Note: To avoid overcrowding the schedule in testing, we only add TDs for the first 3 modules
                    if modules.index(mod_name) < 3: 
                        for grp in groups:
                            Course.objects.create(
                                name=f"{mod_name} (TD)",
                                code=f"{filiere_code}-{mod_name[:3].upper()}-TD",
                                teacher=teacher,
                                filiere=filiere,
                                group=grp, # Linked to your specific manually created group
                                session_type='TD',
                                credits=2
                            )

            self.stdout.write(self.style.SUCCESS("✅ Courses, Rooms, and Teachers created successfully!"))