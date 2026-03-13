import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import time
from fpdf import FPDF
import io
import unicodedata

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

# --- SISTEMA DE LOGIN (BASEADO NA IMAGEM 68a51c) ---
def sistema_login():
    if 'logado' not in st.session_state: st.session_state.logado = False
    
    if not st.session_state.logado:
        aba_login, aba_cad = st.tabs(["Acessar Conta", "Criar Nova Conta"])
        
        with aba_login:
            email = st.text_input("E-mail", key="l_email")
            senha = st.text_input("Senha", type="password", key="l_senha")
            if st.button("Entrar"):
                df_u, _ = carregar_aba_segura("Usuarios")
                user = df_u[(df_u['email'] == email) & (df_u['senha'] == senha)]
                if not user.empty:
                    st.session_state.logado = True
                    st.session_state.usuario = user.iloc[0]['nome']
                    st.session_state.nivel = user.iloc[0]['nivel']
                    st.rerun()
                else: st.error("Usuário ou senha incorretos")
        
        with aba_cad:
            n_nome = st.text_input("Nome Completo")
            n_email = st.text_input("E-mail para acesso")
            n_senha = st.text_input("Crie uma Senha", type="password")
            if st.button("Cadastrar"):
                _, ws_u = carregar_aba_segura("Usuarios")
                ws_u.append_row([n_email, n_senha, n_nome, "user"])
                st.success("Cadastro realizado! Acesse a aba Login.")
        st.stop()

# --- FUNÇÕES DE PDF E REGRAS (MANTIDAS) ---
class PDF(FPDF):
    def header(self):
        try: self.image('DNA_white-1024x576-1.png', 10, 8, 30)
        except: pass
        self.set_font('Arial', 'B', 12); self.cell(0, 10, limpar_texto('Relatorio de Reposicao de Animais'), 0, 1, 'R'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 7); self.cell(0, 10, limpar_texto(f'DNA South America - Pagina {self.page_no()}'), 0, 0, 'C')

def gerar_pdf_multi_reposicao(lista_dados):
    pdf = PDF(); pdf.add_page()
    for dados in lista_dados:
        if pdf.get_y() > 240: pdf.add_page()
        pdf.set_font("Arial", 'B', 9); pdf.cell(0, 7, limpar_texto(f"REPOSICAO: {dados['Brinco']} - CLIENTE: {dados['Cliente']}"), 1, 1, 'L')
        pdf.set_font("Arial", '', 8)
        pdf.cell(25, 6, "Cliente:"); pdf.cell(70, 6, limpar_texto(dados['Cliente']))
        pdf.cell(25, 6, "CNPJ:"); pdf.cell(0, 6, limpar_texto(dados['CNPJ']), 0, 1)
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

def obter_todos_motivos(): return sorted(["Acordo Comercial", "NSA", "Morte/Fratura", "Prolapso", "Hérnia", "Locomotor/Aprumo", "Problema de Casco", "Anestro", "Vulva Infantil"])

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
            try: v_idade = str(r.get('Idade', '0')).strip().replace(',', '.'); st.session_state.idade_f = int(float(v_idade))
            except: st.session_state.idade_f = 0
            st.session_state.lin_f = r.get('Linhagem', ''); st.session_state.sex_f = r.get('Sexo_do_Animal', '')
            nf_raw = str(r.get('Data_NF', '')); st.session_state.entrega_f = nf_raw
            try: dt_e = datetime.strptime(nf_raw, "%d/%m/%Y").date(); st.session_state.dias_f = (date.today() - dt_e).days
            except: st.session_state.dias_f = 9999

