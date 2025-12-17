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
        ('vino', 'Vino'),
        ('cerveza', 'Cerveza'),
        ('licor', 'Licor'),
        ('energizante', 'Energizante'),
        ('blanca', 'Bebidas Blancas'),
        ('snack', 'Snacks'),
        ('golosina', 'Golosinas'),
        ('limpieza', 'Limpieza'),
        ('hogar', 'Hogar'),
        ('electronica', 'Electrónica'),
        ('ropa', 'Ropa'),
        ('calzado', 'Calzado'),
        ('perfumeria', 'Perfumería'),
        ('mascotas', 'Mascotas'),
        ('libros', 'Libros'),
        ('herramientas', 'Herramientas'),
        ('juguetes', 'Juguetes'),
        ('gaming', 'Gaming'),
        ('otros', 'Otros'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)  # quién lo publicó
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='licor')
    ubicacion = models.CharField(max_length=100, blank=True, help_text="Ej: Palermo, Buenos Aires")
    latitud = models.FloatField(blank=True, null=True)
    longitud = models.FloatField(blank=True, null=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True, null=True)
    stock = models.PositiveIntegerField(default=0)

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


class Favorito(models.Model):
    """Productos favoritos/guardados de cada usuario"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='favoritos')
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'producto')
        ordering = ['-fecha_agregado']

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre}"


class Resena(models.Model):
    """Reseñas y valoraciones de productos"""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resenas')
    calificacion = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 estrellas
    comentario = models.TextField(blank=True, max_length=500)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('producto', 'usuario')  # Un usuario solo puede reseñar una vez cada producto
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre} ({self.calificacion}★)"


class Pedido(models.Model):
    """Historial de pedidos de usuarios"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pedidos')
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=50, default='mercadopago')
    
    # Datos de envío/contacto
    nombre_completo = models.CharField(max_length=200)
    email = models.EmailField()
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    
    # ID de transacción de Mercado Pago
    payment_id = models.CharField(max_length=200, blank=True, null=True)
    preference_id = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ['-fecha_pedido']

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username} - ${self.total}"


class ItemPedido(models.Model):
    """Items individuales de cada pedido"""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    nombre_producto = models.CharField(max_length=200)  # Guardamos el nombre por si se elimina el producto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.nombre_producto} x{self.cantidad}"


class Notificacion(models.Model):
    """Notificaciones para usuarios"""
    TIPO_CHOICES = [
        ('venta', 'Nueva Venta'),
        ('mensaje', 'Nuevo Mensaje'),
        ('resena', 'Nueva Reseña'),
        ('sistema', 'Sistema'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensaje = models.TextField()
    leido = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True, null=True)  # URL a donde redirigir
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.get_tipo_display()} para {self.usuario.username}"

class Cupon(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    porcentaje = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    def __str__(self):
        return self.codigo

class Pregunta(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='preguntas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField(max_length=300)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.contenido[:50]

class Respuesta(models.Model):
    pregunta = models.OneToOneField(Pregunta, on_delete=models.CASCADE, related_name='respuesta')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField(max_length=300)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.contenido[:50]

class ResenaVendedor(models.Model):
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resenas_recibidas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resenas_vendedores')
    calificacion = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comentario = models.TextField(blank=True, max_length=500)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('vendedor', 'usuario')
        ordering = ['-fecha_creacion']
    def __str__(self):
        return f"{self.usuario.username} → {self.vendedor.username} ({self.calificacion}★)"
