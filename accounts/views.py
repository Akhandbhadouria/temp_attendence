import face_recognition
import base64
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.base import ContentFile
from .models import UserImages, User, Principal, Teacher, Timetable, TeacherAttendance
from django.utils import timezone
import datetime
import calendar
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

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
    
    return render(request, 'principal_dashboard.html', {
        'teachers': teachers,
        'teachers_by_dept': teachers_by_dept
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

            # Save Face
            face_image_data = face_image_data.split(",")[1]
            face_image = ContentFile(base64.b64decode(face_image_data), name=f'{username}_face.jpg')
            UserImages.objects.create(user=user, face_image=face_image)

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
    # Show timetable
    try:
        teacher = request.user.teacher
        timetable = teacher.timetables.all()
        return render(request, 'teacher_dashboard.html', {'teacher': teacher, 'timetable': timetable})
    except:
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
                return redirect('schedule_teacher', teacher_id=teacher_id)
        except Timetable.DoesNotExist:
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

        context = {
            'teacher': teacher, 
            'face_image': face_image,
            'total_present': total_present,
            'late_attendance': late_count,
            'total_absent': total_absent,
            'undertime': 0, # Placeholder
            'attendance_rate': attendance_rate
        }

        return render(request, 'teacher_profile.html', context)
    except Exception as e:
        print(e)
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
            face_image_data = face_image_data.split(",")[1]
            uploaded_image = ContentFile(base64.b64decode(face_image_data), name=f'{user.username}_verify.jpg')
            
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
                            # Log Attendance
                            TeacherAttendance.objects.create(teacher=teacher)
                            return JsonResponse({'status': 'success', 'message': 'Attendance marked successfully!'})
                        else:
                            return JsonResponse({'status': 'error', 'message': 'Face verification failed. Please try again.'})
                    else:
                        return JsonResponse({'status': 'error', 'message': 'Stored reference image is invalid.'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'No reference image found. Contact Principal.'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'No face detected. Please ensure good lighting.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return render(request, 'mark_attendance.html')
