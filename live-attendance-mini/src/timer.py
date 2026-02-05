import time

class AttendanceTimer:
    def __init__(self):
        self.start_time = None
        self.total_time = 0
        self.running = False

    def start(self):
        if not self.running:
            self.start_time = time.time()
            self.running = True

    def pause(self):
        if self.running:
            self.total_time += time.time() - self.start_time
            self.running = False

    def get_time(self):
        if self.running:
            return self.total_time + (time.time() - self.start_time)
        return self.total_time
