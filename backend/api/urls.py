from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .agent_views import (
    AgentActionCancelView,
    AgentActionConfirmView,
    AgentChatView,
    AgentConversationDetailView,
)
from .gmail_views import GmailCallbackView, GmailConnectView, GmailStatusView, GmailVerifyView
from .views import CandidatureViewSet, CategorieViewSet, PreferenceViewSet, RecommandationIAView, TacheViewSet
from .authentication import (
    current_user,
    login_view,
    logout_view,
    password_reset_confirm_view,
    password_reset_request_view,
    register_view,
)

router = DefaultRouter()
router.register(r'taches', TacheViewSet, basename='tache')
router.register(r'candidatures', CandidatureViewSet, basename='candidature')
router.register(r'categories', CategorieViewSet, basename='categorie')
router.register(r'preferences', PreferenceViewSet, basename='preference')

urlpatterns = [
    path('gmail/connecter/', GmailConnectView.as_view(), name='gmail-connect'),
    path('gmail/oauth/callback/', GmailCallbackView.as_view(), name='gmail-callback'),
    path('gmail/statut/', GmailStatusView.as_view(), name='gmail-status'),
    path('gmail/verifier/', GmailVerifyView.as_view(), name='gmail-verify'),
    path('agent/chat/', AgentChatView.as_view(), name='agent-chat'),
    path(
        'agent/conversations/<int:conversation_id>/',
        AgentConversationDetailView.as_view(),
        name='agent-conversation-detail',
    ),
    path(
        'agent/actions/<int:action_id>/confirmer/',
        AgentActionConfirmView.as_view(),
        name='agent-action-confirm',
    ),
    path(
        'agent/actions/<int:action_id>/annuler/',
        AgentActionCancelView.as_view(),
        name='agent-action-cancel',
    ),
    path('taches/recommandation_ia/', RecommandationIAView.as_view(), name='recommandation-ia'),
    path('', include(router.urls)),
    path('auth/login/', login_view, name='login'),
    path('auth/register/', register_view, name='register'),
    path('auth/mot-de-passe-oublie/', password_reset_request_view, name='password-reset-request'),
    path('auth/reinitialiser-mot-de-passe/', password_reset_confirm_view, name='password-reset-confirm'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/user/', current_user, name='current-user'),
]
