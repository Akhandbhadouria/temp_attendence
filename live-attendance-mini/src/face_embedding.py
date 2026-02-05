import face_recognition
import numpy as np

def get_embedding(frame, face_location=None):
    """
    Returns face embedding for the detected face in frame.
    
    Args:
        frame: The image frame (BGR format from OpenCV)
        face_location: Optional tuple (top, right, bottom, left) of face location.
                       If None, the function will detect faces automatically.
    
    Returns:
        Face embedding array or None if detection fails
    """
    # Convert BGR to RGB
    rgb = frame[:, :, ::-1].copy()  # Make a copy to ensure contiguous array

    try:
        if face_location is not None:
            # Use provided face location - wrap in list for face_encodings
            known_face_locations = [face_location]
            encodings = face_recognition.face_encodings(rgb, known_face_locations)
        else:
            # Auto-detect faces
            locations = face_recognition.face_locations(rgb)
            
            # For auto-detection, require exactly one face
            if len(locations) != 1:
                return None
            
            # Get encodings - let face_recognition handle face detection internally
            # This is more compatible across different library versions
            encodings = face_recognition.face_encodings(rgb)

        if not encodings:
            return None

        return encodings[0]
    
    except Exception as e:
        print(f"Error getting face embedding: {e}")
        return None


def average_embeddings(embeddings):
    return np.mean(embeddings, axis=0)
