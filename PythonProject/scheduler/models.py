from django.db import models
from django.contrib.auth.models import AbstractUser

# ============= USER MODEL =============
class User(AbstractUser):
    ROLE_CHOICES = [('A', 'Admin'), ('T', 'Teacher'), ('S', 'Student')]
    role = models.CharField(max_length=1, choices=ROLE_CHOICES)
    
    # Student is linked to StudentGroup
    student_group = models.ForeignKey('StudentGroup', null=True, blank=True, on_delete=models.SET_NULL)
    
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# ============= HIERARCHY MODELS =============

class Level(models.Model):
    """Licence or Master - PREDEFINED"""
    LEVEL_CHOICES = [
        ('L', 'Licence'),
        ('M', 'Master'),
    ]
    code = models.CharField(max_length=1, choices=LEVEL_CHOICES, unique=True, primary_key=True)
    name = models.CharField(max_length=50)
    
    def save(self, *args, **kwargs):
        # Auto-set name based on code
        if self.code == 'L':
            self.name = 'Licence'
        elif self.code == 'M':
            self.name = 'Master'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['code']


class Filiere(models.Model):
    """AD, IDAI, SSD, etc. - PREDEFINED"""
    
    # Predefined filieres
    FILIERE_CHOICES = [
        # Licence
        ('AD', 'Analytique des Données'),
        ('IDAI', 'Ingénierie de Développement d\'Applications Informatiques'),
        ('SSD', 'Statistique et Sciences des Données'),
        ('MIDS', 'Mathématiques & Informatique Décisionnelles'),
        ('GI', 'Génie Informatique'),
        ('GIND', 'Génie Industriel'),
        # Master
        ('MBD', 'Mobiquité & Big Data'),
        ('SIM', 'Systèmes Informatiques & Mobiles'),
        ('AISD', 'Intelligence Artificielle et Sciences de Données'),
        ('GC', 'Génie Civil'),
        ('GENE', 'Génie Énergétique'),
    ]
    
    code = models.CharField(max_length=20, choices=FILIERE_CHOICES, unique=True)
    name = models.CharField(max_length=200)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    
    def save(self, *args, **kwargs):
        # Auto-set name and level based on code
        filiere_data = {
            # Licence
            'AD': ('Analytique des Données', 'L'),
            'IDAI': ('Ingénierie de Développement d\'Applications Informatiques', 'L'),
            'SSD': ('Statistique et Sciences des Données', 'L'),
            'MIDS': ('Mathématiques & Informatique Décisionnelles', 'L'),
            'GI': ('Génie Informatique', 'L'),
            'GIND': ('Génie Industriel', 'L'),
            # Master
            'MBD': ('Mobiquité & Big Data', 'M'),
            'SIM': ('Systèmes Informatiques & Mobiles', 'M'),
            'AISD': ('Intelligence Artificielle et Sciences de Données', 'M'),
            'GC': ('Génie Civil', 'M'),
            'GENE': ('Génie Énergétique', 'M'),
        }
        
        if self.code in filiere_data:
            self.name, level_code = filiere_data[self.code]
            self.level_id = level_code
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.level.name} - {self.code}"
    
    class Meta:
        ordering = ['level', 'code']


class StudentGroup(models.Model):
    """G1, G2, G3 for each filière - WITH PREDEFINED CAPACITIES"""
    
    GROUP_CHOICES = [
        ('G1', 'Groupe 1'),
        ('G2', 'Groupe 2'),
        ('G3', 'Groupe 3'),
    ]
    
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE)
    name = models.CharField(max_length=10, choices=GROUP_CHOICES)
    capacity = models.IntegerField(default=30)
    
    def save(self, *args, **kwargs):
        # Auto-set capacity based on filiere and group
        default_capacities = {
            # Licence
            'AD': {'G1': 32, 'G2': 30, 'G3': 28},
            'IDAI': {'G1': 35, 'G2': 33, 'G3': 31},
            'SSD': {'G1': 30, 'G2': 28},
            'MIDS': {'G1': 28, 'G2': 27},
            'GI': {'G1': 35, 'G2': 34, 'G3': 32},
            'GIND': {'G1': 30, 'G2': 28},
            # Master
            'MBD': {'G1': 22, 'G2': 20},
            'SIM': {'G1': 20, 'G2': 18},
            'AISD': {'G1': 18, 'G2': 17},
            'GC': {'G1': 20, 'G2': 19},
            'GENE': {'G1': 18, 'G2': 17},
        }
        
        # Auto-set capacity if not manually set
        if not self.capacity or self.capacity == 30:  # 30 is default
            filiere_code = self.filiere.code
            if filiere_code in default_capacities and self.name in default_capacities[filiere_code]:
                self.capacity = default_capacities[filiere_code][self.name]
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.filiere.code} - {self.name}"
    
    class Meta:
        ordering = ['filiere', 'name']
        unique_together = ['filiere', 'name']
        verbose_name = "Student Group"
        verbose_name_plural = "Student Groups"


# ============= ROOM MODEL =============
class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    equipment = models.CharField(max_length=255, blank=True)
    building = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


# ============= COURSE MODEL =============
class Course(models.Model):
    """Course can be CM (entire filière) or TD/TP (specific group)"""
    SESSION_TYPE_CHOICES = [
        ('CM', 'Cours Magistral'),   # Lecture - entire filière
        ('TD', 'Travaux Dirigés'),    # Tutorial - per group
        ('TP', 'Travaux Pratiques'),  # Lab - per group
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'T'})
    
    # Hierarchy
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE)
    
    # If group is NULL → CM (entire filière), if set → TD/TP (specific group)
    group = models.ForeignKey(StudentGroup, null=True, blank=True, on_delete=models.CASCADE)
    
    session_type = models.CharField(max_length=2, choices=SESSION_TYPE_CHOICES, default='CM')
    
    # Other fields
    equipment_needed = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    credits = models.IntegerField(default=3)
    
    def __str__(self):
        if self.group:
            return f"{self.name} ({self.session_type}) - {self.group}"
        return f"{self.name} ({self.session_type}) - {self.filiere.code}"
    
    @property
    def student_count(self):
        """Calculate number of students for this course"""
        if self.group:
            # TD/TP - specific group
            return self.group.capacity
        # CM - entire filière (all groups)
        return sum(
            g.capacity for g in StudentGroup.objects.filter(filiere=self.filiere)
        )
    
    # Backward compatibility
    @property
    def group_name(self):
        """For backward compatibility"""
        if self.group:
            return str(self.group)
        return f"{self.filiere.code} (All groups)"
    
    class Meta:
        ordering = ['filiere', 'session_type', 'name']


# ============= SCHEDULED SESSION =============
class ScheduledSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()
    
    def __str__(self):
        return f"{self.course.name} - {self.day} ({self.start_hour}:00-{self.end_hour}:00)"
    
    class Meta:
        ordering = ['day', 'start_hour']


# ============= RESERVATION REQUEST =============
class ReservationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvée'),
        ('REJECTED', 'Rejetée'),
    ]
    
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'T'})
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Demande de {self.teacher.username} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']


# ============= TEACHER UNAVAILABILITY =============
class TeacherUnavailability(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'T'})
    day = models.CharField(max_length=20)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()
    
    def __str__(self):
        return f"{self.teacher.username} busy on {self.day} {self.start_hour}h-{self.end_hour}h"
    
    class Meta:
        ordering = ['teacher', 'day', 'start_hour']