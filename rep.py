import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import time
from fpdf import FPDF
import io
import unicodedata
import extra_streamlit_components as stx

# --- 1. PREVENIR HIBERNAÇÃO ---
if st.query_params.get("ping") == "true":
    st.write("Sistema Online")
    st.stop()

# --- 2. FUNÇÃO AUXILIAR PDF ---
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).replace("⚠️", "!").replace("✅", "OK").replace("❌", "X")
    return "".join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn').replace('ç', 'c').replace('Ç', 'C')

# 3. Configuração da Página
st.set_page_config(page_title="DNA South America - Gestão de Reposição", layout="wide")

# 4. Conexão Segura
@st.cache_resource
def iniciar_conexao():
    for tentativa in range(3):
        try:
            info = st.secrets["minha_nova_conexao"]
            client = gspread.service_account_from_dict(info)
            # Chave da planilha de Reposição
            sh = client.open_by_key("1ZciM1-ym--0IvGHvJ-xy1lZCki7hbRxDgIOgly1STCQ")
            return sh
        except Exception as e:
            if tentativa == 2:
                st.error(f"⚠️ Erro de Conexão: {e}")
                return None
            time.sleep(1)

sh = iniciar_conexao()

# --- GERENCIADOR DE COOKIES ---
cookie_manager = stx.CookieManager()

# --- FUNÇÃO DE AUXÍLIO PARA LER PLANILHA ---
def ler_planilha_seguro(aba):
    try:
        data = aba.get_all_values()
        if not data or len(data) < 2: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    except: return pd.DataFrame()

# --- LÓGICA DE LOGIN E PERSISTÊNCIA ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    time.sleep(0.6) # Tempo para ler cookies
    saved_email = cookie_manager.get('dna_user_email')
    saved_pass = cookie_manager.get('dna_user_pass')
    
    if saved_email and saved_pass:
        try:
            aba_u = sh.worksheet("Usuarios")
            df_u = ler_planilha_seguro(aba_u)
            user_match = df_u[(df_u['email'].str.lower() == str(saved_email).lower()) & (df_u['senha'].astype(str) == str(saved_pass))]
            if not user_match.empty:
                st.session_state.autenticado = True
                st.session_state.user_email = saved_email
                st.session_state.user_nome = user_match.iloc[0]['nome']
                st.session_state.user_nivel = user_match.iloc[0].get('nivel', 'Vendedor')
                st.rerun()
        except: pass

if not st.session_state.autenticado:
    st.title("DNA South America - Login")
    aba_login, aba_registro = st.tabs(["Acessar Conta", "Criar Nova Conta"])
    
    with aba_login:
        with st.form("form_login"):
            email_input = st.text_input("E-mail").strip().lower()
            senha_input = st.text_input("Senha", type="password").strip()
            lembrar = st.checkbox("Manter conectado", value=True)
            if st.form_submit_button("Entrar"):
                try:
                    aba_users = sh.worksheet("Usuarios")
                    df_users = ler_planilha_seguro(aba_users)
                    user_match = df_users[(df_users['email'].str.lower() == email_input) & (df_users['senha'].astype(str) == senha_input)]
                    if not user_match.empty:
                        st.session_state.autenticado = True
                        st.session_state.user_email = email_input
                        st.session_state.user_nome = user_match.iloc[0]['nome']
                        st.session_state.user_nivel = user_match.iloc[0].get('nivel', 'Vendedor')
                        if lembrar:
                            cookie_manager.set('dna_user_email', email_input, expires_at=datetime.now() + pd.Timedelta(days=30))
                            cookie_manager.set('dna_user_pass', senha_input, expires_at=datetime.now() + pd.Timedelta(days=30))
                        st.rerun()
                    else: st.error("🚫 E-mail ou senha incorretos.")
                except Exception as e: st.error(f"Erro ao acessar base: {e}")

    with aba_registro:
        st.subheader("📝 Cadastre seu usuário")
        with st.form("form_registro"):
            novo_nome = st.text_input("Nome Completo")
            novo_email = st.text_input("E-mail corporativo").strip().lower()
            nova_senha = st.text_input("Defina uma Senha", type="password").strip()
            confirmar_senha = st.text_input("Confirme a Senha", type="password").strip()
            if st.form_submit_button("Registrar"):
                if not novo_nome or not novo_email or not nova_senha: st.warning("Preencha tudo.")
                elif nova_senha != confirmar_senha: st.error("As senhas não coincidem.")
                else:
                    try:
                        aba_users = sh.worksheet("Usuarios")
                        aba_users.append_row([novo_email, nova_senha, novo_nome, "Vendedor"])
                        st.success("✅ Conta criada! Vá para a aba Login.")
                    except Exception as e: st.error(f"Erro ao registrar: {e}")
    st.stop()

