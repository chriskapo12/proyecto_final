from .models import Notificacion

def notificaciones(request):
    if request.user.is_authenticated:
        notificaciones_no_leidas = Notificacion.objects.filter(usuario=request.user, leido=False).count()
        ultimas_notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')[:5]
        return {
            'notificaciones_count': notificaciones_no_leidas,
            'notificaciones_list': ultimas_notificaciones
        }
    return {}
