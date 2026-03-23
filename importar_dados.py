import os
import django
import csv
import re
from datetime import datetime

# Configura o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agendamentos.models import Professor, Sala, Agendamento

# Configurações padrão
DIAS_MAP = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX'}
ANO_PADRAO = 2026 # Ano que aparecia no título da sua planilha

def limpar_horario(texto_hora):
    """Transforma '08h30' ou '8h' em '08:30:00'"""
    texto = texto_hora.strip().lower().replace('min', '')
    if 'h' in texto:
        partes = texto.split('h')
        hora = partes[0].zfill(2)
        minuto = partes[1] if partes[1] else '00'
        return f"{hora}:{minuto}:00"
    return "00:00:00"

def extrair_datas(texto_completo):
    """Busca no texto o padrão DD/MM até DD/MM e converte para data do banco"""
    # Procura algo como "18/02 até 08/07"
    padrao = r'(\d{2}/\d{2})\s*até\s*(\d{2}/\d{2})'
    match = re.search(padrao, texto_completo, re.IGNORECASE)
    
    if match:
        str_inicio, str_fim = match.groups()
        try:
            # Transforma string em objeto Data (YYYY-MM-DD)
            dt_inicio = datetime.strptime(f"{str_inicio}/{ANO_PADRAO}", "%d/%m/%Y").date()
            dt_fim = datetime.strptime(f"{str_fim}/{ANO_PADRAO}", "%d/%m/%Y").date()
            return dt_inicio, dt_fim
        except ValueError:
            return None, None
    return None, None

def processar_celula(texto_celula, dia_sigla):
    if not texto_celula.strip():
        return

    linhas = [linha.strip() for linha in texto_celula.split('\n') if linha.strip()]
    if len(linhas) < 3:
        return

    try:
        # 1. SALA
        nome_sala = linhas[0]
        sala_obj, _ = Sala.objects.get_or_create(nome=nome_sala)

        # 2. HORÁRIO E ALUNOS (Procura a linha do horário)
        linha_horario = next((l for l in linhas if 'às' in l.lower() and ('aluno' in l.lower() or 'h' in l.lower())), None)
        if not linha_horario:
            return

        partes_horario = linha_horario.split('-')
        str_horarios = partes_horario[0]
        str_alunos = partes_horario[1] if len(partes_horario) > 1 else "0"

        hora_inicio = limpar_horario(str_horarios.lower().split('às')[0])
        hora_fim = limpar_horario(str_horarios.lower().split('às')[1])
        qtd_alunos = int(re.sub(r'\D', '', str_alunos) or 0)

        # 3. EXTRAIR DATAS (Busca no bloco inteiro)
        dt_inicio, dt_fim = extrair_datas(texto_celula)

        # 4. PROFESSOR (Geralmente a linha que não é horário, nem data, nem sala)
        idx_horario = linhas.index(linha_horario)
        linha_professor = ""
        idx_prof = -1
        
        # Procura para baixo do horário o nome do professor
        for i in range(idx_horario + 1, len(linhas)):
            texto_lin = linhas[i].lower()
            if 'até' not in texto_lin and 'semestre' not in texto_lin:
                linha_professor = linhas[i]
                idx_prof = i
                break
                
        if not linha_professor: # Fallback caso não ache
            linha_professor = linhas[-1]
            idx_prof = len(linhas) - 1
            
        nome_professor = linha_professor.replace(' ok', '').strip()
        prof_obj, _ = Professor.objects.get_or_create(nome=nome_professor)

        # 5. TEMAS E OBSERVAÇÕES
        # Junta tudo que sobrou (exceções de datas, temas, etc) para não perder nenhuma informação
        linhas_obs = [l for i, l in enumerate(linhas) if i not in (0, idx_horario, idx_prof)]
        temas = "\n".join(linhas_obs)

        # 6. SALVAR NO BANCO
        agendamento, created = Agendamento.objects.get_or_create(
            dia_semana=dia_sigla,
            sala=sala_obj,
            horario_inicio=hora_inicio,
            data_inicio=dt_inicio, # Agora incluímos a data como diferencial!
            defaults={
                'horario_fim': hora_fim,
                'qtd_alunos': qtd_alunos,
                'professor': prof_obj,
                'data_fim': dt_fim,
                'temas': temas
            }
        )
        
        if created:
            data_str = dt_inicio.strftime('%d/%m') if dt_inicio else 'Fixo'
            print(f"✅ Salvo: {dia_sigla} | {data_str} | {nome_sala[:15]}... | Prof: {nome_professor[:15]}")

    except Exception as e:
        print(f"❌ Erro na célula: {linhas[0][:20]}... - Erro: {e}")

def resetar_banco():
    print("🗑️ Apagando todos os dados antigos do banco de dados...")
    Agendamento.objects.all().delete()
    Professor.objects.all().delete()
    Sala.objects.all().delete()
    print("✨ Banco de dados limpo com sucesso!\n")

def importar():
    # 1º Passo: Limpa a casa
    resetar_banco()
    print("banco limpo")
    
    '''# 2º Passo: Lê a planilha e reinsere
    print("🚀 Iniciando importação com Datas...")
    caminho_csv = 'Página1.csv' # CONFIRME SE O NOME DO SEU ARQUIVO AINDA É ESTE
    
    with open(caminho_csv, newline='', encoding='utf-8') as arquivo:
        leitor = csv.reader(arquivo)
        for idx_linha, linha in enumerate(leitor):
            if idx_linha < 2: 
                continue # Pula cabeçalhos
            
            for idx_coluna in range(5):
                if idx_coluna < len(linha):
                    processar_celula(linha[idx_coluna], DIAS_MAP[idx_coluna])

    print("\n🎉 RESET E IMPORTAÇÃO CONCLUÍDOS!")'''

if __name__ == '__main__':
    importar()