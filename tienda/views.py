from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
import mercadopago
from django.conf import settings
from django.db.models import Avg, Count, Q

from .models import Producto, Carrito, CarritoItem, Favorito, Resena, Pedido, ItemPedido, Cupon, Pregunta, Respuesta
from .forms import ProductoForm
from django.core.paginator import Paginator, EmptyPage

# 🏠 Página principal
def home(request):
    categoria = request.GET.get('categoria')
    categorias = Producto.CATEGORIAS
    productos_qs = Producto.objects.all().order_by('-id')
    if categoria and categoria in dict(categorias):
        productos_qs = productos_qs.filter(categoria=categoria)
    
    # Agregar información de favoritos si el usuario está autenticado
    if request.user.is_authenticated:
        productos_qs = productos_qs.annotate(
            es_favorito=Count('favoritos', filter=Q(favoritos__usuario=request.user)),
            promedio_calificacion=Avg('resenas__calificacion'),
            vendedor_estrellas=Avg('usuario__resenas_recibidas__calificacion'),
            vendedor_total=Count('usuario__resenas_recibidas')
        )
    else:
        productos_qs = productos_qs.annotate(
            promedio_calificacion=Avg('resenas__calificacion'),
            vendedor_estrellas=Avg('usuario__resenas_recibidas__calificacion'),
            vendedor_total=Count('usuario__resenas_recibidas')
        )
    
    ultimos_productos = productos_qs[:8]
    populares = Producto.objects.annotate(
        fav_count=Count('favoritos'),
        vendedor_estrellas=Avg('usuario__resenas_recibidas__calificacion'),
        vendedor_total=Count('usuario__resenas_recibidas')
    ).order_by('-fav_count', '-id')[:8]
    return render(request, 'tienda/home.html', {
        'ultimos_productos': ultimos_productos,
        'categorias': categorias,
        'categoria_seleccionada': categoria,
        'populares': populares,
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

# 🛍 Lista de productos con búsqueda avanzada
def productos_view(request):
    productos = Producto.objects.all()
    
    # Búsqueda por nombre o descripción
    buscar = request.GET.get('buscar', '').strip()
    if buscar:
        productos = productos.filter(
            Q(nombre__icontains=buscar) | 
            Q(descripcion__icontains=buscar) |
            Q(categoria__icontains=buscar)
        )
    
    # Filtro por categoría
    categoria = request.GET.get('categoria', '').strip()
    if categoria:
        productos = productos.filter(categoria=categoria)
    
    # Filtro por rango de precio
    precio_min = request.GET.get('precio_min', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    if precio_min:
        try:
            productos = productos.filter(precio__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            productos = productos.filter(precio__lte=float(precio_max))
        except ValueError:
            pass
    
    # Ordenamiento
    orden = request.GET.get('orden', '-id')
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    elif orden == 'nombre':
        productos = productos.order_by('nombre')
    elif orden == 'antiguos':
        productos = productos.order_by('id')
    else:  # 'recientes' o por defecto
        productos = productos.order_by('-id')
    
    # Anotar productos con favoritos y calificación promedio
    if request.user.is_authenticated:
        productos = productos.annotate(
            es_favorito=Count('favoritos', filter=Q(favoritos__usuario=request.user)),
            promedio_calificacion=Avg('resenas__calificacion'),
            vendedor_estrellas=Avg('usuario__resenas_recibidas__calificacion'),
            vendedor_total=Count('usuario__resenas_recibidas')
        )
    else:
        productos = productos.annotate(
            promedio_calificacion=Avg('resenas__calificacion'),
            vendedor_estrellas=Avg('usuario__resenas_recibidas__calificacion'),
            vendedor_total=Count('usuario__resenas_recibidas')
        )
    
    categorias = Producto.CATEGORIAS
    
    return render(request, 'tienda/productos.html', {
        'productos': productos,
        'buscar': buscar,
        'categoria': categoria,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'orden': orden,
        'categorias': categorias,
    })

# 🔍 Detalle de producto
def detalle_producto_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Obtener reseñas del producto
    resenas = producto.resenas.all().select_related('usuario')
    promedio_calificacion = resenas.aggregate(Avg('calificacion'))['calificacion__avg']
    total_resenas = resenas.count()
    
    # Reputación del vendedor (promedio de calificaciones de todos sus productos)
    from .models import Resena
    vendedor_resenas = Resena.objects.filter(producto__usuario=producto.usuario)
    reputacion_vendedor = vendedor_resenas.aggregate(Avg('calificacion'))['calificacion__avg']
    total_resenas_vendedor = vendedor_resenas.count()

    # Productos similares (misma categoría y precio cercano)
    similares = Producto.objects.filter(categoria=producto.categoria).exclude(id=producto.id)
    try:
        rango_min = float(producto.precio) * 0.8
        rango_max = float(producto.precio) * 1.2
        similares = similares.filter(precio__gte=rango_min, precio__lte=rango_max)
    except Exception:
        pass
    similares = similares.order_by('-id')[:8]
    preguntas = producto.preguntas.select_related('usuario').order_by('-fecha_creacion')
    
    # Verificar si el usuario ya reseñó este producto
    resena_usuario = None
    es_favorito = False
    if request.user.is_authenticated:
        resena_usuario = resenas.filter(usuario=request.user).first()
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()
    
    # Verificación de email del vendedor (django-allauth)
    email_verificado = False
    try:
        from allauth.account.models import EmailAddress
        email_verificado = EmailAddress.objects.filter(user=producto.usuario, verified=True).exists()
    except Exception:
        email_verificado = False

    return render(request, 'tienda/detalle_producto.html', {
        'producto': producto,
        'resenas': resenas,
        'promedio_calificacion': promedio_calificacion,
        'total_resenas': total_resenas,
        'resena_usuario': resena_usuario,
        'es_favorito': es_favorito,
        'email_verificado': email_verificado,
        'reputacion_vendedor': reputacion_vendedor,
        'total_resenas_vendedor': total_resenas_vendedor,
        'similares': similares,
        'preguntas': preguntas,
        'categoria_label': producto.get_categoria_display(),
    })

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
    return render(request, 'tienda/agregar_producto.html', {
        'form': form,
    })

# ✏️ Editar producto (solo dueño)
@login_required
def editar_producto_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Verificar que el usuario sea el dueño
    if producto.usuario != request.user:
        messages.error(request, 'Solo podés editar tus propios productos.')
        return redirect('tienda:detalle_producto', producto_id=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('tienda:detalle_producto', producto_id=producto_id)
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'tienda/editar_producto.html', {
        'form': form,
        'producto': producto,
    })

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

    # Validar stock antes de agregar
    if producto.stock <= 0 and creado:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Sin stock disponible'})
        messages.error(request, 'Sin stock disponible')
        return redirect('tienda:ver_carrito')
    else:
        nueva_cantidad = 1 if creado else item.cantidad + 1
        if nueva_cantidad > producto.stock:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'No puedes superar el stock disponible'})
            messages.error(request, 'No puedes superar el stock disponible')
            return redirect('tienda:ver_carrito')
        item.cantidad = nueva_cantidad
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
        direccion = request.POST.get('direccion', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        shipping_method = request.POST.get('shipping_method', 'retiro')
        cupon_code = request.POST.get('cupon', '').strip().upper()

        print(f"[DEBUG] Datos recibidos: nombre={nombre}, email={email}, metodo={metodo_pago}")

        # Validar que el nombre no esté vacío
        if not nombre:
            nombre = request.user.get_full_name() or request.user.username or 'Cliente'

        print(f"[DEBUG] Nombre validado: {nombre}")

        # Validación de seguridad: requerir datos de envío antes de pagar
        if not direccion or not telefono:
            messages.error(request, 'Debes completar dirección y teléfono de envío antes de pagar.')
            return render(request, 'tienda/pago.html', {'items': items, 'total': total})
        shipping_cost = 0
        if shipping_method == 'estandar':
            shipping_cost = 1500
        elif shipping_method == 'express':
            shipping_cost = 3000
        elif shipping_method == 'retiro':
            shipping_cost = 0
        discount_pct = 0
        cupon_obj = None
        if cupon_code:
            cupon_obj = Cupon.objects.filter(codigo=cupon_code, activo=True).first()
            if cupon_obj:
                discount_pct = cupon_obj.porcentaje

        # Guardar datos de envío en sesión para usarlos tras el callback de pago
        request.session['shipping'] = {'nombre': nombre, 'email': email, 'direccion': direccion, 'telefono': telefono, 'shipping_method': shipping_method, 'cupon': cupon_code}

        if metodo_pago == 'mercadopago':
            print("[DEBUG] Procesando pago con Mercado Pago...")

            # Crear preferencia de pago para Mercado Pago
            def apply_discount(price, pct):
                try:
                    return round(float(price) * (100 - int(pct)) / 100, 2)
                except Exception:
                    return float(price)
            discounted_items = [
                {
                    "title": item.producto.nombre,
                    "quantity": item.cantidad,
                    "unit_price": apply_discount(item.producto.precio, discount_pct),
                }
                for item in items
            ]
            preference_data = {
                "items": [
                    *discounted_items,
                    {"title": "Envío", "quantity": 1, "unit_price": float(shipping_cost)} if shipping_cost > 0 else None,
                ],
                "items": [i for i in preference_data["items"] if i],
                "payer": {
                    "name": nombre,
                    "email": email,
                },
                "metadata": {
                    "direccion": direccion,
                    "telefono": telefono,
                    "shipping_method": shipping_method,
                    "cupon": cupon_code
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
            
            # Crear pedido
            discounted_total = sum(item.cantidad * apply_discount(item.producto.precio, discount_pct) for item in items) + shipping_cost
            pedido = Pedido.objects.create(
                usuario=request.user,
                total=discounted_total,
                estado='procesando',
                metodo_pago='tarjeta_local',
                nombre_completo=nombre,
                email=email,
                direccion=request.POST.get('direccion', ''),
                telefono=request.POST.get('telefono', ''),
            )
            
            # Crear items del pedido
            for item in items:
                ItemPedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    nombre_producto=item.producto.nombre,
                    precio_unitario=apply_discount(item.producto.precio, discount_pct),
                    cantidad=item.cantidad,
                )
            # Descontar stock
            if item.producto and item.producto.stock is not None:
                item.producto.stock = max(0, item.producto.stock - item.cantidad)
                item.producto.save()
            
            # Limpiamos el carrito
            carrito.items.all().delete()

            messages.success(request, '¡Pago procesado exitosamente! Gracias por tu compra.')
            return redirect('tienda:detalle_pedido', pedido_id=pedido.id)

    return render(request, 'tienda/pago.html', {
        'items': items,
        'total': total
    })


# ✅ Pago exitoso (Mercado Pago)
@login_required
def pago_exitoso(request):
    """Callback de Mercado Pago cuando el pago es exitoso"""
    carrito = Carrito.objects.filter(usuario=request.user).first()
    
    if carrito and carrito.items.exists():
        # Calcular total
        items = list(carrito.items.select_related('producto').all())
        total = sum(item.cantidad * item.producto.precio for item in items)
        shipping = request.session.get('shipping', {})
        shipping_method = shipping.get('shipping_method', 'retiro')
        cupon_code = shipping.get('cupon')
        shipping_cost = 0
        if shipping_method == 'estandar':
            shipping_cost = 1500
        elif shipping_method == 'express':
            shipping_cost = 3000
        discount_pct = 0
        if cupon_code:
            cupon_obj = Cupon.objects.filter(codigo=cupon_code, activo=True).first()
            if cupon_obj:
                discount_pct = cupon_obj.porcentaje
        
        # Obtener parámetros de Mercado Pago
        payment_id = request.GET.get('payment_id')
        preference_id = request.GET.get('preference_id')
        
        # Leer datos de envío guardados previamente
        shipping = request.session.get('shipping', {})
        # Crear pedido
        def apply_discount(price, pct):
            try:
                return round(float(price) * (100 - int(pct)) / 100, 2)
            except Exception:
                return float(price)
        discounted_total = sum(item.cantidad * apply_discount(item.producto.precio, discount_pct) for item in items) + shipping_cost
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=discounted_total,
            estado='procesando',
            metodo_pago='mercadopago',
            nombre_completo=shipping.get('nombre') or request.user.get_full_name() or request.user.username,
            email=shipping.get('email') or request.user.email,
            direccion=shipping.get('direccion', ''),
            telefono=shipping.get('telefono', ''),
            payment_id=payment_id,
            preference_id=preference_id,
        )
        
        # Crear items del pedido
        for item in items:
            ItemPedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                nombre_producto=item.producto.nombre,
                precio_unitario=apply_discount(item.producto.precio, discount_pct),
                cantidad=item.cantidad,
            )
        # Descontar stock
        if item.producto and item.producto.stock is not None:
            item.producto.stock = max(0, item.producto.stock - item.cantidad)
            item.producto.save()
        
        # Limpiar carrito y datos de envío en sesión
        carrito.items.all().delete()
        try:
            del request.session['shipping']
        except KeyError:
            pass
        
        return render(request, 'tienda/pago_exitoso.html', {'pedido': pedido})
    
    return render(request, 'tienda/pago_exitoso.html')


# ❌ Pago fallido (Mercado Pago)
@login_required
def pago_fallido(request):
    return render(request, 'tienda/pago_fallido.html')


# ⏳ Pago pendiente (Mercado Pago)
@login_required
def pago_pendiente(request):
    return render(request, 'tienda/pago_pendiente.html')

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def mercadopago_webhook(request):
    """Webhook para recibir notificaciones de Mercado Pago y actualizar el estado del pedido."""
    try:
        if request.method == 'POST':
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except Exception:
                payload = {}
            payment_id = request.GET.get('id') or payload.get('id') or payload.get('data', {}).get('id')
            topic = request.GET.get('topic') or payload.get('type') or payload.get('topic')
            status = payload.get('data', {}).get('status') or payload.get('status')
            preference_id = payload.get('data', {}).get('preference_id') or payload.get('preference_id')
            # Intentar actualizar el pedido usando preference_id o payment_id
            pedido = None
            if preference_id:
                pedido = Pedido.objects.filter(preference_id=preference_id).first()
            if not pedido and payment_id:
                pedido = Pedido.objects.filter(payment_id=payment_id).first()
            if pedido:
                if status in ('approved', 'accredited'):
                    pedido.estado = 'procesando'
                elif status in ('pending', 'in_process'):
                    pedido.estado = 'pendiente'
                elif status in ('cancelled', 'rejected'):
                    pedido.estado = 'cancelado'
                pedido.save()
            return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True})
