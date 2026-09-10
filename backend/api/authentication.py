from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import authenticate
from rest_framework import status


class RegistrationRateThrottle(AnonRateThrottle):
    scope = 'registration'


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
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
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
    username = str(request.data.get('username', '')).strip().lower()
    email = str(request.data.get('email', '')).strip().lower()
    password = request.data.get('password', '')

    if not username or not email or not isinstance(password, str) or not password:
        return Response(
            {'error': "Données d'inscription invalides."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username__iexact=username).exists() or User.objects.filter(email__iexact=email).exists():
        return Response(
            {'error': 'Impossible de créer ce compte.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
