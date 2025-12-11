from django.urls import path
from . import views

app_name = 'tienda'  # <--- Esto habilita el namespace en templates

urlpatterns = [
    # 🏠 Página principal
    path('', views.home, name='home'),

    # 🔐 Autenticación
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

  # Productos
    path('productos/', views.productos_view, name='productos'),
  path('productos/api/', views.productos_api, name='productos_api'),
    path('productos/<int:producto_id>/', views.detalle_producto_view, name='detalle_producto'),
    path('agregar/', views.agregar_producto_view, name='agregar_producto'),
    path('editar/<int:producto_id>/', views.editar_producto_view, name='editar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto_view, name='eliminar_producto'),
    # Carrito
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/actualizar/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('carrito/obtener/', views.obtener_carrito_ajax, name='obtener_carrito_ajax'),
    path('pago/', views.procesar_pago, name='procesar_pago'),
    
    # Retornos de Mercado Pago
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),
    path('pago-pendiente/', views.pago_pendiente, name='pago_pendiente'),
    
    # 💬 Chat
    path('chat/conversaciones/', views.obtener_conversaciones, name='obtener_conversaciones'),
    path('chat/mensajes/<int:usuario_id>/', views.obtener_mensajes, name='obtener_mensajes'),
    path('chat/enviar/', views.enviar_mensaje, name='enviar_mensaje'),
    path('chat/usuarios/', views.obtener_usuarios_disponibles, name='obtener_usuarios'),
    
    # 👤 Perfiles
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    path('perfil/<int:usuario_id>/', views.ver_perfil_usuario, name='ver_perfil_usuario'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    
    # ⭐ Favoritos
    path('favoritos/', views.mis_favoritos, name='mis_favoritos'),
    path('favoritos/toggle/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    
    # 📝 Reseñas
    path('resenas/agregar/<int:producto_id>/', views.agregar_resena, name='agregar_resena'),
    path('resenas/eliminar/<int:resena_id>/', views.eliminar_resena, name='eliminar_resena'),
    
    # 📦 Pedidos
    path('pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedidos/<int:pedido_id>/', views.detalle_pedido, name='detalle_pedido'),
]