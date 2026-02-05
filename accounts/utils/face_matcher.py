import face_recognition

def match_face(known_embedding, live_embedding, threshold=0.45):
    distance = face_recognition.face_distance(
        [known_embedding], live_embedding
    )[0]
    return distance < threshold
