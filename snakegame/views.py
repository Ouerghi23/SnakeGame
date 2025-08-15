from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from .models import PlayerScore, GameSession
import json
import logging

logger = logging.getLogger(__name__)

# Vue pour afficher le jeu 3D
def game_view(request):
    top_scores = PlayerScore.objects.select_related('player').order_by('-score')[:10]
    context = {
        'top_scores': top_scores,
        'player_name': request.session.get('player_name', 'Joueur Anonyme')
    }
    return render(request, 'index.html', context)

# API pour mettre à jour le score (améliorée)
@csrf_exempt
@require_http_methods(["POST"])
def update_score(request):
    try:
        # Gérer les données JSON ET form-data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            username = data.get("username")
            points = data.get("points", 0)
            session_id = data.get("session_id")
        else:
            username = request.POST.get("username")
            points = request.POST.get("points", 0)
            session_id = request.POST.get("session_id")

        # Validation des données
        if not username:
            return JsonResponse({"error": "Username requis"}, status=400)
        
        try:
            points = int(points)
        except (ValueError, TypeError):
            return JsonResponse({"error": "Points invalides"}, status=400)

        if points <= 0:
            return JsonResponse({"error": "Points doivent être positifs"}, status=400)

        # Transaction atomique pour éviter les conditions de course
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': username}
            )
            
            score, created = PlayerScore.objects.get_or_create(
                player=user,
                defaults={'score': 0, 'games_played': 0}
            )
            
            # Mettre à jour le score
            score.score += points
            score.games_played += 1
            score.last_played = timezone.now()
            score.save()

            # Enregistrer la session de jeu (optionnel)
            if session_id:
                GameSession.objects.create(
                    player=user,
                    session_id=session_id,
                    points_earned=points,
                    timestamp=timezone.now()
                )

        return JsonResponse({
            "success": True,
            "message": "Score mis à jour avec succès",
            "new_score": score.score,
            "games_played": score.games_played,
            "rank": get_player_rank(score.score)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du score: {str(e)}")
        return JsonResponse({"error": "Erreur serveur interne"}, status=500)

# API pour récupérer les scores
@require_http_methods(["GET"])
def get_leaderboard(request):
    try:
        limit = min(int(request.GET.get('limit', 10)), 100)  # Max 100
        
        scores = PlayerScore.objects.select_related('player').order_by('-score')[:limit]
        
        leaderboard = [{
            'rank': idx + 1,
            'username': score.player.username,
            'score': score.score,
            'games_played': score.games_played,
            'last_played': score.last_played.strftime('%d/%m/%Y %H:%M') if score.last_played else None
        } for idx, score in enumerate(scores)]
        
        return JsonResponse({
            'success': True,
            'leaderboard': leaderboard
        })
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du leaderboard: {str(e)}")
        return JsonResponse({"error": "Erreur serveur interne"}, status=500)

# API pour récupérer le profil du joueur
@require_http_methods(["GET"])
def get_player_profile(request, username):
    try:
        user = User.objects.get(username=username)
        score = PlayerScore.objects.get(player=user)
        
        # Statistiques additionnelles
        recent_sessions = GameSession.objects.filter(player=user).order_by('-timestamp')[:5]
        
        profile = {
            'username': user.username,
            'total_score': score.score,
            'games_played': score.games_played,
            'average_score': round(score.score / max(score.games_played, 1), 2),
            'rank': get_player_rank(score.score),
            'last_played': score.last_played.strftime('%d/%m/%Y %H:%M') if score.last_played else None,
            'recent_sessions': [
                {
                    'points': session.points_earned,
                    'date': session.timestamp.strftime('%d/%m/%Y %H:%M')
                } for session in recent_sessions
            ]
        }
        
        return JsonResponse({'success': True, 'profile': profile})
    
    except User.DoesNotExist:
        return JsonResponse({"error": "Joueur non trouvé"}, status=404)
    except PlayerScore.DoesNotExist:
        return JsonResponse({"error": "Aucun score trouvé pour ce joueur"}, status=404)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du profil: {str(e)}")
        return JsonResponse({"error": "Erreur serveur interne"}, status=500)

# API pour démarrer une nouvelle session de jeu
@csrf_exempt
@require_http_methods(["POST"])
def start_game_session(request):
    try:
        data = json.loads(request.body)
        username = data.get("username")
        
        if not username:
            return JsonResponse({"error": "Username requis"}, status=400)
        
        # Générer un ID de session unique
        import uuid
        session_id = str(uuid.uuid4())
        
        # Stocker dans la session Django
        request.session['game_session_id'] = session_id
        request.session['player_name'] = username
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'message': 'Session de jeu démarrée'
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de la session: {str(e)}")
        return JsonResponse({"error": "Erreur serveur interne"}, status=500)

# Fonction utilitaire pour obtenir le rang du joueur
def get_player_rank(score):
    return PlayerScore.objects.filter(score__gt=score).count() + 1