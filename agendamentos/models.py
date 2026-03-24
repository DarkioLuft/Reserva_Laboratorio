from django.db import models


class Professor(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['nome']
        verbose_name = 'Professor'
        verbose_name_plural = 'Professores'


class Sala(models.Model):
    nome = models.CharField(max_length=100, help_text="Ex: P16, HBB - ESCO PEDIATRIA")

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['nome']
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'


class Agendamento(models.Model):
    DIAS_DA_SEMANA = [
        ('SEG', 'Segunda-feira'),
        ('TER', 'Terça-feira'),
        ('QUA', 'Quarta-feira'),
        ('QUI', 'Quinta-feira'),
        ('SEX', 'Sexta-feira'),
    ]

    dia_semana    = models.CharField(max_length=3, choices=DIAS_DA_SEMANA)
    data_inicio   = models.DateField(null=True, blank=True, help_text="Primeiro dia de aula")
    data_fim      = models.DateField(null=True, blank=True, help_text="Último dia de aula")

    # ── Relacionamentos Many-to-Many ────────────────────────────────────────
    salas      = models.ManyToManyField(Sala,      related_name='agendamentos')
    professores = models.ManyToManyField(Professor, related_name='agendamentos')

    horario_inicio = models.TimeField()
    horario_fim    = models.TimeField()
    qtd_alunos     = models.IntegerField(default=0)

    disciplina = models.CharField(
        max_length=150, blank=True, null=True,
        help_text="Ex: Semiologia, Pediatria, Urgência"
    )

    temas = models.TextField(blank=True, null=True)

    # ── Reserva esporádica: tem prioridade sobre regulares ──────────────────
    esporadica = models.BooleanField(
        default=False,
        verbose_name='Reserva Esporádica',
        help_text='Reservas esporádicas têm prioridade e podem sobrepor reservas regulares.'
    )

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['dia_semana', 'horario_inicio']

    def __str__(self):
        salas_str = ', '.join(s.nome for s in self.salas.all()) or '—'
        return (
            f"{self.get_dia_semana_display()} | "
            f"{salas_str} | "
            f"{self.horario_inicio.strftime('%H:%M')}"
        )

    @property
    def turno(self):
        """Retorna o turno (manha/tarde/noite) com base no horário de início."""
        from datetime import time
        h = self.horario_inicio
        if h < time(12, 0):
            return 'manha'
        elif h < time(18, 0):
            return 'tarde'
        else:
            return 'noite'