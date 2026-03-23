# agendamentos/forms.py
from django import forms
from .models import Agendamento

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        # Adicionamos os dois novos campos na lista
        fields = ['dia_semana', 'data_inicio', 'data_fim', 'sala', 'horario_inicio', 'horario_fim', 'qtd_alunos', 'professor', 'temas']
        
        widgets = {
            'dia_semana': forms.Select(attrs={'class': 'form-select'}),
            # Usamos type='date' para abrir o calendário nativo do navegador
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sala': forms.Select(attrs={'class': 'form-select'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'qtd_alunos': forms.NumberInput(attrs={'class': 'form-control'}),
            'professor': forms.Select(attrs={'class': 'form-select'}),
            'temas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }