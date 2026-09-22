"""Flux OAuth Gmail cote serveur ; aucun envoi de message dans ce module."""

from datetime import timedelta
from hashlib import sha256
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from .models import ConnexionGmail, TentativeOAuthGmail


GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'
TENTATIVE_TTL = timedelta(minutes=10)


class OAuthError(Exception):
    """Erreur publique et non sensible du flux OAuth."""


def _configuration():
    client_id = getattr(settings, 'GMAIL_OAUTH_CLIENT_ID', '')
    client_secret = getattr(settings, 'GMAIL_OAUTH_CLIENT_SECRET', '')
    redirect_uri = getattr(settings, 'GMAIL_OAUTH_REDIRECT_URI', '')
    if not all((client_id, client_secret, redirect_uri)):
        raise OAuthError('configuration_missing')
    return client_id, client_secret, redirect_uri


def _fernet():
    key = getattr(settings, 'GMAIL_TOKEN_ENCRYPTION_KEY', '')
    if not key:
        raise OAuthError('configuration_missing')
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise OAuthError('configuration_invalid') from exc


def chiffrer(value):
    return _fernet().encrypt(value.encode('utf-8')).decode('ascii')


def dechiffrer(value):
    try:
        return _fernet().decrypt(value.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeError) as exc:
        raise OAuthError('credentials_unavailable') from exc


def _client_config():
    client_id, client_secret, redirect_uri = _configuration()
    return {
        'web': {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uris': [redirect_uri],
            'auth_uri': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
        }
    }


def demarrer_connexion(user):
    _configuration()
    _fernet()
    TentativeOAuthGmail.objects.filter(expires_at__lte=timezone.now()).delete()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    flow = Flow.from_client_config(
        _client_config(), scopes=[GMAIL_SEND_SCOPE],
        redirect_uri=settings.GMAIL_OAUTH_REDIRECT_URI,
        state=state, code_verifier=verifier,
    )
    url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    TentativeOAuthGmail.objects.create(
        utilisateur=user,
        state_digest=sha256(state.encode('ascii')).hexdigest(),
        pkce_verifier_chiffre=chiffrer(verifier),
        expires_at=timezone.now() + TENTATIVE_TTL,
    )
    return url


def terminer_connexion(*, state, code=None, error=None):
    if not state or len(state) > 256:
        raise OAuthError('state_invalid')
    digest = sha256(state.encode('utf-8')).hexdigest()
    with transaction.atomic():
        tentative = TentativeOAuthGmail.objects.select_for_update().filter(state_digest=digest).first()
        if not tentative or tentative.consumed_at or tentative.expires_at <= timezone.now():
            raise OAuthError('state_invalid')
        verifier = dechiffrer(tentative.pkce_verifier_chiffre) if code and not error else None
        tentative.consumed_at = timezone.now()
        tentative.pkce_verifier_chiffre = ''
        tentative.save(update_fields=['consumed_at', 'pkce_verifier_chiffre'])

    if error:
        raise OAuthError('consent_denied')
    if not code or len(code) > 2048:
        raise OAuthError('code_invalid')

    flow = Flow.from_client_config(
        _client_config(), scopes=[GMAIL_SEND_SCOPE],
        redirect_uri=settings.GMAIL_OAUTH_REDIRECT_URI,
        state=state, code_verifier=verifier,
    )
    try:
        flow.fetch_token(code=code)
        refresh_token = flow.credentials.refresh_token
    except Exception as exc:
        raise OAuthError('oauth_exchange_failed') from exc
    if not refresh_token:
        raise OAuthError('refresh_token_missing')

    ConnexionGmail.objects.update_or_create(
        utilisateur=tentative.utilisateur,
        defaults={
            'refresh_token_chiffre': chiffrer(refresh_token),
            'statut': ConnexionGmail.Statut.CONNECTE,
            'date_verification': timezone.now(),
        },
    )
    return 'connected'


def statut_connexion(user):
    connexion = ConnexionGmail.objects.filter(utilisateur=user).first()
    if not connexion:
        return 'disconnected'
    return connexion.statut


def verifier_connexion(user):
    connexion = ConnexionGmail.objects.filter(utilisateur=user).first()
    if not connexion:
        return 'disconnected'
    if connexion.statut == ConnexionGmail.Statut.RECONNEXION_REQUISE or not connexion.refresh_token_chiffre:
        return 'reconnect_required'

    client_id, client_secret, _ = _configuration()
    initial_refresh_token = dechiffrer(connexion.refresh_token_chiffre)
    credentials = Credentials(
        token=None,
        refresh_token=initial_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=[GMAIL_SEND_SCOPE],
    )
    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        if 'invalid_grant' not in str(exc).lower():
            raise OAuthError('temporary_error') from exc
        connexion.statut = ConnexionGmail.Statut.RECONNEXION_REQUISE
        connexion.refresh_token_chiffre = ''
        connexion.date_verification = timezone.now()
        connexion.save(update_fields=['statut', 'refresh_token_chiffre', 'date_verification'])
        return 'reconnect_required'
    except TransportError as exc:
        raise OAuthError('temporary_error') from exc

    connexion.date_verification = timezone.now()
    changed_fields = ['date_verification']
    if credentials.refresh_token and credentials.refresh_token != initial_refresh_token:
        connexion.refresh_token_chiffre = chiffrer(credentials.refresh_token)
        changed_fields.append('refresh_token_chiffre')
    connexion.save(update_fields=changed_fields)
    return 'connected'
