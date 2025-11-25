

# Register your models here.
from django.contrib import admin
from .models import Producto, Mensaje

admin.site.register(Producto)
admin.site.register(Mensaje)
