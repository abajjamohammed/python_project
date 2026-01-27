from django.shortcuts import render
from django.contrib.auth.decorators import login_required  # <--- NEW IMPORT
from .models import Room, Course, ReservationRequest, User, ScheduledSession
from django.db.models import Count

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