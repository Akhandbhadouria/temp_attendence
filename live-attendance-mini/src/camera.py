import cv2

def get_camera():
    return cv2.VideoCapture(0)

def read_frame(cap):
    ret, frame = cap.read()
    return ret, frame
