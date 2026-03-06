import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import time
from fpdf import FPDF
import io
import unicodedata

# --- 1. FUNÇÃO PARA EVITAR ERRO DE ACENTOS NO PDF ---
def limpar_texto(texto):
    if not texto: return ""
    # Transforma 'ç' em 'c', 'ã' em 'a', etc., para o PDF não bugar
    return "".join(c for c in unicodedata.normalize('NFD', str(texto))
                   if unicodedata.category(c) != 'Mn').replace('ç', 'c').replace('Ç', 'C')

# --- 2. PORTA DE ENTRADA PARA O ROBÔ (MODO PING) ---
if st.query_params.get("ping") == "true":
    st.write("Sistema DNA South America: Online e Ativo.")
    st.stop()

# 3. Configuração da Página
st.set_page_config(page_title="DNA - Gestão Comercial", layout="wide")

# 4. Conexão Segura
@st.cache_resource
def iniciar_conexao():
    try:
        info = st.secrets["minha_nova_conexao"]
        client = gspread.service_account_from_dict(info)
        sh = client.open_by_key("1ZciM1-ym--0IvGHvJ-xy1lZCki7hbRxDgIOgly1STCQ")
        return sh
    except Exception as e:
        st.error(f"⚠️ Erro de Conexão: {e}")
        return None

sh = iniciar_conexao()

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        try: self.image('DNA_white-1024x576-1.png', 10, 8, 30)
        except: pass
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, 'Relatorio de Reposicao de Animais', 0, 1, 'R')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 10, f'DNA South America - Pagina {self.page_no()}', 0, 0, 'C')

def gerar_pdf_multi_reposicao(lista_dados):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    for dados in lista_dados:
        if pdf.get_y() > 230: pdf.add_page()
        pdf.set_font("Arial", 'B', 9)
        # Limpamos o texto de cada campo para evitar o erro de Unicode
        pdf.cell(0, 7, limpar_texto(f"REPOSICAO: {dados['Brinco']} - CLIENTE: {dados['Cliente']}"), 1, 1, 'L')
        pdf.set_font("Arial", '', 8)
        pdf.cell(25, 6, "Cliente:", 'L'); pdf.cell(70, 6, limpar_texto(dados['Cliente']), 'R')
        pdf.cell(25, 6, "CNPJ:", 'L'); pdf.cell(0, 6, limpar_texto(dados['CNPJ']), 'R', 1)
        pdf.cell(25, 6, "DNA ID:", 'L'); pdf.cell(70, 6, limpar_texto(dados['DNA_ID']), 'R')
        pdf.cell(25, 6, "Brinco:", 'L'); pdf.cell(0, 6, limpar_texto(dados['Brinco']), 'R', 1)
        pdf.cell(25, 6, "Motivo:", 'L'); pdf.cell(70, 6, limpar_texto(dados['Motivo']), 'R')
        pdf.cell(25, 6, "Tipo Repo:", 'L'); pdf.cell(0, 6, limpar_texto(dados['Tipo_repo']), 'R', 1)
        pdf.cell(25, 6, "Status:", 'LB'); pdf.cell(70, 6, limpar_texto(dados['Status']), 'RB')
        pdf.cell(25, 6, "Data Sol.:", 'LB'); pdf.cell(0, 6, limpar_texto(dados.get('Data', 'N/A')), 'RB', 1)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- REGRAS E AUXILIARES ---
def carregar_aba_segura(nome_aba):
    try:
        ws = sh.worksheet(nome_aba)
        dados = ws.get_all_values()
        if not dados or len(dados) < 2: return pd.DataFrame(), ws
        df = pd.DataFrame(dados[1:], columns=dados[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df, ws
    except: return pd.DataFrame(), None

def obter_todos_motivos():
    return sorted(["Acordo Comercial", "NSA", "Morte/Fratura", "Prolapso", "Hérnia", "Locomotor/Aprumo", "Problema de Casco", "Anestro", "Vulva Infantil"])

def validar_prazo_motivo(motivo, sexo, dias):
    try:
        d = int(dias); s = str(sexo).upper()
        if motivo in ["Morte/Fratura", "Prolapso"] and d > 30: return False
        if motivo in ["Hérnia", "Locomotor/Aprumo", "Problema de Casco"] and d > 60: return False
        if motivo in ["Anestro", "Vulva Infantil"]:
            if "F" not in s or d > 150: return False
        return True
    except: return True

def atualizar_dados_animal():
    rk = st.session_state.reset_trigger
    brinco = st.session_state.get(f"br_{rk}")
    dna = st.session_state.get(f"dna_{rk}")
    if brinco and dna:
        df_b = st.session_state.df_base
        c_dna = next((c for c in df_b.columns if 'DNA' in c.upper()), df_b.columns[0])
        animal = df_b[(df_b['Brinco'].astype(str) == str(brinco)) & (df_b[c_dna].astype(str) == str(dna))]
        if not animal.empty:
            r = animal.iloc[0]
            st.session_state.cliente_f = str(r.get('Nome_Cliente', r.get('Cliente', '')))
            st.session_state.cnpj_f = str(r.get('CNPJ', r.get('CNPJ_CPF', '')))
            st.session_state.idade_f = int(r.get('Idade', 0))
            st.session_state.lin_f = r.get('Linhagem', ''); st.session_state.sex_f = r.get('Sexo_do_Animal', '')
            nf_raw = str(r.get('Data_NF', ''))
            st.session_state.entrega_f = nf_raw
            try:
                dt_e = datetime.strptime(nf_raw, "%d/%m/%Y").date()
                st.session_state.dias_f = (date.today() - dt_e).days
            except: st.session_state.dias_f = 9999

if sh:
    menu = st.sidebar.radio("Navegação", ["Cadastrar Reposição", "Aprovação (Diretor)", "Status de Envios"])
    vendedores = ["Amanda","Caio Simões","Leonardo","Thomas","Fabio","Thiagner","Maria Gessica","Eduardo","RPsui","Mariana","André Mallman","Gustavo Laureano"]

    if menu == "Cadastrar Reposição":
        st.title("Pedidos de Reposição")
        if 'reset_trigger' not in st.session_state: st.session_state.reset_trigger = 0
        df_base, _ = carregar_aba_segura("Base de vendidos")
        st.session_state.df_base = df_base
        df_repo, ws_repo = carregar_aba_segura("Relatorio_Reposicoes")
        df_enviados, _ = carregar_aba_segura("Rep enviadas")
        rk = st.session_state.reset_trigger
        col1, col2 = st.columns(2)
        bloqueado = False
        with col1:
            st.subheader("Identificação")
            lista_brincos = [""] + sorted(df_base['Brinco'].unique().astype(str).tolist())
            brinco_sel = st.selectbox("Brinco*", options=lista_brincos, key=f"br_{rk}", on_change=atualizar_dados_animal)
            if brinco_sel and not df_enviados.empty:
                ja_env = df_enviados[(df_enviados.iloc[:, 15].astype(str) == str(brinco_sel)) & (df_enviados.iloc[:, 5].astype(str) == st.session_state.get('cliente_f', ''))]
                if not ja_env.empty:
                    st.write(f":red[**Animal já enviado para este cliente anteriormente.**]"); bloqueado = True
            br_atual = st.session
