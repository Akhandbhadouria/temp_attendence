import face_recognition
import base64
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.files.base import ContentFile
from .models import UserImages, User, Principal, Teacher, Timetable, TeacherAttendance, ClassSession
from django.utils import timezone
import datetime
import calendar
import os 
import numpy as np 
import cv2 
from .utils.face_embedding import get_embedding 
from .utils.face_matcher import match_face
from django.conf import settings 
from django.contrib.auth import authenticate, login 
from django.contrib.auth.decorators import login_required 
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate

def home(request):
    return render(request, 'home.html')

@csrf_exempt
def principal_register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        school_name = request.POST['school_name']

        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username already exists.'})

        user = User.objects.create_user(username=username, password=password)
        Principal.objects.create(user=user, school_name=school_name)
        
        login(request, user)  # Log them in automatically
        return JsonResponse({'status': 'success', 'message': 'Principal registered successfully!', 'redirect': '/principal/dashboard/'})

    return render(request, 'principal_register.html')

def principal_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if hasattr(user, 'principal'):
                login(request, user)
                return redirect('principal_dashboard')
            else:
                 return render(request, 'principal_login.html', {'error': 'Not a valid Principal account'})
        else:
             return render(request, 'principal_login.html', {'error': 'Invalid credentials'})
    return render(request, 'principal_login.html')

@login_required
def principal_dashboard(request):
    from collections import defaultdict
    
    principal = request.user.principal
    teachers = principal.teachers.all().order_by('department', 'name')
    
    # Group teachers by department
    teachers_by_dept = defaultdict(list)
    for teacher in teachers:
        dept_name = teacher.get_department_display()
        teachers_by_dept[dept_name].append(teacher)
    
    # Convert to regular dict and sort by department name
    teachers_by_dept = dict(sorted(teachers_by_dept.items()))

    # Calculate teachers present today
    from django.utils import timezone
    from .models import TeacherAttendance
    today = timezone.now().date()
    
    present_today_count = TeacherAttendance.objects.filter(
        teacher__principal=principal,
        date=today
    ).values('teacher').distinct().count()
    
    total_teachers = teachers.count()
    absent_count = total_teachers - present_today_count
    print(f"DEBUG: Total={total_teachers}, Present={present_today_count}, Absent={absent_count}")
    
    return render(request, 'principal_dashboard.html', {
        'teachers': teachers,
        'teachers_by_dept': teachers_by_dept,
        'present_today_count': present_today_count,
        'absent_count': absent_count
    })

def teacher_login_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            if hasattr(user, 'teacher'):
                login(request, user)
                return redirect('teacher_dashboard')
            else:
                return render(request, 'teacher_login.html', {'error': 'This account is not a Teacher account.'})
        else:
             return render(request, 'teacher_login.html', {'error': 'Invalid username or password'})
    
    return render(request, 'teacher_login.html')

@csrf_exempt
@login_required
def add_teacher(request):
    # Check if user is a principal
    try:
        principal = request.user.principal
    except:
        return JsonResponse({'status': 'error', 'message': 'You must be logged in as a principal to add teachers.'})
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            department = request.POST.get('department', 'OTHER')
            face_image_data = request.POST.get('face_image', '')
            
            # Validate required fields
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Teacher name is required.'})
            if not username:
                return JsonResponse({'status': 'error', 'message': 'Username is required.'})
            if not password:
                return JsonResponse({'status': 'error', 'message': 'Password is required.'})
            if not face_image_data:
                return JsonResponse({'status': 'error', 'message': 'Face image is required. Please capture a photo.'})

            # Check if username already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': f'Username "{username}" is already taken. Please choose a different username.'})

            # Create User with provided password
            user = User.objects.create_user(username=username, password=password) 
            
            # Create Teacher linked to Principal with department
            Teacher.objects.create(user=user, principal=principal, name=name, department=department)

            # --- NEW REGISTRATION LOGIC START ---
            face_data_str = face_image_data.split(",")[1]
            image_data = base64.b64decode(face_data_str)
            
            # 1. Save Face Image to UserImages (for UI display)
            face_image = ContentFile(image_data, name=f'{username}_face.jpg')
            UserImages.objects.create(user=user, face_image=face_image)

            # 2. Process for Embedding (New Logic)
            # Convert base64 to OpenCV image
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Get embedding
            emb = get_embedding(frame)
            
            if emb is None:
                # If we fail to get embedding, we might want to rollback user creation
                # But for now, let's just warn or handle appropriately. 
                # Since face_recognition in views.py (old logic) might handle it differently.
                # But get_embedding uses the same library.
                pass 

            if emb is not None:
                # Save embedding to disk: project_root/data/users/{username}/embeddings.npy
                # We'll use username as the identifier
                project_root = settings.BASE_DIR
                save_dir = os.path.join(project_root, "data", "users", username)
                os.makedirs(save_dir, exist_ok=True)
                np.save(os.path.join(save_dir, "embeddings.npy"), emb)
            # --- NEW REGISTRATION LOGIC END ---

            return JsonResponse({'status': 'success', 'message': f'Teacher {name} registered successfully!'})
        except KeyError as e:
            return JsonResponse({'status': 'error', 'message': f'Missing required field: {str(e)}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'})

    return render(request, 'add_teacher.html')

