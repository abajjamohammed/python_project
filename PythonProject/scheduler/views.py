from django.contrib.auth.decorators import login_required  # <--- NEW IMPORT
from django.contrib import messages
from .models import Room, Course, ReservationRequest, User, ScheduledSession
from django.db.models import Count
from .forms import ReservationForm
from django.shortcuts import render, redirect, get_object_or_404 # Vérifie que tu as tout ça
from .utils import TimetableAlgorithm
from django.http import HttpResponse
import csv


@login_required  # <--- THIS PROTECTS THE VIEW
def dashboard_router(request):
    """The 'Home' page that redirects users based on their role"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.user.role == 'A':
        return redirect('admin_dashboard')
    elif request.user.role == 'T':
        return redirect('teacher_dashboard')
    else:
        return redirect('student_dashboard')
    
def admin_dashboard(request):
    # 1. Fetch Real Data from Database
    total_students = User.objects.filter(role='S').count()
    total_teachers = User.objects.filter(role='T').count()
    total_rooms = Room.objects.count()
    
    # Count pending requests (The "Alerts")
    pending_requests = ReservationRequest.objects.filter(status='PENDING').count()

    # 2. Data for the Chart (e.g., Number of sessions per day)
    # We count how many sessions exist for each day
    sessions_per_day = ScheduledSession.objects.values('day').annotate(count=Count('id'))
    
    # Prepare lists for Chart.js
    # If database is empty, we provide default data so the chart doesn't crash
    if not sessions_per_day:
        chart_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        chart_data = [0, 0, 0, 0, 0]
    else:
        chart_labels = [item['day'] for item in sessions_per_day]
        chart_data = [item['count'] for item in sessions_per_day]

    # 3. Pack everything into a context dictionary
    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_rooms': total_rooms,
        'pending_requests': pending_requests,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }

    # 4. Send to the template
    return render(request, 'scheduler/dashboard.html', context)
#  (Member 2: Teachers, Students, & Generate)

@login_required
def teacher_timetable(request):
    # GOAL: Show courses assigned to the logged-in teacher (Sanae)
    my_sessions = ScheduledSession.objects.filter(course__teacher=request.user).order_by('day', 'start_hour')

    context = {
        'sessions': my_sessions,
        'user_name': request.user.username
    }
    return render(request, 'scheduler/teacher_timetable.html', context)


@login_required
def student_timetable(request):
    # GOAL: Show sessions for the student's group (Mohammed)
    current_group = request.user.student_group 
    
    if current_group:
        group_sessions = ScheduledSession.objects.filter(course__group_name=current_group).order_by('day', 'start_hour')
    else:
        group_sessions = []

    context = {
        'sessions': group_sessions,
        'group_name': current_group
    }
    return render(request, 'scheduler/student_timetable.html', context)


@login_required
def generate_timetable(request):
    # GOAL: Placeholder URL for the 'Generate' button
    return redirect('admin_dashboard')

#added by mohammed# --- AJOUTS MEMBER 4 ---

@login_required
def make_reservation(request):
    """Permet à un prof de faire une demande"""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.teacher = request.user # On attache le prof connecté
            reservation.save()
            messages.success(request, "Demande envoyée avec succès !")
            return redirect('dashboard')
    else:
        form = ReservationForm()
    
    return render(request, 'scheduler/make_reservation.html', {
    'form': form,
    'errors': form.errors 
})

@login_required
def approve_reservations(request):
    """Liste les demandes en attente pour l'admin"""
    requests = ReservationRequest.objects.filter(status='PENDING')
    return render(request, 'scheduler/approve_reservations.html', {'requests': requests})

@login_required
def process_request(request, req_id, action):
    """Traite l'action Accepter ou Refuser"""
    reservation = get_object_or_404(ReservationRequest, id=req_id)
    
    if action == 'approve':
        reservation.status = 'APPROVED'
        reservation.save()
        messages.success(request, "Réservation approuvée.")
    elif action == 'reject':
        reservation.status = 'REJECTED'
        reservation.save()
        messages.error(request, "Réservation rejetée.")
    
    return redirect('approve_reservations')
#Added by Adjii:
def teacher_dashboard(request):
    # Prof sees her specific courses and her requests (Adjii's addition)
    sessions = ScheduledSession.objects.filter(course__teacher=request.user)
    my_reqs = ReservationRequest.objects.filter(teacher=request.user)
    context = {
        'sessions': sessions,
        'my_reqs': my_reqs,
        'days': ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"],
        'hours': [(8, 10), (10, 12), (14, 16)]
    }
    return render(request, 'scheduler/teacher_dashboard.html', context)
def student_dashboard(request):
    #Student see available sessions for his own group (Adjii's addition)
    sessions = ScheduledSession.objects.filter(course__group_name=request.user.student_group)
    context = {
        'sessions': sessions,
        'days': ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"],
        'hours': [(8, 10), (10, 12), (14, 16)]
    }
    return render(request, 'scheduler/student_dashboard.html', context)

#Added by Adjii for time table generation
def run_timetable_generation(request):
    # Security: Ensure only Admins can do this
    if not request.user.is_authenticated or request.user.role != 'A':
        messages.error(request, "Accès refusé.")
        return redirect('login')

    # 1. Clear existing schedule (to avoid duplicates)
    ScheduledSession.objects.all().delete()

    # 2. Trigger the Algorithm
    algo = TimetableAlgorithm()
    unscheduled = algo.generate_timetable()

    # 3. Success/Warning message
    if not unscheduled:
        messages.success(request, "L'emploi du temps a été généré avec succès !")
    else:
        messages.warning(request, f"Généré, mais impossible de placer : {', '.join(unscheduled)}")

    return redirect('admin_dashboard') # Replace with your actual admin dashboard name ?? COME BACK

#Adjii added this for the generate schedule button
@login_required
def export_timetable_csv(request):
    """Generates a CSV file of the timetable for Excel export"""
    
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    # The filename that the user will see when downloading
    response['Content-Disposition'] = 'attachment; filename="university_timetable.xl"'

    writer = csv.writer(response)
    
    writer.writerow(['Course Name', 'Teacher', 'Room', 'Day', 'Start Time', 'End Time'])

    # Determine which data to export based on user role
    if request.user.role == 'A':
        # Admins can export the entire schedule
        sessions = ScheduledSession.objects.all().select_related('course', 'room', 'course__teacher')
    elif request.user.role == 'T':
        # Teachers export only their own classes
        sessions = ScheduledSession.objects.filter(course__teacher=request.user).select_related('course', 'room')
    else:
        # Students export their group's schedule
        sessions = ScheduledSession.objects.filter(course__group_name=request.user.student_group).select_related('course', 'room')

    # Fill the CSV with data from the database
    for session in sessions:
        writer.writerow([
            session.course.name,
            session.course.teacher.username,
            session.room.name,
            session.day,
            f"{session.start_hour}:00",
            f"{session.end_hour}:00"
        ])

    return response