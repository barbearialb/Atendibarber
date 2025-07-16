import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import json
import time

# --- CONFIGURAÇÃO INICIAL E ESTILOS ---

# Configuração da página para layout mais amplo
st.set_page_config(layout="wide")

# CSS customizado para colorir os botões da tabela e centralizar o texto
# CSS customizado para criar uma grade de agendamentos visual e responsiva
st.markdown("""
<style>
    /* Define a célula base do agendamento */
    .schedule-cell {
        height: 50px;              /* Altura fixa para cada célula */
        border-radius: 8px;        /* Bordas arredondadas */
        display: flex;             /* Centraliza o conteúdo */
        align-items: center;
        justify-content: center;
        margin-bottom: 5px;        /* Espaço entre as linhas */
        padding: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24); /* Sombra sutil */
    }

    /* Cores de fundo baseadas no status */
    .schedule-cell.disponivel { background-color: #28a745; } /* Verde */
    .schedule-cell.ocupado    { background-color: #dc3545; } /* Vermelho */
    .schedule-cell.almoco     { background-color: #ffc107; color: black;} /* Laranja */
    .schedule-cell.indisponivel { background-color: #6c757d; } /* Cinza padrão para indisponível (SDJ, Descanso) */
    .schedule-cell.fechado { background-color: #A9A9A9; color: black; } /* Nova classe para "Fechado" */

    /* Estiliza o botão dentro da célula para ser "invisível" mas clicável */
    .schedule-cell button {
        background-color: transparent;
        color: white;
        border: none;
        width: 100%;
        height: 100%;
        font-weight: bold;
    }
    
    /* Para o texto do botão (que é um <p> dentro do botão do Streamlit) */
    .schedule-cell button p {
        color: white; /* Cor do texto para status verde e vermelho */
        margin: 0;
        white-space: nowrap;      /* Impede a quebra de linha */
        overflow: hidden;         /* Esconde o que passar do limite */
        text-overflow: ellipsis;  /* Adiciona "..." ao final de texto longo */
    }

    /* Cor do texto específica para a célula de almoço */
    .schedule-cell.almoco button p {
        color: black;
    }

    /* Remove o ponteiro de clique para horários não clicáveis */
    .schedule-cell.indisponivel {
        pointer-events: none;
    }

</style>
""", unsafe_allow_html=True)


# --- INICIALIZAÇÃO DO FIREBASE E E-MAIL (Mesmo do código original) ---

FIREBASE_CREDENTIALS = None
EMAIL = None
SENHA = None

try:
    firebase_credentials_json = st.secrets["firebase"]["FIREBASE_CREDENTIALS"]
    FIREBASE_CREDENTIALS = json.loads(firebase_credentials_json)
    EMAIL = st.secrets["email"]["EMAIL_CREDENCIADO"]
    SENHA = st.secrets["email"]["EMAIL_SENHA"]
except Exception as e:
    st.error(f"Erro ao carregar credenciais do Streamlit Secrets: {e}")

if FIREBASE_CREDENTIALS and not firebase_admin._apps:
    try:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro ao inicializar o Firebase: {e}")

db = firestore.client() if firebase_admin._apps else None

# --- DADOS BÁSICOS ---
servicos = ["Tradicional", "Social", "Degradê", "Pezim", "Navalhado", "Barba", "Abordagem de visagismo", "Consultoria de visagismo"]
barbeiros = ["Aluizio", "Lucas Borges"]


# --- FUNÇÕES DE BACKEND (Adaptadas e Novas) ---

def enviar_email(assunto, mensagem):
    if not EMAIL or not SENHA:
        st.warning("Credenciais de e-mail não configuradas.")
        return
    try:
        msg = MIMEText(mensagem)
        msg['Subject'] = assunto
        msg['From'] = EMAIL
        msg['To'] = EMAIL
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL, SENHA)
            server.sendmail(EMAIL, EMAIL, msg.as_string())
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")

def salvar_agendamento(data, horario, nome, telefone, servicos, barbeiro):
    if not db: return False
    chave_agendamento = f"{data}_{horario}_{barbeiro}"
    try:
        data_obj = datetime.strptime(data, '%d/%m/%Y')
        db.collection('agendamentos').document(chave_agendamento).set({
            'nome': nome,
            'telefone': telefone,
            'servicos': servicos,
            'barbeiro': barbeiro,
            'data': data_obj,
            'horario': horario
        })
        return True
    except Exception as e:
        st.error(f"Erro ao salvar agendamento: {e}")
        return False

