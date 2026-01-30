from django.contrib.auth.decorators import login_required  
from django.contrib import messages
from .models import Room, Course, ReservationRequest, User, ScheduledSession
from django.db.models import Count
from .forms import ReservationForm, CourseForm, TeacherForm, RoomSearchForm
from django.shortcuts import render, redirect, get_object_or_404 
import json  
from django.contrib.auth import logout
from .utils import TimetableAlgorithm
from django.http import HttpResponse
import csv
from datetime import datetime



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
    
    # Get the actual reservation objects (not just the count)
    pending_reservations = ReservationRequest.objects.filter(status='PENDING')  # REMOVED .count()
    pending_requests = pending_reservations.count()  # Count for the badge

    # 2. Data for the Chart
    sessions_per_day = ScheduledSession.objects.values('day').annotate(count=Count('id'))
    
    if not sessions_per_day:
        chart_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        chart_data = [0, 0, 0, 0, 0]
    else:
        chart_labels = [item['day'] for item in sessions_per_day]
        chart_data = [item['count'] for item in sessions_per_day]

    # 3. Pack everything into context
    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_rooms': total_rooms,
        'pending_requests': pending_requests,  # The count for the badge
        'pending_reservations': pending_reservations,  # <-- ADD THIS LINE - the actual objects for the table
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }

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
    """The dedicated full-page schedule for students"""
    sessions = ScheduledSession.objects.filter(course__group_name=request.user.student_group)
    
    context = {
        'sessions': sessions,
        'days': ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"],
        'hours': [(8, 10), (10, 12), (14, 16)]
    }
    return render(request, 'scheduler/student_timetable.html', context)



@login_required
def generate_timetable(request):
     # Security: Ensure only Admins can do this
    if not request.user.is_authenticated or request.user.role == 'Teacher' or request.user.role == 'Student':
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

from datetime import datetime, timedelta # <--- Make sure you have this import at the top
import json
from django.shortcuts import render
from .models import ScheduledSession


def timetable_view(request):
    """
    Displays the interactive calendar with dynamic dates for the current week.
    """
    sessions = ScheduledSession.objects.all()
    events = []
    
    # 1. Calculate the Monday of the CURRENT week
    today = datetime.now().date()
    # weekday() returns 0 for Monday, 6 for Sunday. 
    # We subtract the current weekday number from today to get back to Monday.
    monday_date = today - timedelta(days=today.weekday())

    # 2. Dynamic Mapping: Map string days to Real Dates for this week
    # If Monday is Jan 26th, Tuesday will be Jan 27th, etc.
    day_mapping = {
        "Monday":    monday_date,
        "Tuesday":   monday_date + timedelta(days=1),
        "Wednesday": monday_date + timedelta(days=2),
        "Thursday":  monday_date + timedelta(days=3),
        "Friday":    monday_date + timedelta(days=4),
        "Saturday":  monday_date + timedelta(days=5),
        "Sunday":    monday_date + timedelta(days=6),
        # Add French mapping just in case your DB has French values
        "Lundi":     monday_date,
        "Mardi":     monday_date + timedelta(days=1),
        "Mercredi":  monday_date + timedelta(days=2),
        "Jeudi":     monday_date + timedelta(days=3),
        "Vendredi":  monday_date + timedelta(days=4),
    }
    
    for session in sessions:
        # Get the real date object for the session's day name
        session_date = day_mapping.get(session.day)
        
        if session_date:
            # Format date as string: "2026-01-26"
            date_str = session_date.strftime('%Y-%m-%d')
            
            events.append({
                'title': f"{session.course.name} ({session.room.name})",
                # ISO Format: YYYY-MM-DDTHH:MM:SS
                'start': f"{date_str}T{session.start_hour:02d}:00:00",
                'end': f"{date_str}T{session.end_hour:02d}:00:00",
                'color': '#3788d8' # Default Blue
            })
            
    context = {
        'events_json': json.dumps(events),
        # Pass the calculated Monday date to the template
        'start_date': monday_date.strftime('%Y-%m-%d') 
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




@login_required
def teacher_dashboard(request):
    # Get teacher's sessions
    sessions = ScheduledSession.objects.filter(course__teacher=request.user).select_related('course', 'room')
    
    # Get today's sessions
    today = datetime.now().strftime('%A')  # Gets day name like "Monday"
    # Handle French day names if you're using them
    day_mapping = {
        'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi', 'Friday': 'Vendredi'
    }
    today_french = day_mapping.get(today, today)
    
    todays_sessions = sessions.filter(day=today_french)
    
    # Get reservation requests
    my_reqs = ReservationRequest.objects.filter(teacher=request.user).order_by('-id')
    
    # Calculate stats
    total_courses = sessions.values('course').distinct().count()
    weekly_hours = sum([(s.end_hour - s.start_hour) for s in sessions])
    pending_requests_count = my_reqs.filter(status='PENDING').count()
    
    context = {
        'sessions': sessions,
        'todays_sessions': todays_sessions,
        'todays_sessions_count': todays_sessions.count(),
        'my_reqs': my_reqs,
        'total_courses': total_courses,
        'weekly_hours': weekly_hours,
        'pending_requests_count': pending_requests_count,
        'days': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        'hours': [(8, 10), (10, 12), (14, 16), (16, 18)]
    }
    return render(request, 'scheduler/teacher_dashboard.html', context)
    return render(request, 'scheduler/teacher_dashboard.html', context)

#Added by Adjii:
def student_dashboard(request):
    # 1. Get all sessions for Mohammed's group
    sessions = ScheduledSession.objects.filter(course__group_name=request.user.student_group)
    
    # 2. Get the "Next Class" (Simplified: the first session found)
    next_class = sessions.first() 

    context = {
        'sessions': sessions,
        'next_class': next_class,
        'days': ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"],
        'hours': [(8, 10), (10, 12), (14, 16)]
    }
    # MAKE SURE THIS POINTS TO THE NEW HTML FILE YOU SHOWED ME
    return render(request, 'scheduler/student_dashboard.html', context)


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

@login_required
def my_reservations(request):
    """Teacher views their own reservation history (read-only)"""
    my_reqs = ReservationRequest.objects.filter(teacher=request.user).order_by('-id')
    return render(request, 'scheduler/my_reservations.html', {'my_reqs': my_reqs})

#for the logout
def custom_logout(request):
    logout(request)
    return redirect('login')



def find_free_rooms(request):
    results = None
    if request.method == 'POST':
        form = RoomSearchForm(request.POST)
        if form.is_valid():
            day = form.cleaned_data['day']
            start = form.cleaned_data['start_hour']
            end = form.cleaned_data['end_hour']
            
            # 1. Get all rooms
            all_rooms = Room.objects.all()
            
            # 2. Get occupied room IDs
            occupied_ids = ScheduledSession.objects.filter(
                day=day,
                start_hour__lt=end,
                end_hour__gt=start
            ).values_list('room_id', flat=True)
            
            # 3. Filter
            results = all_rooms.exclude(id__in=occupied_ids)
    else:
        form = RoomSearchForm()
    
    return render(request, 'scheduler/find_room.html', {'form': form, 'rooms': results})