from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('deletar/<int:id>/', views.deletar_agendamento, name='deletar'),
    path('editar/<int:id>/', views.editar_agendamento, name='editar'),
]