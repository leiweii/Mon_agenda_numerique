import re
from hashlib import sha256

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.text import slugify
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework import status


class RegistrationRateThrottle(AnonRateThrottle):
    scope = 'registration'


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

    def parse_rate(self, rate):
        if rate and rate.endswith('min'):
            requests, period = rate.split('/', 1)
            return int(requests), int(period.removesuffix('min')) * 60
        return super().parse_rate(rate)


class PasswordResetRequestRateThrottle(AnonRateThrottle):
    scope = 'password_reset_request'


class PasswordResetEmailRateThrottle(SimpleRateThrottle):
    scope = 'password_reset_email'

    def get_cache_key(self, request, view):
        email = str(request.data.get('email', '')).strip().lower()
        if not email:
            return None

        email_hash = sha256(email.encode('utf-8')).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': email_hash}


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = 'password_reset'


def generate_username(email):
    username_field = User._meta.get_field('username')
    max_length = username_field.max_length
    local_part = email.split('@', 1)[0]
    normalized_local_part = re.sub(r'[\W_]+', ' ', local_part)
    base_username = (slugify(normalized_local_part) or 'utilisateur')[:max_length]
    username = base_username
    suffix = 2

    while User.objects.filter(username__iexact=username).exists():
        suffix_text = f'-{suffix}'
        username = f'{base_username[:max_length - len(suffix_text)]}{suffix_text}'
        suffix += 1

    return username


def user_response(user, status_code=status.HTTP_200_OK):
    token, created = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    }, status=status_code)

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    identifier = request.data.get('identifier') or request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=identifier, password=password)
    
    if user:
        return user_response(user)
    
    return Response(
        {'error': 'Identifiants invalides'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegistrationRateThrottle])
def register_view(request):
    email = str(request.data.get('email', '')).strip().lower()
    password = request.data.get('password', '')
    password_confirmation = request.data.get('password_confirmation', '')

    if not email or not isinstance(password, str) or not password:
        return Response(
            {'error': "Données d'inscription invalides."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != password_confirmation:
        return Response(
            {'error': 'Les mots de passe ne correspondent pas.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email__iexact=email).exists():
        return Response(
            {'error': 'Un compte existe déjà avec cette adresse e-mail.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = generate_username(email)
    user = User(username=username, email=email)
    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return Response(
            {'error': 'Mot de passe invalide.', 'details': error.messages},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save()
    return user_response(user, status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRequestRateThrottle, PasswordResetEmailRateThrottle])
def password_reset_request_view(request):
    email = str(request.data.get('email', '')).strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first()

    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = (
            f'{settings.FRONTEND_URL.rstrip("/")}/reinitialiser-mot-de-passe/{uid}/{token}'
        )
        send_mail(
            'Réinitialisation de votre mot de passe',
            f'Utilisez ce lien pour réinitialiser votre mot de passe : {reset_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

    return Response({'message': 'Si ce compte existe, un e-mail a été envoyé.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRateThrottle])
def password_reset_confirm_view(request):
    uid = request.data.get('uid')
    token = request.data.get('token')
    password = request.data.get('password', '')
    password_confirmation = request.data.get('password_confirmation', '')

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if not user or not token or not default_token_generator.check_token(user, token):
        return Response(
            {'error': 'Lien de réinitialisation invalide ou expiré.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(password, str) or not password:
        return Response(
            {'error': 'Mot de passe invalide.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != password_confirmation:
        return Response(
            {'error': 'Les mots de passe ne correspondent pas.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return Response(
            {'error': 'Mot de passe invalide.', 'details': error.messages},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save()
    return Response({'message': 'Mot de passe réinitialisé avec succès.'})


@api_view(['POST'])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'message': 'Déconnexion réussie'})

@api_view(['GET'])
def current_user(request):
    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
    })
