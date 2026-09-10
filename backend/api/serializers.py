from rest_framework import serializers
from agenda.models import Tache, Categorie, PreferenceUtilisateur, StatistiqueUtilisation
from django.contrib.auth.models import User

class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = '__all__'
        read_only_fields = ['utilisateur']

class TacheSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)

    def validate_categorie(self, categorie):
        request = self.context.get('request')
        if categorie and request and categorie.utilisateur != request.user:
            raise serializers.ValidationError('Cette catégorie ne vous appartient pas.')
        return categorie
    
    class Meta:
        model = Tache
        fields = '__all__'
        read_only_fields = ['utilisateur', 'date_creation']

class PreferenceUtilisateurSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        debut = attrs.get('heure_productive_debut', getattr(self.instance, 'heure_productive_debut', None))
        fin = attrs.get('heure_productive_fin', getattr(self.instance, 'heure_productive_fin', None))

        if debut and fin and debut >= fin:
            raise serializers.ValidationError({
                'heure_productive_fin': 'L heure de fin doit être postérieure à l heure de début.'
            })
        return attrs

    class Meta:
        model = PreferenceUtilisateur
        fields = '__all__'
        read_only_fields = ['utilisateur']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
