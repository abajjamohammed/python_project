from django.contrib.auth.decorators import login_required  
from django.contrib import messages
from .models import Room, Course, ReservationRequest, User, ScheduledSession, Filiere
from django.db.models import Count,Q
from .forms import ReservationForm, CourseForm, TeacherForm, RoomSearchForm
from django.shortcuts import render, redirect, get_object_or_404 
import json  
from django.contrib.auth import logout
from .utils import TimetableAlgorithm
from django.http import HttpResponse
import csv
from datetime import datetime
from .forms import SessionForm
from django.shortcuts import redirect

from .forms import TeacherForm, TeacherEditForm # Import the new form
from .models import TeacherUnavailability
from .forms import TeacherUnavailabilityForm
from .forms import ProfileForm
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
# --- Make sure this import is at the very top of the file! ---
from .models import Course  
from django.db.models import Q
from django.utils import timezone


from .forms import CourseForm  # <--- Make sure this is here




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
    """Dedicated timetable page for teachers with Rowspan logic"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    hours = range(8, 19) # 8 to 18
    
    # 1. Get all sessions for this teacher
    sessions = ScheduledSession.objects.filter(
        course__teacher=request.user
    ).select_related('course', 'room', 'course__filiere')

    # 2. Calculate stats BEFORE building the grid
    # Total sessions count
    total_sessions = sessions.count()
    
    # Weekly hours calculation
    weekly_hours = sum([(s.end_hour - s.start_hour) for s in sessions])
    
    # Today's sessions
    from datetime import datetime
    today_name = datetime.now().strftime('%A')
    today_sessions_count = sessions.filter(day=today_name).count()
    
    # Next class today
    next_class = sessions.filter(day=today_name, start_hour__gte=datetime.now().hour).order_by('start_hour').first()

    # 3. Build a quick lookup dictionary: (day, start_hour) -> session
    session_map = {}
    for s in sessions:
        session_map[(s.day, s.start_hour)] = s

    # 4. Build the Grid Matrix
    timetable_data = []
    
    # Track which cells to skip because they are covered by a rowspan
    # Format: set of (day, hour) strings/tuples
    skip_slots = set()

    for h in hours:
        row = {'hour': h, 'slots': []}
        for d in days:
            if (d, h) in skip_slots:
                # This slot is covered by a previous class (e.g., 9am covered by 8am class)
                row['slots'].append({'type': 'skipped'})
                continue

            session = session_map.get((d, h))
            
            if session:
                duration = session.end_hour - session.start_hour
                # Mark future slots as skipped
                for i in range(1, duration):
                    skip_slots.add((d, h + i))
                
                row['slots'].append({
                    'type': 'session',
                    'session': session,
                    'rowspan': duration
                })
            else:
                row['slots'].append({'type': 'empty'})
        
        timetable_data.append(row)

    context = {
        'timetable_data': timetable_data, # <--- The new structured data
        'days': days,
        'next_class': next_class,
        'today_sessions_count': today_sessions_count,
        'sessions_count': total_sessions, # Total count - fixed variable name
        'weekly_hours': weekly_hours,
        'user_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'scheduler/teacher_timetable.html', context)


@login_required
def student_timetable(request):
    """Student timetable with proper rowspan handling (like teacher timetable)"""
    student_group = request.user.student_group

    if not student_group:
        return render(request, 'scheduler/student_timetable.html', {
            'error': 'You are not assigned to any group.'
        })

    # Get sessions for the student's group OR for the entire Filière (CM)
    sessions = ScheduledSession.objects.filter(
        Q(course__group=student_group) | 
        Q(course__filiere=student_group.filiere, course__group__isnull=True)
    ).select_related('course', 'room', 'course__teacher', 'course__filiere').order_by('day', 'start_hour')

    # Prepare data structure like teacher timetable
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    hours = range(8, 19)  # 8 AM to 6 PM
    
    # Create session map for quick lookup
    session_map = {}
    for s in sessions:
        session_map[(s.day, s.start_hour)] = s
    
    # Track which cells to skip (covered by rowspan)
    skip_slots = set()
    
    # Build the timetable grid
    timetable_data = []
    for h in hours:
        row = {'hour': h, 'slots': []}
        for d in days:
            if (d, h) in skip_slots:
                # This slot is covered by a previous multi-hour class
                row['slots'].append({'type': 'skipped'})
                continue

            session = session_map.get((d, h))
            
            if session:
                duration = session.end_hour - session.start_hour
                # Mark future slots as skipped
                for i in range(1, duration):
                    skip_slots.add((d, h + i))
                
                row['slots'].append({
                    'type': 'session',
                    'session': session,
                    'rowspan': duration
                })
            else:
                row['slots'].append({'type': 'empty'})
        
        timetable_data.append(row)
    
    # Calculate stats
    total_sessions = sessions.count()
    weekly_hours = sum([(s.end_hour - s.start_hour) for s in sessions])
    
    # Find next class (better logic)
    from datetime import datetime
    today_name = datetime.now().strftime('%A')
    current_hour = datetime.now().hour
    
    # Find next class today
    next_class = sessions.filter(day=today_name, start_hour__gte=current_hour).order_by('start_hour').first()
    if not next_class:
        # If no more classes today, find first class tomorrow
        next_day_index = (days.index(today_name) + 1) % len(days) if today_name in days else 0
        next_class = sessions.filter(day=days[next_day_index]).order_by('start_hour').first()
    
    # Today's sessions count
    today_sessions_count = sessions.filter(day=today_name).count()

    context = {
        'timetable_data': timetable_data,
        'days': days,
        'hours': hours,
        'next_class': next_class,
        'today_sessions_count': today_sessions_count,
        'total_sessions': total_sessions,
        'weekly_hours': weekly_hours,
        'student_group': student_group,
        'student_name': request.user.get_full_name() or request.user.username,
    }
    
    return render(request, 'scheduler/student_timetable.html', context)



@login_required
def generate_timetable(request):
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
            return redirect('course_list') # Go back to dashboard after saving
    else:
        form = CourseForm()
    
    return render(request, 'scheduler/add_course.html', {'form': form})

from datetime import datetime, timedelta # <--- Make sure you have this import at the top
import json
from django.shortcuts import render
from .models import ScheduledSession



def timetable_view(request):
    """
    Admin timetable page - HTML table version (like teacher timetable)
    """
    # 1. Get all filières for dropdown
    filieres = Filiere.objects.all().order_by('level', 'code')
    
    # 2. Get selected filière or show all
    selected_filiere_id = request.GET.get('filiere')
    selected_filiere = None
    
    if selected_filiere_id:
        try:
            selected_filiere = Filiere.objects.get(id=selected_filiere_id)
            # Filter sessions for this filière
            sessions = ScheduledSession.objects.filter(
                course__filiere=selected_filiere
            ).select_related('course', 'room', 'course__teacher', 'course__filiere', 'course__group')
        except Filiere.DoesNotExist:
            sessions = ScheduledSession.objects.all().select_related(
                'course', 'room', 'course__teacher', 'course__filiere', 'course__group'
            )
    else:
        sessions = ScheduledSession.objects.all().select_related(
            'course', 'room', 'course__teacher', 'course__filiere', 'course__group'
        )
    
    # 3. Days and hours for the timetable
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    hours = range(8, 19)  # 8 AM to 6 PM
    
    # 4. Create a session map for quick lookup (like teacher timetable)
    session_map = {}
    skip_slots = set()
    
    for session in sessions:
        session_map[(session.day, session.start_hour)] = session
    
    # 5. Build the timetable grid data
    timetable_data = []
    for h in hours:
        row = {'hour': h, 'slots': []}
        for d in days:
            if (d, h) in skip_slots:
                row['slots'].append({'type': 'skipped'})
                continue
            
            session = session_map.get((d, h))
            
            if session:
                duration = session.end_hour - session.start_hour
                # Mark future slots as skipped
                for i in range(1, duration):
                    skip_slots.add((d, h + i))
                
                row['slots'].append({
                    'type': 'session',
                    'session': session,
                    'rowspan': duration
                })
            else:
                row['slots'].append({'type': 'empty'})
        
        timetable_data.append(row)
    
    # 6. Calculate stats
    total_sessions = sessions.count()
    weekly_hours = sum([(s.end_hour - s.start_hour) for s in sessions])
    
    # Get today's sessions count
    from datetime import datetime
    today_name = datetime.now().strftime('%A')
    today_sessions_count = sessions.filter(day=today_name).count()
    
    context = {
        'filieres': filieres,
        'selected_filiere': selected_filiere,
        'timetable_data': timetable_data,
        'days': days,
        'hours': hours,
        'total_sessions': total_sessions,
        'weekly_hours': weekly_hours,
        'today_sessions_count': today_sessions_count,
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

#Added by Adjii:
@login_required
def student_dashboard(request):
    # 1. Setup the basic grid variables
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    hours = range(8, 19)
    
    user = request.user
    student_group = user.student_group
    
    # 2. Safety check for group
    if not student_group:
        return render(request, 'scheduler/student_dashboard.html', {
            'days': days, 'hours': hours, 'sessions': [],
            'error_message': 'No group assigned.'
        })

    # 3. DEFINE SESSIONS FIRST (This fixes the NameError)
    sessions = ScheduledSession.objects.filter(
        Q(course__group=student_group) | 
        Q(course__filiere=student_group.filiere, course__session_type='CM')
    ).select_related('course', 'room', 'course__teacher')

    # 4. Weekend / Next Up Logic
    now = timezone.localtime()
    today_name = now.strftime('%A')
    current_hour = now.hour
    
    search_day = today_name
    status_label = "NEXT UP"

    if today_name == "Sunday":
        search_day = "Monday"
        status_label = "MONDAY MORNING"
        # Find first class of Monday
        next_class = sessions.filter(day=search_day).order_by('start_hour').first()
    else:
        # Find next class for today
        next_class = sessions.filter(day=today_name, end_hour__gt=current_hour).order_by('start_hour').first()

    # 5. Send everything to the template
    context = {
        'student_group': student_group,
        'sessions': sessions,
        'next_class': next_class,
        'status_label': status_label, # Use this in your HTML badge
        'days': days,
        'hours': hours,
        'today_name': today_name,
        'course_count': sessions.values('course').distinct().count(),
    }
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



"""def student_timetable_view(request):
def student_timetable_view(request):
    # 1. Define the specific time slots from your image
    # We use integer hours to match your database (approximate mapping)
    time_slots = [
        {'label': '09h00 - 10h30', 'start': 9, 'end': 10},
        {'label': '10h45 - 12h15', 'start': 10, 'end': 12}, # Adjusted for logic
        {'label': '12h30 - 14h00', 'start': 12, 'end': 14}, # Lunch
        {'label': '14h15 - 15h45', 'start': 14, 'end': 15},
        {'label': '16h00 - 17h30', 'start': 16, 'end': 17},
    ]

    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    
    # 2. Get all sessions
    all_sessions = ScheduledSession.objects.all()

    # 3. Create a Matrix (Grid) for the template
    # Structure: schedule_grid = [ {'day': 'Lundi', 'slots': [session_or_None, session_or_None...]} ]
    schedule_grid = []

    for day in days:
        day_row = {'day_name': day, 'slots': []}
        
        for slot in time_slots:
            # Find a session that matches this Day AND this Start Hour
            # Note: We filter by Day name (e.g., "Monday") and approximate start hour
            # You might need to adjust 'Monday' vs 'Lundi' depending on what is saved in your DB
            session = all_sessions.filter(
                day__iexact=day,         # Case insensitive match
                start_hour__gte=slot['start'], # Starts around this slot
                start_hour__lt=slot['end']     # Starts before the next slot
            ).first()
            
            day_row['slots'].append(session)
        
        schedule_grid.append(day_row)

    return render(request, 'scheduler/student_timetable.html', {
        'time_slots': time_slots,
        'schedule_grid': schedule_grid
    })""" ##Possibly delete 

# Make sure Q is imported at the top of the file!
from django.db.models import Q 

@login_required
def student_classes(request):
    """List of all courses for the student (CM + TD/TP)"""
    student_group = request.user.student_group
    
    if not student_group:
        return render(request, 'scheduler/student_classes.html', {
            'courses': [],
            'error': 'No group assigned.'
        })

    # Logic: Get courses for THIS Group (TD/TP) OR for the whole Filière (CM)
    courses = Course.objects.filter(
        Q(group=student_group) | 
        Q(filiere=student_group.filiere, group__isnull=True)
    ).select_related('teacher', 'filiere').order_by('name')
    
    context = {
        'courses': courses,
        'student_group': student_group,
    }
    return render(request, 'scheduler/student_classes.html', context)


def add_session(request):
    # Everything below must be INDENTED (Tabbed in)
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('timetable') 
    else:
        form = SessionForm()
    
    return render(request, 'scheduler/add_session.html', {'form': form})
# --- EDIT TEACHER ---
def edit_teacher(request, teacher_id):
    # Find the specific teacher by their ID
    teacher = get_object_or_404(User, pk=teacher_id)
    
    if request.method == 'POST':
        # "instance=teacher" tells Django: "Update THIS specific user"
        form = TeacherEditForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            return redirect('teacher_list')
    else:
        # Pre-fill the form with existing data
        form = TeacherEditForm(instance=teacher)
    
    return render(request, 'scheduler/add_teacher.html', {'form': form, 'title': 'Edit Teacher'})

# --- DELETE TEACHER ---
def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(User, pk=teacher_id)
    
    if request.method == 'POST':
        teacher.delete()
        return redirect('teacher_list')
    
    # Show a confirmation page before deleting
    return render(request, 'scheduler/confirm_delete.html', {'teacher': teacher})




@login_required
def find_rooms(request):
    """Search for available rooms - OPTIMIZED VERSION"""
    available_rooms = []
    search_performed = False
    
    if request.method == 'GET' and any(request.GET.values()):
        search_performed = True
        day = request.GET.get('day')
        start_hour = request.GET.get('start_hour')
        end_hour = request.GET.get('end_hour')
        min_capacity = request.GET.get('min_capacity')
        
        # Start with all rooms
        rooms = Room.objects.all()
        
        # Filter by capacity
        if min_capacity:
            rooms = rooms.filter(capacity__gte=int(min_capacity))
        
        if day and start_hour and end_hour:
            # Get occupied room IDs from scheduled sessions (EFFICIENT)
            occupied_by_sessions = ScheduledSession.objects.filter(
                day=day,
                start_hour__lt=int(end_hour),
                end_hour__gt=int(start_hour)
            ).values_list('room_id', flat=True)
            
            # Get occupied room IDs from approved reservations (EFFICIENT)
            occupied_by_reservations = ReservationRequest.objects.filter(
                day=day,
                status='APPROVED',
                start_hour__lt=int(end_hour),
                end_hour__gt=int(start_hour)
            ).values_list('room_id', flat=True)
            
            # Combine both lists of occupied rooms
            occupied_room_ids = set(occupied_by_sessions) | set(occupied_by_reservations)
            
            # Exclude occupied rooms (SINGLE QUERY)
            available_rooms = rooms.exclude(id__in=occupied_room_ids)
        else:
            # No time criteria - just show rooms matching capacity
            available_rooms = rooms
    
    context = {
        'available_rooms': available_rooms,
        'search_performed': search_performed,
        'days': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        'hours': range(8, 19),
    }
    return render(request, 'scheduler/find_rooms.html', context)



from .models import TeacherUnavailability
from .forms import TeacherUnavailabilityForm

@login_required
def manage_unavailability(request):
    """Teacher can view and manage their unavailability"""
    # Get teacher's existing unavailabilities
    unavailabilities = TeacherUnavailability.objects.filter(teacher=request.user).order_by('day', 'start_hour')
    
    # Handle form submission
    if request.method == 'POST':
        form = TeacherUnavailabilityForm(request.POST)
        if form.is_valid():
            unavailability = form.save(commit=False)
            unavailability.teacher = request.user
            unavailability.save()
            messages.success(request, "Unavailability added successfully!")
            return redirect('manage_unavailability')
    else:
        form = TeacherUnavailabilityForm()
    
    context = {
        'form': form,
        'unavailabilities': unavailabilities,
    }
    return render(request, 'scheduler/manage_unavailability.html', context)

@login_required
def delete_unavailability(request, unavail_id):
    """Delete an unavailability entry"""
    unavailability = get_object_or_404(TeacherUnavailability, id=unavail_id, teacher=request.user)
    
    if request.method == 'POST':
        unavailability.delete()
        messages.success(request, "Unavailability removed!")
        return redirect('manage_unavailability')
    
    return render(request, 'scheduler/confirm_delete_unavailability.html', {'unavailability': unavailability})

def settings_view(request):
    user = request.user

    # 1. Initialize BOTH forms with default data first.
    # This ensures variables always exist, preventing the UnboundLocalError.
    profile_form = ProfileForm(instance=user)
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        # --- SCENARIO A: Updating Profile ---
        if 'update_profile' in request.POST:
            # Re-initialize profile_form with the submitted data
            profile_form = ProfileForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('settings')

        # --- SCENARIO B: Updating Password ---
        elif 'change_password' in request.POST:
            # Re-initialize password_form with the submitted data
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Important: Keep the user logged in
                update_session_auth_hash(request, user) 
                messages.success(request, 'Your password was successfully updated!')
                return redirect('settings')
            else:
                messages.error(request, 'Please correct the error below.')

    # 3. Render the template
    # Since we defined both forms at the very top, this will never crash now!
    context = {
        'profile_form': profile_form,
        'password_form': password_form
    }
    return render(request, 'scheduler/settings.html', context)


# --- Paste this function at the bottom ---
def course_list(request):
    # Fetch all courses
    courses = Course.objects.all()
    return render(request, 'scheduler/course_list.html', {'courses': courses})
# --- EDIT COURSE ---
# --- EDIT COURSE ---
# --- EDIT COURSE ---
def edit_course(request, course_id):
    # Find the course by ID
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        # Load the form with the existing course data (instance=course)
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        # Pre-fill the form
        form = CourseForm(instance=course)
    
    # Reuse the add_course template but with data filled in
    return render(request, 'scheduler/add_course.html', {'form': form, 'is_edit': True})

# --- DELETE COURSE ---
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course.delete()
        return redirect('course_list')
    
    return render(request, 'scheduler/confirm_delete_course.html', {'course': course})



from django.http import HttpResponse
import csv
import json
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

# 1. SIMPLIFIED Helper function
def get_filtered_sessions_simple(request):
    """Simplified version to get sessions"""
    user = request.user
    selected_filiere_id = request.GET.get('filiere')
    
    if user.role == 'A':
        # Admin: all sessions
        queryset = ScheduledSession.objects.all()
        
        # Apply filière filter if specified
        if selected_filiere_id and selected_filiere_id != 'None':
            queryset = queryset.filter(course__filiere_id=selected_filiere_id)
            
    elif user.role == 'T':
        # Teacher: only their sessions
        queryset = ScheduledSession.objects.filter(course__teacher=user)
        
        if selected_filiere_id and selected_filiere_id != 'None':
            queryset = queryset.filter(course__filiere_id=selected_filiere_id)
            
    else:
        # Student
        if not user.student_group:
            return ScheduledSession.objects.none()
        
        queryset = ScheduledSession.objects.filter(
            Q(course__group=user.student_group) | 
            Q(course__filiere=user.student_group.filiere, course__group__isnull=True)
        )
    
    return queryset.select_related('course', 'room', 'course__teacher', 'course__filiere', 'course__group')

# 2. SIMPLIFIED Excel Export (This will work!)
@login_required
def export_excel(request):
    """Export timetable as Excel - SIMPLIFIED VERSION"""
    # Get sessions
    sessions = get_filtered_sessions_simple(request)
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Emploi du Temps"
    
    # Title
    ws['A1'] = "EMPLOI DU TEMPS UNIVERSITAIRE"
    ws['A1'].font = Font(bold=True, size=16, color="366092")
    
    # Info
    ws['A2'] = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A3'] = f"Généré par: {request.user.get_full_name() or request.user.username}"
    ws['A4'] = f"Rôle: {request.user.get_role_display()}"
    
    # Add filter info if applicable
    selected_filiere_id = request.GET.get('filiere')
    if selected_filiere_id and selected_filiere_id != 'None':
        try:
            filiere = Filiere.objects.get(id=selected_filiere_id)
            ws['A5'] = f"Filière: {filiere.name} ({filiere.code})"
        except:
            pass
    
    # Simple list format (easier to debug)
    ws['A7'] = "LISTE DES SÉANCES"
    ws['A7'].font = Font(bold=True, size=14)
    
    # Headers
    headers = ["Cours", "Type", "Enseignant", "Salle", "Jour", "Heure début", "Heure fin", "Groupe/Filière"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=8, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    # Data rows
    row = 9
    for session in sessions:
        # Get group/filière info
        if session.course.group:
            group_info = f"Groupe: {session.course.group.name}"
        else:
            group_info = f"Filière: {session.course.filiere.code}"
        
        # Write data
        ws.cell(row=row, column=1, value=session.course.name)
        ws.cell(row=row, column=2, value=session.course.get_session_type_display())
        ws.cell(row=row, column=3, value=session.course.teacher.get_full_name() or session.course.teacher.username)
        ws.cell(row=row, column=4, value=session.room.name)
        ws.cell(row=row, column=5, value=session.day)
        ws.cell(row=row, column=6, value=f"{session.start_hour}:00")
        ws.cell(row=row, column=7, value=f"{session.end_hour}:00")
        ws.cell(row=row, column=8, value=group_info)
        
        # Color by session type
        fill_color = "FFFFFF"  # Default white
        
        if session.course.session_type == 'CM':
            fill_color = "E2EFDA"  # Light green
        elif session.course.session_type == 'TD':
            fill_color = "FFF2CC"  # Light yellow
        elif session.course.session_type == 'TP':
            fill_color = "DDEBF7"  # Light blue
        
        # Apply color to row
        for col in range(1, 9):
            ws.cell(row=row, column=col).fill = PatternFill(
                start_color=fill_color, end_color=fill_color, fill_type="solid"
            )
        
        row += 1
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        adjusted_width = min(max_length + 2, 30)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="emploi_du_temps.xlsx"'
    wb.save(response)
    return response

from django.template.loader import render_to_string
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
import pytz

# 3. PDF Export
@login_required
def export_pdf(request):
    """Export timetable as PDF with complete grid layout"""
    # Get sessions using the same logic as export_excel
    sessions = get_filtered_sessions_simple(request)
    
    # Get selected filière for PDF title
    selected_filiere_id = request.GET.get('filiere')
    selected_filiere = None
    if selected_filiere_id and selected_filiere_id != 'None':
        try:
            selected_filiere = Filiere.objects.get(id=selected_filiere_id)
        except Filiere.DoesNotExist:
            pass
    
    # Prepare data for PDF - COMPLETE TIME SLOTS VERSION
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    # Define ALL possible time slots (standard university schedule)
    time_slots = [
        {"start": 8, "end": 10, "label": "8:00-10:00"},
        {"start": 10, "end": 12, "label": "10:00-12:00"},
        {"start": 12, "end": 14, "label": "12:00-14:00"},
        {"start": 14, "end": 16, "label": "14:00-16:00"},
        {"start": 16, "end": 18, "label": "16:00-18:00"},
        {"start": 18, "end": 20, "label": "18:00-20:00"},
    ]
    
    # Organize sessions by day and start hour for quick lookup
    session_dict = {}
    for session in sessions:
        day_key = session.day
        if day_key not in session_dict:
            session_dict[day_key] = {}
        session_dict[day_key][session.start_hour] = session
    
    # Create table data and track session cells for styling
    table_data = []
    session_cells_info = []  # Store session cell information separately
    
    # Header row
    header_row = ["TIME"]
    for day in days:
        header_row.append(day[:3].upper())
    table_data.append(header_row)
    
    # Add rows for each time slot
    for slot_idx, slot in enumerate(time_slots):
        row_idx = slot_idx + 1  # +1 for header row
        row = [slot["label"]]
        
        for day_idx, day in enumerate(days):
            col_idx = day_idx + 1  # +1 for TIME column
            cell_content = ""
            
            # Check if there's a session starting in this time slot
            if day in session_dict:
                # Check all hours in this slot for starting sessions
                for hour in range(slot["start"], slot["end"]):
                    if hour in session_dict[day]:
                        session = session_dict[day][hour]
                        
                        # Format session info - cleaner formatting
                        session_type_display = session.course.get_session_type_display()
                        
                        # Teacher name
                        teacher_name = session.course.teacher.get_full_name() or session.course.teacher.username
                        if len(teacher_name) > 15:
                            teacher_name = teacher_name.split()[0]
                        
                        # Course name
                        course_name = session.course.name
                        if len(course_name) > 20:
                            course_name = course_name[:17] + "..."
                        
                        cell_content = f"<b>{course_name}</b><br/>"
                        cell_content += f"{session_type_display}<br/>"
                        cell_content += f"Room: {session.room.name}<br/>"
                        cell_content += f"Prof: {teacher_name}"
                        
                        # Store session cell info for styling
                        session_cells_info.append({
                            'row': row_idx,
                            'col': col_idx,
                            'session': session
                        })
                        break
            
            row.append(cell_content)
        
        table_data.append(row)
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    
    # Set filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if selected_filiere:
        filename = f"timetable_{selected_filiere.code}_{timestamp}.pdf"
    elif request.user.role == 'T':
        filename = f"timetable_teacher_{request.user.username}_{timestamp}.pdf"
    elif request.user.role == 'S':
        filename = f"timetable_student_{request.user.username}_{timestamp}.pdf"
    else:
        filename = f"timetable_all_{timestamp}.pdf"
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=0.3*inch,
        leftMargin=0.3*inch,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=colors.HexColor('#1e3a8a')
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=15,
        textColor=colors.HexColor('#475569')
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        textColor=colors.white
    )
    
    time_style = ParagraphStyle(
        'TimeStyle',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    session_style = ParagraphStyle(
        'SessionStyle',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        leading=7
    )
    
    empty_style = ParagraphStyle(
        'EmptyStyle',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    
    # Create story (content)
    story = []
    
    # Title
    if selected_filiere:
        title = f"UNIVERSITY TIMETABLE - {selected_filiere.name}"
    elif request.user.role == 'T':
        title = f"TEACHER TIMETABLE - {request.user.get_full_name() or request.user.username}"
    elif request.user.role == 'S':
        title = f"STUDENT TIMETABLE - {request.user.username}"
    else:
        title = "COMPLETE UNIVERSITY TIMETABLE"
    
    story.append(Paragraph(title, title_style))
    
    # Subtitle
    subtitle = f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Total Sessions: {sessions.count()}"
    story.append(Paragraph(subtitle, subtitle_style))
    
    # Convert table data to Paragraph objects
    formatted_table_data = []
    for row_idx, row in enumerate(table_data):
        formatted_row = []
        for col_idx, cell in enumerate(row):
            if row_idx == 0:  # Header row
                formatted_row.append(Paragraph(cell, header_style))
            elif col_idx == 0:  # Time column
                formatted_row.append(Paragraph(cell, time_style))
            elif cell:  # Session cell
                formatted_row.append(Paragraph(cell, session_style))
            else:  # Empty cell
                formatted_row.append(Paragraph("", empty_style))
        formatted_table_data.append(formatted_row)
    
    # Create timetable table
    table = Table(formatted_table_data, 
                  colWidths=[0.9*inch] + [1.5*inch] * len(days),
                  rowHeights=[0.4*inch] + [1.2*inch] * (len(time_slots)))
    
    # Apply table styling
    table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Time column styling
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('VALIGN', (0, 1), (0, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (0, -1), 8),
        
        # Grid lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94a3b8')),
        
        # Cell alignment and padding for all cells
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (1, 1), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])
    
    # Apply background colors to session cells
    for cell_info in session_cells_info:
        session = cell_info['session']
        
        # Set background color based on session type
        if session.course.session_type == 'CM':
            bg_color = colors.HexColor('#dbeafe')  # Light blue for CM
        elif session.course.session_type == 'TD':
            bg_color = colors.HexColor('#d1fae5')  # Light green for TD
        elif session.course.session_type == 'TP':
            bg_color = colors.HexColor('#fef3c7')  # Light yellow for TP
        else:
            bg_color = colors.HexColor('#f1f5f9')  # Light gray
        
        table_style.add('BACKGROUND', 
                      (cell_info['col'], cell_info['row']),
                      (cell_info['col'], cell_info['row']),
                      bg_color)
    
    table.setStyle(table_style)
    
    # Add table to story
    story.append(table)
    story.append(Spacer(1, 12))
    
    # Add legend
    legend_style = ParagraphStyle(
        'LegendStyle',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=4,
        alignment=TA_CENTER
    )
    
    legend_text = """
    <b>Legend:</b> 
    <font color="#1d4ed8">■ CM (Lecture)</font> | 
    <font color="#047857">■ TD (Tutorial)</font> | 
    <font color="#b45309">■ TP (Lab)</font>
    """
    story.append(Paragraph(legend_text, legend_style))
    
    # Add statistics
    total_hours = sum((s.end_hour - s.start_hour) for s in sessions)
    unique_days = len(set(s.day for s in sessions))
    unique_rooms = len(set(s.room.name for s in sessions))
    
    stats_text = f"""
    <b>Statistics:</b> Total Sessions: {sessions.count()} | Total Hours: {total_hours} | Days: {unique_days} | Rooms Used: {unique_rooms}
    """
    story.append(Paragraph(stats_text, legend_style))
    
    # Build PDF
    try:
        doc.build(story)
        return response
    except Exception as e:
        # Simple error response
        import traceback
        error_details = traceback.format_exc()
        return HttpResponse(f"PDF Generation Error: {str(e)}\n\nDetails:\n{error_details}", 
                          content_type='text/plain')