@csrf_exempt
@login_required
def delete_teacher(request, teacher_id):
    if request.method == 'POST':
        try:
            # Get the teacher and verify it belongs to this principal
            teacher = Teacher.objects.get(id=teacher_id, principal=request.user.principal)
            
            # Get the associated user
            user = teacher.user
            
            # Delete the teacher (this will cascade to timetables and attendance records)
            teacher.delete()
            
            # Delete the associated user and their face images
            user.delete()
            
            return JsonResponse({'status': 'success', 'message': 'Teacher deleted successfully!'})
        except Teacher.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Teacher not found or unauthorized.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        face_image_data = request.POST['face_image']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found.'})

        if not hasattr(user, 'teacher'):
             return JsonResponse({'status': 'error', 'message': 'This is not a teacher account.'})

        face_image_data = face_image_data.split(",")[1]
        uploaded_image = ContentFile(base64.b64decode(face_image_data), name=f'{username}_temp.jpg')

        try:
            uploaded_face_image = face_recognition.load_image_file(uploaded_image)
            uploaded_face_encodings = face_recognition.face_encodings(uploaded_face_image)

            if len(uploaded_face_encodings) > 0:
                uploaded_face_encoding = uploaded_face_encodings[0]
                user_image = UserImages.objects.filter(user=user).first()
                if user_image:
                    stored_face_image = face_recognition.load_image_file(user_image.face_image.path)
                    stored_face_encodings = face_recognition.face_encodings(stored_face_image)
                    
                    if len(stored_face_encodings) > 0:
                        stored_face_encoding = stored_face_encodings[0]
                        match = face_recognition.compare_faces([stored_face_encoding], uploaded_face_encoding)
                        if match[0]:
                            login(request, user) # Optional: creates session
                            return JsonResponse({'status': 'success', 'message': 'Login successful!', 'redirect': '/teacher/dashboard/'}) # Redirect to a teacher dashboard?
                        else:
                            return JsonResponse({'status': 'error', 'message': 'Face recognition failed.'})
                    else:
                        return JsonResponse({'status': 'error', 'message': 'No face found in stored image.'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'No registered face found.'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'No face detected in uploaded image.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing image: {str(e)}'})
            
        return JsonResponse({'status': 'error', 'message': 'Face recognition failed.'})
   
    return render(request, 'login.html')

@login_required
def teacher_dashboard(request):
    try:
        teacher = request.user.teacher
        timetable = teacher.timetables.all().order_by('start_time')
        
        # Group by day for the dashboard view
        from collections import defaultdict
        
        # Order of days for display
        day_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        day_mapping = dict(Timetable.DAYS_OF_WEEK)
        
        # Bucket slots by day code
        temp_schedule = defaultdict(list)
        for slot in timetable:
            temp_schedule[slot.day].append(slot)
            
        # Create ordered dictionary with full day names
        grouped_schedule = {}
        for code in day_order:
            if code in temp_schedule:
                full_name = day_mapping.get(code, code)
                grouped_schedule[full_name] = temp_schedule[code]
        
        # Check for any ongoing sessions
        active_session = ClassSession.objects.filter(teacher=teacher, status='Ongoing').first()
        
        return render(request, 'teacher_dashboard.html', {
            'teacher': teacher, 
            'timetable': timetable,
            'grouped_schedule': grouped_schedule,
            'active_session': active_session
        })
    except Exception as e:
        print(e)
        return redirect('home')

@login_required
def schedule_teacher(request, teacher_id):
    try:
        # Ensure the teacher belongs to the logged-in principal
        teacher = Teacher.objects.get(id=teacher_id, principal=request.user.principal)
        
        if request.method == 'POST':
            subject = request.POST.get('subject')
            day = request.POST.get('day')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            
            Timetable.objects.create(
                teacher=teacher,
                subject=subject,
                day=day,
                start_time=start_time,
                end_time=end_time
            )
            return redirect('schedule_teacher', teacher_id=teacher_id)
            
        timetable = Timetable.objects.filter(teacher=teacher).order_by('day', 'start_time')
        return render(request, 'schedule_teacher.html', {'teacher': teacher, 'timetable': timetable})
    except Teacher.DoesNotExist:
        return redirect('principal_dashboard')

@login_required
def delete_schedule(request, timetable_id):
    if request.method == 'POST':
        try:
            # Ensure the slot belongs to a teacher managed by the logged-in principal
            slot = Timetable.objects.get(id=timetable_id)
            if slot.teacher.principal == request.user.principal:
                teacher_id = slot.teacher.id
                slot.delete()
                messages.success(request, "Class removed from schedule.")
                return redirect('schedule_teacher', teacher_id=teacher_id)
        except Timetable.DoesNotExist:
            pass
    return redirect('principal_dashboard')

@login_required
def delete_all_schedule(request, teacher_id):
    if request.method == 'POST':
        try:
            teacher = Teacher.objects.get(id=teacher_id, principal=request.user.principal)
            Timetable.objects.filter(teacher=teacher).delete()
            messages.success(request, f"All scheduled classes for {teacher.name} have been cleared.")
            return redirect('schedule_teacher', teacher_id=teacher_id)
        except Teacher.DoesNotExist:
            pass
    return redirect('principal_dashboard')

@login_required
def teacher_profile(request):
    try:
        teacher = request.user.teacher
        face_image = UserImages.objects.filter(user=request.user).first()
        
        # Calculate Stats for Current Month
        now = timezone.now()
        current_year = now.year
        current_month = now.month
        
        # 1. Total Present (This Month)
        attendance_records = TeacherAttendance.objects.filter(
            teacher=teacher, 
            date__year=current_year, 
            date__month=current_month
        )
        total_present = attendance_records.count()
        
        # 2. Late Attendance
        late_count = 0
        day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
        
        for record in attendance_records:
            day_str = day_map[record.date.weekday()]
            # Find earliest class for this day
            first_class = teacher.timetables.filter(day=day_str).order_by('start_time').first()
            
            attendance_time = record.time
            # Standard cutoff 9:00 AM if no class, else class start time
            cutoff_time = datetime.time(9, 0, 0)
            if first_class:
                cutoff_time = first_class.start_time
            
            if attendance_time > cutoff_time:
                late_count += 1

        # 3. Total Absent (Working days passed - Present days)
        # Assume Mon-Sat are working days
        valid_workdays = 0
        today_date = now.date()
        cal = calendar.monthcalendar(current_year, current_month)
        
        for week in cal:
            for day in week:
                if day == 0: continue
                current_date = datetime.date(current_year, current_month, day)
                if current_date > today_date:
                    continue
                if current_date.weekday() < 6: # 0-5 is Mon-Sat
                    valid_workdays += 1
        
        total_absent = valid_workdays - total_present
        if total_absent < 0: total_absent = 0

        # 4. Attendance Rate
        attendance_rate = 0 
        if valid_workdays > 0:
            attendance_rate = int((total_present / valid_workdays) * 100)

        # 5. Class History (Completed Sessions)
        class_history = ClassSession.objects.filter(teacher=teacher, status='Completed').order_by('-start_time')
        
        date_filter = request.GET.get('date')
        if date_filter:
            class_history = class_history.filter(start_time__date=date_filter)

        # 6. Today's Classes
        today_str = day_map[now.weekday()]
        today_classes = teacher.timetables.filter(day=today_str).order_by('start_time')

        context = {
            'teacher': teacher, 
            'face_image': face_image,
            'total_present': total_present,
            'late_attendance': late_count,
            'total_absent': total_absent,
            'undertime': 0, # Placeholder
            'attendance_rate': attendance_rate,
            'class_history': class_history,
            'today_classes': today_classes,
            'date_filter': date_filter
        }

        return render(request, 'teacher_profile.html', context)
    except Exception as e:
        print(e)
        return redirect('home')

