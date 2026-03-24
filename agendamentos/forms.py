# agendamentos/forms.py
from django import forms
from django.db.models import Q

from .models import Agendamento, Sala, Professor


# ─────────────────────────────────────────────────────────────────────────────
# Widget customizado: checkboxes com estilo Bootstrap
# ─────────────────────────────────────────────────────────────────────────────
class BootstrapCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """CheckboxSelectMultiple que renderiza cada item com classes Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def optgroups(self, name, value, attrs=None):
        groups = super().optgroups(name, value, attrs)
        return groups


# ─────────────────────────────────────────────────────────────────────────────
# Formulário principal de Agendamento
# ─────────────────────────────────────────────────────────────────────────────
class AgendamentoForm(forms.ModelForm):

    # Sobrescreve queryset para ordenar as opções
    salas = forms.ModelMultipleChoiceField(
        queryset=Sala.objects.order_by('nome'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Sala(s)',
        error_messages={'required': 'Selecione ao menos uma sala.'},
    )
    professores = forms.ModelMultipleChoiceField(
        queryset=Professor.objects.order_by('nome'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Professor(a/es)',
        error_messages={'required': 'Selecione ao menos um professor.'},
    )

    class Meta:
        model = Agendamento
        fields = [
            'dia_semana', 'data_inicio', 'data_fim',
            'salas', 'professores', 'disciplina',
            'horario_inicio', 'horario_fim', 'qtd_alunos',
            'esporadica', 'temas',
        ]
        widgets = {
            'dia_semana':      forms.Select(attrs={'class': 'form-select'}),
            'data_inicio':     forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim':        forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'disciplina':      forms.TextInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Ex: Semiologia, Pediatria, Urgência',
                               }),
            'horario_inicio':  forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fim':     forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'qtd_alunos':      forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'esporadica':      forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_esporadica'}),
            'temas':           forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    # ------------------------------------------------------------------
    # Validações de campo individual
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
    # Validação de conflito — NÃO levanta erro para reservas esporádicas
    # (a view cuida do fluxo de confirmação)
    # ------------------------------------------------------------------
    def clean(self):
        cleaned    = super().clean()
        esporadica = cleaned.get('esporadica', False)

        # Reservas esporádicas ignoram verificação de conflito no form;
        # a view trata o modal de confirmação.
        if esporadica:
            return cleaned

        salas          = cleaned.get('salas')
        dia_semana     = cleaned.get('dia_semana')
        horario_inicio = cleaned.get('horario_inicio')
        horario_fim    = cleaned.get('horario_fim')
        data_inicio    = cleaned.get('data_inicio')
        data_fim       = cleaned.get('data_fim')

        if not all([salas, dia_semana, horario_inicio, horario_fim]):
            return cleaned

        conflitos = buscar_conflitos(
            salas=salas,
            dia_semana=dia_semana,
            horario_inicio=horario_inicio,
            horario_fim=horario_fim,
            data_inicio=data_inicio,
            data_fim=data_fim,
            exclude_pk=self.instance.pk if self.instance else None,
        )

        if conflitos.exists():
            primeiro = conflitos.first()
            salas_conf = ', '.join(s.nome for s in primeiro.salas.filter(id__in=[s.id for s in salas]))
            raise forms.ValidationError(
                f'Conflito de horário! A(s) sala(s) "{salas_conf}" já estão ocupadas nesse '
                f'período por {", ".join(p.nome for p in primeiro.professores.all())} '
                f'({primeiro.horario_inicio.strftime("%H:%M")} às {primeiro.horario_fim.strftime("%H:%M")}).'
            )

        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Utilitário: busca conflitos de horário / período
# ─────────────────────────────────────────────────────────────────────────────
def buscar_conflitos(salas, dia_semana, horario_inicio, horario_fim,
                     data_inicio=None, data_fim=None, exclude_pk=None):
    """
    Retorna um QuerySet de Agendamentos que conflitam com os parâmetros fornecidos.
    Considera sobreposição de horário E sobreposição de período de datas.
    """
    qs = Agendamento.objects.filter(
        salas__in=salas,
        dia_semana=dia_semana,
        horario_inicio__lt=horario_fim,
        horario_fim__gt=horario_inicio,
    ).distinct()

    # Filtro de sobreposição de datas
    if data_inicio and data_fim:
        qs = qs.filter(
            Q(data_inicio__isnull=True) |
            (Q(data_inicio__lte=data_fim) & Q(data_fim__gte=data_inicio))
        )
    elif data_inicio:
        qs = qs.filter(
            Q(data_inicio__isnull=True) |
            Q(data_inicio=data_inicio)
        )

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs