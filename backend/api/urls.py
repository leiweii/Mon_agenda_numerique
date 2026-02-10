from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TacheViewSet, CategorieViewSet, PreferenceViewSet
from .authentication import login_view, logout_view, current_user

router = DefaultRouter()
router.register(r'taches', TacheViewSet, basename='tache')
router.register(r'categories', CategorieViewSet, basename='categorie')
router.register(r'preferences', PreferenceViewSet, basename='preference')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/user/', current_user, name='current-user'),
]