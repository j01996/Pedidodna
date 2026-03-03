import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import time
from fpdf import FPDF
import io

# 1. Configuração da Página
st.set_page_config(page_title="DNA - Gestão Comercial", layout="wide")

# 2. Conexão Segura
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

# --- CLASSE PDF (P&B, ORGANIZADO) ---
class PDF(FPDF):
    def header(self):
        try: self.image('DNA_white-1024x576-1.png', 10, 8, 30)
        except: pass
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0) # Preto e Branco
        self.cell(0, 10, 'Relatório de Reposição de Animais', 0, 1, 'R')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 10, f'DNA South America - Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_multi_reposicao(lista_dados):
    lista_dados = sorted(lista_dados, key=lambda x: x['Cliente'].upper())
    pdf = PDF()
    pdf.add_page()
    for i, dados in enumerate(lista_dados):
        if pdf.get_y() > 240: pdf.add_page()
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 7, f"REPOSIÇÃO: {dados['Brinco']} - CLIENTE: {dados['Cliente']}", 1, 1, 'L')
        pdf.set_font("Arial", '', 8)
        pdf.cell(25, 6, "Cliente:", 'L'); pdf.cell(70, 6, str(dados['Cliente']), 'R')
        pdf.cell(25, 6, "CNPJ:", 'L'); pdf.cell(0, 6, str(dados['CNPJ']), 'R', 1)
        pdf.cell(25, 6, "DNA ID:", 'L'); pdf.cell(70, 6, str(dados['DNA_ID']), 'R')
        pdf.cell(25, 6, "Brinco:", 'L'); pdf.cell(0, 6, str(dados['Brinco']), 'R', 1)
        pdf.cell(25, 6, "Motivo:", 'L'); pdf.cell(70, 6, str(dados['Motivo']), 'R')
        pdf.cell(25, 6, "Tipo Repo:", 'L'); pdf.cell(0, 6, str(dados['Tipo_repo']), 'R', 1)
        pdf.cell(25, 6, "Status:", 'LB'); pdf.cell(70, 6, str(dados['Status']), 'RB')
        pdf.cell(25, 6, "Data Sol.:", 'LB'); pdf.cell(0, 6, str(dados.get('Data', 'N/A')), 'RB', 1)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1')

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