@login_required
def previous_records_teacher(request):
    try:
        teacher = request.user.teacher
        # All completed sessions
        all_sessions = ClassSession.objects.filter(teacher=teacher, status='Completed').order_by('-start_time')
        
        context = {
            'teacher': teacher,
            'sessions': all_sessions
        }
        return render(request, 'previous_records_teacher.html', context)
    except:
        return redirect('home')
@csrf_exempt

@login_required
def mark_attendance(request):
    if request.method == 'POST':
        try:
            face_image_data = request.POST['face_image']
            user = request.user
            
            if not hasattr(user, 'teacher'):
                 return JsonResponse({'status': 'error', 'message': 'Only teachers can mark attendance.'})

            teacher = user.teacher
            
            # Check if attendance already marked for today
            from django.utils import timezone
            today = timezone.now().date()
            if TeacherAttendance.objects.filter(teacher=teacher, date=today).exists():
                 return JsonResponse({'status': 'error', 'message': 'Attendance already marked for today.'})

            # Verify Face
            face_data_str = face_image_data.split(",")[1]
            image_data = base64.b64decode(face_data_str)
            
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            live_emb = get_embedding(frame)
            
            if live_emb is None:
                 return JsonResponse({'status': 'error', 'message': 'No face detected in the image.'})
            
            # Load stored embedding
            project_root = settings.BASE_DIR
            embedding_path = os.path.join(project_root, "data", "users", user.username, "embeddings.npy")
            
            if not os.path.exists(embedding_path):
                 return JsonResponse({'status': 'error', 'message': 'Face registration data not found. Please contact admin to re-register.'})
            
            try:
                stored_emb = np.load(embedding_path)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': 'Error loading face data.'})
            
            # Match
            is_match = match_face(stored_emb, live_emb)
            
            if is_match:
                 # Log Attendance
                 TeacherAttendance.objects.create(teacher=teacher)
                 return JsonResponse({'status': 'success', 'message': 'Attendance marked successfully!'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Face verification failed. Please try again.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # Ensure user is a teacher for GET too if the template depends on it
    if hasattr(request.user, 'teacher'):
        return render(request, 'mark_attendance.html', {'teacher': request.user.teacher})
    return redirect('login')
@login_required
def start_class(request, timetable_id):
    try:
        teacher = request.user.teacher
        timetable = Timetable.objects.get(id=timetable_id, teacher=teacher)
        
        # Security Check: Enforce scheduled time and day
        now = timezone.localtime(timezone.now())
        current_time = now.time()
        current_day_name = now.strftime('%A')
        day_map = {
            'Monday': 'MON', 'Tuesday': 'TUE', 'Wednesday': 'WED', 
            'Thursday': 'THU', 'Friday': 'FRI', 'Saturday': 'SAT'
        }
        current_day_code = day_map.get(current_day_name)

        if timetable.day != current_day_code:
            messages.error(request, f"Access Denied: This class is scheduled for {timetable.get_day_display()}, but today is {current_day_name}.")
            return redirect('teacher_dashboard')
            
        if not (timetable.start_time <= current_time <= timetable.end_time):
            messages.error(request, f"Access Denied: You can only start this class during its scheduled time ({timetable.start_time.strftime('%I:%M %p')} - {timetable.end_time.strftime('%I:%M %p')}).")
            return redirect('teacher_dashboard')
        
        # Check if a session already exists for this specific timetable slot today
        existing_session = ClassSession.objects.filter(
            teacher=teacher,
            timetable=timetable,
            start_time__date=now.date()
        ).first()

        if existing_session:
            # If already ongoing, just redirect
            if existing_session.status == 'Ongoing':
                return redirect('live_class_monitoring')
            else:
                # Resume the completed session
                existing_session.status = 'Ongoing'
                existing_session.save()
                return redirect('live_class_monitoring')

        # Create new session if none exists for today
        ClassSession.objects.create(
            teacher=teacher,
            timetable=timetable,
            status='Ongoing',
            total_active_duration=datetime.timedelta(0),
            monitoring_resumption_count=0  # Will be incremented on monitoring page load
        )
        return redirect('live_class_monitoring')
    except Exception as e:
        messages.error(request, f"Error starting class: {e}")
        return redirect('teacher_dashboard')

@login_required
def end_class(request):
    try:
        teacher = request.user.teacher
        session = ClassSession.objects.filter(teacher=teacher, status='Ongoing').first()
        if session:
            session.end_time = timezone.now()
            session.status = 'Completed'
            session.save()
        
        return redirect('teacher_dashboard')
    except Exception as e:
        print(e)
        return redirect('teacher_dashboard')

@login_required
def live_class_monitoring(request):
    try:
        teacher = request.user.teacher
        session = ClassSession.objects.filter(teacher=teacher, status='Ongoing').first()
        if not session:
            return redirect('teacher_dashboard')
        
        # Increment resumption count (counts as a 'login' or session start)
        session.monitoring_resumption_count += 1
        session.save()
            
        return render(request, 'live_class_monitoring.html', {'session': session})
    except:
        return redirect('home')

@csrf_exempt
@login_required
def update_live_attendance(request):
    if request.method == 'POST':
        try:
            face_image_data = request.POST.get('face_image')
            if not face_image_data:
                return JsonResponse({'status': 'error', 'message': 'No image data'})

            teacher = request.user.teacher
            session = ClassSession.objects.filter(teacher=teacher, status='Ongoing').first()
            
            if not session:
                 return JsonResponse({'status': 'error', 'message': 'No ongoing session.'})

            # Verify Face
            face_data_str = face_image_data.split(",")[1]
            image_data = base64.b64decode(face_data_str)
            
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            live_emb = get_embedding(frame)
            
            if live_emb is None:
                 return JsonResponse({'status': 'warning', 'message': 'No face detected.'})

            # Load stored embedding
            project_root = settings.BASE_DIR
            user_dir = os.path.join(project_root, "data", "users", request.user.username)
            embedding_path = os.path.join(user_dir, "embeddings.npy")
            
            stored_emb = None
            
            if os.path.exists(embedding_path):
                stored_emb = np.load(embedding_path)
            else:
                # Fallback: Try to create embedding from existing UserImages
                print(f"Embedding not found for {request.user.username}, attempting to generate from stored image.")
                
                # Ensure directory exists first!
                os.makedirs(user_dir, exist_ok=True)
                
                user_image = UserImages.objects.filter(user=request.user).first()
                if user_image and user_image.face_image:
                    try:
                        # Load image using face_recognition (as in old logic) or cv2
                        # Let's use face_recognition since we have the file path
                        image_path = user_image.face_image.path
                        # Check module import inside fallback
                        import face_recognition
                        
                        image = face_recognition.load_image_file(image_path)
                        encodings = face_recognition.face_encodings(image)
                        
                        if len(encodings) > 0:
                            stored_emb = encodings[0]
                            # Save it for future use!
                            np.save(embedding_path, stored_emb)
                            print(f"Generated and saved new embedding for {request.user.username}")
                        else:
                            print("No face found in stored UserImage")
                    except Exception as e:
                        print(f"Error generating fallback embedding: {e}")
                
            if stored_emb is None:
                 return JsonResponse({'status': 'error', 'message': 'Registration data missing. Please re-register.'})
            
            if match_face(stored_emb, live_emb):
                # Increment active duration
                # Assuming this endpoint is called every 5 seconds
                session.total_active_duration += datetime.timedelta(seconds=5)
                session.save()
                
                # Format duration for display
                total_seconds = int(session.total_active_duration.total_seconds())
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                duration_str = f"{minutes}m {seconds}s"
                
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Authorized',
                    'duration': duration_str
                })
            else:
                return JsonResponse({'status': 'warning', 'message': 'Unknown face detected'})

        except Exception as e:
            print(f"Update error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})

@login_required
def view_teacher_reports(request, teacher_id):
    try:
        from django.utils import timezone
        import datetime
        
        # Verify access: Principal can only view their own teachers
        teacher = Teacher.objects.get(id=teacher_id, principal=request.user.principal)
        
        # Get Filter Parameters
        selected_month = request.GET.get('month')
        selected_year = request.GET.get('year')
        selected_date = request.GET.get('date')
        
        now = timezone.now()
        class_history = ClassSession.objects.filter(teacher=teacher, status='Completed')
        
        if selected_date:
            date_dt = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
            class_history = class_history.filter(start_time__date=date_dt)
        elif selected_month and selected_year:
            class_history = class_history.filter(
                start_time__year=selected_year,
                start_time__month=selected_month
            )
        
        class_history = list(class_history.order_by('-start_time'))

        # Calculate metrics for each session
        for session in class_history:
            if session.timetable:
                # Calculate expected duration in minutes
                s_start = session.timetable.start_time
                s_end = session.timetable.end_time
                start_mins = s_start.hour * 60 + s_start.minute
                end_mins = s_end.hour * 60 + s_end.minute
                session.expected_duration_minutes = end_mins - start_mins
                
                # Check for low attendance (< 60% of expected)
                total_active_mins = session.total_active_duration.total_seconds() / 60 if session.total_active_duration else 0
                if session.expected_duration_minutes > 0:
                    percentage = (total_active_mins / session.expected_duration_minutes) * 100
                    session.is_low_attendance = percentage < 60
                else:
                    session.is_low_attendance = False
            else:
                session.expected_duration_minutes = 0 # Or handle extra classes differently
                session.is_low_attendance = False
        
        # Years and Months for filters
        years = range(now.year - 2, now.year + 1)
        months = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        
        context = {
            'teacher': teacher,
            'class_history': class_history,
            'selected_month': int(selected_month) if selected_month else None,
            'selected_year': int(selected_year) if selected_year else None,
            'selected_date': selected_date,
            'years': years,
            'months': months,
        }
        
        return render(request, 'teacher_reports.html', context)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error viewing reports: {e}")
        return redirect('principal_dashboard')

@login_required
def principal_analysis(request):
    try:
        from django.utils import timezone
        import datetime
        from django.db.models import F, Sum, Count, Q
        
        principal = request.user.principal
        
        # Get Filter Parameters
        selected_dept = request.GET.get('department')
        selected_month = request.GET.get('month') # Format: 1-12
        selected_year = request.GET.get('year')   # Format: 2024
        selected_day = request.GET.get('day')     # Format: YYYY-MM-DD

        now = timezone.now()
        
        # Determine Date Range
        if selected_day:
            day_dt = datetime.datetime.strptime(selected_day, '%Y-%m-%d')
            start_date = timezone.make_aware(day_dt.replace(hour=0, minute=0, second=0))
            end_date = start_date + datetime.timedelta(days=1)
            is_single_day = True
        elif selected_month and selected_year:
            start_date = timezone.make_aware(datetime.datetime(int(selected_year), int(selected_month), 1))
            if int(selected_month) == 12:
                next_month = timezone.make_aware(datetime.datetime(int(selected_year) + 1, 1, 1))
            else:
                next_month = timezone.make_aware(datetime.datetime(int(selected_year), int(selected_month) + 1, 1))
            end_date = next_month
            is_single_day = False
        else:
            # Default to current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now + datetime.timedelta(days=1)
            is_single_day = False
            selected_month = str(now.month)
            selected_year = str(now.year)

        teachers = Teacher.objects.filter(principal=principal)
        if selected_dept and selected_dept != 'ALL':
            teachers = teachers.filter(department=selected_dept)

        # 1. Teacher Attendance Consistency (Bar Chart)
        consistency_labels = []
        consistency_data = []
        
        # 2. Total Teaching Time (Bar Chart)
        teaching_time_labels = []
        teaching_time_data = []

        # 5. Late Entry and Early Exit (Stacked Bar)
        discipline_labels = []
        late_entries = []
        early_exits = []

        # 6. Class Completion Rate (Bar Chart)
        completion_labels = []
        completion_data = []

        day_map_idx = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
        dept_map = dict(Teacher.DEPARTMENT_CHOICES)

        for teacher in teachers:
            sessions = ClassSession.objects.filter(
                teacher=teacher, 
                start_time__gte=start_date,
                start_time__lt=end_date
            )
            completed_sessions = sessions.filter(status='Completed')
            
            total_scheduled_minutes = 0
            total_active_minutes = 0
            
            for session in completed_sessions:
                if session.timetable:
                    # Approximation for minutes
                    start = datetime.datetime.combine(datetime.date.today(), session.timetable.start_time)
                    end = datetime.datetime.combine(datetime.date.today(), session.timetable.end_time)
                    total_scheduled_minutes += (end - start).total_seconds() / 60
                    if session.total_active_duration:
                        total_active_minutes += session.total_active_duration.total_seconds() / 60
            
            if total_scheduled_minutes > 0:
                consistency_data.append(round(min(100, (total_active_minutes / total_scheduled_minutes) * 100), 1))
            else:
                consistency_data.append(0)
            consistency_labels.append(teacher.name)
            
            teaching_time_labels.append(teacher.name)
            teaching_time_data.append(int(total_active_minutes))

            # --- 5. Discipline Metrics (Late Entries, Early Exits) ---
            l_count = 0
            e_count = 0
            for session in sessions:
                if session.timetable:
                    # Scheduled times (Naive time objects)
                    s_start = session.timetable.start_time
                    s_end = session.timetable.end_time
                    
                    # Convert session times to local timezone for accurate comparison
                    local_session_start = timezone.localtime(session.start_time)
                    a_start = local_session_start.time()
                    
                    # Calculate Late Entry (Grace period: 5 minutes)
                    sched_start_mins = s_start.hour * 60 + s_start.minute
                    act_start_mins = a_start.hour * 60 + a_start.minute
                    if act_start_mins > (sched_start_mins + 5):
                        l_count += 1
                    
                    # Calculate Early Exit
                    if session.end_time:
                        local_session_end = timezone.localtime(session.end_time)
                        a_end = local_session_end.time()
                        
                        sched_end_mins = s_end.hour * 60 + s_end.minute
                        act_end_mins = a_end.hour * 60 + a_end.minute
                        
                        # Early exit if they left before the scheduled end time
                        if act_end_mins < sched_end_mins:
                            e_count += 1
            
            discipline_labels.append(teacher.name)
            late_entries.append(l_count)
            early_exits.append(e_count)

            # --- 6. Completion Rate ---
            # Calculate scheduled classes in this period
            scheduled_count = 0
            timetables = teacher.timetables.all()
            temp_date = start_date.date()
            loop_end = end_date.date() if not is_single_day else end_date.date()
            
            while temp_date < loop_end:
                for tt in timetables:
                    if temp_date.weekday() == day_map_idx.get(tt.day):
                        scheduled_count += 1
                temp_date += datetime.timedelta(days=1)
            
            actual_completed = completed_sessions.count()
            if scheduled_count > 0:
                rate = (actual_completed / scheduled_count) * 100
                completion_data.append(round(min(100, rate), 1))
            else:
                # If single day and no classes scheduled, completion might be 0 but avoid dividing by 0
                completion_data.append(0)
            completion_labels.append(teacher.name)

        # 3. Daily Attendance Trend (Line Chart)
        # Always show last 14 days relative to the end of the selected period for context
        trend_end = end_date.date()
        trend_start = trend_end - datetime.timedelta(days=14)
        attendance_trends = TeacherAttendance.objects.filter(
            teacher__principal=principal,
            date__gte=trend_start,
            date__lt=trend_end
        )
        if selected_dept and selected_dept != 'ALL':
            attendance_trends = attendance_trends.filter(teacher__department=selected_dept)
            
        attendance_trends = attendance_trends.values('date').annotate(count=Count('teacher', distinct=True)).order_by('date')
        
        daily_trend_labels = [item['date'].strftime('%b %d') for item in attendance_trends]
        daily_trend_data = [item['count'] for item in attendance_trends]

        # 4. Department-wise Presence (Doughnut)
        # For the selected day OR specifically today if month selected
        target_presence_date = start_date.date() if is_single_day else now.date()
        present_on_date = TeacherAttendance.objects.filter(
            teacher__principal=principal,
            date=target_presence_date
        )
        if selected_dept and selected_dept != 'ALL':
            present_on_date = present_on_date.filter(teacher__department=selected_dept)
            
        present_on_date = present_on_date.values('teacher__department').annotate(count=Count('id'))
        
        dept_presence_labels = [dept_map.get(item['teacher__department'], item['teacher__department']) for item in present_on_date]
        dept_presence_data = [item['count'] for item in present_on_date]

        # Years for dropdown
        years = range(now.year - 2, now.year + 1)
        months = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]

        context = {
            'consistency_labels': consistency_labels,
            'consistency_data': consistency_data,
            'teaching_time_labels': teaching_time_labels,
            'teaching_time_data': teaching_time_data,
            'daily_trend_labels': daily_trend_labels,
            'daily_trend_data': daily_trend_data,
            'dept_presence_labels': dept_presence_labels,
            'dept_presence_data': dept_presence_data,
            'discipline_labels': discipline_labels,
            'late_entries': late_entries,
            'early_exits': early_exits,
            'completion_labels': completion_labels,
            'completion_data': completion_data,
            'departments': Teacher.DEPARTMENT_CHOICES,
            'selected_dept': selected_dept,
            'selected_month': int(selected_month) if selected_month else None,
            'selected_year': int(selected_year) if selected_year else None,
            'selected_day': selected_day,
            'years': years,
            'months': months,
        }
        return render(request, 'principal_analysis.html', context)
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error loading analysis: {str(e)}")
        print(f"Analysis error: {e}")
        return redirect('principal_dashboard')

