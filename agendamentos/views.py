# agendamentos/views.py
import json
from datetime import time as dtime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AgendamentoForm, buscar_conflitos
from .models import Agendamento, Professor, Sala


# ─────────────────────────────────────────────────────────────────────────────
# Configurações de grade
# ─────────────────────────────────────────────────────────────────────────────
DIAS_CONFIG = [
    {'sigla': 'SEG', 'nome': 'Segunda-feira',  'nome_curto': 'Seg'},
    {'sigla': 'TER', 'nome': 'Terça-feira',    'nome_curto': 'Ter'},
    {'sigla': 'QUA', 'nome': 'Quarta-feira',   'nome_curto': 'Qua'},
    {'sigla': 'QUI', 'nome': 'Quinta-feira',   'nome_curto': 'Qui'},
    {'sigla': 'SEX', 'nome': 'Sexta-feira',    'nome_curto': 'Sex'},
]

TURNOS_CONFIG = [
    {'key': 'manha', 'label': 'Manhã',  'icone': '🌅', 'horario': '06:00–12:00',
     'limite_inicio': dtime(0, 0),   'limite_fim': dtime(12, 0)},
    {'key': 'tarde', 'label': 'Tarde',  'icone': '☀️',  'horario': '12:00–18:00',
     'limite_inicio': dtime(12, 0),  'limite_fim': dtime(18, 0)},
    {'key': 'noite', 'label': 'Noite',  'icone': '🌙', 'horario': '18:00–00:00',
     'limite_inicio': dtime(18, 0),  'limite_fim': dtime(23, 59)},
]


