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
    path('productos/<int:producto_id>/', views.detalle_producto_view, name='detalle_producto'),
    path('agregar/', views.agregar_producto_view, name='agregar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto_view, name='eliminar_producto'),
    # Carrito
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/actualizar/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('carrito/obtener/', views.obtener_carrito_ajax, name='obtener_carrito_ajax'),
    path('pago/', views.procesar_pago, name='procesar_pago'),
]