@login_required
def export_defaulter_csv(request):
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    import datetime
    from .models import Teacher, ClassSession, TeacherAttendance
    
    principal = request.user.principal
    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')
    selected_dept = request.GET.get('department')
    
    now = timezone.now()
    month = int(selected_month) if selected_month else now.month
    year = int(selected_year) if selected_year else now.year
    
    # Date Range
    start_date = timezone.make_aware(datetime.datetime(year, month, 1))
    if month == 12:
        end_date = timezone.make_aware(datetime.datetime(year + 1, 1, 1))
    else:
        end_date = timezone.make_aware(datetime.datetime(year, month + 1, 1))
    
    # Response Configuration
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="defaulter_report_{month}_{year}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Teacher Name', 'Department', 'Attendance Consistency (%)', 'Completion Rate (%)',
        'Late Entries', 'Early Exits', 'Interruptions', 'Risk Score', 'Status'
    ])
    
    teachers = Teacher.objects.filter(principal=principal)
    if selected_dept and selected_dept != 'ALL':
        teachers = teachers.filter(department=selected_dept)
        
    day_map_idx = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
    dept_map = dict(Teacher.DEPARTMENT_CHOICES)
    
    for teacher in teachers:
        sessions = ClassSession.objects.filter(
            teacher=teacher, 
            start_time__gte=start_date,
            start_time__lt=end_date
        )
        completed_sessions = sessions.filter(status='Completed')
        
        total_scheduled_minutes = 0
        total_active_minutes = 0
        late_entries = 0
        early_exits = 0
        interruptions = 0
        
        for session in sessions:
            if session.timetable:
                s_start = session.timetable.start_time
                s_end = session.timetable.end_time
                
                if session.status == 'Completed' and session.total_active_duration:
                    total_active_minutes += session.total_active_duration.total_seconds() / 60
                    
                d_start = datetime.datetime.combine(datetime.date.today(), s_start)
                d_end = datetime.datetime.combine(datetime.date.today(), s_end)
                total_scheduled_minutes += (d_end - d_start).total_seconds() / 60
                
                a_start = session.start_time.astimezone(timezone.get_current_timezone()).time()
                if (a_start.hour * 60 + a_start.minute) > (s_start.hour * 60 + s_start.minute + 5):
                    late_entries += 1
                
                if session.end_time:
                    a_end = session.end_time.astimezone(timezone.get_current_timezone()).time()
                    if (a_end.hour * 60 + a_end.minute) < (s_end.hour * 60 + s_end.minute):
                        early_exits += 1
            
            if session.monitoring_resumption_count > 1:
                interruptions += (session.monitoring_resumption_count - 1)

        consistency = 0
        if total_scheduled_minutes > 0:
            consistency = round((total_active_minutes / total_scheduled_minutes) * 100, 1)
            
        scheduled_classes_count = 0
        timetables = teacher.timetables.all()
        
        # Calculate scheduled classes for that specific month
        temp_date = start_date.date()
        loop_end = end_date.date()
        while temp_date < loop_end:
            for tt in timetables:
                if temp_date.weekday() == day_map_idx.get(tt.day):
                    scheduled_classes_count += 1
            temp_date += datetime.timedelta(days=1)
            
        actual_completed = completed_sessions.count()
        completion_rate = 0
        if scheduled_classes_count > 0:
            completion_rate = round((actual_completed / scheduled_classes_count) * 100, 1)
            
        # Scoring
        risk_score = 0
        if consistency < 75: risk_score += 3
        elif 75 <= consistency <= 85: risk_score += 2
        if early_exits > 3: risk_score += 2
        if late_entries > 3: risk_score += 1
        if interruptions > 0: risk_score += 2
        if completion_rate < 80: risk_score += 2
            
        is_defaulter = False
        if consistency < 70 or risk_score >= 6 or (early_exits > 3 and interruptions > 0):
            is_defaulter = True
            
        status = 'DEFAULTER' if is_defaulter else ('Warning' if risk_score >= 3 else 'Good Standing')
        
        writer.writerow([
            teacher.name,
            dept_map.get(teacher.department, teacher.department),
            f"{consistency}%",
            f"{completion_rate}%",
            late_entries,
            early_exits,
            interruptions,
            risk_score,
            status
        ])
    
    return response

