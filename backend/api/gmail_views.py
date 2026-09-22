"""Endpoints de connexion Gmail, separes des endpoints d'envoi."""

from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .gmail_oauth_service import (
    OAuthError,
    demarrer_connexion,
    statut_connexion,
    terminer_connexion,
    verifier_connexion,
)


def _message(statut):
    if statut == 'reconnect_required':
        return 'Reconnectez votre compte Gmail pour continuer.'
    if statut == 'connected':
        return 'Compte Gmail connecte.'
    return 'Aucun compte Gmail connecte.'


class GmailConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            url = demarrer_connexion(request.user)
        except OAuthError:
            return Response({'detail': 'La connexion Gmail est indisponible.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'authorization_url': url})


class GmailCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        outcome = 'error'
        try:
            outcome = terminer_connexion(
                state=request.query_params.get('state', ''),
                code=request.query_params.get('code'),
                error=request.query_params.get('error'),
            )
        except OAuthError:
            pass
        destination = f'{settings.FRONTEND_URL.rstrip("/")}/parametres?{urlencode({"gmail": outcome})}'
        return HttpResponseRedirect(destination)


class GmailStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current = statut_connexion(request.user)
        return Response({'status': current})


class GmailVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            current = verifier_connexion(request.user)
        except OAuthError:
            return Response(
                {'detail': 'Verification Gmail momentanement indisponible. Reessayez plus tard.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'status': current, 'message': _message(current)})
