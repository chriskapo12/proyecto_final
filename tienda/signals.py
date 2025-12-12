from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Pedido, ItemPedido, Mensaje, Resena, Notificacion

@receiver(post_save, sender=ItemPedido)
def notificar_venta(sender, instance, created, **kwargs):
    """Notificar al vendedor cuando se vende uno de sus productos"""
    if created:
        producto = instance.producto
        vendedor = producto.usuario
        comprador = instance.pedido.usuario
        
        # No notificar si el vendedor es el mismo comprador (auto-compra)
        if vendedor != comprador:
            Notificacion.objects.create(
                usuario=vendedor,
                tipo='venta',
                mensaje=f"¡Felicidades! {comprador.username} compró tu producto '{producto.nombre}'.",
                link='/tienda/mis-ventas/'  # Link al historial de ventas
            )

@receiver(post_save, sender=Mensaje)
def notificar_mensaje(sender, instance, created, **kwargs):
    """Notificar al destinatario cuando recibe un mensaje"""
    if created:
        Notificacion.objects.create(
            usuario=instance.destinatario,
            tipo='mensaje',
            mensaje=f"Nuevo mensaje de {instance.remitente.username}: {instance.contenido[:30]}...",
            link=f"/tienda/chat/mensajes/{instance.remitente.id}/"
        )

@receiver(post_save, sender=Resena)
def notificar_resena(sender, instance, created, **kwargs):
    """Notificar al vendedor cuando reciben una reseña"""
    if created:
        vendedor = instance.producto.usuario
        autor = instance.usuario
        
        if vendedor != autor:
            Notificacion.objects.create(
                usuario=vendedor,
                tipo='resena',
                mensaje=f"{autor.username} calificó tu producto '{instance.producto.nombre}' con {instance.calificacion} estrellas.",
                link=f"/tienda/productos/{instance.producto.id}/"
            )
