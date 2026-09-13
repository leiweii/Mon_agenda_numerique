from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend


class EmailOuUsernameBackend(BaseBackend):
    """Authentifie un compte à partir de son e-mail ou de son nom d'utilisateur."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = str(username or kwargs.get('identifier') or '').strip()
        if not identifier or not password:
            return None

        user_model = get_user_model()
        lookup = {'email__iexact': identifier} if '@' in identifier else {'username__iexact': identifier}
        user = user_model.objects.filter(**lookup).first()

        if user and user.is_active and user.check_password(password):
            return user
        return None