def cancelar_agendamento(data, horario, barbeiro):
    if not db: return None
    chave_agendamento = f"{data}_{horario}_{barbeiro}"
    agendamento_ref = db.collection('agendamentos').document(chave_agendamento)
    try:
        doc = agendamento_ref.get()
        if doc.exists:
            agendamento_data = doc.to_dict()
            agendamento_ref.delete()
            return agendamento_data
        return None
    except Exception as e:
        st.error(f"Erro ao cancelar agendamento: {e}")
        return None

def bloquear_horario(data, horario, barbeiro, motivo="Almoço"):
    if not db: return False
    chave_bloqueio = f"{data}_{horario}_{barbeiro}"
    try:
        data_obj = datetime.strptime(data, '%d/%m/%Y')
        db.collection('agendamentos').document(chave_bloqueio).set({
            'nome': motivo, 'telefone': "INTERNO", 'servicos': [],
            'barbeiro': barbeiro, 'data': data_obj, 'horario': horario
        })
        return True
    except Exception as e:
        st.error(f"Erro ao bloquear horário: {e}")
        return False

def desbloquear_horario_seguinte(data, horario, barbeiro):
    if not db: return
    try:
        horario_dt = datetime.strptime(horario, '%H:%M') + timedelta(minutes=30)
        horario_seguinte_str = horario_dt.strftime('%H:%M')
        chave_bloqueio = f"{data}_{horario_seguinte_str}_{barbeiro}_BLOQUEADO"
        bloqueio_ref = db.collection('agendamentos').document(chave_bloqueio)
        if bloqueio_ref.get().exists:
            bloqueio_ref.delete()
            st.info(f"Horário seguinte ({horario_seguinte_str}) desbloqueado.")
    except Exception as e:
        st.warning(f"Não foi possível desbloquear o horário seguinte: {e}")


def verificar_status_horario(data, horario, barbeiro):
    """Verifica o status e retorna (status, dados_do_agendamento)."""
    if not db: return ("indisponivel", None)

    chave_agendamento = f"{data}_{horario}_{barbeiro}"
    doc_ref = db.collection('agendamentos').document(chave_agendamento)
    try:
        doc = doc_ref.get()
        if doc.exists:
            dados = doc.to_dict()
            nome = dados.get("nome", "Ocupado")
            if nome == "Almoço":
                return ("almoco", dados)
            elif nome == "BLOQUEADO":
                 return("ocupado", dados) # Para bloqueios de Corte+Barba
            elif nome == "Fechado":
                return ("fechado", dados)
            return ("ocupado", dados)
        else:
            return ("disponivel", None)
    except Exception as e:
        print(f"Erro ao verificar status: {e}")
        return ("indisponivel", None)

def verificar_disponibilidade_horario_seguinte(data, horario, barbeiro):
    horario_seguinte_dt = datetime.strptime(horario, '%H:%M') + timedelta(minutes=30)
    if horario_seguinte_dt.hour >= 20: return False
    horario_seguinte_str = horario_seguinte_dt.strftime('%H:%M')
    status, _ = verificar_status_horario(data, horario_seguinte_str, barbeiro)
    return status == "disponivel"

# NOVA FUNÇÃO PARA FECHAR HORÁRIOS EM LOTE
def fechar_horario(data, horario, barbeiro, motivo="Fechado"):
    """Salva um registro especial para marcar um horário como Fechado."""
    if not db: return False
    chave_fechamento = f"{data}_{horario}_{barbeiro}"
    try:
        data_obj = datetime.strptime(data, '%d/%m/%Y')
        # Cria ou sobrescreve o documento com o status "Fechado"
        db.collection('agendamentos').document(chave_fechamento).set({
            'nome': motivo,
            'telefone': "INTERNO",
            'servicos': [],
            'barbeiro': barbeiro,
            'data': data_obj,
            'horario': horario
        })
        return True
    except Exception as e:
        st.error(f"Erro ao fechar horário: {e}")
        return False

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'view' not in st.session_state:
    st.session_state.view = 'main' # 'main', 'agendar', 'cancelar'
    st.session_state.selected_data = None
    st.session_state.agendamento_info = {}

