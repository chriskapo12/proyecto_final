from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json

from .models import Producto, Carrito, CarritoItem
from .forms import ProductoForm

# 🏠 Página principal
def home(request):
    categoria = request.GET.get('categoria')
    categorias = [
        ('licor', 'Licor'),
        ('energizante', 'Energizante'),
        ('cerveza', 'Cerveza'),
        ('vino', 'Vino'),
    ]
    productos_qs = Producto.objects.all().order_by('-id')
    if categoria in dict(categorias):
        productos_qs = productos_qs.filter(categoria=categoria)
    ultimos_productos = productos_qs[:8]
    return render(request, 'tienda/home.html', {
        'ultimos_productos': ultimos_productos,
        'categorias': categorias,
        'categoria_seleccionada': categoria,
    })

# 🧍 Registro de usuario
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este correo ya está en uso.')
            return redirect('tienda:register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        Carrito.objects.create(usuario=user)

        messages.success(request, 'Cuenta creada exitosamente. Ahora podés iniciar sesión.')
        return redirect('tienda:login')

    return render(request, 'tienda/register.html')

# 🔐 Login
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('tienda:productos')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'tienda/login.html')

# 🚪 Logout
def logout_view(request):
    logout(request)
    return redirect('tienda:home')

# 🛍 Lista de productos
def productos_view(request):
    productos = Producto.objects.all().order_by('-id')  # Ordenamos por más recientes primero
    return render(request, 'tienda/productos.html', {'productos': productos})

# 🔍 Detalle de producto
def detalle_producto_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'tienda/detalle_producto.html', {'producto': producto})

# ➕ Agregar producto (solo usuarios registrados)
@login_required
def agregar_producto_view(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario = request.user
            producto.save()
            return redirect('tienda:productos')
    else:
        form = ProductoForm()
    return render(request, 'tienda/agregar_producto.html', {'form': form})

# ❌ Eliminar producto (solo dueño)
@login_required
def eliminar_producto_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if producto.usuario == request.user:
        producto.delete()
    else:
        messages.error(request, 'Solo podés eliminar tus propios productos.')
    return redirect('tienda:productos')

# 🛍 Agregar producto al carrito
@login_required
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    item, creado = CarritoItem.objects.get_or_create(carrito=carrito, producto=producto)

    if not creado:
        item.cantidad += 1
        item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        total_items = carrito.total_items()
        return JsonResponse({'success': True, 'total_items': total_items})

    return redirect('tienda:ver_carrito')

# 👁 Ver carrito
@login_required
def ver_carrito(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    items = list(carrito.items.select_related('producto').all())

    # calcular subtotal por item y total del carrito
    total = 0
    for it in items:
        it.subtotal = it.cantidad * it.producto.precio
        total += it.subtotal

    return render(request, 'tienda/carrito.html', {
        'carrito': carrito,
        'items': items,
        'total': total,
    })

# 🗑 Eliminar producto del carrito vía AJAX
@login_required
def eliminar_del_carrito(request, producto_id):
    carrito = get_object_or_404(Carrito, usuario=request.user)
    item = carrito.items.filter(producto_id=producto_id).first()
    if item:
        item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        total = sum(i.cantidad * i.producto.precio for i in carrito.items.all())
        total_items = carrito.total_items()
        return JsonResponse({'success': True, 'total': float(total), 'total_items': total_items})
    
    return redirect('tienda:ver_carrito')

# ➕➖ Actualizar cantidad del carrito (AJAX)
@login_required
def actualizar_cantidad(request):
    if request.method == "POST":
        # aceptar tanto JSON (fetch con application/json) como form-urlencoded (fallback)
        try:
            data = json.loads(request.body)
            producto_id = data.get("producto_id")
            accion = data.get("accion")
        except Exception:
            producto_id = request.POST.get("producto_id")
            accion = request.POST.get("accion")

        carrito = get_object_or_404(Carrito, usuario=request.user)
        item = get_object_or_404(CarritoItem, carrito=carrito, producto_id=producto_id)

        if accion == "sumar":
            item.cantidad += 1
        elif accion == "restar" and item.cantidad > 1:
            item.cantidad -= 1

        item.save()

        total_items = carrito.total_items()
        total = float(sum(i.cantidad * i.producto.precio for i in carrito.items.all()))
        subtotal = float(item.cantidad * item.producto.precio)

        return JsonResponse({
            'success': True,
            'cantidad': item.cantidad,
            'subtotal': subtotal,
            'total': total,
            'total_items': total_items
        })

    return JsonResponse({'error': 'Solicitud inválida'}, status=400)

# 💰 Procesar pago
@login_required
def procesar_pago(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    items = list(carrito.items.select_related('producto').all())
    
    if not items:
        messages.error(request, 'Tu carrito está vacío')
        return redirect('tienda:ver_carrito')
        
    total = sum(item.cantidad * item.producto.precio for item in items)
    
    if request.method == 'POST':
        # Aquí iría la lógica de procesamiento del pago real
        # Por ahora solo simularemos que el pago fue exitoso
        
        # Limpiamos el carrito
        carrito.items.all().delete()
        
        messages.success(request, '¡chriskapo te agradece por tu compra!')
        return redirect('tienda:productos')
    
    return render(request, 'tienda/pago.html', {
        'items': items,
        'total': total
    })

# �🔄 Cargar carrito dinámico (AJAX)
@login_required
def obtener_carrito_ajax(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    items = []
    total = 0

    for item in carrito.items.select_related('producto'):
        subtotal = item.cantidad * item.producto.precio
        total += subtotal
        items.append({
            'id': item.id,
            'producto_id': item.producto.id,
            'nombre': item.producto.nombre,
            'precio': float(item.producto.precio),
            'cantidad': item.cantidad,
            'subtotal': float(subtotal),
            'imagen': item.producto.imagen.url if item.producto.imagen else None
        })

    return JsonResponse({
        'items': items,
        'total': float(total),
        'total_items': carrito.total_items(),
    })
