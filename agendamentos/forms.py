# agendamentos/forms.py
from django import forms
from .models import Agendamento
from django.db.models import Q

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = [
            'dia_semana', 'data_inicio', 'data_fim',
            'sala', 'professor', 'disciplina',
            'horario_inicio', 'horario_fim', 'qtd_alunos',
            'temas'
        ]

        widgets = {
            'dia_semana':      forms.Select(attrs={'class': 'form-select'}),
            'data_inicio':     forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim':        forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sala':            forms.Select(attrs={'class': 'form-select'}),
            'professor':       forms.Select(attrs={'class': 'form-select'}),
            'disciplina':      forms.TextInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Ex: Semiologia, Pediatria, Urgência'
                               }),
            'horario_inicio':  forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fim':     forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'qtd_alunos':      forms.NumberInput(attrs={'class': 'form-control'}),
            'temas':           forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    # ------------------------------------------------------------------
    # Validação de campos individuais
    # ------------------------------------------------------------------
    def clean_horario_fim(self):
        inicio = self.cleaned_data.get('horario_inicio')
        fim    = self.cleaned_data.get('horario_fim')
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError('O horário de fim deve ser posterior ao horário de início.')
        return fim

    def clean_data_fim(self):
        d_inicio = self.cleaned_data.get('data_inicio')
        d_fim    = self.cleaned_data.get('data_fim')
        if d_inicio and d_fim and d_fim < d_inicio:
            raise forms.ValidationError('A data de fim não pode ser anterior à data de início.')
        return d_fim

    # ------------------------------------------------------------------
    # Validação de conflito de horário na mesma sala
    # ------------------------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        sala          = cleaned.get('sala')
        dia_semana    = cleaned.get('dia_semana')
        horario_inicio = cleaned.get('horario_inicio')
        horario_fim   = cleaned.get('horario_fim')
        data_inicio   = cleaned.get('data_inicio')
        data_fim      = cleaned.get('data_fim')

        # Só valida se todos os campos essenciais estiverem preenchidos
        if not all([sala, dia_semana, horario_inicio, horario_fim]):
            return cleaned

        # Monta a query base: mesma sala e mesmo dia da semana
        conflitos = Agendamento.objects.filter(
            sala=sala,
            dia_semana=dia_semana,
        ).filter(
            # Sobreposição de horário: o intervalo salvo começa antes do nosso fim
            # E termina depois do nosso início
            horario_inicio__lt=horario_fim,
            horario_fim__gt=horario_inicio,
        )

        # Sobreposição de período de datas (quando informadas)
        if data_inicio and data_fim:
            conflitos = conflitos.filter(
                Q(data_inicio__isnull=True) |          # sem período definido (semestre todo)
                Q(data_inicio__lte=data_fim) &
                Q(data_fim__gte=data_inicio)            # períodos se sobrepõem
            )
        elif data_inicio:
            conflitos = conflitos.filter(
                Q(data_inicio__isnull=True) |
                Q(data_inicio=data_inicio)
            )

        # Na edição, ignora o próprio registro
        if self.instance and self.instance.pk:
            conflitos = conflitos.exclude(pk=self.instance.pk)

        if conflitos.exists():
            conflito = conflitos.first()
            raise forms.ValidationError(
                f'Conflito de horário! A sala "{sala}" já está ocupada nesse período '
                f'por {conflito.professor} ({conflito.horario_inicio.strftime("%H:%M")} '
                f'às {conflito.horario_fim.strftime("%H:%M")}).'
            )

        return cleaned