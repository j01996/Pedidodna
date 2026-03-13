import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import time
from fpdf import FPDF
import io
import unicodedata
import extra_streamlit_components as stx

# --- 1. PREVENIR HIBERNAÇÃO (KEEP ALIVE) ---
if st.query_params.get("ping") == "true":
    st.write("Sistema Online")
    st.stop()

# --- 2. FUNÇÃO PARA LIMPAR CARACTERES DO PDF ---
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).replace("⚠️", "!").replace("✅", "OK").replace("❌", "X")
    return "".join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn').replace('ç', 'c').replace('Ç', 'C')

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

# --- GERENCIADOR DE COOKIES (LOGIN PERSISTENTE) ---
cookie_manager = stx.CookieManager()

# --- SISTEMA DE LOGIN E PERSISTÊNCIA ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # Tenta recuperar login salvo
    time.sleep(0.5) 
    saved_email = cookie_manager.get('dna_user_email')
    saved_pass = cookie_manager.get('dna_user_pass')
    
    if saved_email and saved_pass:
        try:
            ws_u = sh.worksheet("Usuarios")
            df_u = pd.DataFrame(ws_u.get_all_records())
            user = df_u[(df_u['email'].astype(str) == str(saved_email)) & (df_u['senha'].astype(str) == str(saved_pass))]
            if not user.empty:
                st.session_state.logado = True
                st.session_state.usuario_nome = user.iloc[0]['nome']
                st.session_state.usuario_nivel = user.iloc[0]['nivel']
                st.rerun()
        except: pass

if not st.session_state.logado:
    st.title("DNA - Acesso ao Sistema")
    aba_login, aba_cad = st.tabs(["Acessar Conta", "Criar Nova Conta"])
    
    with aba_login:
        email_log = st.text_input("E-mail", key="l_email")
        senha_log = st.text_input("Senha", type="password", key="l_pass")
        lembrar = st.checkbox("Manter conectado", value=True)
        if st.button("Entrar"):
            try:
                ws_u = sh.worksheet("Usuarios")
                df_u = pd.DataFrame(ws_u.get_all_records())
                user = df_u[(df_u['email'].astype(str) == str(email_log)) & (df_u['senha'].astype(str) == str(senha_log))]
                if not user.empty:
                    st.session_state.logado = True
                    st.session_state.usuario_nome = user.iloc[0]['nome']
                    st.session_state.usuario_nivel = user.iloc[0]['nivel']
                    if lembrar:
                        cookie_manager.set('dna_user_email', email_log, expires_at=datetime.now() + pd.Timedelta(days=30))
                        cookie_manager.set('dna_user_pass', str(senha_log), expires_at=datetime.now() + pd.Timedelta(days=30))
                    st.rerun()
                else: st.error("E-mail ou senha incorretos.")
            except: st.error("Erro ao conectar com base de usuários.")
    
    with aba_cad:
        n_nome = st.text_input("Nome Completo")
        n_email = st.text_input("E-mail corporativo")
        n_senha = st.text_input("Crie uma Senha", type="password")
        if st.button("Cadastrar"):
            try:
                ws_u = sh.worksheet("Usuarios")
                ws_u.append_row([n_email, n_senha, n_nome, "user"])
                st.success("Conta criada! Acesse a aba Login.")
            except: st.error("Erro ao cadastrar.")
    st.stop()

# --- CLASSES E FUNÇÕES ORIGINAIS (MANTIDAS) ---
class PDF(FPDF):
    def header(self):
        try: self.image('DNA_white-1024x576-1.png', 10, 8, 30)
        except: pass
        self.set_font('Arial', 'B', 12); self.set_text_color(0, 0, 0)
        self.cell(0, 10, limpar_texto('Relatorio de Reposicao de Animais'), 0, 1, 'R'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 7)
        self.cell(0, 10, limpar_texto(f'DNA South America - Pagina {self.page_no()}'), 0, 0, 'C')

def gerar_pdf_multi_reposicao(lista_dados):
    lista_dados = sorted(lista_dados, key=lambda x: x['Cliente'].upper())
    pdf = PDF(); pdf.add_page()
    for i, dados in enumerate(lista_dados):
        if pdf.get_y() > 240: pdf.add_page()
        pdf.set_font("Arial", 'B', 9)
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

