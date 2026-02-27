import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

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

def ler_planilha_seguro(aba):
    data = aba.get_all_values()
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# --- FUNÇÃO DE LOGIN ---
def realizar_login(sh):
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.title("DNA South America - Pedidos")
        with st.form("login"):
            e = st.text_input("E-mail").lower().strip()
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                aba_u = sh.worksheet("Usuarios")
                df_u = ler_planilha_seguro(aba_u)
                user = df_u[(df_u['email'].str.lower() == e) & (df_u['senha'].astype(str) == s)]
                if not user.empty:
                    st.session_state.autenticado = True
                    st.session_state.user_nome = user.iloc[0]['nome']
                    st.session_state.user_email = e
                    st.session_state.user_nivel = user.iloc[0]['nivel']
                    st.rerun()
                else: st.error("Usuário/Senha inválidos")
        return False
    return True

# --- CONFIGURAÇÃO DE COLUNAS ---
opcoes_desc = ["Matriz L600 Núcleo 100kg", "Matriz L600 Núcleo 110kg", "Matriz L241", "Reprodutor L600", "Reprodutor Terminador"] # Resumido para o exemplo
column_config_padrao = {
    "Descrição": st.column_config.SelectboxColumn("Descrição", options=opcoes_desc, required=True),
    "Data de entrega": st.column_config.DateColumn("Data de entrega", format="DD/MM/YYYY"),
    "Programado": st.column_config.CheckboxColumn("Programado")
}

if sh and realizar_login(sh):
    st.sidebar.write(f"👤 {st.session_state.user_nome} ({st.session_state.user_nivel})")
    aba_nav = st.sidebar.radio("Navegação", ["Novo Pedido", "Gerenciar Pedido", "Histórico de Vendas"])

    if aba_nav == "Novo Pedido":
        # ... (Mantém o código de salvamento anterior que você já tem)
        st.info("Use esta aba para criar novos pedidos conforme o modelo anterior.")

    elif aba_nav == "Gerenciar Pedido":
        id_busca = st.text_input("ID do Pedido para Editar")
        if id_busca:
            aba_p = sh.worksheet("Relatorio de pedidos")
            df_total = ler_planilha_seguro(aba_p)
            ped_original = df_total[df_total['ID Pedido'] == id_busca].copy()

            if not ped_original.empty:
                # Preparar para edição
                cols_edit = ["Descrição", "Modalidade", "Quantidade", "KG Total", "Preço Unitário R$", "Prêmio Genético", "Prazo de Pagamento", "Pagamento Fêmea Retirada KG", "Pagamento Fêmea Retirada R$", "Aluguel", "Indexador", "Cobrar Frete", "Cobrar Registro Genealógico", "Data de entrega", "Programado", "Observação"]
                df_para_editar = ped_original[cols_edit].copy()
                df_para_editar['Programado'] = df_para_editar['Programado'].map({'TRUE': True, 'FALSE': False, True: True, False: False})
                
                df_editado = st.data_editor(df_para_editar, num_rows="dynamic", use_container_width=True, column_config=column_config_padrao)

                if st.button("🆙 SALVAR ALTERAÇÕES"):
                    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    # LOG DE ALTERAÇÕES (SÓ SE ESTIVER PROGRAMADO)
                    esta_programado = any(ped_original['Programado'].map({'TRUE': True, 'FALSE': False, True: True, False: False}))
                    
                    if esta_programado:
                        aba_log = sh.worksheet("Log_Alteracoes")
                        # Comparação simples (Item a Item)
                        log_msg = f"Alteração no Pedido {id_busca} por {st.session_state.user_nome}. "
                        aba_log.append_row([agora, id_busca, st.session_state.user_nome, "Edição de Pedido Programado"])

                    # Deletar e Reinserir (Sua lógica anterior mantendo a ordem A-AC)
                    cell_list = aba_p.findall(id_busca)
                    rows_to_del = sorted(list(set([c.row for c in cell_list])), reverse=True)
                    for r in rows_to_del: aba_p.delete_rows(r)

                    novas_linhas = []
                    for _, row in df_editado.iterrows():
                        if row['Descrição']:
                            # Aqui você monta a lista de A até AC exatamente como no código anterior
                            # Incluindo o status 'ATUALIZADO'
                            novas_linhas.append([
                                id_busca, ped_original.iloc[0]['Cliente'], ped_original.iloc[0]['Vendedor'], ped_original.iloc[0]['Data'],
                                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], 
                                str(row[13]), ped_original.iloc[0]['Cidade'], ped_original.iloc[0]['Estado'], row[15],
                                ped_original.iloc[0]['GTA - CPF/CNPJ'], ped_original.iloc[0].get('GTA - IE',''), ped_original.iloc[0].get('GTA - Código do estabelecimento',''), 
                                ped_original.iloc[0].get('GTA - Estabelecimento',''), str(row[14]), agora, "ALTERADO", st.session_state.user_email
                            ])
                    aba_p.append_rows(novas_linhas)
                    st.success("Pedido atualizado e alteração registrada!")

    elif aba_nav == "Histórico de Vendas":
        st.subheader("📋 Meus Registros de Pedidos")
        aba_p = sh.worksheet("Relatorio de pedidos")
        df_hist = ler_planilha_seguro(aba_p)
        
        if st.session_state.user_nivel != "Admin":
            df_hist = df_hist[df_hist['Vendedor'] == st.session_state.user_nome]
        
        st.dataframe(df_hist, use_container_width=True)

        # SEÇÃO EXCLUSIVA PARA ADMIN: LOG DE ALTERAÇÕES
        if st.session_state.user_nivel == "Admin":
            st.markdown("---")
            st.subheader("🛡️ Log de Auditoria (Apenas Admin)")
            st.caption("Alterações realizadas em pedidos que já estavam 'Programados'")
            try:
                aba_log = sh.worksheet("Log_Alteracoes")
                df_log = ler_planilha_seguro(aba_log)
                if not df_log.empty:
                    st.table(df_log.tail(20)) # Mostra as últimas 20 alterações
                else:
                    st.info("Nenhuma alteração em pedidos programados até o momento.")
            except:
                st.error("Aba 'Log_Alteracoes' não encontrada na planilha.")