# --- BUSCA INSTANTÂNEA ---
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
                ja_env = df_enviados[(df_enviados.iloc[:, 15].astype(str) == str(brinco_sel)) & (df_enviados.iloc[:, 5].astype(str) == st.session_state.get('cliente_f'))]
                if not ja_env.empty:
                    st.write(f":red[**Animal já enviado para este cliente anteriormente.**]"); bloqueado = True
            br_atual = st.session_state.get(f"br_{rk}")
            ids_dna = [""]
            if br_atual:
                c_dna = next((c for c in df_base.columns if 'DNA' in c.upper()), df_base.columns[0])
                ids_dna = [""] + sorted(df_base[df_base['Brinco'].astype(str)==br_atual][c_dna].unique().tolist())
            dna_sel = st.selectbox("ID_DNA*", options=ids_dna, key=f"dna_{rk}", on_change=atualizar_dados_animal)
            if brinco_sel and dna_sel and not df_repo.empty:
                ja_sol = df_repo[(df_repo.iloc[:, 1].astype(str) == str(brinco_sel)) & (df_repo.iloc[:, 0].astype(str) == str(dna_sel))]
                if not ja_sol.empty:
                    st.write(f":red[**Solicitação já existente. Status: {ja_sol.iloc[-1, 13]}**]"); bloqueado = True
            st.text_input("Cliente", value=st.session_state.get('cliente_f', ''), disabled=True)
            st.text_input("CNPJ", value=st.session_state.get('cnpj_f', ''), disabled=True)
        with col2:
            st.subheader("Detalhes")
            st.text_input("Entrega Original", value=st.session_state.get('entrega_f', ''), disabled=True)
            vendedor_sel = st.selectbox("Solicitante*", options=[""] + vendedores, key=f"sol_{rk}")
            
            # MOSTRA TODOS OS MOTIVOS SEMPRE
            motivos_lista = obter_todos_motivos()
            motivo_sel = st.selectbox("Motivo*", options=[""] + motivos_lista, key=f"mot_{rk}")
            
            # VALIDAÇÃO DO PRAZO (APENAS AVISO)
            if motivo_sel:
                dentro_prazo = validar_prazo_motivo(motivo_sel, st.session_state.get('sex_f',''), st.session_state.get('dias_f', 9999))
                if not dentro_prazo:
                    st.error(f"⚠️ O motivo '{motivo_sel}' está fora do prazo de garantia ({st.session_state.get('dias_f', 0)} dias após entrega).")
            
            st.number_input("Idade (Dias)", value=st.session_state.get('idade_f', 0), disabled=True)
        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            foto = st.file_uploader("Foto", type=['png', 'jpg', 'jpeg'], key=f"foto_{rk}")
            add_prog = st.selectbox("Adicionar animal na programação?*", ["", "Sim", "Não"], key=f"prog_{rk}")
        with c4:
            obs = st.text_area("Observações*", key=f"obs_{rk}")
            tipo_r = st.selectbox("Tipo*", options=["", "Parcialmente", "Total"], key=f"tipo_{rk}")
        if st.button("Salvar Solicitação", disabled=bloqueado):
            if not brinco_sel or not dna_sel or not vendedor_sel:
                st.warning("⚠️ Preencha os campos obrigatórios!")
            else:
                # SALVA O MOTIVO COM MARCAÇÃO SE ESTIVER FORA DO PRAZO
                motivo_final = motivo_sel
                if not validar_prazo_motivo(motivo_sel, st.session_state.get('sex_f',''), st.session_state.get('dias_f', 9999)):
                    motivo_final = f"⚠️ FORA DO PRAZO - {motivo_sel}"
                
                ws_repo.append_row([
                    str(dna_sel), str(brinco_sel), date.today().strftime("%d/%m/%Y"),
                    st.session_state.get('entrega_f',''), st.session_state.get('cliente_f',''),
                    vendedor_sel, motivo_final, str(st.session_state.get('idade_f',0)),
                    (foto.name if foto else ""), obs, add_prog, tipo_r, "Não", "PENDENTE", st.session_state.get('cnpj_f','')
                ])
                st.success("✅ Salvo!"); time.sleep(1); st.session_state.reset_trigger += 1; st.rerun()
        
        st.divider(); st.subheader("Últimos Lançamentos")
        filtro_nome = st.selectbox("Filtrar por Solicitante:", ["Todos"] + vendedores)
        filtro_brinco = st.text_input("Filtrar por Brinco:")
        if not df_repo.empty:
            df_hist = df_repo.copy()
            if filtro_nome != "Todos": df_hist = df_hist[df_hist.iloc[:, 5] == filtro_nome]
            if filtro_brinco: df_hist = df_hist[df_hist.iloc[:, 1].astype(str).str.contains(filtro_brinco)]
            exibicao = df_hist.iloc[::-1].head(10)
            st.dataframe(exibicao, use_container_width=True)
            id_para_excluir = st.selectbox("Excluir Reposição (Selecione o Brinco):", [""] + exibicao.iloc[:, 1].tolist())
            if id_para_excluir and st.button(f"Confirmar Exclusão de {id_para_excluir}"):
                dna_aux = exibicao[exibicao.iloc[:, 1] == id_para_excluir].iloc[0, 0]
                linhas = ws_repo.get_all_values()
                for idx, row in enumerate(linhas):
                    if idx == 0: continue
                    if str(row[1]) == str(id_para_excluir) and str(row[0]) == str(dna_aux):
                        ws_repo.delete_rows(idx + 1)
                        st.rerun()

    elif menu == "Aprovação (Diretor)":
        st.title("Painel de Aprovação")
        pwd = st.text_input("Senha", type="password")
        if pwd == "dna123":
            df_ap, ws_ap = carregar_aba_segura("Relatorio_Reposicoes")
            if not df_ap.empty:
                pend = df_ap[df_ap.iloc[:, 13] == "PENDENTE"].copy()
                if pend.empty: st.success("Nada pendente.")
                else:
                    st.subheader("Selecione os itens para aprovação em massa:")
                    pend.insert(0, "Selecionar", False)
                    edit_ap = st.data_editor(pend.iloc[::-1], column_config={"Selecionar": st.column_config.CheckboxColumn(required=True)}, disabled=[c for c in pend.columns if c != "Selecionar"], use_container_width=True, hide_index=True)
                    sel_ap = edit_ap[edit_ap["Selecionar"] == True]
                    if not sel_ap.empty:
                        c1, c2 = st.columns(2)
                        if c1.button(f"✅ APROVAR SELECIONADOS ({len(sel_ap)})", use_container_width=True):
                            for _, r in sel_ap.iterrows():
                                idx = df_ap[(df_ap.iloc[:,1].astype(str)==str(r.iloc[2])) & (df_ap.iloc[:,0].astype(str)==str(r.iloc[1]))].index[0]
                                ws_ap.update_cell(idx + 2, 14, "APROVADO")
                            st.success("Processado!"); time.sleep(1); st.rerun()
                        if c2.button(f"❌ RECUSAR SELECIONADOS ({len(sel_ap)})", use_container_width=True):
                            for _, r in sel_ap.iterrows():
                                idx = df_ap[(df_ap.iloc[:,1].astype(str)==str(r.iloc[2])) & (df_ap.iloc[:,0].astype(str)==str(r.iloc[1]))].index[0]
                                ws_ap.update_cell(idx + 2, 14, "REPROVADO")
                            st.warning("Processado!"); time.sleep(1); st.rerun()

    elif menu == "Status de Envios":
        st.title("🚚 Status e Exportação PDF")
        df_s, _ = carregar_aba_segura("Relatorio_Reposicoes")
        if not df_s.empty:
            df_v = df_s.copy(); df_v.insert(0, "Selecionar", False)
            edit_v = st.data_editor(df_v.iloc[::-1], column_config={"Selecionar": st.column_config.CheckboxColumn(required=True)}, disabled=[c for c in df_v.columns if c != "Selecionar"], use_container_width=True, hide_index=True)
            sel_v = edit_v[edit_v["Selecionar"] == True]
            if not sel_v.empty:
                if st.button("Gerar PDF Selecionados"):
                    list_pdf = []
                    for _, r in sel_v.iterrows():
                        list_pdf.append({
                            'DNA_ID': r.iloc[1], 'Brinco': r.iloc[2], 'Data': r.iloc[3], 
                            'Cliente': r.iloc[5], 'Motivo': r.iloc[7], 'Tipo_repo': r.iloc[12], 
                            'Status': r.iloc[14], 'CNPJ': r.iloc[15] if len(r)>15 else "N/A"
                        })
                    pdf_bytes = gerar_pdf_multi_reposicao(list_pdf)
                    st.download_button("Baixar PDF", data=pdf_bytes, file_name="Relatorio_DNA.pdf", mime="application/pdf")
    st.caption("DNA América do Sul - v6.3")
