import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date

# 1. Configuração da Página
st.set_page_config(page_title="DNA South America - Gestão de Pedidos", layout="wide")

# 2. Conexão com Google Sheets
@st.cache_resource
def iniciar_conexao():
    try:
        info = st.secrets["minha_nova_conexao"]
        client = gspread.service_account_from_dict(info)
        sh = client.open_by_key("19Hxt0HwrHeEZm-OFv7M9NAQgZjoHdmBpGBSrSHofNbk")
        return sh
    except Exception as e:
        st.error(f"⚠️ Erro de Conexão: {e}")
        return None

sh = iniciar_conexao()

# --- FUNÇÃO DE AUXÍLIO PARA LER PLANILHA SEGURA ---
def ler_planilha_seguro(aba):
    data = aba.get_all_values()
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df.loc[:, ~df.columns.str.contains('^$')]
    return df

# --- FUNÇÃO DE LOGIN E REGISTRO ---
def realizar_login(sh):
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.title("DNA South America - Pedidos de Animais")
        aba_login, aba_registro = st.tabs(["Acessar Conta", "Criar Nova Conta"])
        with aba_login:
            with st.form("form_login"):
                email_input = st.text_input("E-mail").strip().lower()
                senha_input = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    try:
                        aba_users = sh.worksheet("Usuarios")
                        df_users = ler_planilha_seguro(aba_users)
                        df_users.columns = [str(c).strip().lower() for c in df_users.columns]
                        col_email = next((c for c in df_users.columns if 'mail' in c), None)
                        user_match = df_users[(df_users[col_email].str.lower() == email_input) & (df_users['senha'].astype(str) == senha_input)]
                        if not user_match.empty:
                            st.session_state.autenticado = True
                            st.session_state.user_email = email_input
                            st.session_state.user_nome = user_match.iloc[0]['nome']
                            st.session_state.user_nivel = user_match.iloc[0].get('nivel', 'Vendedor')
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
                if st.form_submit_button("Registrar e Acessar"):
                    if not novo_nome or not novo_email or not nova_senha: st.warning("Preencha todos os campos.")
                    elif nova_senha != confirmar_senha: st.error("As senhas não coincidem.")
                    else:
                        try:
                            aba_users = sh.worksheet("Usuarios")
                            aba_users.append_row([novo_nome, novo_email, nova_senha, "Vendedor"])
                            st.success("✅ Conta criada! Faça o login.")
                        except Exception as e: st.error(f"Erro ao registrar: {e}")
        return False
    return True

