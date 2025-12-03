from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):
    """Perfil de usuario con foto y información adicional"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True, default='perfiles/default.png')
    bio = models.TextField(blank=True, max_length=500, help_text='Cuéntanos sobre ti')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Perfil de {self.usuario.username}"
    
    def productos_count(self):
        """Retorna el número de productos publicados por este usuario"""
        return self.usuario.producto_set.count()


# Señales para crear automáticamente el perfil cuando se crea un usuario
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(usuario=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()


class Producto(models.Model):

    CATEGORIAS = [
        ('licor', 'Licor'),
        ('energizante', 'Energizante'),
        ('cerveza', 'Cerveza'),
        ('vino', 'Vino'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)  # quién lo publicó
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='licor')

    def __str__(self):
        return self.nombre


class Carrito(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

    def total_items(self):
        return sum(item.cantidad for item in self.items.all())


class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class Mensaje(models.Model):
    """Modelo para mensajes de chat en tiempo real entre usuarios"""
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    contenido = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.remitente.username} → {self.destinatario.username}: {self.contenido[:50]}"