def carregar_aba_segura(nome_aba):
    try:
        ws = sh.worksheet(nome_aba); dados = ws.get_all_values()
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
    brinco = st.session_state.get(f"br_{rk}"); dna = st.session_state.get(f"dna_{rk}")
    if brinco and dna:
        df_b = st.session_state.df_base
        c_dna = next((c for c in df_b.columns if 'DNA' in c.upper()), df_b.columns[0])
        animal = df_b[(df_b['Brinco'].astype(str) == str(brinco)) & (df_b[c_dna].astype(str) == str(dna))]
        if not animal.empty:
            r = animal.iloc[0]; st.session_state.cliente_f = str(r.get('Nome_Cliente', r.get('Cliente', '')))
            st.session_state.cnpj_f = str(r.get('CNPJ', r.get('CNPJ_CPF', '')))
            try:
                v_idade = str(r.get('Idade', '0')).strip().replace(',', '.')
                st.session_state.idade_f = int(float(v_idade)) if v_idade else 0
            except: st.session_state.idade_f = 0
            st.session_state.lin_f = r.get('Linhagem', ''); st.session_state.sex_f = r.get('Sexo_do_Animal', '')
            nf_raw = str(r.get('Data_NF', '')); st.session_state.entrega_f = nf_raw
            try:
                dt_e = datetime.strptime(nf_raw, "%d/%m/%Y").date()
                st.session_state.dias_f = (date.today() - dt_e).days
            except: st.session_state.dias_f = 9999

