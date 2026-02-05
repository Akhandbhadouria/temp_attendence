from django.db import models
from django.contrib.auth.models import User
import datetime




class UserImages(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    face_image = models.ImageField(upload_to='user_faces/')
    
    def __str__(self):
        return self.user.username

class Principal(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    school_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Principal: {self.user.username}"

class Teacher(models.Model):
    DEPARTMENT_CHOICES = (
        ('CS', 'Computer Science'),
        ('MATH', 'Mathematics'),
        ('PHY', 'Physics'),
        ('CHEM', 'Chemistry'),
        ('BIO', 'Biology'),
        ('ENG', 'English'),
        ('HIST', 'History'),
        ('GEO', 'Geography'),
        ('ECON', 'Economics'),
        ('COMM', 'Commerce'),
        ('PE', 'Physical Education'),
        ('ART', 'Arts'),
        ('OTHER', 'Other'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    principal = models.ForeignKey(Principal, on_delete=models.CASCADE, related_name='teachers')
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, default='OTHER')

    def __str__(self):
        return f"{self.name} (School: {self.principal.school_name})"

class Timetable(models.Model):
    DAYS_OF_WEEK = (
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
    )

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='timetables')
    subject = models.CharField(max_length=100)
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.subject} - {self.teacher.name}"

class TeacherAttendance(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Present')

    def __str__(self):
        return f"{self.teacher.name} - {self.date}"

class ClassSession(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='class_sessions')
    timetable = models.ForeignKey(Timetable, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_active_duration = models.DurationField(null=True, blank=True, default=datetime.timedelta(0))
    status = models.CharField(max_length=20, default='Ongoing') # Ongoing, Completed
    monitoring_resumption_count = models.IntegerField(default=1) # Track sessions/logins

    def __str__(self):
        return f"{self.teacher.name} - {self.timetable.subject if self.timetable else 'Extra Class'} - {self.start_time.date()}"