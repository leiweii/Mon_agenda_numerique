from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategorieViewSet, PreferenceViewSet, RecommandationIAView, TacheViewSet
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
router.register(r'categories', CategorieViewSet, basename='categorie')
router.register(r'preferences', PreferenceViewSet, basename='preference')

urlpatterns = [
    path('taches/recommandation_ia/', RecommandationIAView.as_view(), name='recommandation-ia'),
    path('', include(router.urls)),
    path('auth/login/', login_view, name='login'),
    path('auth/register/', register_view, name='register'),
    path('auth/mot-de-passe-oublie/', password_reset_request_view, name='password-reset-request'),
    path('auth/reinitialiser-mot-de-passe/', password_reset_confirm_view, name='password-reset-confirm'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/user/', current_user, name='current-user'),
]
