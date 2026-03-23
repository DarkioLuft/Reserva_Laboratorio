from django.contrib import admin

from .models import Professor, Sala, Agendamento

admin.site.register(Professor)
admin.site.register(Sala)

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('dia_semana', 'sala', 'horario_inicio', 'horario_fim', 'professor')
    list_filter = ('dia_semana', 'sala')
    search_fields = ('professor__nome', 'sala__nome')
