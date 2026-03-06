import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import time
from fpdf import FPDF
import io
import unicodedata

# --- FUNÇÃO AUXILIAR PARA PDF ---
def limpar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto))
                   if unicodedata.category(c) != 'Mn').replace('ç', 'c').replace('Ç', 'C')

# --- PORTA DE ENTRADA PARA O ROBÔ ---
if st.query_params.get("manter_vivo") == "verdadeiro":
    st.write("Sistema Online")
    st.stop()

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
        st.error(f"⚠️ Erro de Conexao: {e}")
        return None

sh = iniciar_conexao()

class PDF(FPDF):
    def header(self):
        try: self.image('DNA_white-1024x576-1.png', 10, 8, 30)
        except: pass
        self.set_font('Arial', 'B', 12)
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
        # Limpamos todos os campos antes de enviar para o PDF
        pdf.cell(0, 7, limpar_texto(f"REPOSICAO: {dados['Brinco']} - CLIENTE: {dados['Cliente']}"), 1, 1, 'L')
        pdf.set_font("Arial", '', 8)
        pdf.cell(25, 6, "Cliente:", 'L'); pdf.cell(70, 6, limpar_texto(dados['Cliente']), 'R')
        pdf.cell(25, 6, "CNPJ:", 'L'); pdf.cell(0, 6, limpar_texto(dados['CNPJ']), 'R', 1)
        pdf.cell(25, 6, "DNA ID:", 'L'); pdf.cell(70, 6, limpar_texto(dados['DNA_ID']), 'R')
        pdf.cell(25, 6, "Brinco:", 'L'); pdf.cell(0, 6, limpar_texto(dados['Brinco']), 'R', 1)
        pdf.cell(25, 6, "Motivo:", 'L'); pdf.cell(70, 6, limpar_texto(dados['Motivo']), 'R')
        pdf.cell(25, 6, "Tipo:", 'L'); pdf.cell(0, 6, limpar_texto(dados['Tipo_repo']), 'R', 1)
        pdf.cell(25, 6, "Status:", 'LB'); pdf.cell(70, 6, limpar_texto(dados['Status']), 'RB')
        pdf.cell(25, 6, "Data:", 'LB'); pdf.cell(0, 6, limpar_texto(dados.get('Data', 'N/A')), 'RB', 1)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# Manter o restante do seu código original (Cadastrar, Aprovação, Status) abaixo
# Certifique-se de chamar limpar_texto() sempre que gerar dados para o PDF
