from django.contrib import admin
from .models import UserImages, Timetable, Principal, Teacher

admin.site.register(UserImages)
admin.site.register(Principal)
admin.site.register(Teacher)

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'day', 'start_time', 'end_time')
    list_filter = ('day', 'teacher__principal')  # Filter by Principal
    search_fields = ('subject', 'teacher__name')