@login_required
def confirmar_recepcion(request, pedido_id):
    """El comprador confirma la recepción: marcamos el pedido como entregado y notificamos al vendedor."""
    from django.urls import reverse
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    if request.method == 'POST':
        pedido.estado = 'entregado'
        pedido.save()
        # Notificar a cada vendedor involucrado
        for item in pedido.items.select_related('producto'):
            if item.producto and item.producto.usuario:
                try:
                    Notificacion.objects.create(
                        usuario=item.producto.usuario,
                        tipo='venta',
                        mensaje=f'El comprador confirmó la recepción del pedido #{pedido.id}.',
                        link=reverse('tienda:detalle_pedido', args=[pedido.id])
                    )
                except Exception:
                    pass
        messages.success(request, 'Recepción confirmada. El vendedor fue notificado.')
        return redirect('tienda:detalle_pedido', pedido_id=pedido.id)
    return redirect('tienda:detalle_pedido', pedido_id=pedido.id)

def garantia(request):
    return render(request, 'tienda/garantia.html')

def _haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def productos_cerca_view(request):
    categorias = Producto.CATEGORIAS
    return render(request, 'tienda/cerca.html', {'categorias': categorias})

def productos_cerca_api(request):
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
    except Exception:
        return JsonResponse({'error': 'Ubicación inválida'}, status=400)
    try:
        radius = float(request.GET.get('radius', 10))
    except Exception:
        radius = 10.0
    qs = Producto.objects.exclude(latitud__isnull=True).exclude(longitud__isnull=True)
    items = []
    for p in qs:
        d = _haversine(lat, lon, p.latitud, p.longitud)
        if d <= radius:
            items.append({
                'id': p.id,
                'nombre': p.nombre,
                'precio': float(p.precio),
                'imagen': p.imagen.url if p.imagen else None,
                'categoria': p.get_categoria_display(),
                'distancia_km': round(d, 2),
                'ubicacion': p.ubicacion,
                'usuario_id': p.usuario_id,
                'usuario_nombre': p.usuario.username,
                'latitud': p.latitud,
                'longitud': p.longitud,
            })
    items.sort(key=lambda x: x['distancia_km'])
    return JsonResponse({'products': items})

