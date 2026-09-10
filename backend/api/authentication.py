import re

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import authenticate
from django.utils.text import slugify
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
