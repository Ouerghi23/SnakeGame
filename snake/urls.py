from django.contrib import admin
from django.urls import path
from snakegame import views  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.game_view, name='game'),
]
