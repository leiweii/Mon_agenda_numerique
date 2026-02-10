from rest_framework import serializers
from agenda.models import Tache, Categorie, PreferenceUtilisateur, StatistiqueUtilisation
from django.contrib.auth.models import User

class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = '__all__'

class TacheSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    
    class Meta:
        model = Tache
        fields = '__all__'
        read_only_fields = ['utilisateur', 'date_creation']

class PreferenceUtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreferenceUtilisateur
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']