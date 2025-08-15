from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator

class PlayerScore(models.Model):
    player = models.OneToOneField(User, on_delete=models.CASCADE, related_name='game_score')
    score = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        help_text="Score total du joueur"
    )
    games_played = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Nombre total de parties jouées"
    )
    best_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Meilleur score en une partie"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_played = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-score']
        verbose_name = "Score du Joueur"
        verbose_name_plural = "Scores des Joueurs"
    
    def __str__(self):
        return f"{self.player.username}: {self.score} points"
    
    @property
    def average_score(self):
        """Calcule le score moyen par partie"""
        if self.games_played == 0:
            return 0
        return round(self.score / self.games_played, 2)
    
    @property
    def rank(self):
        """Calcule le rang du joueur"""
        return PlayerScore.objects.filter(score__gt=self.score).count() + 1

class GameSession(models.Model):
    """Enregistre chaque session de jeu individuelle"""
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    points_earned = models.IntegerField(validators=[MinValueValidator(0)])
    duration_seconds = models.IntegerField(null=True, blank=True)
    fruits_collected = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Session de Jeu"
        verbose_name_plural = "Sessions de Jeu"
    
    def __str__(self):
        return f"{self.player.username} - {self.points_earned} pts ({self.timestamp.strftime('%d/%m/%Y %H:%M')})"

class Achievement(models.Model):
    """Système de succès/réalisations"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    points_required = models.IntegerField(null=True, blank=True)
    games_required = models.IntegerField(null=True, blank=True)
    icon = models.CharField(max_length=10, default="🏆")
    
    def __str__(self):
        return f"{self.icon} {self.name}"

class PlayerAchievement(models.Model):
    """Relation entre joueurs et leurs succès"""
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('player', 'achievement')
        verbose_name = "Succès du Joueur"
        verbose_name_plural = "Succès des Joueurs"