# Register your models here.

from django.contrib import admin

from .models import UserDetails, UserProfile, Recommendation

admin.site.register(UserDetails)
admin.site.register(UserProfile)
admin.site.register(Recommendation)