# --- INÍCIO DO PROGRAMA ---
if sh:
    sistema_login() # ACIONA O LOGIN
    
    st.sidebar.write(f"Usuário: **{st.session_state.usuario}**")
    menu = st.sidebar.radio("Navegação", ["Cadastrar Reposição", "Aprovação (Diretor)", "Status de Envios"])
    if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

    if menu == "Cadastrar Reposição":
        st.title("Pedidos de Reposição")
        if 'reset_trigger' not in st.session_state: st.session_state.reset_trigger = 0
        df_base, _ = carregar_aba_segura("Base de vendidos")
        st.session_state.df_base = df_base
        df_repo, ws_repo = carregar_aba_segura("Relatorio_Reposicoes")
        df_enviados, _ = carregar_aba_segura("Rep enviadas")
        rk = st.session_state.reset_trigger
        
        col1, col2 = st.columns(2); bloqueado = False
        with col1:
            st.subheader("Identificação")
            lista_brincos = [""] + sorted(df_base['Brinco'].unique().astype(str).tolist())
            brinco_sel = st.selectbox("Brinco*", options=lista_brincos, key=f"br_{rk}", on_change=atualizar_dados_animal)
            # BLOQUEIO: Não deixa cadastrar se já foi enviado
            if brinco_sel and not df_enviados.empty:
                ja_env = df_enviados[(df_enviados.iloc[:, 15].astype(str) == str(brinco_sel)) & (df_enviados.iloc[:, 5].astype(str) == st.session_state.get('cliente_f'))]
                if not ja_env.empty: st.write(f":red[**Reposição deste animal já foi cadastrada anteriormente**]"); bloqueado = True
            
            dna_sel = st.selectbox("ID_DNA*", options=[""] + sorted(df_base[df_base['Brinco'].astype(str)==st.session_state.get(f"br_{rk}")].iloc[:,0].unique().tolist()) if st.session_state.get(f"br_{rk}") else [""], key=f"dna_{rk}", on_change=atualizar_dados_animal)
            st.text_input("Cliente", value=st.session_state.get('cliente_f', ''), disabled=True)
            st.text_input("CNPJ", value=st.session_state.get('cnpj_f', ''), disabled=True)
        
        with col2:
            st.subheader("Detalhes")
            st.text_input("Solicitante", value=st.session_state.usuario, disabled=True)
            motivo_sel = st.selectbox("Motivo*", options=[""] + obter_todos_motivos(), key=f"mot_{rk}")
            st.number_input("Idade (Dias)", value=st.session_state.get('idade_f', 0), disabled=True)
            tipo_r = st.selectbox("Tipo*", options=["", "Parcial", "Total"], key=f"tipo_{rk}")
            obs = st.text_area("Observações*", key=f"obs_{rk}")

        if st.button("Salvar Solicitação", disabled=bloqueado):
            if not brinco_sel or not dna_sel: st.warning("⚠️ Preencha os obrigatórios!")
            else:
                ws_repo.append_row([str(dna_sel), str(brinco_sel), date.today().strftime("%d/%m/%Y"), st.session_state.get('entrega_f',''), st.session_state.get('cliente_f',''), st.session_state.usuario, motivo_sel, str(st.session_state.get('idade_f',0)), "", obs, "", tipo_r, "Não", "PENDENTE", st.session_state.get('cnpj_f','')])
                st.success("✅ Salvo!"); time.sleep(1); st.session_state.reset_trigger += 1; st.rerun()

        # FILTRO DE VISIBILIDADE: Usuário comum vê apenas as dele
        st.divider(); st.subheader("📋 Histórico")
        if not df_repo.empty:
            df_hist = df_repo.copy()
            if st.session_state.nivel != "admin":
                df_hist = df_hist[df_hist.iloc[:, 5] == st.session_state.usuario]
            st.dataframe(df_hist.iloc[::-1], use_container_width=True, height=300)

    elif menu == "Aprovação (Diretor)":
        st.title("Painel de Aprovação")
        pwd = st.text_input("Senha", type="password")
        if pwd == "dna123":
            df_ap, ws_ap = carregar_aba_segura("Relatorio_Reposicoes")
            if not df_ap.empty:
                pend = df_ap[df_ap.iloc[:, 13] == "PENDENTE"].copy()
                if pend.empty: st.success("Nada pendente.")
                else:
                    pend.insert(0, "Selecionar", False)
                    edit_ap = st.data_editor(pend.iloc[::-1], column_config={"Selecionar": st.column_config.CheckboxColumn(required=True)}, disabled=[c for c in pend.columns if c != "Selecionar"], use_container_width=True, hide_index=True)
                    sel_ap = edit_ap[edit_ap["Selecionar"] == True]
                    if not sel_ap.empty:
                        if st.button("✅ APROVAR SELECIONADOS"):
                            for _, r in sel_ap.iterrows():
                                idx = df_ap[(df_ap.iloc[:,1].astype(str)==str(r.iloc[2])) & (df_ap.iloc[:,0].astype(str)==str(r.iloc[1]))].index[0]
                                ws_ap.update_cell(idx + 2, 14, "APROVADO")
                            st.rerun()

    elif menu == "Status de Envios":
        st.title("🚚 Status")
        df_s, ws_s = carregar_aba_segura("Relatorio_Reposicoes")
        df_env, _ = carregar_aba_segura("Rep enviadas")
        
        if not df_s.empty:
            # FILTRO POR NÍVEL: Admin vê tudo, User vê apenas as dele
            if st.session_state.nivel != "admin":
                df_s = df_s[df_s.iloc[:, 5] == st.session_state.usuario]
            
            # ATUALIZAÇÃO AUTOMÁTICA DE "CONTA COMO REP ENVIADA"
            if not df_env.empty:
                for idx, row in df_s.iterrows():
                    # Coluna 1 é Brinco, Coluna 12 é o status "Não/Sim"
                    brinco_v = str(row.iloc[1])
                    if brinco_v in df_env.iloc[:, 15].astype(str).values:
                        if row.iloc[12] != "Sim":
                            ws_s.update_cell(idx + 2, 13, "Sim")
                            st.rerun()

            st.dataframe(df_s.iloc[::-1], use_container_width=True)
            
    st.caption("DNA América do Sul - v7.1")
