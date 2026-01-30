from django.shortcuts import render
from django.contrib.auth.decorators import login_required  # <--- NEW IMPORT
from django.contrib import messages
from .models import Room, Course, ReservationRequest, User, ScheduledSession
from django.db.models import Count
from .forms import ReservationForm
from django.shortcuts import render, redirect, get_object_or_404 # Vérifie que tu as tout ça
from .forms import CourseForm
from django.shortcuts import redirect
import json  # <--- CRITICAL: You need this for the calendar data
from .forms import TeacherForm # Import the new form



@login_required  # <--- THIS PROTECTS THE VIEW
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
    
    return render(request, 'scheduler/make_reservation.html', {'form': form})

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
def teacher_list(request):
    # Filter only users who are Teachers ('T')
    teachers = User.objects.filter(role='T')
    return render(request, 'scheduler/teacher_list.html', {'teachers': teachers})

def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard') # Go back to dashboard after saving
    else:
        form = CourseForm()
    
    return render(request, 'scheduler/add_course.html', {'form': form})
def timetable_view(request):
    """
    Displays the interactive calendar
    """
    sessions = ScheduledSession.objects.all()
    events = []
    
    # Simple mapping to turn "Monday" into a date the calendar understands
    # Let's pretend the week starts on Feb 5th, 2024 just for display purposes
    day_mapping = {
        "Monday": "05", "Lundi": "05",
        "Tuesday": "06", "Mardi": "06",
        "Wednesday": "07", "Mercredi": "07",
        "Thursday": "08", "Jeudi": "08",
        "Friday": "09", "Vendredi": "09"
    }
    
    for session in sessions:
        # Get the day number (default to 05 if not found)
        day_num = day_mapping.get(session.day, "05")
        
        events.append({
            'title': f"{session.course.name} ({session.room.name})",
            # ISO Format: YYYY-MM-DDTHH:MM:SS
            'start': f"2024-02-{day_num}T{session.start_hour:02d}:00:00",
            'end': f"2024-02-{day_num}T{session.end_hour:02d}:00:00",
            'color': '#3788d8' # Default Blue
        })
        
    context = {
        'events_json': json.dumps(events)
    }
    return render(request, 'scheduler/timetable.html', context)

def add_teacher(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('teacher_list') # Go back to the list
    else:
        form = TeacherForm()
    
    return render(request, 'scheduler/add_teacher.html', {'form': form})