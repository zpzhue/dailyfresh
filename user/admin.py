from django.contrib import admin
from .models import Address
# Register your models here.

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'receiver', 'addr', 'zip_code', 'phone', 'is_default']