def get_turno_key(horario_inicio):
    """Retorna a chave do turno ('manha'/'tarde'/'noite') para um horário."""
    if horario_inicio < dtime(12, 0):
        return 'manha'
    elif horario_inicio < dtime(18, 0):
        return 'tarde'
    else:
        return 'noite'


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
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

    salas_ids      = request.POST.getlist('salas')
    dia_semana     = request.POST.get('dia_semana')
    horario_inicio = request.POST.get('horario_inicio')
    horario_fim    = request.POST.get('horario_fim')
    data_inicio    = request.POST.get('data_inicio') or None
    data_fim       = request.POST.get('data_fim') or None
    agendamento_id = request.POST.get('agendamento_id') or None

    from datetime import datetime, date

    try:
        salas = Sala.objects.filter(id__in=salas_ids)
        hi    = datetime.strptime(horario_inicio, '%H:%M').time()
        hf    = datetime.strptime(horario_fim,    '%H:%M').time()
        di    = datetime.strptime(data_inicio, '%Y-%m-%d').date() if data_inicio else None
        df    = datetime.strptime(data_fim,    '%Y-%m-%d').date() if data_fim    else None
    except (ValueError, TypeError):
        return JsonResponse({'conflitos': []})

    conflitos = buscar_conflitos(
        salas=salas,
        dia_semana=dia_semana,
        horario_inicio=hi,
        horario_fim=hf,
        data_inicio=di,
        data_fim=df,
        exclude_pk=int(agendamento_id) if agendamento_id else None,
    ).prefetch_related('salas', 'professores')

    data = []
    for c in conflitos:
        data.append({
            'id':          c.id,
            'dia':         c.get_dia_semana_display(),
            'horario':     f"{c.horario_inicio.strftime('%H:%M')} – {c.horario_fim.strftime('%H:%M')}",
            'salas':       [s.nome for s in c.salas.all()],
            'professores': [p.nome for p in c.professores.all()],
            'disciplina':  c.disciplina or '',
            'esporadica':  c.esporadica,
        })

    return JsonResponse({'conflitos': data})


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    # ── Salvar agendamento ────────────────────────────────────────────────────
    conflitos_data_modal = []   # conflitos a exibir no modal de confirmação
    mostrar_modal         = False

    if request.method == 'POST':
        form = AgendamentoForm(request.POST)
        confirmar_sobreposicao = request.POST.get('confirmar_sobreposicao') == '1'

        if form.is_valid():
            esporadica = form.cleaned_data.get('esporadica', False)

            # Reserva esporádica: verificar conflitos ANTES de salvar
            if esporadica and not confirmar_sobreposicao:
                salas          = form.cleaned_data.get('salas')
                dia_semana     = form.cleaned_data.get('dia_semana')
                horario_inicio = form.cleaned_data.get('horario_inicio')
                horario_fim    = form.cleaned_data.get('horario_fim')
                data_inicio    = form.cleaned_data.get('data_inicio')
                data_fim       = form.cleaned_data.get('data_fim')

                conflitos_qs = buscar_conflitos(
                    salas=salas,
                    dia_semana=dia_semana,
                    horario_inicio=horario_inicio,
                    horario_fim=horario_fim,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    exclude_pk=None,
                ).prefetch_related('salas', 'professores')

                if conflitos_qs.exists():
                    # Não salva ainda — exibe modal de confirmação
                    mostrar_modal = True
                    for c in conflitos_qs:
                        conflitos_data_modal.append({
                            'id':          c.id,
                            'descricao':   str(c),
                            'dia':         c.get_dia_semana_display(),
                            'horario':     f"{c.horario_inicio.strftime('%H:%M')} – {c.horario_fim.strftime('%H:%M')}",
                            'salas':       [s.nome for s in c.salas.all()],
                            'professores': [p.nome for p in c.professores.all()],
                            'disciplina':  c.disciplina or '',
                            'esporadica':  c.esporadica,   # Bug 2 fix
                        })
                    # Continua abaixo para montar contexto e renderizar com modal
                else:
                    # Sem conflitos: salva normalmente
                    _salvar_agendamento(form)
                    messages.success(request, '✅ Reserva esporádica salva com sucesso!')
                    return redirect('dashboard')

            else:
                # Reserva regular confirmada, ou esporádica com sobreposição confirmada
                if esporadica and confirmar_sobreposicao:
                    # Identifica as reservas que serão sobrepostas ANTES de salvar
                    salas          = form.cleaned_data.get('salas')
                    dia_semana     = form.cleaned_data.get('dia_semana')
                    horario_inicio = form.cleaned_data.get('horario_inicio')
                    horario_fim    = form.cleaned_data.get('horario_fim')
                    data_inicio    = form.cleaned_data.get('data_inicio')
                    data_fim       = form.cleaned_data.get('data_fim')

                    conflitos_qs = buscar_conflitos(
                        salas=salas,
                        dia_semana=dia_semana,
                        horario_inicio=horario_inicio,
                        horario_fim=horario_fim,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                    )
                    ids_conflito = list(conflitos_qs.values_list('id', flat=True))

                _salvar_agendamento(form)
                messages.success(request, '✅ Agendamento salvo com sucesso!')

                if esporadica and confirmar_sobreposicao and ids_conflito:
                    # Guarda na sessão para exibir aviso no dashboard
                    request.session['conflitos_pendentes'] = ids_conflito
                    messages.warning(
                        request,
                        f'⚠️ {len(ids_conflito)} reserva(s) foi sobreposta pela reserva esporádica. '
                        f'Por favor, realoque ou exclua cada uma abaixo.'
                    )

                return redirect('dashboard')

        else:
            messages.error(request, '❌ Corrija os erros no formulário abaixo.')

    else:
        form = AgendamentoForm()

    # ── Filtro de salas ───────────────────────────────────────────────────────
    filtro = request.GET.get('filtro', 'todas')
    qs = (
        Agendamento.objects
        .prefetch_related('salas', 'professores')
        .all()
    )

    if filtro == 'P8':
        qs = qs.filter(Q(salas__nome__icontains='P8') | Q(salas__nome__icontains='P08')).distinct()
    elif filtro == 'P16':
        qs = qs.filter(salas__nome__icontains='P16').distinct()
    elif filtro != 'todas':
        qs = qs.filter(salas__nome=filtro).distinct()

    # ── Salas disponíveis para os botões de filtro ────────────────────────────
    salas_disponiveis = Sala.objects.order_by('nome').values_list('nome', flat=True).distinct()

    # ── Monta a grade semanal (turnos × dias) ─────────────────────────────────
    # Inicializa a grade: grade[turno_key][dia_sigla] = []
    grade: dict[str, dict[str, list]] = {
        t['key']: {d['sigla']: [] for d in DIAS_CONFIG}
        for t in TURNOS_CONFIG
    }

    for ag in qs:
        turno_key = get_turno_key(ag.horario_inicio)
        grade[turno_key][ag.dia_semana].append(ag)

    # Converte para estrutura iterável pelo template
    grade_semana = []
    for turno in TURNOS_CONFIG:
        celulas = [
            {
                'dia':         dia['sigla'],
                'agendamentos': sorted(
                    grade[turno['key']][dia['sigla']],
                    key=lambda x: x.horario_inicio,
                ),
            }
            for dia in DIAS_CONFIG
        ]
        grade_semana.append({'turno': turno, 'celulas': celulas})

    # ── Conflitos pendentes (sessão) ──────────────────────────────────────────
    ids_pendentes = request.session.get('conflitos_pendentes', [])
    conflitos_pendentes = []
    if ids_pendentes:
        conflitos_pendentes = list(
            Agendamento.objects
            .filter(id__in=ids_pendentes)
            .prefetch_related('salas', 'professores')
        )

    contexto = {
        'grade_semana':          grade_semana,
        'dias_config':           DIAS_CONFIG,
        'form':                  form,
        'filtro_atual':          filtro,
        'salas_disponiveis':     salas_disponiveis,
        'conflitos_pendentes':   conflitos_pendentes,
        # Modal de confirmação de sobreposição
        'mostrar_modal_conflito':    mostrar_modal,
        # Bug 1 fix: serializado como JSON válido (|safe renderizaria Python com aspas simples)
        'conflitos_data_modal_json': json.dumps(conflitos_data_modal, ensure_ascii=False),
    }
    return render(request, 'agendamentos/dashboard.html', contexto)