# --- LÓGICA DE NAVEGAÇÃO E EXIBIÇÃO (MODAIS) ---

# ---- MODAL DE AGENDAMENTO ----
if st.session_state.view == 'agendar':
    info = st.session_state.agendamento_info
    st.header("Confirmar Agendamento")
    st.subheader(f"🗓️ {info['data_str']} às {info['horario']} com {info['barbeiro']}")

    with st.container(border=True):
        nome_cliente = st.text_input("Nome do Cliente*", key="cliente_nome")
        servicos_selecionados = st.multiselect("Serviços (opcional)", servicos, key="servicos_selecionados")

        # Validação de Visagismo
        is_visagismo = any(s in servicos_selecionados for s in ["Abordagem de visagismo", "Consultoria de visagismo"])
        if is_visagismo and info['barbeiro'] == 'Aluizio':
            st.error("Serviços de visagismo são apenas com Lucas Borges.")
        else:
            cols = st.columns(3)
            # --- BOTÃO CONFIRMAR AGENDAMENTO ---
            if cols[0].button("✅ Confirmar Agendamento", type="primary", use_container_width=True):
                if not nome_cliente:
                    st.error("O nome do cliente é obrigatório!")
                else:
                    with st.spinner("Processando..."):
                        precisa_bloquear_proximo = False
                        if "Barba" in servicos_selecionados and any(c in servicos_selecionados for c in ["Tradicional", "Social", "Degradê", "Navalhado"]):
                            if verificar_disponibilidade_horario_seguinte(info['data_str'], info['horario'], info['barbeiro']):
                                precisa_bloquear_proximo = True
                            else:
                                st.error("Não é possível agendar Corte+Barba. O horário seguinte não está disponível.")
                                st.stop()

                        if salvar_agendamento(info['data_str'], info['horario'], nome_cliente, "INTERNO", servicos_selecionados, info['barbeiro']):
                            if precisa_bloquear_proximo:
                                horario_dt = datetime.strptime(info['horario'], '%H:%M') + timedelta(minutes=30)
                                horario_seguinte_str = horario_dt.strftime('%H:%M')
                                bloquear_horario(info['data_str'], horario_seguinte_str, info['barbeiro'], "BLOQUEADO")

                            st.success(f"Agendamento para {nome_cliente} confirmado!")
                            assunto_email = f"Novo Agendamento: {nome_cliente} em {info['data_str']}"
                            mensagem_email = (
                                f"Novo agendamento realizado:\n\n"
                                f"Cliente: {nome_cliente}\n"
                                f"Data: {info['data_str']}\n"
                                f"Horário: {info['horario']}\n"
                                f"Barbeiro: {info['barbeiro']}\n"
                                f"Serviços: {', '.join(servicos_selecionados) if servicos_selecionados else 'Nenhum'}"
                            )
                            enviar_email(assunto_email, mensagem_email)
                            st.session_state.view = 'main'
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Falha ao salvar. Tente novamente.")

            # --- BOTÃO MARCAR COMO ALMOÇO ---
            if cols[1].button("🍽️ Marcar como Almoço", use_container_width=True):
                with st.spinner("Bloqueando para almoço..."):
                    if bloquear_horario(info['data_str'], info['horario'], info['barbeiro'], "Almoço"):
                        st.success("Horário marcado como almoço.")
                        st.session_state.view = 'main'
                        time.sleep(2)
                        st.rerun()

            # --- BOTÃO VOLTAR ---
            if cols[2].button("⬅️ Voltar", use_container_width=True):
                st.session_state.view = 'main'
                st.rerun()

