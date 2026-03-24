from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.dashboard,               name='dashboard'),
    path('login/',                  views.login_view,              name='login'),
    path('logout/',                 views.logout_view,             name='logout'),
    path('deletar/<int:id>/',       views.deletar_agendamento,     name='deletar'),
    path('editar/<int:id>/',        views.editar_agendamento,      name='editar'),
    path('api/verificar-conflito/', views.verificar_conflito_ajax, name='verificar_conflito'),
]