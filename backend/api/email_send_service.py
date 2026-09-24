"""Transitions sûres pour l'envoi individuel des candidatures."""

import hashlib
import re
from datetime import timedelta
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from .gmail_send_service import EnvoiRefuse, ResultatIncertain, envoyer_message_gmail
from .models import ActionCandidature, CVUtilisateur, ConnexionGmail, EmailCandidature


RECONCILIATION_DELAY = timedelta(minutes=5)
MAX_CV_BYTES = 5 * 1024 * 1024


class EmailSendError(Exception):
    def __init__(self, detail, status_code):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def reconciliation_disponible(email, now=None):
    return email.status == EmailCandidature.Status.SENDING and (
        bool(email.error_message) or email.updated_at <= (now or timezone.now()) - RECONCILIATION_DELAY
    )


def _history(email, *, manual=False):
    label = 'confirme manuellement apres resultat incertain' if manual else 'envoye via Gmail'
    ActionCandidature.objects.create(
        candidature=email.candidature,
        type_action=ActionCandidature.TypeAction.CANDIDATURE_ENVOYEE,
        date_action=timezone.now(),
        commentaire=f'Email #{email.id} {label}.',
    )


def lire_cv_par_defaut(user):
    """Retourne les octets figés et une empreinte du contenu et du nom joint."""
    cv = CVUtilisateur.objects.filter(utilisateur=user).first()
    if not cv or not cv.fichier:
        raise EmailSendError('Configurez un CV par defaut accessible.', 400)
    try:
        with cv.fichier.open('rb') as source:
            cv_bytes = source.read(MAX_CV_BYTES + 1)
    except (OSError, ValueError):
        raise EmailSendError('Le CV par defaut est inaccessible.', 400) from None
    if (
        len(cv_bytes) > MAX_CV_BYTES or not cv_bytes.startswith(b'%PDF-')
        or not cv.fichier.name.lower().endswith('.pdf')
    ):
        raise EmailSendError('Le CV par defaut doit etre un PDF de 5 Mio maximum.', 400)
    filename = PurePosixPath(cv.fichier.name).name
    fingerprint = hashlib.sha256(filename.encode('utf-8') + b'\0' + cv_bytes).hexdigest()
    return cv_bytes, filename, fingerprint


def _prepare_payload(email, user, expected_cv_fingerprint):
    if not isinstance(expected_cv_fingerprint, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_cv_fingerprint):
        raise EmailSendError('Confirmez le CV avant l’envoi.', 400)
    try:
        validate_email(user.email)
    except ValidationError:
        raise EmailSendError('Adresse de l’expediteur invalide.', 400) from None
    try:
        validate_email(email.recipient_email)
    except ValidationError:
        raise EmailSendError('Adresse du destinataire invalide.', 400) from None
    if not email.subject.strip() or not email.body.strip() or any(char in email.subject for char in '\r\n\x00'):
        raise EmailSendError('Objet et message requis.', 400)
    connexion = ConnexionGmail.objects.filter(utilisateur=user).first()
    if not connexion or connexion.statut != ConnexionGmail.Statut.CONNECTE or not connexion.refresh_token_chiffre:
        raise EmailSendError('Reconnectez votre compte Gmail avant l’envoi.', 409)
    cv_bytes, cv_filename, cv_fingerprint = lire_cv_par_defaut(user)
    if expected_cv_fingerprint != cv_fingerprint:
        raise EmailSendError('Le CV a change depuis votre confirmation. Verifiez-le avant l’envoi.', 409)
    return connexion, cv_bytes, cv_filename


def envoyer_email(email, user, expected_cv_fingerprint):
    """Réserve en base avant le réseau, puis finalise sans jamais retransmettre."""
    with transaction.atomic():
        current = EmailCandidature.objects.select_for_update().get(pk=email.pk)
        if current.status == EmailCandidature.Status.SENT:
            return current, 200
        if current.status != EmailCandidature.Status.READY:
            raise EmailSendError('Cet email n’est pas pret pour l’envoi.', 409)

    connexion, cv_bytes, cv_filename = _prepare_payload(current, user, expected_cv_fingerprint)
    with transaction.atomic():
        current = EmailCandidature.objects.select_for_update().get(pk=email.pk)
        if current.status == EmailCandidature.Status.SENT:
            return current, 200
        if current.status != EmailCandidature.Status.READY:
            raise EmailSendError('Cet email est deja en cours ou traite.', 409)
        current.status = EmailCandidature.Status.SENDING
        current.error_message = ''
        current.save(update_fields=['status', 'error_message', 'updated_at'])

    try:
        gmail_id = envoyer_message_gmail(
            connexion=connexion,
            recipient=current.recipient_email,
            subject=current.subject,
            body=current.body,
            cv_bytes=cv_bytes,
            cv_filename=cv_filename,
        )
    except EnvoiRefuse as exc:
        outcome, status_code = exc.code, 502
    except ResultatIncertain as exc:
        outcome, status_code = exc.code, 202
    except Exception:
        outcome, status_code = 'gmail_outcome_unknown', 202
    else:
        if isinstance(gmail_id, str) and gmail_id.strip() and len(gmail_id) <= 255:
            outcome, status_code = gmail_id, 200
        else:
            outcome, status_code = 'gmail_response_incomplete', 202

    with transaction.atomic():
        current = EmailCandidature.objects.select_for_update().get(pk=email.pk)
        if current.status != EmailCandidature.Status.SENDING:
            return current, 200 if current.status == EmailCandidature.Status.SENT else 409
        if status_code == 200:
            current.status = EmailCandidature.Status.SENT
            current.gmail_message_id = outcome
            current.sent_at = timezone.now()
            current.error_message = ''
            current.save(update_fields=['status', 'gmail_message_id', 'sent_at', 'error_message', 'updated_at'])
            _history(current)
        elif status_code == 502:
            current.status = EmailCandidature.Status.FAILED
            current.error_message = outcome
            current.save(update_fields=['status', 'error_message', 'updated_at'])
        else:
            current.error_message = outcome
            current.save(update_fields=['error_message', 'updated_at'])
    return current, status_code


def confirmer_manuellement(email):
    with transaction.atomic():
        current = EmailCandidature.objects.select_for_update().get(pk=email.pk)
        if current.status == EmailCandidature.Status.SENT:
            return current
        if not reconciliation_disponible(current):
            raise EmailSendError('Attendez la fin de l’envoi avant de confirmer.', 409)
        current.status = EmailCandidature.Status.SENT
        current.manual_confirmation_at = timezone.now()
        current.sent_at = current.manual_confirmation_at
        current.error_message = ''
        current.save(update_fields=['status', 'manual_confirmation_at', 'sent_at', 'error_message', 'updated_at'])
        _history(current, manual=True)
    return current


def nouvelle_tentative(email):
    with transaction.atomic():
        current = EmailCandidature.objects.select_for_update().get(pk=email.pk)
        existing = EmailCandidature.objects.filter(retry_of=current).first()
        if existing:
            return existing, False
        retryable = current.status in {EmailCandidature.Status.SENDING, EmailCandidature.Status.FAILED} or (
            current.status == EmailCandidature.Status.CANCELLED and current.retry_of_id is not None
        )
        if not retryable:
            raise EmailSendError('Aucune nouvelle tentative possible pour cet email.', 409)
        if current.status == EmailCandidature.Status.SENDING and not reconciliation_disponible(current):
            raise EmailSendError('Attendez la fin de l’envoi avant de relancer.', 409)
        try:
            with transaction.atomic():
                retry = EmailCandidature.objects.create(
                    candidature=current.candidature,
                    retry_of=current,
                    recipient_email=current.recipient_email,
                    recipient_name=current.recipient_name,
                    subject=current.subject,
                    body=current.body,
                )
        except IntegrityError:
            retry = EmailCandidature.objects.get(retry_of=current)
            return retry, False
    return retry, True
