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
from .forms import SessionForm
from django.shortcuts import redirect
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TeacherForm, TeacherEditForm # Import the new form
from .models import TeacherUnavailability
from .forms import TeacherUnavailabilityForm
from .forms import ProfileForm
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm




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
    next_class = sessions.first()
    
    context = {
        'sessions': sessions,
        'days': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        'hours': [9,10,11,12,13,14,15,16],
        'next_class': next_class,
        'student_group': request.user.student_group,
        'time_slots': [
            {'label': '(9, 10):00', 'start': 9},
            {'label': '(10, 12):00', 'start': 10},
            {'label': '(14, 16):00', 'start': 14},
        ]
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
    sessions = ScheduledSession.objects.all()
    events = []
    
    # Date mapping logic... (Keep your existing date mapping here)
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
        day_num = day_mapping.get(session.day, "05")
        
        events.append({
            'title': session.course.name,
            # We send extra data to display inside the card
            'extendedProps': {
                'room': session.room.name,
                'group': session.course.group_name, # <--- Added Group Name
                'teacher': session.course.teacher.username
            },
            'start': f"2024-02-{day_num}T{session.start_hour:02d}:00:00",
            'end': f"2024-02-{day_num}T{session.end_hour:02d}:00:00",
            # We don't set colors here anymore. CSS will handle the "Blue" look.
        })

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
def student_dashboard(request):
    # 1. Get student info and basic counts
    student_group = request.user.student_group
    sessions = ScheduledSession.objects.filter(course__group_name=student_group)
    course_count = Course.objects.filter(group_name=student_group).count()
    
    # 2. Time-Table display settings
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # 3. SMART "NEXT UP" LOGIC
    now = datetime.now()
    current_day = now.strftime("%A")
    current_hour = now.hour
    next_class = None

    if sessions.exists():
        # A. Look for classes left TODAY
        today_remaining = sessions.filter(day=current_day, start_hour__gt=current_hour).order_by('start_hour')
        
        if today_remaining.exists():
            next_class = today_remaining.first()
        else:
            # B. Look for classes later this week
            current_day_index = day_order.index(current_day) if current_day in day_order else -1
            later_this_week = sessions.exclude(day=current_day).filter(
                day__in=day_order[current_day_index + 1:]
            )
            
            if later_this_week.exists():
                next_class = sorted(list(later_this_week), key=lambda x: (day_order.index(x.day), x.start_hour))[0]
            else:
                # C. LOOP BACK: Monday morning
                next_class = sorted(list(sessions), key=lambda x: (day_order.index(x.day), x.start_hour))[0]

    # Context for the dashboard
    context = {
        'sessions': sessions,
        'course_count': course_count, # Correctly displays 4 courses
        'next_class': next_class,     # Looping spotlight
        'student_group': student_group,
        'days': day_order,
        'hours': [9, 10, 11, 12, 13, 14, 15, 16], # Compacted to match reference
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
def student_classes(request):
    # Fetch all courses assigned to this student's group
    courses = Course.objects.filter(group_name=request.user.student_group)
    
    context = {
        'courses': courses,
        'student_group': request.user.student_group,
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

from datetime import datetime

def get_next_spotlight_session(student_group):
    # 1. Define day order to handle sorting
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # 2. Get current time and day
    now = datetime.now()
    current_day = now.strftime("%A")
    current_hour = now.hour

    # 3. Get all sessions for this student
    all_sessions = ScheduledSession.objects.filter(course__group_name=student_group)
    
    if not all_sessions.exists():
        return None

    # 4. Filter for sessions LATER today
    today_remaining = all_sessions.filter(day=current_day, start_hour__gt=current_hour).order_by('start_hour')
    
    if today_remaining.exists():
        return today_remaining.first()

    # 5. Filter for sessions LATER this week
    current_day_index = day_order.index(current_day) if current_day in day_order else -1
    later_this_week = all_sessions.exclude(day=current_day).filter(
        day__in=day_order[current_day_index + 1:]
    )
    
    # Sort these by day index then hour
    if later_this_week.exists():
        return sorted(list(later_this_week), key=lambda x: (day_order.index(x.day), x.start_hour))[0]

    # 6. LOOP BACK: If nothing is left this week, get the very first session on Monday
    return sorted(list(all_sessions), key=lambda x: (day_order.index(x.day), x.start_hour))[0]