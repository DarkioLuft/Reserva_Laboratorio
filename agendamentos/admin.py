from django.contrib import admin
from .models import Professor, Sala, Agendamento


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display  = ('nome',)
    search_fields = ('nome',)


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display  = ('nome',)
    search_fields = ('nome',)


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display  = ('dia_semana', 'get_salas', 'horario_inicio', 'horario_fim', 'get_professores', 'disciplina', 'esporadica')
    list_filter   = ('dia_semana', 'esporadica', 'disciplina')
    search_fields = ('professores__nome', 'salas__nome', 'disciplina')
    filter_horizontal = ('salas', 'professores')

    @admin.display(description='Sala(s)')
    def get_salas(self, obj):
        return ', '.join(s.nome for s in obj.salas.all())

    @admin.display(description='Professor(es)')
    def get_professores(self, obj):
        return ', '.join(p.nome for p in obj.professores.all())