import os
import django
import datetime
import csv
from django.utils import timezone
from django.db.models import Count, Sum

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'facere.settings')
django.setup()

from accounts.models import Teacher, ClassSession, Timetable, TeacherAttendance

def generate_defaulter_report(filename='defaulter_report.csv'):
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today = now.date()
    
    teachers = Teacher.objects.all()
    
    day_map_idx = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
    
    report_data = []
    
    headers = [
        'Teacher Name', 'Department', 'Attendance Consistency (%)', 'Completion Rate (%)',
        'Late Entries', 'Early Exits', 'Interruptions', 'Risk Score', 'Status'
    ]
    
    for teacher in teachers:
        # Fetch sessions for current month
        sessions = ClassSession.objects.filter(
            teacher=teacher, 
            start_time__gte=start_of_month
        )
        completed_sessions = sessions.filter(status='Completed')
        
        # 1. Calculate Consistency
        total_scheduled_minutes = 0
        total_active_minutes = 0
        late_entries = 0
        early_exits = 0
        interruptions = 0
        
        for session in sessions:
            if session.timetable:
                s_start = session.timetable.start_time
                s_end = session.timetable.end_time
                
                # Active minutes
                if session.status == 'Completed' and session.total_active_duration:
                    total_active_minutes += session.total_active_duration.total_seconds() / 60
                    
                # Scheduled minutes
                # Use a dummy date to calc duration
                d_start = datetime.datetime.combine(datetime.date.today(), s_start)
                d_end = datetime.datetime.combine(datetime.date.today(), s_end)
                total_scheduled_minutes += (d_end - d_start).total_seconds() / 60
                
                # Late Entry Check (> 5 mins)
                a_start = session.start_time.astimezone(timezone.get_current_timezone()).time()
                if (a_start.hour * 60 + a_start.minute) > (s_start.hour * 60 + s_start.minute + 5):
                    late_entries += 1
                
                # Early Exit Check
                if session.end_time:
                    a_end = session.end_time.astimezone(timezone.get_current_timezone()).time()
                    if (a_end.hour * 60 + a_end.minute) < (s_end.hour * 60 + s_end.minute):
                        early_exits += 1
            
            # Interruptions (Resumption Count - 1)
            if session.monitoring_resumption_count > 1:
                interruptions += (session.monitoring_resumption_count - 1)

        consistency = 0
        if total_scheduled_minutes > 0:
            consistency = round((total_active_minutes / total_scheduled_minutes) * 100, 1)
            
        # 2. Completion Rate
        # Calculate how many classes were scheduled in the timetable for this month so far
        scheduled_classes_count = 0
        timetables = teacher.timetables.all()
        temp_date = start_of_month.date()
        while temp_date <= today:
            for tt in timetables:
                if temp_date.weekday() == day_map_idx.get(tt.day):
                    scheduled_classes_count += 1
            temp_date += datetime.timedelta(days=1)
            
        actual_completed = completed_sessions.count()
        completion_rate = 0
        if scheduled_classes_count > 0:
            completion_rate = round((actual_completed / scheduled_classes_count) * 100, 1)
            
        # --- Scoring Logic ---
        risk_score = 0
        
        # Attendance Score
        if consistency < 75:
            risk_score += 3
        elif 75 <= consistency <= 85:
            risk_score += 2
            
        # Early Exits
        if early_exits > 3:
            risk_score += 2
            
        # Late Entries
        if late_entries > 3:
            risk_score += 1
            
        # Interruptions
        if interruptions > 0:
            risk_score += 2
            
        # Class Completion
        if completion_rate < 80:
            risk_score += 2
            
        # --- Defaulter Rule ---
        # Marked Defaulter if:
        # Consistency < 70% OR Risk Score >= 6 OR Repeated Early Exits (say > 3) + Interruptions
        is_defaulter = False
        if consistency < 70:
            is_defaulter = True
        elif risk_score >= 6:
            is_defaulter = True
        elif early_exits > 3 and interruptions > 0:
            is_defaulter = True
            
        status = 'DEFAULTER' if is_defaulter else ('Warning' if risk_score >= 3 else 'Good Standing')
        
        report_data.append({
            'Teacher Name': teacher.name,
            'Department': teacher.get_department_display(),
            'Attendance Consistency (%)': f"{consistency}%",
            'Completion Rate (%)': f"{completion_rate}%",
            'Late Entries': late_entries,
            'Early Exits': early_exits,
            'Interruptions': interruptions,
            'Risk Score': risk_score,
            'Status': status
        })
        
    # Write to CSV
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in report_data:
            writer.writerow(row)
            
    print(f"Report generated: {filename}")
    return filename

if __name__ == "__main__":
    generate_defaulter_report()
