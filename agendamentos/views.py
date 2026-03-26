# agendamentos/views.py
import json
from datetime import time as dtime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AgendamentoForm, buscar_conflitos
from .models import Agendamento, Professor, Sala  # noqa: F401 – Professor/Sala usados em outros módulos


# ─────────────────────────────────────────────────────────────────────────────
# Configurações de grade
# ─────────────────────────────────────────────────────────────────────────────
DIAS_CONFIG = [
    {'sigla': 'SEG', 'nome': 'Segunda-feira', 'nome_curto': 'Seg'},
    {'sigla': 'TER', 'nome': 'Terça-feira',   'nome_curto': 'Ter'},
    {'sigla': 'QUA', 'nome': 'Quarta-feira',  'nome_curto': 'Qua'},
    {'sigla': 'QUI', 'nome': 'Quinta-feira',  'nome_curto': 'Qui'},
    {'sigla': 'SEX', 'nome': 'Sexta-feira',   'nome_curto': 'Sex'},
]

TURNOS_CONFIG = [
    {
        'key': 'manha', 'label': 'Manhã', 'icone': '🌅', 'horario': '06:00–12:00',
        'limite_inicio': dtime(0, 0),  'limite_fim': dtime(12, 0),
    },
    {
        'key': 'tarde', 'label': 'Tarde', 'icone': '☀️',  'horario': '12:00–18:00',
        'limite_inicio': dtime(12, 0), 'limite_fim': dtime(18, 0),
    },
    {
        'key': 'noite', 'label': 'Noite', 'icone': '🌙', 'horario': '18:00–00:00',
        'limite_inicio': dtime(18, 0), 'limite_fim': dtime(23, 59),
    },
]


def get_turno_key(horario_inicio):
    """Retorna a chave do turno ('manha'/'tarde'/'noite') para um horário."""
    if horario_inicio < dtime(12, 0):
        return 'manha'
    elif horario_inicio < dtime(18, 0):
        return 'tarde'
    return 'noite'


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários de reserva esporádica
# ─────────────────────────────────────────────────────────────────────────────

def _serializar_conflito(agendamento):
    """
    Serializa um Agendamento em um dict adequado para exibição
    no modal de conflito (tanto no dashboard quanto na edição).

    Usado por:
      - _checar_conflitos_esporadica
      - verificar_conflito_ajax
    """
    return {
        'id':          agendamento.id,
        'descricao':   str(agendamento),
        'dia':         agendamento.get_dia_semana_display(),
        'horario': (
            f"{agendamento.horario_inicio.strftime('%H:%M')}"
            f" – {agendamento.horario_fim.strftime('%H:%M')}"
        ),
        'salas':       [s.nome for s in agendamento.salas.all()],
        'professores': [p.nome for p in agendamento.professores.all()],
        'disciplina':  agendamento.disciplina or '',
        'esporadica':  agendamento.esporadica,
    }


def _params_conflito_do_form(cleaned_data):
    """
    Extrai do cleaned_data os kwargs necessários para chamar buscar_conflitos().
    Evita repetição da extração manual de campos em múltiplos pontos da view.
    """
    return {
        'salas':          cleaned_data.get('salas'),
        'dia_semana':     cleaned_data.get('dia_semana'),
        'horario_inicio': cleaned_data.get('horario_inicio'),
        'horario_fim':    cleaned_data.get('horario_fim'),
        'data_inicio':    cleaned_data.get('data_inicio'),
        'data_fim':       cleaned_data.get('data_fim'),
    }


def _checar_conflitos_esporadica(cleaned_data, exclude_pk=None):
    """
    Verifica conflitos para uma reserva esporádica a partir do cleaned_data
    de um AgendamentoForm válido.

    Retorna uma tupla (ha_conflitos, conflitos_list, conflitos_json) onde:
      - ha_conflitos   : bool — True quando há ao menos um conflito
      - conflitos_list : list[dict] — conflitos serializados para o modal
      - conflitos_json : str  — JSON pronto para o template (|safe)

    O parâmetro ``exclude_pk`` é usado na edição para ignorar o próprio
    agendamento sendo editado na busca de conflitos.
    """
    params = _params_conflito_do_form(cleaned_data)
    conflitos_qs = (
        buscar_conflitos(**params, exclude_pk=exclude_pk)
        .prefetch_related('salas', 'professores')
    )

    if not conflitos_qs.exists():
        return False, [], '[]'

    conflitos_list = [_serializar_conflito(c) for c in conflitos_qs]
    conflitos_json = json.dumps(conflitos_list, ensure_ascii=False)
    return True, conflitos_list, conflitos_json