# ---- MODAL DE CANCELAMENTO ----
elif st.session_state.view == 'cancelar':
    info = st.session_state.agendamento_info
    st.header("Confirmar Cancelamento")
    st.subheader(f"Cancelar agendamento de **{info['dados']['nome']}**?")
    st.write(f"**Data:** {info['data_str']}")
    st.write(f"**Horário:** {info['horario']}")
    st.write(f"**Barbeiro:** {info['barbeiro']}")
    st.write(f"**Serviços:** {', '.join(info['dados']['servicos'])}")

    cols = st.columns(2)
    # --- BOTÃO CONFIRMAR CANCELAMENTO ---
    if cols[0].button("❌ Sim, Cancelar", type="primary", use_container_width=True):
        with st.spinner("Cancelando..."):
            dados_cancelados = cancelar_agendamento(info['data_str'], info['horario'], info['barbeiro'])
            if dados_cancelados:
                # Se era um agendamento de Corte+Barba, desbloqueia o horário seguinte
                if "Barba" in dados_cancelados.get('servicos', []) and any(c in dados_cancelados.get('servicos', []) for c in ["Tradicional", "Social", "Degradê", "Navalhado"]):
                    desbloquear_horario_seguinte(info['data_str'], info['horario'], info['barbeiro'])

                st.success("Agendamento cancelado!")
                nome_cliente_cancelado = dados_cancelados.get('nome', 'N/A')
                assunto_email = f"Cancelamento de Agendamento: {nome_cliente_cancelado} em {info['data_str']}"
                mensagem_email = (
                    f"O seguinte agendamento foi CANCELADO:\n\n"
                    f"Cliente: {nome_cliente_cancelado}\n"
                    f"Data: {info['data_str']}\n"
                    f"Horário: {info['horario']}\n"
                    f"Barbeiro: {info['barbeiro']}"
                )
                enviar_email(assunto_email, mensagem_email)
                st.session_state.view = 'main'
                time.sleep(2)
                st.rerun()
            else:
                st.error("Não foi possível cancelar. O agendamento pode já ter sido removido.")
                
    if cols[1].button("⬅️ Voltar", use_container_width=True):
        st.session_state.view = 'main' # Retorna para a tela principal
        st.rerun()

# ---- NOVO MODAL PARA FECHAR HORÁRIOS ----
elif st.session_state.view == 'fechar':
    st.header("🔒 Fechar Horários")
    data_para_fechar = st.session_state.data_str_selecionada
    st.subheader(f"Data selecionada: {data_para_fechar}")

    # Lista de horários para os seletores
    horarios_tabela = [f"{h:02d}:{m:02d}" for h in range(7, 20) for m in (0, 30)]

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            horario_inicio = st.selectbox("Horário de Início", options=horarios_tabela, key="fecha_inicio")
        with col2:
            # O 'index' pré-seleciona o último horário da lista
            horario_fim = st.selectbox("Horário Final", options=horarios_tabela, key="fecha_fim", index=len(horarios_tabela)-1)

        barbeiro_fechar = st.selectbox("Selecione o Barbeiro", options=barbeiros, key="fecha_barbeiro")

        # Aviso sobre a ação (a "cor amarela" que você mencionou)
        st.warning("Atenção: Esta ação irá sobrescrever quaisquer agendamentos existentes no intervalo selecionado.", icon="⚠️")

        btn_cols = st.columns(2)
        if btn_cols[0].button("✔️ Confirmar Fechamento", type="primary", use_container_width=True):
            try:
                start_index = horarios_tabela.index(horario_inicio)
                end_index = horarios_tabela.index(horario_fim)

                if start_index > end_index:
                    st.error("O horário de início deve ser anterior ao horário final.")
                else:
                    with st.spinner(f"Fechando horários para {barbeiro_fechar}..."):
                        horarios_para_fechar = horarios_tabela[start_index:end_index+1]
                        sucesso_total = True
                        for horario in horarios_para_fechar:
                            if not fechar_horario(data_para_fechar, horario, barbeiro_fechar):
                                sucesso_total = False
                                break
                        if sucesso_total:
                            st.success("Horários fechados com sucesso!")
                            st.session_state.view = 'main'
                            time.sleep(2) # Pausa para o usuário ler a mensagem
                            st.rerun()
                        else:
                            st.error("Ocorreu um erro ao fechar um ou mais horários.")
            except ValueError:
                st.error("Horário selecionado inválido.")

        if btn_cols[1].button("⬅️ Voltar", use_container_width=True):
            st.session_state.view = 'main'
            st.rerun()
