import face_recognition
import base64
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.base import ContentFile
from .models import UserImages, User, Principal, Teacher
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
    principal = request.user.principal
    teachers = principal.teachers.all()
    return render(request, 'principal_dashboard.html', {'teachers': teachers})

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
    if request.method == 'POST':
        try:
            name = request.POST['name']
            username = request.POST['username'] # Teacher needs unique username
            password = request.POST['password']
            face_image_data = request.POST['face_image']

            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'Username already taken.'})

            # Create User with provided password
            user = User.objects.create_user(username=username, password=password) 
            
            # Create Teacher linked to Principal
            Teacher.objects.create(user=user, principal=request.user.principal, name=name)

            # Save Face
            face_image_data = face_image_data.split(",")[1]
            face_image = ContentFile(base64.b64decode(face_image_data), name=f'{username}_face.jpg')
            UserImages.objects.create(user=user, face_image=face_image)

            return JsonResponse({'status': 'success', 'message': 'Teacher added successfully!'})
        except Exception as e:
             return JsonResponse({'status': 'error', 'message': str(e)})

    return render(request, 'add_teacher.html')

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
