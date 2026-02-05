# Live Attendance System

A real-time face recognition-based attendance tracking system using Python, OpenCV, and the `face_recognition` library (dlib).

## Features

- **Face Detection & Recognition**: Uses the robust `face_recognition` library (HOG/CNN methods).
- **User Registration**: Capture 5 face images to build a reliable face embedding.
- **Live Attendance Tracking**: Real-time identification and session timing.
- **Automatic Time Tracking**: Records session start, end, and duration.
- **CSV Logging**: Automatically saves attendance records to `data/attendance_logs/attendance.csv`.

## Project Structure

```
live-attendance-mini/
│
├── data/
│   ├── users/                  # User face data storage
│   │   ├── [user_id]/
│   │   │   ├── img1.jpg to img5.jpg  # Captured reference images
│   │   │   └── embeddings.npy        # Averaged face embedding
│   │
│   └── attendance_logs/
│       └── attendance.csv      # Attendance history records
│
├── src/
│   ├── camera.py              # Camera initialization and frame reading
│   ├── face_detector.py       # Wrapper for face detection
│   ├── face_embedding.py      # Generates 128-d face encodings
│   ├── face_matcher.py        # Compares face embeddings (Euclidean distance)
│   ├── register_user.py       # User registration logic
│   ├── live_attendance.py     # Main attendance tracking loop
│   └── timer.py               # Session timer utility
│
├── main.py                     # Entry point script
├── requirements.txt            # Project dependencies
└── README.md                   # Project documentation
```

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This requires `dlib`, which may need CMake installed on your system.*

2. **Verify Camera**: Ensure your webcam is connected.

## Usage

Run the main script:
```bash
python main.py
```

### 1. Register New User
1. Select option **1**.
2. Enter a unique **User ID**.
3. The camera will open. Ensure your face is detected (green box).
4. Press **'c'** to capture an image.
5. Capture **5 images** from slightly different angles.
6. Press **'q'** if you wish to quit early.

### 2. Start Live Attendance
1. Select option **2**.
2. Enter the **User ID** you want to track.
3. The system will verify your identity in real-time.
4. If authorized, the timer starts.
5. Press **'q'** to stop the session.
6. Your attendance (Date, Time In, Time Out, Duration) will be saved to `data/attendance_logs/attendance.csv`.

## Troubleshooting

- **"No face detected"**: Ensure good lighting and look directly at the camera.
- **"Multiple faces"**: Ensure only one person is in the frame during registration.
- **Camera issues**: Check if another app is using the webcam.

## Dependencies

- python >= 3.x
- opencv-python
- face_recognition
- numpy

