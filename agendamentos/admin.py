from django.contrib import admin
from .models import Professor, Sala, Agendamento

@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

admin.site.register(Sala)

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('dia_semana', 'sala', 'horario_inicio', 'horario_fim', 'professor', 'disciplina')
    list_filter = ('dia_semana', 'sala', 'disciplina')
    search_fields = ('professor__nome', 'sala__nome', 'disciplina')