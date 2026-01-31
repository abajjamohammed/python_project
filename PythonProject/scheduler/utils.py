from .models import Room, Course, ScheduledSession, User, ReservationRequest
from django.db.models import Q
from .models import TeacherUnavailability
#created by mohammed 05/01  this is the main algorithm for generating the timetable(the logic)
class TimetableAlgorithm:
    def __init__(self):
        # On définit les créneaux horaires fixes (comme dans ton main.py)
        self.timeslots = [
            ("Monday", 8, 10), ("Monday", 10, 12), ("Monday", 14, 16),
            ("Tuesday", 8, 10), ("Tuesday", 10, 12), ("Tuesday", 14, 16),
            ("Wednesday", 8, 10), ("Wednesday", 10, 12),
            ("Thursday", 8, 10), ("Thursday", 10, 12),
            ("Friday", 8, 10), ("Friday", 10, 12)
        ]

    def check_conflict(self, day, start, end, room=None, teacher=None, group=None):
        """
        Vérifie si une séance existe déjà dans la base de données
        qui chevauche ce créneau pour la Salle, le Prof ou le Groupe.
        """
        # On cherche des sessions qui ont lieu le même jour
        # ET qui chevauchent les heures (Fin > Start ET Debut < End)
        conflicts = ScheduledSession.objects.filter(
            day=day,
            start_hour__lt=end,
            end_hour__gt=start
        )

        if room:
            if conflicts.filter(room=room).exists():
                return True # La salle est prise
        
        if teacher:
            # On vérifie si ce prof a déjà cours
            if conflicts.filter(course__teacher=teacher).exists():
                return True # Le prof est occupé
            
               # Check declared unavailability
            busy = TeacherUnavailability.objects.filter(
                teacher=teacher,
                day=day,
                start_hour__lt=end,
                end_hour__gt=start
            ).exists()
            if busy:
                return True
        

        if group:
            # On vérifie si ce groupe a déjà cours
            if conflicts.filter(course__group_name=group).exists():
                return True # Les étudiants sont occupés

        return False

def find_best_room(self, course, day, start, end):
    """
    Trouve la meilleure salle libre (Capacité et Équipements)
    """
    all_rooms = Room.objects.all()
    suitable_rooms = []

    for room in all_rooms:
        # 1. Check Capacity
        if room.capacity < course.student_count:
            continue
        
        # 2. Check Equipment
        if course.equipment_needed and course.equipment_needed not in room.equipment:
            continue

        # 3. Check if room is free (no scheduled sessions)
        if self.check_conflict(day, start, end, room=room):
            continue  # Room is occupied by a scheduled session
        
        # 4. Check for approved teacher reservations
        reservation_exists = ReservationRequest.objects.filter(
            room=room,
            day=day,
            start_hour__lt=end,
            end_hour__gt=start,
            status='APPROVED'
        ).exists()

        if reservation_exists:
            continue  # Room is reserved by a teacher
        
        # 5. If we reach here, room is suitable!
        suitable_rooms.append(room)

    # No rooms found
    if not suitable_rooms:
        return None

    # Return the smallest suitable room (optimization)
    suitable_rooms.sort(key=lambda r: r.capacity)
    return suitable_rooms[0]
    

    def generate_timetable(self):
        """
        Fonction principale qui génère tout
        """
        #Adjii's additions
        # Étape 0 : Nettoyer l'emploi du temps existant (Optionnel, pour éviter les doublons lors des tests)
        # ScheduledSession.objects.all().delete() 

        courses = Course.objects.all().order_by('-student_count') # On place les gros cours en premier
        unscheduled = []

        for course in courses:
            is_scheduled = False
            
            # On essaie chaque créneau horaire
            for day, start, end in self.timeslots:
                
                # 1. Vérifier si le Prof est libre
                if self.check_conflict(day, start, end, teacher=course.teacher):
                    continue # Prof pas là, on change d'heure
                
                # 2. Vérifier si le Groupe est libre
                if self.check_conflict(day, start, end, group=course.group_name):
                    continue # Groupe is not free so we change hour

                # 3. Trouver une salle
                best_room = self.find_best_room(course, day, start, end)

                if best_room:
                    # 4. On sauvegarde en Base de Données !
                    ScheduledSession.objects.create(
                        course=course,
                        room=best_room,
                        day=day,
                        start_hour=start,
                        end_hour=end
                    )
                    is_scheduled = True
                    print(f"✅ Cours planifié : {course.name} en {best_room.name} le {day} à {start}h")
                    break # On passe au cours suivant

            if not is_scheduled:
                unscheduled.append(course.name)
                print(f"❌ Impossible de placer : {course.name}")
        
        return unscheduled
    
    