# --- SISTEMA APÓS LOGIN ---
class PDF(FPDF):
    def header(self):
        try: self.image('DNA_white-1024x576-1.png', 10, 8, 30)
        except: pass
        self.set_font('Arial', 'B', 12); self.cell(0, 10, limpar_texto('Relatorio de Reposicao'), 0, 1, 'R'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 7); self.cell(0, 10, limpar_texto(f'DNA South America - Página {self.page_no()}'), 0, 0, 'C')

def gerar_pdf_multi_reposicao(lista_dados):
    lista_dados = sorted(lista_dados, key=lambda x: x['Cliente'].upper())
    pdf = PDF(); pdf.add_page()
    for dados in lista_dados:
        if pdf.get_y() > 240: pdf.add_page()
        pdf.set_font("Arial", 'B', 9); pdf.cell(0, 7, limpar_texto(f"REPOSICAO: {dados['Brinco']} - CLIENTE: {dados['Cliente']}"), 1, 1, 'L')
        pdf.set_font("Arial", '', 8)
        pdf.cell(25, 6, "Cliente:"); pdf.cell(70, 6, limpar_texto(dados['Cliente']))
        pdf.cell(25, 6, "CNPJ:"); pdf.cell(0, 6, limpar_texto(dados['CNPJ']), 0, 1)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def obter_todos_motivos(): return sorted(["Acordo Comercial", "NSA", "Morte/Fratura", "Prolapso", "Hérnia", "Locomotor/Aprumo", "Problema de Casco", "Anestro", "Vulva Infantil"])

def atualizar_dados_animal():
    rk = st.session_state.reset_trigger
    brinco = st.session_state.get(f"br_{rk}"); dna = st.session_state.get(f"dna_{rk}")
    if brinco and dna:
        df_b = st.session_state.df_base
        c_dna = next((c for c in df_b.columns if 'DNA' in c.upper()), df_b.columns[0])
        animal = df_b[(df_b['Brinco'].astype(str) == str(brinco)) & (df_b[c_dna].astype(str) == str(dna))]
        if not animal.empty:
            r = animal.iloc[0]
            st.session_state.cliente_f = str(r.get('Nome_Cliente', r.get('Cliente', '')))
            st.session_state.cnpj_f = str(r.get('CNPJ', r.get('CNPJ_CPF', '')))
            try: v_idade = str(r.get('Idade', '0')).strip().replace(',', '.'); st.session_state.idade_f = int(float(v_idade))
            except: st.session_state.idade_f = 0
            st.session_state.entrega_f = str(r.get('Data_NF', ''))

