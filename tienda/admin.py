

# Register your models here.
from django.contrib import admin
from .models import Producto, Mensaje, Perfil

admin.site.register(Producto)
admin.site.register(Mensaje)
admin.site.register(Perfil)
