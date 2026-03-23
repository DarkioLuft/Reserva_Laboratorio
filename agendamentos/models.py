from django.db import models

class Professor(models.Model):
    nome = models.CharField(max_length=100)
    disciplina = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.nome} - {self.disciplina}"

class Sala(models.Model):
    nome = models.CharField(max_length=100, help_text="Ex: P16, HBB - ESCO PEDIATRIA")

    def __str__(self):
        return f"{self.nome}"

class Agendamento(models.Model):
    DIAS_DA_SEMANA = [
        ('SEG', 'Segunda-feira'),
        ('TER', 'Terça-feira'),
        ('QUA', 'Quarta-feira'),
        ('QUI', 'Quinta-feira'),
        ('SEX', 'Sexta-feira'),
    ]

    dia_semana = models.CharField(max_length=3, choices=DIAS_DA_SEMANA)
    # --- NOVOS CAMPOS DE DATA ---
    data_inicio = models.DateField(null=True, blank=True, help_text="Primeiro dia de aula")
    data_fim = models.DateField(null=True, blank=True, help_text="Último dia de aula")
    # ----------------------------
    
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='agendamentos')
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()
    qtd_alunos = models.IntegerField(default=0)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    temas = models.TextField(blank=True, null=True)

    class Meta:
        # Atualizamos a regra para não ter choque na mesma sala, no mesmo dia, mesmo horário e mesma data de início
        unique_together = ('dia_semana', 'sala', 'horario_inicio', 'data_inicio')

    def __str__(self):
        return f"{self.get_dia_semana_display()} | {self.sala.nome} | {self.horario_inicio.strftime('%H:%M')}"