from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
import mercadopago
from django.conf import settings

from .models import Producto, Carrito, CarritoItem
from .forms import ProductoForm
from django.core.paginator import Paginator, EmptyPage

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

    # Inicializar cliente de Mercado Pago
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    if request.method == 'POST':
        print("[DEBUG] POST recibido - método: procesar_pago")

        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', request.user.email)
        metodo_pago = request.POST.get('metodo_pago', 'mercadopago')

        print(f"[DEBUG] Datos recibidos: nombre={nombre}, email={email}, metodo={metodo_pago}")

        # Validar que el nombre no esté vacío
        if not nombre:
            nombre = request.user.get_full_name() or request.user.username or 'Cliente'

        print(f"[DEBUG] Nombre validado: {nombre}")

        if metodo_pago == 'mercadopago':
            print("[DEBUG] Procesando pago con Mercado Pago...")

            # Crear preferencia de pago para Mercado Pago
            preference_data = {
                "items": [
                    {
                        "title": item.producto.nombre,
                        "quantity": item.cantidad,
                        "unit_price": float(item.producto.precio),
                    }
                    for item in items
                ],
                "payer": {
                    "name": nombre,
                    "email": email,
                },
                "back_urls": {
                    "success": settings.MERCADOPAGO_SUCCESS_URL,
                    "failure": settings.MERCADOPAGO_FAILURE_URL,
                    "pending": settings.MERCADOPAGO_PENDING_URL,
                },
                # "auto_return": "approved",  # removed to avoid invalid_auto_return when back_urls isn't accepted
                "external_reference": f"pedido_{request.user.id}_{carrito.id}",
            }

            print(f"[DEBUG] Preferencia data: {preference_data}")

            try:
                preference_response = sdk.preference().create(preference_data)
                print(f"[DEBUG] Response status: {preference_response.get('status')}")
                print(f"[DEBUG] Response keys: {list(preference_response.keys())}")

                if preference_response.get("status") == 201:
                    init_point = preference_response["response"].get("init_point")
                    print(f"[DEBUG] init_point: {init_point}")
                    # Redirigir a Mercado Pago
                    return redirect(init_point)
                else:
                    # Volcar response completo para diagnosticar error 400
                    print(f"[DEBUG] Error: Status no es 201, es {preference_response.get('status')}")
                    try:
                        print(f"[DEBUG] preference_response content: {preference_response.get('response')}")
                    except Exception:
                        print(repr(preference_response))
                    messages.error(request, 'Error al crear la preferencia de pago. Intenta nuevamente.')
                    return redirect('tienda:ver_carrito')
            except Exception as e:
                print(f"[DEBUG] EXCEPCIÓN: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al conectar con Mercado Pago: {str(e)}')
                return redirect('tienda:ver_carrito')

        else:
            print("[DEBUG] Procesando pago con tarjeta local...")
            # Método de pago simulado (tarjeta de crédito local)
            # Limpiamos el carrito
            carrito.items.all().delete()

            messages.success(request, '¡Pago procesado exitosamente! Gracias por tu compra.')
            return redirect('tienda:productos')

    return render(request, 'tienda/pago.html', {
        'items': items,
        'total': total
    })


# ✅ Pago exitoso (Mercado Pago)
@login_required
def pago_exitoso(request):
    carrito = Carrito.objects.filter(usuario=request.user).first()
    if carrito:
        carrito.items.all().delete()
    
    return render(request, 'tienda/pago_exitoso.html')


# ❌ Pago fallido (Mercado Pago)
@login_required
def pago_fallido(request):
    return render(request, 'tienda/pago_fallido.html')


# ⏳ Pago pendiente (Mercado Pago)
@login_required
def pago_pendiente(request):
    return render(request, 'tienda/pago_pendiente.html')


# API: productos paginados (JSON)
def productos_api(request):
    categoria = request.GET.get('categoria')
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size', 8))
    except ValueError:
        page_size = 8

    categorias = dict([('licor', 'Licor'), ('energizante', 'Energizante'), ('cerveza', 'Cerveza'), ('vino', 'Vino')])
    productos_qs = Producto.objects.all().order_by('-id')
    if categoria in categorias:
        productos_qs = productos_qs.filter(categoria=categoria)

    paginator = Paginator(productos_qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({'products': [], 'has_next': False})

    productos = []
    for p in page_obj.object_list:
        productos.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio': float(p.precio),
            'imagen': p.imagen.url if p.imagen else None,
            'categoria': p.get_categoria_display(),
        })

    return JsonResponse({
        'products': productos,
        'has_next': page_obj.has_next(),
        'page': page,
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