# API: productos paginados (JSON)
def productos_api(request):
    categoria = request.GET.get('categoria', '').strip()
    q = request.GET.get('q', '').strip()
    precio_min = request.GET.get('precio_min', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    orden = request.GET.get('orden', 'recientes').strip()
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size', 12))
    except ValueError:
        page_size = 12
    categorias = dict(Producto.CATEGORIAS)
    productos_qs = Producto.objects.all()
    if q:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q) | Q(categoria__icontains=q)
        )
    if categoria in categorias:
        productos_qs = productos_qs.filter(categoria=categoria)
    if precio_min:
        try:
            productos_qs = productos_qs.filter(precio__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            productos_qs = productos_qs.filter(precio__lte=float(precio_max))
        except ValueError:
            pass
    if orden == 'precio_asc':
        productos_qs = productos_qs.order_by('precio')
    elif orden == 'precio_desc':
        productos_qs = productos_qs.order_by('-precio')
    elif orden == 'nombre':
        productos_qs = productos_qs.order_by('nombre')
    elif orden == 'antiguos':
        productos_qs = productos_qs.order_by('id')
    else:
        productos_qs = productos_qs.order_by('-id')
    if request.user.is_authenticated:
        productos_qs = productos_qs.annotate(
            es_favorito=Count('favoritos', filter=Q(favoritos__usuario=request.user)),
            promedio_calificacion=Avg('resenas__calificacion')
        )
    else:
        productos_qs = productos_qs.annotate(
            promedio_calificacion=Avg('resenas__calificacion')
        )
    paginator = Paginator(productos_qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({'products': [], 'has_next': False, 'page': page})
    productos = []
    email_verificado_cache = {}
    try:
        from allauth.account.models import EmailAddress
        email_model = EmailAddress
    except Exception:
        email_model = None
    for p in page_obj.object_list:
        verificado = False
        if email_model:
            uid = p.usuario_id
            if uid in email_verificado_cache:
                verificado = email_verificado_cache[uid]
            else:
                verificado = email_model.objects.filter(user_id=uid, verified=True).exists()
                email_verificado_cache[uid] = verificado
        # Vendor rating cache
        from .models import ResenaVendedor
        vendor_stats_cache = locals().get('vendor_stats_cache', {})
        if 'vendor_stats_cache' not in locals():
            vendor_stats_cache = {}
        estrellas = None
        total_estrellas = 0
        uid = p.usuario_id
        if uid in vendor_stats_cache:
            estrellas, total_estrellas = vendor_stats_cache[uid]
        else:
            agg = ResenaVendedor.objects.filter(vendedor_id=uid).aggregate(avg=Avg('calificacion'), total=Count('id'))
            estrellas = agg.get('avg')
            total_estrellas = agg.get('total') or 0
            vendor_stats_cache[uid] = (estrellas, total_estrellas)
        productos.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio': float(p.precio),
            'imagen': p.imagen.url if p.imagen else None,
            'categoria': p.get_categoria_display(),
            'usuario_id': p.usuario.id,
            'usuario_nombre': p.usuario.username,
            'stock': p.stock,
            'promedio_calificacion': float(p.promedio_calificacion) if p.promedio_calificacion else None,
            'es_favorito': bool(getattr(p, 'es_favorito', 0)),
            'email_verificado': verificado,
            'vendedor_estrellas': float(estrellas) if estrellas is not None else None,
            'vendedor_total': int(total_estrellas),
            'latitud': p.latitud,
            'longitud': p.longitud,
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


# 💬 Chat en tiempo real
@login_required
def obtener_conversaciones(request):
    """Obtiene lista de usuarios con conversaciones"""
    from django.db.models import Q
    from .models import Mensaje
    
    # Usuarios con los que el usuario actual ha chateado
    usuarios = User.objects.filter(
        Q(mensajes_enviados__destinatario=request.user) |
        Q(mensajes_recibidos__remitente=request.user)
    ).distinct().exclude(id=request.user.id)
    
    conversaciones = []
    for usuario in usuarios:
        ultimo_mensaje = Mensaje.objects.filter(
            Q(remitente=request.user, destinatario=usuario) |
            Q(remitente=usuario, destinatario=request.user)
        ).last()
        
        no_leidos = Mensaje.objects.filter(
            remitente=usuario,
            destinatario=request.user,
            leido=False
        ).count()
        
        conversaciones.append({
            'id': usuario.id,
            'username': usuario.username,
            'ultimo_mensaje': ultimo_mensaje.contenido[:50] if ultimo_mensaje else '',
            'timestamp': ultimo_mensaje.timestamp.isoformat() if ultimo_mensaje else None,
            'no_leidos': no_leidos,
        })
    
    return JsonResponse({'conversaciones': conversaciones})


@login_required
def obtener_mensajes(request, usuario_id):
    """Obtiene mensajes de una conversación específica"""
    from .models import Mensaje
    from django.db.models import Q
    
    try:
        otro_usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    mensajes = Mensaje.objects.filter(
        Q(remitente=request.user, destinatario=otro_usuario) |
        Q(remitente=otro_usuario, destinatario=request.user)
    ).select_related('remitente')
    
    # Marcar como leídos los mensajes del otro usuario
    Mensaje.objects.filter(
        remitente=otro_usuario,
        destinatario=request.user,
        leido=False
    ).update(leido=True)
    
    mensajes_list = []
    for msg in mensajes:
        mensajes_list.append({
            'id': msg.id,
            'remitente': msg.remitente.username,
            'remitente_id': msg.remitente.id,
            'contenido': msg.contenido,
            'timestamp': msg.timestamp.isoformat(),
            'es_mio': msg.remitente.id == request.user.id,
        })
    
    return JsonResponse({
        'otro_usuario': {
            'id': otro_usuario.id,
            'username': otro_usuario.username,
        },
        'mensajes': mensajes_list,
    })


@login_required
def enviar_mensaje(request):
    """Envía un mensaje a otro usuario"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    from .models import Mensaje
    
    data = json.loads(request.body)
    destinatario_id = data.get('destinatario_id')
    contenido = data.get('contenido', '').strip()
    
    if not contenido:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)
    
    try:
        destinatario = User.objects.get(id=destinatario_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    mensaje = Mensaje.objects.create(
        remitente=request.user,
        destinatario=destinatario,
        contenido=contenido
    )
    
    return JsonResponse({
        'success': True,
        'mensaje': {
            'id': mensaje.id,
            'remitente': mensaje.remitente.username,
            'contenido': mensaje.contenido,
            'timestamp': mensaje.timestamp.isoformat(),
        }
    })


@login_required
def obtener_usuarios_disponibles(request):
    """Obtiene lista de todos los usuarios (excepto el actual) para iniciar chat"""
    usuarios = User.objects.exclude(id=request.user.id).values('id', 'username')
    return JsonResponse({'usuarios': list(usuarios)})

@login_required
def agregar_pregunta(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        contenido = request.POST.get('contenido', '').strip()
        if contenido and request.user != producto.usuario:
            Pregunta.objects.create(producto=producto, usuario=request.user, contenido=contenido)
        return redirect('tienda:detalle_producto', producto_id=producto_id)
    return redirect('tienda:detalle_producto', producto_id=producto_id)

@login_required
def responder_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    producto = pregunta.producto
    if request.user != producto.usuario:
        return redirect('tienda:detalle_producto', producto_id=producto.id)
    if request.method == 'POST':
        contenido = request.POST.get('contenido', '').strip()
        if contenido:
            Respuesta.objects.update_or_create(pregunta=pregunta, defaults={'usuario': request.user, 'contenido': contenido})
        return redirect('tienda:detalle_producto', producto_id=producto.id)
    return redirect('tienda:detalle_producto', producto_id=producto.id)


# 👤 Perfil de Usuario
@login_required
def mi_perfil(request):
    """Vista del perfil del usuario actual con sus productos"""
    # Asegurar que el perfil existe
    from .models import Perfil
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)
    
    # Obtener productos del usuario
    mis_productos = Producto.objects.filter(usuario=request.user).order_by('-id')
    
    # Verificación de email (django-allauth)
    email_verificado = False
    try:
        from allauth.account.models import EmailAddress
        email_verificado = EmailAddress.objects.filter(user=request.user, verified=True).exists()
    except Exception:
        email_verificado = False

    return render(request, 'tienda/mi_perfil.html', {
        'perfil': perfil,
        'mis_productos': mis_productos,
        'email_verificado': email_verificado,
    })


def ver_perfil_usuario(request, usuario_id):
    """Vista del perfil de cualquier usuario (público)"""
    from .models import Perfil
    usuario = get_object_or_404(User, id=usuario_id)
    perfil, created = Perfil.objects.get_or_create(usuario=usuario)
    
    # Obtener productos del usuario
    productos = Producto.objects.filter(usuario=usuario).order_by('-id')
    
    # Verificación de email del usuario (django-allauth)
    email_verificado = False
    try:
        from allauth.account.models import EmailAddress
        email_verificado = EmailAddress.objects.filter(user=usuario, verified=True).exists()
    except Exception:
        email_verificado = False
    
    from .models import ResenaVendedor
    vendor_qs = ResenaVendedor.objects.filter(vendedor=usuario)
    vendor_stats = vendor_qs.aggregate(avg=Avg('calificacion'), total=Count('id'))
    reputacion_vendedor = vendor_stats.get('avg')
    total_resenas_vendedor = vendor_stats.get('total')
    dist_raw = list(vendor_qs.values('calificacion').annotate(c=Count('id')))
    histograma = {i: 0 for i in range(1, 6)}
    for r in dist_raw:
        histograma[int(r['calificacion'])] = int(r['c'])
    total = total_resenas_vendedor or 0
    histograma_pct = {k: (int(round(v * 100 / total)) if total > 0 else 0) for k, v in histograma.items()}
    histograma_items = [(s, histograma.get(s, 0), histograma_pct.get(s, 0)) for s in [5, 4, 3, 2, 1]]
    badges = []
    if reputacion_vendedor and total_resenas_vendedor:
        if reputacion_vendedor >= 4.5 and total_resenas_vendedor >= 10:
            badges.append('Excelente reputación')
        elif reputacion_vendedor >= 4.0 and total_resenas_vendedor >= 5:
            badges.append('Confiable')
        if total_resenas_vendedor < 3:
            badges.append('Nuevo vendedor')
    if productos.count() >= 10:
        badges.append('Vendedor activo')
    resena_actual = None
    if request.user.is_authenticated and request.user != usuario:
        resena_actual = ResenaVendedor.objects.filter(vendedor=usuario, usuario=request.user).first()

    return render(request, 'tienda/perfil_usuario.html', {
        'perfil': perfil,
        'usuario_perfil': usuario,
        'productos': productos,
        'email_verificado': email_verificado,
        'reputacion_vendedor': reputacion_vendedor,
        'total_resenas_vendedor': total_resenas_vendedor,
        'resena_actual': resena_actual,
        'histograma': histograma,
        'histograma_items': histograma_items,
        'badges': badges,
    })

@login_required
def calificar_vendedor(request, usuario_id):
    vendedor = get_object_or_404(User, id=usuario_id)
    if request.user == vendedor:
        return redirect('tienda:ver_perfil_usuario', usuario_id=usuario_id)
    from .models import ResenaVendedor
    if request.method == 'POST':
        cal = request.POST.get('calificacion')
        comentario = request.POST.get('comentario', '')
        try:
            cal = int(cal)
            if cal < 1 or cal > 5:
                raise ValueError()
        except Exception:
            messages.error(request, 'Selecciona una calificación válida.')
            return redirect('tienda:ver_perfil_usuario', usuario_id=usuario_id)
        obj, created = ResenaVendedor.objects.update_or_create(
            vendedor=vendedor, usuario=request.user,
            defaults={'calificacion': cal, 'comentario': comentario}
        )
        messages.success(request, 'Calificación registrada.')
    return redirect('tienda:ver_perfil_usuario', usuario_id=usuario_id)

def vendedores_destacados_view(request):
    from django.db.models import Avg, Count
    from .models import ResenaVendedor
    users = User.objects.annotate(
        estrellas=Avg('resenas_recibidas__calificacion'),
        total_estrellas=Count('resenas_recibidas')
    ).filter(total_estrellas__gt=0).order_by('-estrellas', '-total_estrellas')
    return render(request, 'tienda/vendedores_destacados.html', {'usuarios': users})

@login_required
def editar_perfil(request):
    """Editar perfil del usuario actual"""
    from .models import Perfil
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)
    
    if request.method == 'POST':
        # Actualizar bio
        bio = request.POST.get('bio', '')
        perfil.bio = bio
        
        # Actualizar foto de perfil si se subió una nueva
        if 'foto_perfil' in request.FILES:
            perfil.foto_perfil = request.FILES['foto_perfil']
        
        perfil.save()
        messages.success(request, '¡Perfil actualizado exitosamente!')
        return redirect('tienda:mi_perfil')
    
    return render(request, 'tienda/editar_perfil.html', {
        'perfil': perfil,
    })


# 📊 Dashboard de Vendedor
@login_required
def dashboard_view(request):
    """Panel principal del vendedor con estadísticas"""
    from django.db.models import Sum, Count
    from .models import ItemPedido, Producto
    
    # Obtener todos los items vendidos por este usuario
    # Un ItemPedido está vinculado a un Producto, y el Producto tiene un usuario (vendedor)
    items_vendidos = ItemPedido.objects.filter(producto__usuario=request.user).select_related('pedido', 'producto')
    
    # Calcular total ganado (suma de precio_unitario * cantidad)
    total_ganado = sum(item.subtotal() for item in items_vendidos)
    
    # Cantidad de ventas (cantidad de items vendidos)
    cantidad_ventas = items_vendidos.count()
    
    # Cantidad de productos publicados
    productos_publicados = Producto.objects.filter(usuario=request.user).count()
    
    # Últimas 5 ventas
    ultimas_ventas = items_vendidos.order_by('-pedido__fecha_pedido')[:5]
    
    return render(request, 'tienda/dashboard.html', {
        'total_ganado': total_ganado,
        'cantidad_ventas': cantidad_ventas,
        'productos_publicados': productos_publicados,
        'ultimas_ventas': ultimas_ventas,
    })


@login_required
def mis_ventas_view(request):
    """Listado completo de ventas realizadas"""
    from .models import ItemPedido
    
    items_vendidos = ItemPedido.objects.filter(producto__usuario=request.user)\
                                     .select_related('pedido', 'producto', 'pedido__usuario')\
                                     .order_by('-pedido__fecha_pedido')
    
    return render(request, 'tienda/mis_ventas.html', {
        'items_vendidos': items_vendidos,
    })


@login_required
def actualizar_estado_item(request, item_id):
    """Actualizar el estado de un ítem vendido"""
    from .models import ItemPedido
    from django.contrib import messages
    
    if request.method == 'POST':
        item = get_object_or_404(ItemPedido, id=item_id, producto__usuario=request.user)
        nuevo_estado = request.POST.get('estado')
        
        if nuevo_estado in dict(ItemPedido.ESTADO_CHOICES):
            item.estado = nuevo_estado
            item.save()
            messages.success(request, f'Estado actualizado a "{item.get_estado_display()}"')
        else:
            messages.error(request, 'Estado no válido')
            
    return redirect('tienda:mis_ventas')


# ========== FUNCIONALIDADES CORE ==========

# ⭐ Sistema de Favoritos
@login_required
def toggle_favorito(request, producto_id):
    """Agregar o quitar producto de favoritos (AJAX)"""
    from .models import Favorito
    producto = get_object_or_404(Producto, id=producto_id)
    favorito, created = Favorito.objects.get_or_create(usuario=request.user, producto=producto)
    
    if not created:
        favorito.delete()
        return JsonResponse({'status': 'removed', 'message': 'Producto quitado de favoritos'})
    
    return JsonResponse({'status': 'added', 'message': 'Producto agregado a favoritos'})


@login_required
def mis_favoritos(request):
    """Lista de productos favoritos del usuario"""
    from .models import Favorito
    favoritos = Favorito.objects.filter(usuario=request.user).select_related('producto')
    return render(request, 'tienda/favoritos.html', {
        'favoritos': favoritos,
    })


# 📝 Sistema de Reseñas
@login_required
def agregar_resena(request, producto_id):
    """Agregar o editar reseña de un producto"""
    from .models import Resena
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        comentario = request.POST.get('comentario', '')
        
        if not calificacion or int(calificacion) < 1 or int(calificacion) > 5:
            messages.error(request, 'Debes seleccionar una calificación válida (1-5 estrellas).')
            return redirect('tienda:detalle_producto', producto_id=producto_id)
        
        # Actualizar si ya existe, crear si no
        resena, created = Resena.objects.update_or_create(
            producto=producto,
            usuario=request.user,
            defaults={'calificacion': int(calificacion), 'comentario': comentario}
        )
        
        if created:
            messages.success(request, '¡Gracias por tu reseña!')
        else:
            messages.success(request, '¡Tu reseña ha sido actualizada!')
        
        return redirect('tienda:detalle_producto', producto_id=producto_id)
    
    return redirect('tienda:detalle_producto', producto_id=producto_id)


@login_required
def eliminar_resena(request, resena_id):
    """Eliminar una reseña propia"""
    from .models import Resena
    resena = get_object_or_404(Resena, id=resena_id, usuario=request.user)
    producto_id = resena.producto.id
    resena.delete()
    messages.success(request, 'Tu reseña ha sido eliminada.')
    return redirect('tienda:detalle_producto', producto_id=producto_id)


# 📦 Historial de Pedidos
@login_required
def mis_pedidos(request):
    """Lista de pedidos del usuario"""
    from .models import Pedido
    pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('items')
    return render(request, 'tienda/pedidos.html', {
        'pedidos': pedidos,
    })


@login_required
def detalle_pedido(request, pedido_id):
    """Detalle de un pedido específico"""
    from .models import Pedido
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'tienda/detalle_pedido.html', {
        'pedido': pedido,
    })
