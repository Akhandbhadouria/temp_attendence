import cv2
import os
import numpy as np
from .camera import get_camera, read_frame
from .face_embedding import get_embedding, average_embeddings
from .face_detector import detect_faces

def register_user(user_id):
    cap = get_camera()
    
    if not cap.isOpened():
        print("❌ Could not open camera. Please check camera connection.")
        return
    
    embeddings = []

    # Create directory relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_dir = os.path.join(project_root, "data", "users", user_id)
    os.makedirs(save_dir, exist_ok=True)

    print("\n📷 USER REGISTRATION")
    print("=" * 40)
    print("INSTRUCTIONS:")
    print(" - Press 'c' to CAPTURE image")
    print(" - Press 'q' to QUIT")
    print(" - Make sure only YOUR face is visible")
    print(" - Move your head slightly for different angles")
    print("=" * 40)

    img_count = 0

    while True:
        ret, frame = read_frame(cap)
        if not ret:
            print("❌ Could not read frame from camera.")
            break

        # Detect faces for visual feedback
        faces = detect_faces(frame)
        num_faces = len(faces)
        
        # Draw rectangle around detected faces
        for (top, right, bottom, left) in faces:
            color = (0, 255, 0) if num_faces == 1 else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        # Status message
        if num_faces == 0:
            status = "No face detected"
            status_color = (0, 0, 255)
        elif num_faces == 1:
            status = "Face detected - Press 'c' to capture"
            status_color = (0, 255, 0)
        else:
            status = f"Multiple faces ({num_faces}) - Only show 1 face"
            status_color = (0, 0, 255)

        cv2.putText(
            frame,
            f"Images: {img_count}/5",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        
        cv2.putText(
            frame,
            status,
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2
        )

        cv2.imshow("Register User", frame)

        key = cv2.waitKey(1) & 0xFF

        # Capture image
        if key == ord('c'):
            emb = get_embedding(frame)

            if emb is None:
                print("❌ No face OR multiple faces detected. Try again.")
                continue

            embeddings.append(emb)
            img_count += 1

            cv2.imwrite(os.path.join(save_dir, f"img{img_count}.jpg"), frame)
            print(f"✅ Captured image {img_count}/5")

            if img_count >= 5:
                print("\n🎉 All 5 images captured!")
                break

        # Quit
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if len(embeddings) >= 3:
        avg_emb = average_embeddings(embeddings)
        np.save(os.path.join(save_dir, "embeddings.npy"), avg_emb)
        print(f"\n✅ User '{user_id}' registered successfully!")
        print(f"   Embeddings saved to: {save_dir}/embeddings.npy")
    else:
        print(f"\n❌ Registration failed. Need at least 3 good images (got {len(embeddings)}).")

