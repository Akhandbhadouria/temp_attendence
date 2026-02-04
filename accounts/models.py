from django.db import models
from django.contrib.auth.models import User




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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    principal = models.ForeignKey(Principal, on_delete=models.CASCADE, related_name='teachers')
    name = models.CharField(max_length=100)

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