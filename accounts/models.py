from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
import datetime
import os
import shutil




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


class PrincipalDocument(models.Model):
    """Stores policy/handbook documents uploaded by a Principal for their RAG chatbot."""
    principal = models.ForeignKey(Principal, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='principal_docs/')
    file_type = models.CharField(max_length=10)  # pdf, md, txt
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_ingested = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.principal.school_name})"


# ── Signal: Remove ChromaDB chunks when a document is deleted ──
@receiver(post_delete, sender=PrincipalDocument)
def remove_document_from_vector_store(sender, instance, **kwargs):
    """When a PrincipalDocument is deleted, remove its chunks from ChromaDB."""
    try:
        import chromadb
        from django.conf import settings as app_settings
        chroma_dir = os.path.join(app_settings.BASE_DIR, "chroma_db")
        client = chromadb.PersistentClient(path=chroma_dir)
        collection_name = f"principal_{instance.principal.id}"
        try:
            collection = client.get_collection(collection_name)
            # Delete all chunks that belong to this document file
            collection.delete(where={"source_file": os.path.basename(instance.file.name)})
        except Exception:
            pass  # Collection may not exist yet
    except Exception:
        pass


# ── Signal: Auto-delete User and face data when Teacher is deleted ──
@receiver(post_delete, sender=Teacher)
def delete_teacher_user_and_data(sender, instance, **kwargs):
    """When a Teacher is deleted, also remove the linked User and their face embeddings."""
    user = instance.user
    username = user.username

    # Delete face embedding data from disk
    from django.conf import settings as app_settings
    data_dir = os.path.join(app_settings.BASE_DIR, "data", "users", username)
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)

    # Delete the User (this also cascades to UserImages via ForeignKey)
    user.delete()