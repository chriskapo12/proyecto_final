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

from .models import Producto, Carrito, CarritoItem, Favorito, Resena, Pedido, ItemPedido
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
    
    # Agregar información de favoritos si el usuario está autenticado
    if request.user.is_authenticated:
        productos_qs = productos_qs.annotate(
            es_favorito=Count('favoritos', filter=Q(favoritos__usuario=request.user)),
            promedio_calificacion=Avg('resenas__calificacion')
        )
    else:
        productos_qs = productos_qs.annotate(
            promedio_calificacion=Avg('resenas__calificacion')
        )
    
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
            promedio_calificacion=Avg('resenas__calificacion')
        )
    else:
        productos = productos.annotate(
            promedio_calificacion=Avg('resenas__calificacion')
        )
    
    categorias = [
        ('licor', 'Licor'),
        ('energizante', 'Energizante'),
        ('cerveza', 'Cerveza'),
        ('vino', 'Vino'),
    ]
    
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
    
    # Verificar si el usuario ya reseñó este producto
    resena_usuario = None
    es_favorito = False
    if request.user.is_authenticated:
        resena_usuario = resenas.filter(usuario=request.user).first()
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()
    
    return render(request, 'tienda/detalle_producto.html', {
        'producto': producto,
        'resenas': resenas,
        'promedio_calificacion': promedio_calificacion,
        'total_resenas': total_resenas,
        'resena_usuario': resena_usuario,
        'es_favorito': es_favorito,
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
    return render(request, 'tienda/agregar_producto.html', {'form': form})

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
    
    return render(request, 'tienda/editar_producto.html', {'form': form, 'producto': producto})

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
            
            # Crear pedido
            pedido = Pedido.objects.create(
                usuario=request.user,
                total=total,
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
                    precio_unitario=item.producto.precio,
                    cantidad=item.cantidad,
                )
            
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
        
        # Obtener parámetros de Mercado Pago
        payment_id = request.GET.get('payment_id')
        preference_id = request.GET.get('preference_id')
        
        # Crear pedido
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total,
            estado='procesando',
            metodo_pago='mercadopago',
            nombre_completo=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            payment_id=payment_id,
            preference_id=preference_id,
        )
        
        # Crear items del pedido
        for item in items:
            ItemPedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                nombre_producto=item.producto.nombre,
                precio_unitario=item.producto.precio,
                cantidad=item.cantidad,
            )
        
        # Limpiar carrito
        carrito.items.all().delete()
        
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
            'usuario_id': p.usuario.id,
            'usuario_nombre': p.usuario.username,
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


# 👤 Perfil de Usuario
@login_required
def mi_perfil(request):
    """Vista del perfil del usuario actual con sus productos"""
    # Asegurar que el perfil existe
    from .models import Perfil
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)
    
    # Obtener productos del usuario
    mis_productos = Producto.objects.filter(usuario=request.user).order_by('-id')
    
    return render(request, 'tienda/mi_perfil.html', {
        'perfil': perfil,
        'mis_productos': mis_productos,
    })


def ver_perfil_usuario(request, usuario_id):
    """Vista del perfil de cualquier usuario (público)"""
    from .models import Perfil
    usuario = get_object_or_404(User, id=usuario_id)
    perfil, created = Perfil.objects.get_or_create(usuario=usuario)
    
    # Obtener productos del usuario
    productos = Producto.objects.filter(usuario=usuario).order_by('-id')
    
    return render(request, 'tienda/perfil_usuario.html', {
        'perfil': perfil,
        'usuario_perfil': usuario,
        'productos': productos,
    })


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
