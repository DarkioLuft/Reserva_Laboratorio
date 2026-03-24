# agendamentos/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import Agendamento, Sala
from .forms import AgendamentoForm


# ------------------------------------------------------------------
# AUTENTICAÇÃO
# ------------------------------------------------------------------

def login_view(request):
    """Tela de login simples."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Respeita o ?next= da URL para redirecionar após login
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuário ou senha incorretos.')

    return render(request, 'agendamentos/login.html')


def logout_view(request):
    """Encerra a sessão e redireciona para o login."""
    logout(request)
    messages.success(request, 'Você saiu com sucesso.')
    return redirect('login')


# ------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------

@login_required
def dashboard(request):
    # ---- Salvar novo agendamento ----
    if request.method == 'POST':
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Agendamento salvo com sucesso!')
            return redirect('dashboard')
        else:
            messages.error(request, '❌ Corrija os erros no formulário abaixo.')
    else:
        form = AgendamentoForm()

    # ---- Filtro de salas ----
    filtro = request.GET.get('filtro', 'todas')
    agendamentos_base = Agendamento.objects.select_related('sala', 'professor').all()

    if filtro == 'P8':
        agendamentos_base = agendamentos_base.filter(
            Q(sala__nome__icontains='P8') | Q(sala__nome__icontains='P08')
        )
    elif filtro == 'P16':
        agendamentos_base = agendamentos_base.filter(sala__nome__icontains='P16')
    elif filtro != 'todas':
        # Filtro dinâmico: nome exato da sala clicada
        agendamentos_base = agendamentos_base.filter(sala__nome=filtro)

    # ---- Filtro dinâmico: lista salas únicas para os botões ----
    salas_disponiveis = Sala.objects.order_by('nome').values_list('nome', flat=True).distinct()

    # ---- Agenda por dia da semana ----
    dias_config = [
        {'sigla': 'SEG', 'nome': 'Segunda-feira', 'cor': 'primary'},
        {'sigla': 'TER', 'nome': 'Terça-feira',   'cor': 'success'},
        {'sigla': 'QUA', 'nome': 'Quarta-feira',  'cor': 'warning'},
        {'sigla': 'QUI', 'nome': 'Quinta-feira',  'cor': 'danger'},
        {'sigla': 'SEX', 'nome': 'Sexta-feira',   'cor': 'info'},
    ]

    agenda_semana = []
    for dia in dias_config:
        aulas = agendamentos_base.filter(
            dia_semana=dia['sigla']
        ).order_by('horario_inicio', 'sala__nome')

        # Inclui todos os dias — mesmo os sem agendamento (com lista vazia)
        agenda_semana.append({
            'nome':         dia['nome'],
            'sigla':        dia['sigla'],
            'cor':          dia['cor'],
            'agendamentos': aulas,
            'tem_aulas':    aulas.exists(),
        })

    contexto = {
        'agenda_semana':      agenda_semana,
        'form':               form,
        'filtro_atual':       filtro,
        'salas_disponiveis':  salas_disponiveis,
    }
    return render(request, 'agendamentos/dashboard.html', contexto)


# ------------------------------------------------------------------
# DELETAR
# ------------------------------------------------------------------

@login_required
def deletar_agendamento(request, id):
    agendamento = get_object_or_404(Agendamento, id=id)
    desc = str(agendamento)
    agendamento.delete()
    messages.success(request, f'🗑️ Agendamento "{desc}" excluído com sucesso.')
    return redirect('dashboard')


# ------------------------------------------------------------------
# EDITAR
# ------------------------------------------------------------------

@login_required
def editar_agendamento(request, id):
    agendamento = get_object_or_404(Agendamento, id=id)

    if request.method == 'POST':
        form = AgendamentoForm(request.POST, instance=agendamento)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Agendamento atualizado com sucesso!')
            return redirect('dashboard')
        else:
            messages.error(request, '❌ Corrija os erros abaixo antes de salvar.')
    else:
        form = AgendamentoForm(instance=agendamento)

    return render(request, 'agendamentos/editar.html', {
        'form': form,
        'agendamento': agendamento,
    })