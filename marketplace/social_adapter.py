from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter que intenta vincular automáticamente una cuenta social a un usuario
    local existente buscándolo por email. Si encuentra el usuario, llama a
    `sociallogin.connect(request, user)` para asociar la SocialAccount al usuario
    y evitar la pantalla de signup de allauth.
    """

    def pre_social_login(self, request, sociallogin):
        # Si el usuario ya está autenticado, no hacemos nada
        if request.user.is_authenticated:
            return

        # Intentar obtener el email desde distintos lugares
        email = None
        try:
            email = sociallogin.account.extra_data.get('email')
        except Exception:
            pass

        if not email:
            email = getattr(sociallogin.user, 'email', None)

        # some providers populate sociallogin.email_addresses
        try:
            if (not email) and hasattr(sociallogin, 'email_addresses'):
                if sociallogin.email_addresses:
                    email = sociallogin.email_addresses[0].email
        except Exception:
            pass

        if not email:
            return

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        # Vincular la SocialAccount al usuario existente para evitar el formulario
        try:
            sociallogin.connect(request, user)
        except Exception:
            # Si algo falla, no interrumpimos el flujo; dejamos que allauth maneje
            # el caso por defecto (mostrar el formulario de registro o error)
            pass
