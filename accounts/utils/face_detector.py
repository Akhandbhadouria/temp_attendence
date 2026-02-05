import face_recognition

def detect_faces(frame):
    rgb = frame[:, :, ::-1]
    locations = face_recognition.face_locations(rgb)
    return locations
