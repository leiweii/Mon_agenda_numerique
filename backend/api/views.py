from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from datetime import datetime, timedelta
from agenda.models import Tache, Categorie, PreferenceUtilisateur, StatistiqueUtilisation
from .serializers import TacheSerializer, CategorieSerializer, PreferenceUtilisateurSerializer

class TacheViewSet(viewsets.ModelViewSet):
    serializer_class = TacheSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Tache.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)
    
    @action(detail=False, methods=['get'])
    def aujourd_hui(self, request):
        today = datetime.now().date()
        taches = self.get_queryset().filter(
            date_echeance__date=today
        )
        serializer = self.get_serializer(taches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cette_semaine(self, request):
        today = datetime.now().date()
        fin_semaine = today + timedelta(days=7)
        taches = self.get_queryset().filter(
            date_echeance__date__range=[today, fin_semaine]
        )
        serializer = self.get_serializer(taches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        total = self.get_queryset().count()
        completees = self.get_queryset().filter(completee=True).count()
        par_priorite = self.get_queryset().values('priorite').annotate(count=Count('id'))
        
        return Response({
            'total': total,
            'completees': completees,
            'en_cours': total - completees,
            'par_priorite': par_priorite,
            'taux_completion': (completees / total * 100) if total > 0 else 0
        })
    
    @action(detail=False, methods=['get'])
    def meilleur_moment(self, request):
        """Algorithme de recommandation du meilleur moment de travail"""
        stats = StatistiqueUtilisation.objects.filter(
            utilisateur=request.user
        ).values('heure_completion__hour').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        if stats:
            heures_productives = [s['heure_completion__hour'] for s in stats]
            return Response({
                'heures_recommandees': heures_productives,
                'message': f'Vous êtes plus productif vers {heures_productives[0]}h'
            })
        return Response({'message': 'Pas assez de données pour une recommandation'})

class CategorieViewSet(viewsets.ModelViewSet):
    serializer_class = CategorieSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Categorie.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)

class PreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = PreferenceUtilisateurSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PreferenceUtilisateur.objects.filter(utilisateur=self.request.user)