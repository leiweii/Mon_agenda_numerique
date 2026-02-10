from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Tache(models.Model):
    PRIORITE_CHOICES = [
        (1, 'Basse'),
        (2, 'Moyenne'),
        (3, 'Haute'),
        (4, 'Urgente'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taches')
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateTimeField()
    priorite = models.IntegerField(choices=PRIORITE_CHOICES, default=2)
    couleur = models.CharField(max_length=7, default='#3498db')  # Format hex
    emoji = models.CharField(max_length=10, default='📝')
    completee = models.BooleanField(default=False)
    categorie = models.ForeignKey('Categorie', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-date_echeance', '-priorite']
    
    def __str__(self):
        return f"{self.emoji} {self.titre}"

class Categorie(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    nom = models.CharField(max_length=100)
    couleur = models.CharField(max_length=7, default='#95a5a6')
    emoji = models.CharField(max_length=10, default='📁')
    
    def __str__(self):
        return f"{self.emoji} {self.nom}"

class PreferenceUtilisateur(models.Model):
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    heure_productive_debut = models.TimeField(default='09:00')
    heure_productive_fin = models.TimeField(default='17:00')
    theme = models.CharField(max_length=20, default='clair')
    notifications_actives = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Préférences de {self.utilisateur.username}"

class StatistiqueUtilisation(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statistiques')
    date = models.DateField(auto_now_add=True)
    heure_completion = models.TimeField()
    tache = models.ForeignKey(Tache, on_delete=models.CASCADE)
    duree_estimee = models.IntegerField(help_text="Durée en minutes")
    
    class Meta:
        ordering = ['-date']