# agendamentos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q  # Importamos o Q para buscas complexas
from .models import Agendamento
from .forms import AgendamentoForm

def dashboard(request):
    # Lógica de salvar novo agendamento
    if request.method == 'POST':
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = AgendamentoForm()

    # --- LÓGICA DO FILTRO ---
    # Pega o que está na URL (ex: ?filtro=P8). Se não tiver nada, o padrão é 'todas'
    filtro = request.GET.get('filtro', 'todas')
    agendamentos_base = Agendamento.objects.all()

    if filtro == 'P8':
        # Filtra onde o nome da sala contém 'P8' OU 'P08'
        agendamentos_base = agendamentos_base.filter(Q(sala__nome__icontains='P8') | Q(sala__nome__icontains='P08'))
    elif filtro == 'P16':
        # Filtra onde o nome da sala contém 'P16'
        agendamentos_base = agendamentos_base.filter(sala__nome__icontains='P16')

    # --- CONFIGURAÇÃO DOS DIAS ---
    dias_config = [
        {'sigla': 'SEG', 'nome': 'Segunda-feira', 'cor': 'primary'},
        {'sigla': 'TER', 'nome': 'Terça-feira', 'cor': 'success'},
        {'sigla': 'QUA', 'nome': 'Quarta-feira', 'cor': 'warning'},
        {'sigla': 'QUI', 'nome': 'Quinta-feira', 'cor': 'danger'},
        {'sigla': 'SEX', 'nome': 'Sexta-feira', 'cor': 'info'},
    ]

    agenda_semana = []
    for dia in dias_config:
        # Usa a base já filtrada em vez de buscar tudo de novo
        aulas_do_dia = agendamentos_base.filter(dia_semana=dia['sigla']).order_by('horario_inicio', 'sala__nome')
        
        if aulas_do_dia.exists():
            agenda_semana.append({
                'nome': dia['nome'],
                'cor': dia['cor'],
                'agendamentos': aulas_do_dia
            })

    contexto = {
        'agenda_semana': agenda_semana,
        'form': form,
        'filtro_atual': filtro  # Enviamos isso para deixar o botão aceso na tela
    }
    return render(request, 'agendamentos/dashboard.html', contexto)

def deletar_agendamento(request, id):
    agendamento = get_object_or_404(Agendamento, id=id)
    agendamento.delete()
    return redirect('dashboard')

# --- NOVA LÓGICA DE EDIÇÃO ---
def editar_agendamento(request, id):
    # Busca o agendamento específico no banco
    agendamento = get_object_or_404(Agendamento, id=id)
    
    if request.method == 'POST':
        # Passamos a "instance" para dizer ao Django que estamos ATUALIZANDO, não criando um novo
        form = AgendamentoForm(request.POST, instance=agendamento)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        # Preenche o formulário vazio com os dados da aula que queremos editar
        form = AgendamentoForm(instance=agendamento)
    
    return render(request, 'agendamentos/editar.html', {'form': form, 'agendamento': agendamento})