import cv2
import numpy as np
import time
import os
import csv
from datetime import datetime
from .camera import get_camera, read_frame
from .face_detector import detect_faces
from .face_embedding import get_embedding
from .face_matcher import match_face
from .timer import AttendanceTimer


def save_attendance_record(project_root, user_id, time_in, time_out, duration_seconds):
    """
    Save attendance record to CSV file
    """
    csv_path = os.path.join(project_root, "data", "attendance_logs", "attendance.csv")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    # Check if file exists and has headers
    file_exists = os.path.exists(csv_path)
    
    # Format the data
    date_str = time_in.strftime("%Y-%m-%d")
    time_in_str = time_in.strftime("%H:%M:%S")
    time_out_str = time_out.strftime("%H:%M:%S")
    duration_minutes = round(duration_seconds / 60, 2)
    
    # Write to CSV
    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header if file is new or empty
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writerow(["User ID", "Date", "Time In", "Time Out", "Duration (minutes)"])
        
        writer.writerow([user_id, date_str, time_in_str, time_out_str, duration_minutes])
    
    return csv_path


def live_attendance(user_id):
    # Get project root directory for consistent path handling
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    embedding_path = os.path.join(project_root, "data", "users", user_id, "embeddings.npy")
    
    # Check if user exists
    if not os.path.exists(embedding_path):
        print(f"❌ User '{user_id}' not found. Please register first.")
        return
    
    known_embedding = np.load(embedding_path)
    cap = get_camera()
    
    if not cap.isOpened():
        print("❌ Could not open camera. Please check camera connection.")
        return
    
    timer = AttendanceTimer()
    last_seen = time.time()
    
    # Record session start time
    session_start_time = datetime.now()

    print("📷 Live Attendance Started")
    print(f"Session started at: {session_start_time.strftime('%H:%M:%S')}")
    print("Press 'q' to quit")

    while True:
        ret, frame = read_frame(cap)
        if not ret:
            print("❌ Could not read frame from camera.")
            break

        faces = detect_faces(frame)
        num_faces = len(faces)
        authorized = False
        status = "No face detected"

        if num_faces == 1:
            # Single face detected - check if it matches
            emb = get_embedding(frame, faces[0])
            if emb is not None and match_face(known_embedding, emb):
                authorized = True
                last_seen = time.time()
                status = "✓ Authorized"
            else:
                status = "✗ Unknown person"
        elif num_faces > 1:
            status = f"⚠ Multiple faces ({num_faces})"

        if authorized:
            timer.start()
        else:
            if time.time() - last_seen > 2:
                timer.pause()

        elapsed = int(timer.get_time())
        
        # Draw status on frame
        color = (0, 255, 0) if authorized else (0, 0, 255)
        cv2.putText(frame, f"Time: {elapsed}s",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2)
        
        cv2.putText(frame, status,
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, color, 2)

        cv2.imshow("Live Attendance", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Record session end time
    session_end_time = datetime.now()
    final_time = int(timer.get_time())
    
    # Save attendance record to CSV
    if final_time > 0:
        csv_path = save_attendance_record(
            project_root, 
            user_id, 
            session_start_time, 
            session_end_time, 
            final_time
        )
        print(f"\n✅ Attendance record saved to: {csv_path}")
    
    print(f"🎯 Final attendance time: {final_time} seconds ({final_time // 60} minutes)")
    print(f"   Session: {session_start_time.strftime('%H:%M:%S')} - {session_end_time.strftime('%H:%M:%S')}")

