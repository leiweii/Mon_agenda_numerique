"""Envoi individuel via Gmail API, sans retransmission automatique."""

import base64
import socket
from email.message import EmailMessage

import requests
from django.utils import timezone
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .gmail_oauth_service import GMAIL_SEND_SCOPE, OAuthError, _configuration, chiffrer, dechiffrer
from .models import ConnexionGmail


SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'


class EnvoiRefuse(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ResultatIncertain(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _dns_error(error):
    """Reconnaît uniquement les échecs de résolution identifiables."""
    pending = [error]
    visited = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if isinstance(current, socket.gaierror):
            return True
        pending.extend(value for value in getattr(current, 'args', ()) if isinstance(value, BaseException))
        pending.extend(
            value for value in (getattr(current, '__cause__', None), getattr(current, '__context__', None))
            if isinstance(value, BaseException)
        )
        reason = getattr(current, 'reason', None)
        if isinstance(reason, BaseException):
            pending.append(reason)
    return False


def _access_token(connexion):
    if connexion.statut != ConnexionGmail.Statut.CONNECTE or not connexion.refresh_token_chiffre:
        raise EnvoiRefuse('reconnect_required')
    try:
        client_id, client_secret, _ = _configuration()
        original_refresh = dechiffrer(connexion.refresh_token_chiffre)
    except OAuthError as exc:
        raise EnvoiRefuse('reconnect_required' if exc.args[0] == 'credentials_unavailable' else 'oauth_configuration') from None

    credentials = Credentials(
        token=None,
        refresh_token=original_refresh,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=[GMAIL_SEND_SCOPE],
    )
    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        if 'invalid_grant' in str(exc).lower():
            connexion.statut = ConnexionGmail.Statut.RECONNEXION_REQUISE
            connexion.refresh_token_chiffre = ''
            connexion.date_verification = timezone.now()
            connexion.save(update_fields=['statut', 'refresh_token_chiffre', 'date_verification'])
            raise EnvoiRefuse('reconnect_required') from None
        raise EnvoiRefuse('oauth_unavailable') from None
    except (TransportError, requests.RequestException):
        raise EnvoiRefuse('oauth_unavailable') from None
    if not credentials.token:
        raise EnvoiRefuse('oauth_unavailable')

    connexion.date_verification = timezone.now()
    changed = ['date_verification']
    if credentials.refresh_token and credentials.refresh_token != original_refresh:
        connexion.refresh_token_chiffre = chiffrer(credentials.refresh_token)
        changed.append('refresh_token_chiffre')
    connexion.save(update_fields=changed)
    return credentials.token


def envoyer_message_gmail(*, connexion, recipient, subject, body, cv_bytes, cv_filename):
    access_token = _access_token(connexion)
    message = EmailMessage()
    message['From'] = connexion.utilisateur.email
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(body)
    message.add_attachment(cv_bytes, maintype='application', subtype='pdf', filename=cv_filename)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')

    try:
        response = requests.post(
            SEND_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            json={'raw': raw},
            timeout=(5, 20),
            allow_redirects=False,
        )
    except requests.exceptions.ConnectTimeout:
        raise EnvoiRefuse('connection_not_established') from None
    except requests.exceptions.SSLError as exc:
        # Une erreur TLS tardive peut survenir apres la transmission du POST.
        # Seul un handshake explicitement identifie prouve l'absence d'envoi.
        if 'handshake' in str(exc).lower() or 'certificate verify' in str(exc).lower():
            raise EnvoiRefuse('connection_not_established') from None
        raise ResultatIncertain('network_outcome_unknown') from None
    except requests.exceptions.ConnectionError as exc:
        if _dns_error(exc):
            raise EnvoiRefuse('connection_not_established') from None
        raise ResultatIncertain('network_outcome_unknown') from None
    except requests.RequestException:
        raise ResultatIncertain('network_outcome_unknown') from None

    if 200 <= response.status_code < 300:
        try:
            message_id = response.json().get('id')
        except (ValueError, AttributeError, TypeError):
            message_id = None
        if isinstance(message_id, str) and message_id.strip():
            return message_id
        raise ResultatIncertain('gmail_response_incomplete')
    if 400 <= response.status_code < 500 and response.status_code != 408:
        if response.status_code == 401:
            connexion.statut = ConnexionGmail.Statut.RECONNEXION_REQUISE
            connexion.refresh_token_chiffre = ''
            connexion.date_verification = timezone.now()
            connexion.save(update_fields=['statut', 'refresh_token_chiffre', 'date_verification'])
            raise EnvoiRefuse('reconnect_required')
        raise EnvoiRefuse('gmail_rejected')
    raise ResultatIncertain('gmail_outcome_unknown')