# --- TELA PRINCIPAL (GRID DE AGENDAMENTOS) ---
else:
    st.title("Barbearia Lucas Borges - Agendamentos Internos")
    # Centraliza a logo usando colunas e aumenta o tamanho
    cols_logo = st.columns([1, 2, 1])
    with cols_logo[1]:
        st.image("https://github.com/barbearialb/sistemalb/blob/main/icone.png?raw=true", width=350)

    data_selecionada = st.date_input(
        "Selecione a data para visualizar",
        value=datetime.today(),
        min_value=datetime.today().date(),
        key="data_input"
    )

    data_str = data_selecionada.strftime('%d/%m/%Y')
    data_obj = data_selecionada
    dia_semana = data_obj.weekday() # 0=Segunda, 6=Domingo
    dia_mes = data_obj.day
    mes_ano = data_obj.month

    if st.button("🔒 Fechar Horários", use_container_width=True):
        st.session_state.view = 'fechar'
        st.session_state.data_str_selecionada = data_str
        st.rerun()


    # Header da Tabela
    header_cols = st.columns([1.5, 3, 3])
    header_cols[0].markdown("**Horário**")
    header_cols[1].markdown(f"### {barbeiros[0]}")
    header_cols[2].markdown(f"### {barbeiros[1]}")
    st.divider()

    # Geração do Grid Interativo
    horarios_tabela = [f"{h:02d}:{m:02d}" for h in range(7, 20) for m in (0, 30)]

    for horario in horarios_tabela:
        grid_cols = st.columns([1.5, 3, 3])
        grid_cols[0].markdown(f"#### {horario}")

        for i, barbeiro in enumerate(barbeiros):
            status = "indisponivel"
            texto_botao = "N/A"
            dados_agendamento = None
            is_clicavel = True

            hora_int = int(horario.split(':')[0])
            is_periodo_especial_julho = (mes_ano == 7 and 10 <= dia_mes <= 19)

            # Lógica de status (unificada)
            if horario in ["07:00", "07:30"] and not is_periodo_especial_julho:
                status, texto_botao, is_clicavel = "indisponivel", "SDJ", False
            elif dia_semana == 6 and not is_periodo_especial_julho:
                status, texto_botao, is_clicavel = "indisponivel", "Descanso", False
            elif dia_semana < 5 and not is_periodo_especial_julho and ((barbeiro == "Aluizio" and hora_int in [12, 13]) or (barbeiro == "Lucas Borges" and hora_int in [12, 13])):
                status, texto_botao = "almoco", "Almoço"
            else:
                status, dados_agendamento = verificar_status_horario(data_str, horario, barbeiro)
                if status == 'disponivel':
                    texto_botao = 'Disponível'
                elif status == 'ocupado':
                    texto_botao = dados_agendamento.get('nome', 'Ocupado')
                elif status == 'almoco':
                    texto_botao = "Almoço"
                elif status == 'fechado':
                    texto_botao = "Fechado"
                    is_clicavel = True

            # Renderiza o botão dentro de um container div para aplicar o estilo CSS
            key = f"btn_{data_str}_{horario}_{barbeiro}"
            with grid_cols[i+1]:
                cor_botao = "#28a745" if status == "disponivel" else "#dc3545" if status == "ocupado" else "#ffc107" if status == "almoco" else "#A9A9A9" if status == "fechado" else "#6c757d"
                cor_texto = "black" if status == "almoco" or status == "fechado" else "white"
                botao_html = f"""
                    <button style='
                        background-color: {cor_botao};
                        color: {cor_texto};
                        border: none;
                        border-radius: 6px;
                        padding: 4px 8px;
                        width: 100%;
                        font-size: 12px;
                        font-weight: bold;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    '  onclick="document.getElementById('{key}').click()">{texto_botao}</button>
                    <input type="hidden" id="{key}">
                 """
                st.markdown(botao_html, unsafe_allow_html=True)
            
                st.markdown(f"<div style='text-align: center; font-size: 12px; color: #AAA;'>{barbeiro}</div>", unsafe_allow_html=True)

                if st.button("", key=key, disabled=not is_clicavel):
                    if status == 'disponivel':
                        st.session_state.view = 'agendar'
                        st.session_state.agendamento_info = {
                            'data_str': data_str,
                            'horario': horario,
                            'barbeiro': barbeiro
                        }
                        st.rerun()
                    elif status in ['ocupado', 'almoco', 'fechado']:
                        st.session_state.view = 'cancelar'
                        st.session_state.agendamento_info = {
                            'data_str': data_str,
                            'horario': horario,
                            'barbeiro': barbeiro,
                            'dados': dados_agendamento
                        }
                        st.rerun()
                        