def _salvar_agendamento(form):
    """Salva um Agendamento a partir de um form válido (incluindo M2M)."""
    agendamento = form.save()
    return agendamento


# ─────────────────────────────────────────────────────────────────────────────
# DELETAR
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def deletar_agendamento(request, id):
    agendamento = get_object_or_404(Agendamento, id=id)
    desc = str(agendamento)
    agendamento.delete()
    messages.success(request, f'🗑️ Agendamento "{desc}" excluído com sucesso.')
    return redirect('dashboard')


# ─────────────────────────────────────────────────────────────────────────────
# EDITAR
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def editar_agendamento(request, id):
    agendamento = get_object_or_404(Agendamento, id=id)
    aviso_conflito = request.GET.get('aviso_conflito') == '1'

    if request.method == 'POST':
        form = AgendamentoForm(request.POST, instance=agendamento)
        if form.is_valid():
            form.save()
                # ── Limpar o conflito resolvido da sessão ──────────────────────────────
            if 'conflitos_pendentes' in request.session:
                ids_pendentes = request.session['conflitos_pendentes']
                
                # Se o ID da reserva excluída estava na lista de pendências, removemos
                if id in ids_pendentes:
                    ids_pendentes.remove(id)
                    request.session['conflitos_pendentes'] = ids_pendentes
                    request.session.modified = True  # Avisa o Django que a lista mudou
            messages.success(request, '✅ Agendamento atualizado com sucesso!')
            return redirect('dashboard')
        messages.error(request, '❌ Corrija os erros abaixo antes de salvar.')
    else:
        form = AgendamentoForm(instance=agendamento)



    return render(request, 'agendamentos/editar.html', {
        'form':           form,
        'agendamento':    agendamento,
        'aviso_conflito': aviso_conflito,
    })