if sh:
    st.sidebar.write(f"👤 **{st.session_state.user_nome}**")
    if st.sidebar.button("Sair"):
        cookie_manager.delete('dna_user_email')
        cookie_manager.delete('dna_user_pass')
        st.session_state.autenticado = False
        st.rerun()

    menu = st.sidebar.radio("Navegação", ["Cadastrar Reposição", "Aprovação (Diretor)", "Status de Envios"])

    if menu == "Cadastrar Reposição":
        st.title("Pedidos de Reposição")
        if 'reset_trigger' not in st.session_state: st.session_state.reset_trigger = 0
        df_base = ler_planilha_seguro(sh.worksheet("Base de vendidos")); st.session_state.df_base = df_base
        df_repo, ws_repo = ler_planilha_seguro(sh.worksheet("Relatorio_Reposicoes")), sh.worksheet("Relatorio_Reposicoes")
        df_enviados = ler_planilha_seguro(sh.worksheet("Rep enviadas"))
        rk = st.session_state.reset_trigger
        
        col1, col2 = st.columns(2); bloqueado = False
        with col1:
            brinco_sel = st.selectbox("Brinco*", options=[""] + sorted(df_base['Brinco'].unique().astype(str).tolist()), key=f"br_{rk}", on_change=atualizar_dados_animal)
            dna_sel = st.selectbox("ID_DNA*", options=[""] + sorted(df_base[df_base['Brinco'].astype(str)==st.session_state.get(f"br_{rk}")].iloc[:,0].unique().tolist()) if st.session_state.get(f"br_{rk}") else [""], key=f"dna_{rk}", on_change=atualizar_dados_animal)
            st.text_input("Cliente", value=st.session_state.get('cliente_f', ''), disabled=True)
        with col2:
            st.text_input("Solicitante", value=st.session_state.user_nome, disabled=True)
            motivo_sel = st.selectbox("Motivo*", options=[""] + obter_todos_motivos(), key=f"mot_{rk}")
            tipo_r = st.selectbox("Tipo*", options=["", "Parcial", "Total"], key=f"tipo_{rk}")
        
        if st.button("Salvar Solicitação", disabled=bloqueado):
            ws_repo.append_row([str(dna_sel), str(brinco_sel), date.today().strftime("%d/%m/%Y"), st.session_state.get('entrega_f',''), st.session_state.get('cliente_f',''), st.session_state.user_nome, motivo_sel, str(st.session_state.get('idade_f',0)), "", "", "Não", tipo_r, "Não", "PENDENTE", st.session_state.get('cnpj_f','')])
            st.success("✅ Salvo!"); time.sleep(1); st.session_state.reset_trigger += 1; st.rerun()

        st.divider(); st.subheader("📋 Meus Lançamentos")
        if not df_repo.empty:
            df_hist = df_repo.copy()
            if st.session_state.user_nivel != 'Admin':
                df_hist = df_hist[df_hist.iloc[:, 5] == st.session_state.user_nome]
            st.dataframe(df_hist.iloc[::-1], use_container_width=True, height=300)

    elif menu == "Aprovação (Diretor)":
        st.title("Painel de Aprovação")
        pwd = st.text_input("Senha Diretor", type="password")
        if pwd == "dna123":
            df_ap, ws_ap = ler_planilha_seguro(sh.worksheet("Relatorio_Reposicoes")), sh.worksheet("Relatorio_Reposicoes")
            pend = df_ap[df_ap.iloc[:, 13] == "PENDENTE"].copy()
            if not pend.empty:
                pend.insert(0, "Selecionar", False)
                edit_ap = st.data_editor(pend, use_container_width=True, hide_index=True)
                if st.button("✅ APROVAR SELECIONADOS"):
                    for _, r in edit_ap[edit_ap["Selecionar"] == True].iterrows():
                        idx = df_ap[(df_ap.iloc[:,1].astype(str)==str(r.iloc[2])) & (df_ap.iloc[:,0].astype(str)==str(r.iloc[1]))].index[0]
                        ws_ap.update_cell(idx + 2, 14, "APROVADO")
                    st.rerun()

    elif menu == "Status de Envios":
        st.title("🚚 Status")
        df_s, ws_s = ler_planilha_seguro(sh.worksheet("Relatorio_Reposicoes")), sh.worksheet("Relatorio_Reposicoes")
        df_env = ler_planilha_seguro(sh.worksheet("Rep enviadas"))
        if not df_s.empty:
            if st.session_state.user_nivel != 'Admin':
                df_s = df_s[df_s.iloc[:, 5] == st.session_state.user_nome]
            
            # ATUALIZAÇÃO AUTOMÁTICA DO STATUS "SIM"
            if not df_env.empty:
                for idx, row in df_s.iterrows():
                    if str(row.iloc[1]) in df_env.iloc[:, 15].astype(str).values and row.iloc[12] != "Sim":
                        ws_s.update_cell(idx + 2, 13, "Sim")
                        st.rerun()
            st.dataframe(df_s.iloc[::-1], use_container_width=True)
    st.caption("DNA América do Sul - v7.6")