@login_required
def teacher_help(request):
    try:
        teacher = request.user.teacher
        return render(request, 'teacher_help.html', {'teacher': teacher})
    except:
        return redirect('home')

@login_required
def teacher_analysis(request, teacher_id):
    """Comprehensive per-teacher analysis with Risk Gauge, Heatmap, and more."""
    try:
        import json
        from django.utils import timezone as tz
        from django.db.models import F, Sum, Count, Q

        principal = request.user.principal
        teacher = Teacher.objects.get(id=teacher_id, principal=principal)

        now = tz.now()
        # Filter params
        selected_month = request.GET.get('month')
        selected_year = request.GET.get('year')

        if selected_month and selected_year:
            month = int(selected_month)
            year = int(selected_year)
        else:
            month = now.month
            year = now.year
            selected_month = str(month)
            selected_year = str(year)

        start_date = tz.make_aware(datetime.datetime(year, month, 1))
        if month == 12:
            end_date = tz.make_aware(datetime.datetime(year + 1, 1, 1))
        else:
            end_date = tz.make_aware(datetime.datetime(year, month + 1, 1))

        day_map_idx = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
        dept_map = dict(Teacher.DEPARTMENT_CHOICES)

        sessions = ClassSession.objects.filter(
            teacher=teacher,
            start_time__gte=start_date,
            start_time__lt=end_date
        )
        completed_sessions = sessions.filter(status='Completed')

        # ──────────────────────────────────────────────
        # 1. RISK SCORE GAUGE
        # ──────────────────────────────────────────────
        total_scheduled_minutes = 0
        total_active_minutes = 0
        late_entries_count = 0
        early_exits_count = 0
        interruptions_count = 0

        for session in sessions:
            if session.timetable:
                s_start = session.timetable.start_time
                s_end = session.timetable.end_time

                if session.status == 'Completed' and session.total_active_duration:
                    total_active_minutes += session.total_active_duration.total_seconds() / 60

                d_start = datetime.datetime.combine(datetime.date.today(), s_start)
                d_end = datetime.datetime.combine(datetime.date.today(), s_end)
                total_scheduled_minutes += (d_end - d_start).total_seconds() / 60

                a_start = session.start_time.astimezone(tz.get_current_timezone()).time()
                if (a_start.hour * 60 + a_start.minute) > (s_start.hour * 60 + s_start.minute + 5):
                    late_entries_count += 1

                if session.end_time:
                    a_end = session.end_time.astimezone(tz.get_current_timezone()).time()
                    if (a_end.hour * 60 + a_end.minute) < (s_end.hour * 60 + s_end.minute):
                        early_exits_count += 1

            if session.monitoring_resumption_count > 1:
                interruptions_count += (session.monitoring_resumption_count - 1)

        consistency = 0
        if total_scheduled_minutes > 0:
            consistency = round((total_active_minutes / total_scheduled_minutes) * 100, 1)

        # Scheduled classes count
        scheduled_classes_count = 0
        timetables = teacher.timetables.all()
        temp_date = start_date.date()
        loop_end = end_date.date()
        while temp_date < loop_end:
            for tt in timetables:
                if temp_date.weekday() == day_map_idx.get(tt.day):
                    scheduled_classes_count += 1
            temp_date += datetime.timedelta(days=1)

        actual_completed = completed_sessions.count()
        completion_rate = 0
        if scheduled_classes_count > 0:
            completion_rate = round((actual_completed / scheduled_classes_count) * 100, 1)

        # Risk score calculation (same as CSV export)
        risk_score = 0
        if consistency < 75:
            risk_score += 3
        elif 75 <= consistency <= 85:
            risk_score += 2
        if early_exits_count > 3:
            risk_score += 2
        if late_entries_count > 3:
            risk_score += 1
        if interruptions_count > 0:
            risk_score += 2
        if completion_rate < 80:
            risk_score += 2

        max_risk = 10
        # Performance score: inverse of risk (higher = better)
        performance_score = max(0, round(100 - (risk_score / max_risk) * 100))

        if performance_score >= 75:
            risk_category = 'Reliable'
            risk_color = '#10b981'
        elif performance_score >= 45:
            risk_category = 'Needs Attention'
            risk_color = '#f59e0b'
        else:
            risk_category = 'Defaulter'
            risk_color = '#ef4444'

        # ──────────────────────────────────────────────
        # 2. WEEKLY PERFORMANCE HEATMAP
        # ──────────────────────────────────────────────
        days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        days_display = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        # Time slots: 8AM-6PM in 1-hour blocks
        time_slots = []
        for h in range(8, 18):
            time_slots.append(f"{h:02d}:00")

        # Build heatmap_data: rows=days, cols=time_slots, value=active minutes
        heatmap_data = []
        for day_code in days_order:
            row = []
            for slot_idx, slot in enumerate(time_slots):
                slot_start_hour = 8 + slot_idx
                slot_end_hour = slot_start_hour + 1

                total_mins = 0
                for session in completed_sessions:
                    if session.timetable and session.timetable.day == day_code:
                        if session.total_active_duration:
                            # Check if session overlaps this time slot
                            tt_start_h = session.timetable.start_time.hour
                            tt_end_h = session.timetable.end_time.hour
                            if session.timetable.end_time.minute > 0:
                                tt_end_h += 1

                            if tt_start_h < slot_end_hour and tt_end_h > slot_start_hour:
                                # Distribute active time proportionally
                                tt_total_slots = max(1, tt_end_h - tt_start_h)
                                active_mins = session.total_active_duration.total_seconds() / 60
                                total_mins += active_mins / tt_total_slots

                row.append(round(total_mins, 1))
            heatmap_data.append(row)

        # ──────────────────────────────────────────────
        # 3. ATTENDANCE CONSISTENCY RADAR
        # ──────────────────────────────────────────────
        # Dimensions: Punctuality, Duration, Completion, Regularity, Focus
        punctuality_score = max(0, 100 - (late_entries_count * 15)) if scheduled_classes_count > 0 else 0
        duration_score = min(100, consistency)
        completion_score = min(100, completion_rate)
        
        # Regularity: attendance frequency
        attendance_in_period = TeacherAttendance.objects.filter(
            teacher=teacher,
            date__gte=start_date.date(),
            date__lt=end_date.date()
        ).count()
        working_days_in_period = 0
        temp_date = start_date.date()
        while temp_date < end_date.date():
            if temp_date.weekday() < 6:
                working_days_in_period += 1
            temp_date += datetime.timedelta(days=1)
        regularity_score = min(100, round((attendance_in_period / max(1, working_days_in_period)) * 100))
        
        # Focus: lower interruptions = better
        focus_score = max(0, 100 - (interruptions_count * 20))

        radar_labels = ['Punctuality', 'Duration', 'Completion', 'Regularity', 'Focus']
        radar_data = [punctuality_score, duration_score, completion_score, regularity_score, focus_score]

        # ──────────────────────────────────────────────
        # 4. MONTHLY TREND (last 6 months)
        # ──────────────────────────────────────────────
        monthly_trend_labels = []
        monthly_trend_data = []
        for i in range(5, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            m_start = tz.make_aware(datetime.datetime(y, m, 1))
            if m == 12:
                m_end = tz.make_aware(datetime.datetime(y + 1, 1, 1))
            else:
                m_end = tz.make_aware(datetime.datetime(y, m + 1, 1))

            m_sessions = ClassSession.objects.filter(
                teacher=teacher,
                status='Completed',
                start_time__gte=m_start,
                start_time__lt=m_end
            )
            m_total_active = 0
            m_total_sched = 0
            for s in m_sessions:
                if s.timetable and s.total_active_duration:
                    m_total_active += s.total_active_duration.total_seconds() / 60
                    d_s = datetime.datetime.combine(datetime.date.today(), s.timetable.start_time)
                    d_e = datetime.datetime.combine(datetime.date.today(), s.timetable.end_time)
                    m_total_sched += (d_e - d_s).total_seconds() / 60

            m_consistency = round((m_total_active / m_total_sched) * 100, 1) if m_total_sched > 0 else 0
            month_name = datetime.date(y, m, 1).strftime('%b %Y')
            monthly_trend_labels.append(month_name)
            monthly_trend_data.append(min(100, m_consistency))

        # ──────────────────────────────────────────────
        # 5. CLASS-WISE PERFORMANCE (per subject)
        # ──────────────────────────────────────────────
        subject_stats = {}
        for session in completed_sessions:
            if session.timetable:
                subj = session.timetable.subject
                if subj not in subject_stats:
                    subject_stats[subj] = {'active': 0, 'scheduled': 0, 'count': 0}
                subject_stats[subj]['count'] += 1
                if session.total_active_duration:
                    subject_stats[subj]['active'] += session.total_active_duration.total_seconds() / 60
                d_s = datetime.datetime.combine(datetime.date.today(), session.timetable.start_time)
                d_e = datetime.datetime.combine(datetime.date.today(), session.timetable.end_time)
                subject_stats[subj]['scheduled'] += (d_e - d_s).total_seconds() / 60

        classwise_labels = list(subject_stats.keys())
        classwise_active = [round(v['active'], 1) for v in subject_stats.values()]
        classwise_scheduled = [round(v['scheduled'], 1) for v in subject_stats.values()]

        # ──────────────────────────────────────────────
        # 6. PUNCTUALITY DOUGHNUT
        # ──────────────────────────────────────────────
        on_time_count = 0
        late_count = 0
        for session in sessions:
            if session.timetable:
                s_start = session.timetable.start_time
                a_start = session.start_time.astimezone(tz.get_current_timezone()).time()
                if (a_start.hour * 60 + a_start.minute) > (s_start.hour * 60 + s_start.minute + 5):
                    late_count += 1
                else:
                    on_time_count += 1

        punctuality_labels = ['On Time', 'Late Entry']
        punctuality_data = [on_time_count, late_count]

        # ──────────────────────────────────────────────
        # 7. SUMMARY STATS CARDS
        # ──────────────────────────────────────────────
        total_classes_taken = actual_completed
        avg_duration_mins = round(total_active_minutes / max(1, actual_completed), 1) if actual_completed > 0 else 0

        # Years / Months for filter
        years = range(now.year - 2, now.year + 1)
        months_list = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]

        context = {
            'teacher': teacher,
            # Gauge
            'performance_score': performance_score,
            'risk_category': risk_category,
            'risk_color': risk_color,
            'risk_score': risk_score,
            # Stats
            'consistency': consistency,
            'completion_rate': completion_rate,
            'total_classes_taken': total_classes_taken,
            'scheduled_classes_count': scheduled_classes_count,
            'late_entries_count': late_entries_count,
            'early_exits_count': early_exits_count,
            'interruptions_count': interruptions_count,
            'avg_duration_mins': avg_duration_mins,
            'total_active_minutes': round(total_active_minutes, 1),
            'attendance_in_period': attendance_in_period,
            'working_days_in_period': working_days_in_period,
            # Heatmap
            'heatmap_data': json.dumps(heatmap_data),
            'heatmap_days': json.dumps(days_display),
            'heatmap_slots': json.dumps(time_slots),
            # Radar
            'radar_labels': json.dumps(radar_labels),
            'radar_data': json.dumps(radar_data),
            # Monthly Trend
            'monthly_trend_labels': json.dumps(monthly_trend_labels),
            'monthly_trend_data': json.dumps(monthly_trend_data),
            # Class-wise
            'classwise_labels': json.dumps(classwise_labels),
            'classwise_active': json.dumps(classwise_active),
            'classwise_scheduled': json.dumps(classwise_scheduled),
            # Punctuality
            'punctuality_labels': json.dumps(punctuality_labels),
            'punctuality_data': json.dumps(punctuality_data),
            # Filters
            'selected_month': int(selected_month),
            'selected_year': int(selected_year),
            'years': years,
            'months': months_list,
        }
        return render(request, 'teacher_analysis.html', context)

    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error loading teacher analysis: {str(e)}")
        return redirect('principal_dashboard')