# --- INÍCIO DO SISTEMA LOGADO ---
if sh:
    st.sidebar.write(f"👤 **{st.session_state.usuario_nome}**")
    if st.sidebar.button("Sair"):
        cookie_manager.delete('dna_user_email')
        cookie_manager.delete('dna_user_pass')
        st.session_state.logado = False; st.rerun()

    menu = st.sidebar.radio("Navegação", ["Cadastrar Reposição", "Aprovação (Diretor)", "Status de Envios"])

    if menu == "Cadastrar Reposição":
        st.title("Pedidos de Reposição")
        if 'reset_trigger' not in st.session_state: st.session_state.reset_trigger = 0
        df_base, _ = carregar_aba_segura("Base de vendidos"); st.session_state.df_base = df_base
        df_repo, ws_repo = carregar_aba_segura("Relatorio_Reposicoes")
        df_enviados, _ = carregar_aba_segura("Rep enviadas")
        rk = st.session_state.reset_trigger
        
        col1, col2 = st.columns(2); bloqueado = False
        with col1:
            st.subheader("Identificação")
            brinco_sel = st.selectbox("Brinco*", options=[""] + sorted(df_base['Brinco'].unique().astype(str).tolist()), key=f"br_{rk}", on_change=atualizar_dados_animal)
            if brinco_sel and not df_enviados.empty:
                ja_env = df_enviados[(df_enviados.iloc[:, 15].astype(str) == str(brinco_sel)) & (df_enviados.iloc[:, 5].astype(str) == st.session_state.get('cliente_f'))]
                if not ja_env.empty: st.write(f":red[**Animal já enviado anteriormente.**]"); bloqueado = True
            
            dna_sel = st.selectbox("ID_DNA*", options=[""] + sorted(df_base[df_base['Brinco'].astype(str)==st.session_state.get(f"br_{rk}")].iloc[:,0].unique().tolist()) if st.session_state.get(f"br_{rk}") else [""], key=f"dna_{rk}", on_change=atualizar_dados_animal)
            st.text_input("Cliente", value=st.session_state.get('cliente_f', ''), disabled=True)
        with col2:
            st.subheader("Detalhes")
            st.text_input("Solicitante", value=st.session_state.usuario_nome, disabled=True)
            motivo_sel = st.selectbox("Motivo*", options=[""] + obter_todos_motivos(), key=f"mot_{rk}")
            st.number_input("Idade (Dias)", value=st.session_state.get('idade_f', 0), disabled=True)
        
        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            foto = st.file_uploader("Foto", type=['png', 'jpg', 'jpeg'], key=f"foto_{rk}")
            add_prog = st.selectbox("Adicionar animal na programação?*", ["", "Sim", "Não"], key=f"prog_{rk}")
        with c4:
            obs = st.text_area("Observações*", key=f"obs_{rk}")
            tipo_r = st.selectbox("Tipo*", options=["", "Parcial", "Total"], key=f"tipo_{rk}")
        
        if st.button("Salvar Solicitação", disabled=bloqueado):
            ws_repo.append_row([str(dna_sel), str(brinco_sel), date.today().strftime("%d/%m/%Y"), st.session_state.get('entrega_f',''), st.session_state.get('cliente_f',''), st.session_state.usuario_nome, motivo_sel, str(st.session_state.get('idade_f',0)), (foto.name if foto else ""), obs, add_prog, tipo_r, "Não", "PENDENTE", st.session_state.get('cnpj_f','')])
            st.success("✅ Salvo!"); time.sleep(1); st.session_state.reset_trigger += 1; st.rerun()

        st.divider(); st.subheader("📋 Histórico")
        if not df_repo.empty:
            df_hist = df_repo.copy()
            # REGRA: Admin vê tudo, user vê só o dele
            if st.session_state.usuario_nivel != 'admin':
                df_hist = df_hist[df_hist.iloc[:, 5] == st.session_state.usuario_nome]
            st.dataframe(df_hist.iloc[::-1], use_container_width=True, height=400)

    elif menu == "Aprovação (Diretor)":
        st.title("Painel de Aprovação")
        pwd = st.text_input("Senha Diretor", type="password")
        if pwd == "dna123":
            df_ap, ws_ap = carregar_aba_segura("Relatorio_Reposicoes")
            pend = df_ap[df_ap.iloc[:, 13] == "PENDENTE"].copy()
            if not pend.empty:
                pend.insert(0, "Selecionar", False)
                edit_ap = st.data_editor(pend.iloc[::-1], use_container_width=True, hide_index=True)
                if st.button("✅ APROVAR SELECIONADOS"):
                    for _, r in edit_ap[edit_ap["Selecionar"] == True].iterrows():
                        idx = df_ap[(df_ap.iloc[:,1].astype(str)==str(r.iloc[2])) & (df_ap.iloc[:,0].astype(str)==str(r.iloc[1]))].index[0]
                        ws_ap.update_cell(idx + 2, 14, "APROVADO")
                    st.rerun()

    elif menu == "Status de Envios":
        st.title("🚚 Status")
        df_s, ws_s = carregar_aba_segura("Relatorio_Reposicoes")
        df_env, _ = carregar_aba_segura("Rep enviadas")
        if not df_s.empty:
            # REGRA: Admin vê tudo, user vê só o dele
            if st.session_state.usuario_nivel != 'admin':
                df_s = df_s[df_s.iloc[:, 5] == st.session_state.usuario_nome]
            
            # ATUALIZAÇÃO AUTOMÁTICA DO STATUS "SIM"
            if not df_env.empty:
                for idx, row in df_s.iterrows():
                    if str(row.iloc[1]) in df_env.iloc[:, 15].astype(str).values and row.iloc[12] != "Sim":
                        ws_s.update_cell(idx + 2, 13, "Sim"); st.rerun()

            df_v = df_s.copy(); df_v.insert(0, "Selecionar", False)
            edit_v = st.data_editor(df_v.iloc[::-1], use_container_width=True, hide_index=True)
            if st.button("Gerar PDF Selecionados"):
                list_pdf = []
                for _, r in edit_v[edit_v["Selecionar"] == True].iterrows():
                    list_pdf.append({'DNA_ID': r.iloc[1], 'Brinco': r.iloc[2], 'Data': r.iloc[3], 'Cliente': r.iloc[5], 'Motivo': r.iloc[7], 'Tipo_repo': r.iloc[12], 'Status': r.iloc[14], 'CNPJ': r.iloc[15] if len(r)>15 else "N/A"})
                pdf_bytes = gerar_pdf_multi_reposicao(list_pdf)
                st.download_button("Baixar PDF", data=pdf_bytes, file_name="Relatorio_DNA.pdf", mime="application/pdf")
    st.caption("DNA América do Sul - v7.1")
