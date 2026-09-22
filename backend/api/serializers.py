from rest_framework import serializers
from agenda.models import Tache, Categorie, PreferenceUtilisateur, StatistiqueUtilisation
from api.models import ActionCandidature, Candidature, EmailCandidature
from django.contrib.auth.models import User
from urllib.parse import urlsplit


class ImportCandidatureSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=1000)

    def validate_url(self, value):
        parts = urlsplit(value)
        try:
            port = parts.port
        except ValueError:
            raise serializers.ValidationError('Le port de cette URL est invalide.')
        if port == 0:
            raise serializers.ValidationError('Le port de cette URL est invalide.')
        if parts.scheme not in {'http', 'https'} or parts.username or parts.password:
            raise serializers.ValidationError('Une URL HTTP(S) sans identifiants est requise.')
        return value

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


class CandidatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidature
        fields = '__all__'
        read_only_fields = ['utilisateur', 'date_ajout', 'date_modification']


class ActionCandidatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionCandidature
        fields = '__all__'
        read_only_fields = ['candidature', 'date_creation']


class PreparationEmailCandidatureSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(max_length=254)
    civilite = serializers.CharField(required=False, allow_blank=True, max_length=30)
    prenom_contact = serializers.CharField(required=False, allow_blank=True, max_length=100)
    nom_contact = serializers.CharField(required=False, allow_blank=True, max_length=100)
    formation = serializers.CharField(max_length=255)
    portfolio_url = serializers.URLField(max_length=500)
    github_url = serializers.URLField(max_length=500)


class EmailCandidatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailCandidature
        fields = '__all__'
        read_only_fields = [
            'candidature',
            'status',
            'created_at',
            'updated_at',
            'sent_at',
            'error_message',
            'gmail_message_id',
        ]
