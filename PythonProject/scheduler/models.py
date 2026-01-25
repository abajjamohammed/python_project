from django.db import models
from django.contrib.auth.models import AbstractUser

# replaces users.py logic
class User(AbstractUser):
    ROLE_CHOICES = [('A', 'Admin'), ('T', 'Teacher'), ('S', 'Student')]
    role = models.CharField(max_length=1, choices=ROLE_CHOICES)
    # Le groupe de l'étudiant (ex: "G1", "Info-A"). 
    # blank=True car les Profs et Admin n'ont pas de groupe.
    student_group = models.CharField(max_length=50, blank=True, null=True) #added this bcs we need to know the group of the student :mohammed 25/01

# replaces rooms.py
class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    # Stores equipment as a comma-separated string or a new table
    equipment = models.CharField(max_length=255) 

# replaces courses.py
class Course(models.Model):
    name = models.CharField(max_length=200)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    group_name = models.CharField(max_length=50)
    student_count = models.IntegerField()
    equipment_needed = models.CharField(max_length=255)

# replaces schedule.py "session" logic
class ScheduledSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()
    
    
#added those :mohammed 25/01
class ReservationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvée'),
        ('REJECTED', 'Rejetée'),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()
    reason = models.TextField(blank=True, help_text="Motif de la réservation (ex: Rattrapage)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"Demande de {self.teacher.username} - {self.status}"