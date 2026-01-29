from django.contrib.auth.decorators import login_required  # <--- NEW IMPORT
from django.contrib import messages
from .models import Room, Course, ReservationRequest, User, ScheduledSession
from django.db.models import Count
from .forms import ReservationForm
from django.shortcuts import render, redirect, get_object_or_404 # Vérifie que tu as tout ça
from .utils import TimetableAlgorithm

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