# --- LISTAS DE OPÇÕES ---
opcoes_desc = ["Matriz L600 Núcleo 100kg", "Matriz L600 Núcleo 110kg", "Matriz L600 Núcleo 20kg", "Matriz L600 Núcleo 30kg", "Matriz L600 Núcleo 40kg", "Matriz L600 Núcleo 50kg", "Matriz L600 Núcleo 60kg", "Matriz L600 Núcleo 70kg", "Matriz L600 Núcleo 80kg", "Matriz L600 Núcleo 90kg", "Matriz L241", "Matriz L241 100kg", "Matriz L241 110kg", "Matriz L241 20kg", "Matriz L241 30kg", "Matriz L241 40kg", "Matriz L241 50kg", "Matriz L241 60kg", "Matriz L241 70kg", "Matriz L241 80kg", "Matriz L241 90kg", "Matriz L241 Retenção", "Matriz Avó L400 100kg", "Matriz Avó L400 110kg", "Matriz Avó L400 20kg", "Matriz Avó L400 30kg", "Matriz Avó L400 40kg", "Matriz Avó L400 50kg", "Matriz Avó L400 60kg", "Matriz Avó L400 70kg", "Matriz Avó L400 80kg", "Matriz Avó L400 90kg", "Matriz Avó L400 Off Test", "Matriz Avó L400 Retenção", "Matriz Bisavó L400", "Matriz Bisavó L400 100kg", "Matriz Bisavó L400 110kg", "Matriz Bisavó L400 20kg", "Matriz Bisavó L400 30kg", "Matriz Bisavó L400 40kg", "Matriz Bisavó L400 50kg", "Matriz Bisavó L400 60kg", "Matriz Bisavó L400 70kg", "Matriz Bisavó L400 80kg", "Matriz Bisavó L400 90kg", "Matriz Bisavó L400 Retenção", "Matriz Avó L200", "Matriz Avó L200 100kg", "Matriz Avó L200 110kg", "Matriz Avó L200 20kg", "Matriz Avó L200 30kg", "Matriz Avó L200 40kg", "Matriz Avó L200 50kg", "Matriz Avó L200 60kg", "Matriz Avó L200 70kg", "Matriz Avó L200 80kg", "Matriz Avó L200 90kg", "Matriz Avó L200 Off Test", "Matriz Avó L200 Retenção", "Matriz Bisavó L200", "Matriz Bisavó L200 100kg", "Matriz Bisavó L200 110kg", "Matriz Bisavó L200 20kg", "Matriz Bisavó L200 30kg", "Matriz Bisavó L200 40kg", "Matriz Bisavó L200 50kg", "Matriz Bisavó L200 60kg", "Matriz Bisavó L200 70kg", "Matriz Bisavó L200 80kg", "Matriz Bisavó L200 90kg", "Matriz Bisavó L200 Retenção", "Reprodutor L600 Núcleo", "Reprodutor Terminador L600", "Reprodutor Terminador L600 Deca 1", "Reprodutor Terminador L600 Deca 2", "Reprodutor Terminador L600 Deca 3", "Reprodutor Avô L400", "Reprodutor Núcleo L400", "Reprodutor Avô L200", "Reprodutor Núcleo L200", "Reprodutor L600/USA", "Reprodutor L400/USA", "Reprodutor L200/USA", "Reprodutor Terminador Duroc Núcleo", "Reprodutor Rufiao", "Matriz L241 Prime", "Matriz L241 100kg Prime", "Matriz L241 110kg Prime", "Matriz L241 20kg Prime", "Matriz L241 30kg Prime", "Matriz L241 40kg Prime", "Matriz L241 50kg Prime", "Matriz L241 60kg Prime", "Matriz L241 70kg Prime", "Matriz L241 80kg Prime", "Matriz L241 90kg Prime"]
opcoes_modalidade = ["VENDA DIRETA", "ALUGUEL", "RETENÇÃO F1", "RETENÇÃO AVÓ"]
opcoes_prazo_unificado = sorted(list(set(["Á VISTA", "10, 15", "10, 15, 30", "10, 15, 30, 45", "10, 30", "10, 30, 45", "10, 30, 45, 60", "10, 30, 45, 60, 90", "10,30, 60", "10, 30, 60, 90", "30", "15", "45", "60", "90", "30, 45, 60", "30, 45", "30, 45, 60, 75", "30, 60, 90", "30, 60", "30, 60, 90, 120", "30,60,90,120, 150", "30, 60, 90, 120, 150, 180", "30, 60, 90, 120, 150, 180, 210", "30,60,90, 120, 150, 180, 210, 240", "30,60,90, 120, 150, 180, 210, 240, 270", "30,60,90, 120, 150, 180, 210, 240, 270, 300", "30,60,90, 120, 150, 180, 210, 240, 270, 300, 330", "30,60,90, 120, 150, 180, 210, 240, 270, 300, 330, 360", "OUTRO (ESPECIFICAR NA OBSERVAÇÃO)"])))
opcoes_indexador = ["ASEMG", "APCS", "JOX MÉDIO/SP", "ACRISMAT", "CEPEA/PR", "CEPEA/SC", "CEPEA/RS", "CEPEA/SP", "CEPEA/MG", "DFSUIN"]
opcoes_sim_nao = ["Sim", "Não"]

column_config_padrao = {
    "Descrição": st.column_config.SelectboxColumn("Descrição", options=opcoes_desc, required=True),
    "Modalidade": st.column_config.SelectboxColumn("Modalidade", options=opcoes_modalidade),
    "Prazo de Pagamento": st.column_config.SelectboxColumn("Prazo de Pagamento", options=opcoes_prazo_unificado),
    "Indexador": st.column_config.SelectboxColumn("Indexador", options=opcoes_indexador),
    "Cobrar Frete": st.column_config.SelectboxColumn("Cobrar Frete", options=opcoes_sim_nao),
    "Cobrar Registro Genealógico": st.column_config.SelectboxColumn("Cobrar Registro Genealógico", options=opcoes_sim_nao),
    "Data de entrega": st.column_config.DateColumn("Data de entrega", format="DD/MM/YYYY"),
    "Programado": st.column_config.CheckboxColumn("Programado", default=False)
}