def _registrar_sobreposicao_na_sessao(request, cleaned_data, exclude_pk=None):
    """
    Localiza os agendamentos sobrepostos pela reserva esporádica que
    acaba de ser salva, persiste seus IDs na sessão e emite uma mensagem
    de aviso para o usuário.

    Deve ser chamado APÓS salvar o agendamento, passando o mesmo
    cleaned_data do formulário.

    Retorna o número de conflitos registrados.
    """
    params = _params_conflito_do_form(cleaned_data)
    ids_conflito = list(
        buscar_conflitos(**params, exclude_pk=exclude_pk)
        .values_list('id', flat=True)
    )

    if not ids_conflito:
        return 0

    request.session['conflitos_pendentes'] = ids_conflito
    qtd = len(ids_conflito)
    messages.warning(
        request,
        f'⚠️ {qtd} reserva(s) foi sobreposta pela reserva esporádica. '
        f'Por favor, realoque ou exclua cada uma abaixo.',
    )
    return qtd


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        messages.error(request, 'Usuário ou senha incorretos.')

    return render(request, 'agendamentos/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Você saiu com sucesso.')
    return redirect('login')


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR CONFLITO (AJAX)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def verificar_conflito_ajax(request):
    """
    Endpoint AJAX chamado antes de salvar uma reserva esporádica.
    Retorna JSON com lista de conflitos encontrados.

    Usa _serializar_conflito() — a mesma serialização do modal do dashboard
    e da edição — garantindo consistência de formato.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

    from datetime import datetime

    salas_ids      = request.POST.getlist('salas')
    dia_semana     = request.POST.get('dia_semana')
    horario_inicio = request.POST.get('horario_inicio')
    horario_fim    = request.POST.get('horario_fim')
    data_inicio    = request.POST.get('data_inicio') or None
    data_fim       = request.POST.get('data_fim') or None
    agendamento_id = request.POST.get('agendamento_id') or None

    try:
        salas = Sala.objects.filter(id__in=salas_ids)
        hi = datetime.strptime(horario_inicio, '%H:%M').time()
        hf = datetime.strptime(horario_fim,    '%H:%M').time()
        di = datetime.strptime(data_inicio, '%Y-%m-%d').date() if data_inicio else None
        df = datetime.strptime(data_fim,    '%Y-%m-%d').date() if data_fim    else None
    except (ValueError, TypeError):
        return JsonResponse({'conflitos': []})

    conflitos_qs = (
        buscar_conflitos(
            salas=salas,
            dia_semana=dia_semana,
            horario_inicio=hi,
            horario_fim=hf,
            data_inicio=di,
            data_fim=df,
            exclude_pk=int(agendamento_id) if agendamento_id else None,
        )
        .prefetch_related('salas', 'professores')
    )

    # Reutiliza _serializar_conflito — mesmo formato esperado pelo modal JS
    return JsonResponse({'conflitos': [_serializar_conflito(c) for c in conflitos_qs]})


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    mostrar_modal     = False
    conflitos_json    = '[]'

    if request.method == 'POST':
        form = AgendamentoForm(request.POST)
        confirmar = request.POST.get('confirmar_sobreposicao') == '1'

        if form.is_valid():
            esporadica = form.cleaned_data.get('esporadica', False)

            if esporadica and not confirmar:
                # Verifica conflitos antes de exibir modal de confirmação.
                ha_conflitos, _, conflitos_json = _checar_conflitos_esporadica(
                    form.cleaned_data
                )
                if ha_conflitos:
                    mostrar_modal = True
                    # Não salva ainda — renderiza o dashboard com o modal aberto.
                else:
                    _salvar_agendamento(form)
                    messages.success(request, '✅ Reserva esporádica salva com sucesso!')
                    return redirect('dashboard')

            else:
                # Reserva regular, ou esporádica já confirmada pelo usuário.
                if esporadica and confirmar:
                    # Salva primeiro e depois registra sobreposições na sessão.
                    # O exclude_pk=None é correto aqui (novo agendamento ainda
                    # não tem PK, não pode conflitar consigo mesmo).
                    _salvar_agendamento(form)
                    _registrar_sobreposicao_na_sessao(request, form.cleaned_data)
                else:
                    _salvar_agendamento(form)

                messages.success(request, '✅ Agendamento salvo com sucesso!')
                return redirect('dashboard')

        else:
            messages.error(request, '❌ Corrija os erros no formulário abaixo.')

    else:
        form = AgendamentoForm()

    # ── Filtro de salas ───────────────────────────────────────────────────────
    filtro = request.GET.get('filtro', 'todas')
    qs = Agendamento.objects.prefetch_related('salas', 'professores').all()

    if filtro == 'P8':
        qs = qs.filter(
            Q(salas__nome__icontains='P8') | Q(salas__nome__icontains='P08')
        ).distinct()
    elif filtro == 'P16':
        qs = qs.filter(salas__nome__icontains='P16').distinct()
    elif filtro != 'todas':
        qs = qs.filter(salas__nome=filtro).distinct()

    salas_disponiveis = (
        Sala.objects.order_by('nome').values_list('nome', flat=True).distinct()
    )

    # ── Monta a grade semanal ─────────────────────────────────────────────────
    grade = {
        t['key']: {d['sigla']: [] for d in DIAS_CONFIG}
        for t in TURNOS_CONFIG
    }
    for ag in qs:
        grade[get_turno_key(ag.horario_inicio)][ag.dia_semana].append(ag)

    grade_semana = [
        {
            'turno': turno,
            'celulas': [
                {
                    'dia': dia['sigla'],
                    'agendamentos': sorted(
                        grade[turno['key']][dia['sigla']],
                        key=lambda x: x.horario_inicio,
                    ),
                }
                for dia in DIAS_CONFIG
            ],
        }
        for turno in TURNOS_CONFIG
    ]

    # ── Conflitos pendentes (sessão) ──────────────────────────────────────────
    ids_pendentes = request.session.get('conflitos_pendentes', [])
    conflitos_pendentes = (
        list(
            Agendamento.objects
            .filter(id__in=ids_pendentes)
            .prefetch_related('salas', 'professores')
        )
        if ids_pendentes else []
    )

    return render(request, 'agendamentos/dashboard.html', {
        'grade_semana':           grade_semana,
        'dias_config':            DIAS_CONFIG,
        'form':                   form,
        'filtro_atual':           filtro,
        'salas_disponiveis':      salas_disponiveis,
        'conflitos_pendentes':    conflitos_pendentes,
        'mostrar_modal_conflito': mostrar_modal,
        'conflitos_data_modal_json': conflitos_json,
    })


def _salvar_agendamento(form):
    """Salva um Agendamento a partir de um form válido (incluindo M2M)."""
    return form.save()


# ─────────────────────────────────────────────────────────────────────────────
# DELETAR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def deletar_agendamento(request, id):
    agendamento = get_object_or_404(Agendamento, id=id)
    desc = str(agendamento)
    agendamento.delete()

    # Remove o ID da lista de conflitos pendentes na sessão, se estiver lá.
    ids_pendentes = request.session.get('conflitos_pendentes', [])
    if id in ids_pendentes:
        ids_pendentes.remove(id)
        request.session['conflitos_pendentes'] = ids_pendentes
        request.session.modified = True

    messages.success(request, f'🗑️ Agendamento "{desc}" excluído com sucesso.')
    return redirect('dashboard')


# ─────────────────────────────────────────────────────────────────────────────
# EDITAR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def editar_agendamento(request, id):
    """
    Edição de agendamento. Aplica a mesma regra de negócio de reserva
    esporádica do dashboard, reutilizando _checar_conflitos_esporadica()
    e _registrar_sobreposicao_na_sessao() com exclude_pk=agendamento.pk
    para ignorar o próprio registro na busca de conflitos.
    """
    agendamento    = get_object_or_404(Agendamento, id=id)
    aviso_conflito = request.GET.get('aviso_conflito') == '1'
    mostrar_modal  = False
    conflitos_json = '[]'

    if request.method == 'POST':
        form      = AgendamentoForm(request.POST, instance=agendamento)
        confirmar = request.POST.get('confirmar_sobreposicao') == '1'

        if form.is_valid():
            esporadica = form.cleaned_data.get('esporadica', False)

            if esporadica and not confirmar:
                # Verifica conflitos excluindo o próprio agendamento editado.
                ha_conflitos, _, conflitos_json = _checar_conflitos_esporadica(
                    form.cleaned_data, exclude_pk=agendamento.pk
                )
                if ha_conflitos:
                    mostrar_modal = True
                    # Não salva ainda — re-renderiza a tela de edição com modal.
                else:
                    form.save()
                    messages.success(request, '✅ Agendamento atualizado com sucesso!')
                    return redirect('dashboard')

            else:
                # Sem verificação (regular) ou sobreposição já confirmada.
                form.save()

                if esporadica and confirmar:
                    _registrar_sobreposicao_na_sessao(
                        request, form.cleaned_data, exclude_pk=agendamento.pk
                    )

                # Limpa o próprio ID dos conflitos pendentes na sessão.
                ids_pendentes = request.session.get('conflitos_pendentes', [])
                if id in ids_pendentes:
                    ids_pendentes.remove(id)
                    request.session['conflitos_pendentes'] = ids_pendentes
                    request.session.modified = True

                messages.success(request, '✅ Agendamento atualizado com sucesso!')
                return redirect('dashboard')

        else:
            messages.error(request, '❌ Corrija os erros abaixo antes de salvar.')

    else:
        form = AgendamentoForm(instance=agendamento)

    return render(request, 'agendamentos/editar.html', {
        'form':                   form,
        'agendamento':            agendamento,
        'aviso_conflito':         aviso_conflito,
        # Variáveis do modal de conflito — o template editar.html
        # deve incluir o mesmo bloco de modal do dashboard.html.
        'mostrar_modal_conflito': mostrar_modal,
        'conflitos_data_modal_json': conflitos_json,
    })