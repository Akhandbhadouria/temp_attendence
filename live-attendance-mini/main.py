from src.register_user import register_user
from src.live_attendance import live_attendance

print("1. Register User")
print("2. Start Live Attendance")

choice = input("Enter choice: ")

if choice == "1":
    uid = input("Enter user id: ")
    register_user(uid)

elif choice == "2":
    uid = input("Enter user id: ")
    live_attendance(uid)