# --- PROGRAMA PRINCIPAL ---
if sh:
    if realizar_login(sh):
        st.sidebar.write(f"👤 Usuário: **{st.session_state.user_nome}**")
        if st.sidebar.button("🔄 Atualizar Base de Dados"):
            st.cache_data.clear()
            st.rerun()
        if st.sidebar.button("Sair"):
            st.session_state.autenticado = False
            st.rerun()

        df_sap = ler_planilha_seguro(sh.worksheet("Base de clientes sap"))
        aba = st.sidebar.radio("Navegação", ["Novo Pedido", "Gerenciar Pedido", "Histórico de Vendas"])

        if aba == "Novo Pedido":
            st.subheader("Novo Pedido de Venda")
            lista_clientes = [""] + sorted(df_sap['Razão Social'].unique().tolist())
            cliente_sel = st.selectbox("Selecione o Cliente", lista_clientes)
            
            if cliente_sel != "":
                dados_cli = df_sap[df_sap['Razão Social'] == cliente_sel].iloc[0]
                with st.expander("📄 Detalhes do Cliente", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        in_cnpj = st.text_input("CNPJ/CPF", value=str(dados_cli.get('CPF_CNPJ', '')))
                        in_ie = st.text_input("I.E", value=str(dados_cli.get('I.E', '')))
                    with c2:
                        in_cid = st.text_input("Cidade", value=str(dados_cli.get('Cidade', '')))
                        in_est = st.text_input("Estado", value=str(dados_cli.get('Estado', '')))
                    with c3:
                        in_gta_cod = st.text_input("GTA - Código", value=str(dados_cli.get('GTA - Código do estabelecimento', '')))
                        in_gta_est = st.text_input("GTA - Estabelecimento", value=str(dados_cli.get('GTA - Estabelecimento', '')))

                with st.form("form_venda", clear_on_submit=True):
                    vendedor_final = st.text_input("Vendedor Responsável", value=st.session_state.user_nome, disabled=True)
                    data_ped = st.date_input("Data do Pedido", datetime.now())
                    
                    # Tabela conforme a necessidade do APP (Linhagem e USD removidos da interface)
                    df_vazio = pd.DataFrame(columns=["Descrição", "Modalidade", "Quantidade", "KG Total", "Preço Unitário R$", "Prêmio Genético", "Prazo de Pagamento", "Pagamento Fêmea Retirada KG", "Pagamento Fêmea Retirada R$", "Aluguel", "Indexador", "Cobrar Frete", "Cobrar Registro Genealógico", "Data de entrega", "Programado"])
                    tabela = st.data_editor(df_vazio, num_rows="dynamic", use_container_width=True, column_config=column_config_padrao, hide_index=True)
                    obs = st.text_area("Observações Adicionais")
                    
                    if st.form_submit_button("💾 SALVAR NOVO PEDIDO"):
                        if tabela.empty or not any(tabela['Descrição']): st.warning("⚠️ Adicione itens.")
                        else:
                            id_p = f"DNA-{datetime.now().strftime('%Y%m%d-%H%M')}"
                            agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            try:
                                aba_pedidos = sh.worksheet("Relatorio de pedidos")
                                for _, row in tabela.iterrows():
                                    if row['Descrição']:
                                        d_ent = row.get('Data de entrega')
                                        dt_s = d_ent.strftime("%d/%m/%Y") if pd.notnull(d_ent) and hasattr(d_ent, 'strftime') else ""
                                        
                                        # MONTAGEM EXATA CONFORME SEQUÊNCIA A até AC
                                        aba_pedidos.append_row([
                                            id_p, str(cliente_sel), st.session_state.user_nome, data_ped.strftime("%d/%m/%Y"), # A, B, C, D
                                            str(row[0]), # E: Descrição
                                            str(row[1]), # F: Modalidade
                                            str(row[2]), # G: Quantidade
                                            str(row[3]), # H: KG Total
                                            str(row[4]), # I: Preço Unitário
                                            str(row[5]), # J: Prêmio Genético
                                            str(row[6]), # K: Prazo de Pagamento
                                            str(row[7]), # L: Pagamento Fêmea KG
                                            str(row[8]), # M: Pagamento Fêmea R$
                                            str(row[9]), # N: Aluguel
                                            str(row[10]),# O: Indexador
                                            str(row[11]),# P: Cobrar Frete
                                            str(row[12]),# Q: Cobrar Registro
                                            dt_s,        # R: Data de entrega
                                            in_cid,      # S: Cidade
                                            in_est,      # T: Estado
                                            obs,         # U: Observação
                                            in_cnpj,     # V: GTA CNPJ
                                            in_ie,       # W: GTA IE
                                            in_gta_cod,  # X: GTA Código
                                            in_gta_est,  # Y: GTA Estabelecimento
                                            str(row[14]),# Z: Programado
                                            agora_str,   # AA: Ultima Modificacao
                                            "CRIADO NOVO",# AB: Status Registro
                                            st.session_state.user_email # AC: Alterado por
                                        ])
                                st.success(f"✅ Pedido {id_p} salvo!")
                                st.cache_data.clear()
                            except Exception as e: st.error(f"Erro ao salvar: {e}")

        elif aba == "Gerenciar Pedido":
            st.subheader("Gerenciar Pedido")
            id_busca = st.text_input("Digite o ID do Pedido").strip()
            if id_busca:
                try:
                    aba_p = sh.worksheet("Relatorio de pedidos")
                    df_total = ler_planilha_seguro(aba_p)
                    ped_comp = df_total[df_total['ID Pedido'] == id_busca].copy()
                    
                    if not ped_comp.empty:
                        orig = ped_comp.iloc[0].to_dict()
                        # Colunas que o usuário edita no APP
                        cols_edit = ["Descrição", "Modalidade", "Quantidade", "KG Total", "Preço Unitário R$", "Prêmio Genético", "Prazo de Pagamento", "Pagamento Fêmea Retirada KG", "Pagamento Fêmea Retirada R$", "Aluguel", "Indexador", "Cobrar Frete", "Cobrar Registro Genealógico", "Data de entrega", "Programado", "Observação"]
                        
                        ped_filtro = ped_comp[cols_edit].copy()
                        ped_filtro['Data de entrega'] = pd.to_datetime(ped_filtro['Data de entrega'], dayfirst=True, errors='coerce')
                        ped_filtro['Programado'] = ped_filtro['Programado'].apply(lambda x: True if str(x).upper() == "TRUE" else False)
                        
                        df_ed = st.data_editor(ped_filtro, num_rows="dynamic", use_container_width=True, column_config=column_config_padrao, hide_index=True)
                        
                        if st.button("🆙 ATUALIZAR PEDIDO"):
                            agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            cell_list = aba_p.findall(id_busca)
                            rows_indices = sorted(list(set([c.row for c in cell_list])), reverse=True)
                            for r in rows_indices: aba_p.delete_rows(r)
                            
                            novas_linhas = []
                            for _, r in df_ed.iterrows():
                                if r.get('Descrição'):
                                    d_ed = r.get('Data de entrega')
                                    dt_s = d_ed.strftime("%d/%m/%Y") if pd.notnull(d_ed) and hasattr(d_ed, 'strftime') else ""
                                    
                                    novas_linhas.append([
                                        id_busca, str(orig['Cliente']), str(orig['Vendedor']), str(orig['Data']),
                                        str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]), str(r[6]), str(r[7]), str(r[8]), str(r[9]), str(r[10]), str(r[11]), str(r[12]), dt_s, 
                                        str(orig.get('Cidade','')), str(orig.get('Estado','')), str(r[15]),
                                        str(orig.get('GTA - CPF/CNPJ','')), str(orig.get('GTA - IE','')), str(orig.get('GTA - Código do estabelecimento','')), str(orig.get('GTA - Estabelecimento','')),
                                        str(r[14]), agora_str, "ATUALIZADO", st.session_state.user_email
                                    ])
                            aba_p.append_rows(novas_linhas)
                            st.success(f"✅ Pedido {id_busca} atualizado!")
                            st.rerun()
                    else: st.warning("Não encontrado.")
                except Exception as e: st.error(f"Erro: {e}")

        elif aba == "Histórico de Vendas":
            st.subheader("Meus Registros")
            try:
                df_hist = ler_planilha_seguro(sh.worksheet("Relatorio de pedidos"))
                if st.session_state.user_nivel != "Admin":
                    df_hist = df_hist[df_hist['Vendedor'] == st.session_state.user_nome]
                st.dataframe(df_hist, use_container_width=True)
            except Exception as e: st.error(f"Erro: {e}")
