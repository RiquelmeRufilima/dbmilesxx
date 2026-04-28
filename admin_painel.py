"""
admin_panel.py - Painel Administrativo DBMILESX
Sistema completo para administração de empresas e equipe
Acesso restrito para usuários com nível 'admin' ou 'gerente'
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import os
import time
import plotly.express as px
import plotly.graph_objects as go

from database import (
    listar_historico, 
    get_usuarios_empresa, 
    atualizar_nivel_acesso, 
    registrar_evento_seguranca, 
    criar_cotacao, 
    salvar_calculo,
    get_db_cursor,
    get_empresa,
    obter_estatisticas_usuario
)
from auth import gerar_convite_com_email
from exportacao import gerar_relatorio_pdf, get_currency_symbol, exportar_para_csv
from theme_manager import get_cores
from empresa import gerar_novo_codigo_acesso

logger = logging.getLogger(__name__)


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def pagina_admin_empresa():
    """Página exclusiva para administradores e gerentes"""
    
    # Verificar permissão
    if st.session_state.get('nivel_acesso') not in ['admin', 'gerente']:
        st.error("⛔ Acesso negado. Apenas administradores e gerentes podem acessar esta página.")
        return
    
    cores = get_cores()
    empresa_id = st.session_state.get('empresa_id')
    
    if not empresa_id:
        st.warning("⚠️ Você não está vinculado a nenhuma empresa.")
        if st.button("🏠 Voltar ao Início"):
            st.session_state.pagina = 'inicio'
            st.rerun()
        return
    
    # Cabeçalho
    empresa_info = get_empresa(empresa_id)
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, {cores['destaque']}, {cores['destaque']}dd);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
    '>
        <h1 style='color: white; margin: 0;'>👑 Painel Administrativo</h1>
        <p style='color: rgba(255,255,255,0.9); margin: 5px 0 0 0;'>
            {empresa_info.get('nome', st.session_state.get('empresa_nome', 'Sua Empresa'))}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Abas principais
    tab_visao_geral, tab_membros, tab_historico, tab_exportar = st.tabs([
        "📊 Visão Geral", 
        "👥 Membros da Equipe", 
        "📋 Histórico Completo", 
        "📤 Exportar Dados"
    ])
    
    with tab_visao_geral:
        _render_visao_geral(empresa_id)
    
    with tab_membros:
        _render_membros(empresa_id)
    
    with tab_historico:
        _render_historico_geral(empresa_id)
    
    with tab_exportar:
        _render_exportar_dados(empresa_id)


# ============================================================================
# VISÃO GERAL
# ============================================================================

def _render_visao_geral(empresa_id: int):
    """Visão geral da empresa com gráficos e métricas"""
    cores = get_cores()
    
    usuarios = get_usuarios_empresa(empresa_id)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Membros", len(usuarios))
    
    # Contar por nível
    admins = sum(1 for u in usuarios if u.get('nivel_acesso') == 'admin')
    gerentes = sum(1 for u in usuarios if u.get('nivel_acesso') == 'gerente')
    membros = sum(1 for u in usuarios if u.get('nivel_acesso') == 'membro')
    
    with col2:
        st.metric("👑 Administradores", admins)
    with col3:
        st.metric("📋 Gerentes", gerentes)
    with col4:
        st.metric("👤 Membros", membros)
    
    st.markdown("---")
    
    # Gráfico de distribuição de membros
    if usuarios:
        fig = px.pie(
            values=[admins, gerentes, membros],
            names=['Administradores', 'Gerentes', 'Membros'],
            title="Distribuição da Equipe",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Atividade recente da equipe
    st.subheader("📈 Atividade Recente da Equipe")
    
    with st.spinner("Carregando atividades..."):
        try:
            historico_recente = listar_historico(
                usuario_id=st.session_state.usuario_id,
                admin_visualizando=True,
                empresa_id=empresa_id,
                limite=50
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar atividades: {e}")
            historico_recente = []
    
    if historico_recente:
        from collections import defaultdict
        stats = defaultdict(lambda: {'total': 0, 'valor': 0})
        
        for item in historico_recente:
            usuario = item.get('usuario_nome', 'Desconhecido')
            stats[usuario]['total'] += 1
            stats[usuario]['valor'] += item.get('total_geral', 0)
        
        data = []
        for usuario, dados in stats.items():
            data.append({
                'Usuário': usuario,
                'Cotações': dados['total'],
                'Total Gasto': f"R$ {dados['valor']:,.2f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Gráfico de barras
        fig_bar = px.bar(
            df, 
            x='Usuário', 
            y='Cotações',
            title="Cotações por Usuário",
            color='Cotações',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("📭 Nenhuma atividade recente da equipe")


# ============================================================================
# GERENCIAMENTO DE MEMBROS
# ============================================================================

def _render_membros(empresa_id: int):
    """Lista e gerencia membros da equipe"""
    cores = get_cores()
    usuarios = get_usuarios_empresa(empresa_id)
    
    st.subheader(f"👥 Membros da Equipe ({len(usuarios)})")
    
    # ===== EXPANDER: CONVIDAR NOVO MEMBRO =====
    with st.expander("➕ Convidar Novo Membro", expanded=False):
        st.markdown("""
        <div style='background: #f0f8ff; padding: 15px; border-radius: 10px; margin-bottom: 15px;'>
            <strong>📨 Convidar por Email</strong><br>
            O convidado receberá um link para criar sua conta e entrar na empresa.
        </div>
        """, unsafe_allow_html=True)
        
        col_nome, col_email = st.columns(2)
        with col_nome:
            nome_convite = st.text_input("Nome completo", key="convite_nome")
        with col_email:
            email_convite = st.text_input("Email", key="convite_email")
        
        nivel_convite = st.selectbox(
            "Nível de acesso",
            ['membro', 'gerente'],
            format_func=lambda x: {
                'membro': '👤 Membro (uso normal)',
                'gerente': '📋 Gerente (pode gerenciar membros)',
            }[x],
            key="nivel_convite"
        )
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("📨 GERAR CONVITE", type="primary", use_container_width=True, key="btn_gerar_convite"):
                if not nome_convite or not email_convite:
                    st.error("❌ Preencha nome e email do convidado")
                else:
                    # Configuração de email
                    config_email = None
                    try:
                        if hasattr(st, 'secrets') and 'email' in st.secrets:
                            if os.getenv('STREAMLIT_CLOUD'):
                                app_url = st.secrets.get('email', {}).get('APP_URL', 'dbmilesx.streamlit.app')
                                base_url = f"https://{app_url}"
                            else:
                                base_url = "http://localhost:8501"
                            
                            config_email = {
                                'host': st.secrets['email'].get('SMTP_HOST', 'smtp.gmail.com'),
                                'port': int(st.secrets['email'].get('SMTP_PORT', 587)),
                                'user': st.secrets['email'].get('USER', ''),
                                'password': st.secrets['email'].get('PASSWORD', ''),
                                'from': st.secrets['email'].get('FROM', 'noreply@dbmilesx.com'),
                                'base_url': base_url
                            }
                            
                            if not config_email['user'] or not config_email['password']:
                                config_email = None
                                st.info("ℹ️ Email não configurado. Apenas o link será gerado.")
                    except Exception as e:
                        logger.warning(f"Erro ao carregar config de email: {e}")
                        config_email = None
                    
                    with st.spinner("🔄 Gerando convite..."):
                        token = gerar_convite_com_email(
                            empresa_id=empresa_id,
                            email=email_convite.strip().lower(),
                            nome=nome_convite.strip(),
                            nivel_acesso=nivel_convite,
                            convidado_por=st.session_state.usuario_id,
                            config_email=config_email
                        )
                    
                    if token:
                        if os.getenv('STREAMLIT_CLOUD'):
                            app_url = st.secrets.get('email', {}).get('APP_URL', 'dbmilesx.streamlit.app') if hasattr(st, 'secrets') else 'dbmilesx.streamlit.app'
                            base_url = f"https://{app_url}"
                        else:
                            base_url = "http://localhost:8501"
                        
                        link_convite = f"{base_url}/?convite={token}"
                        
                        st.success("✅ Convite gerado com sucesso!")
                        st.code(link_convite, language="text")
                        
                        if config_email:
                            st.success("📧 Email enviado automaticamente para o convidado!")
                        else:
                            st.info("📋 Copie o link acima e envie para o convidado")
                    else:
                        st.error("❌ Erro ao gerar convite. Verifique se o email já não está cadastrado.")
    
    # ===== EXPANDER: GERAR CÓDIGO DE ACESSO =====
    with st.expander("🔑 Gerar Código de Acesso", expanded=False):
        st.markdown("""
        Gere um código para novos membros acessarem a empresa sem precisar de convite por email.
        O código expira em **7 dias**.
        """)
        
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            if st.button("🎲 GERAR NOVO CÓDIGO", type="primary", use_container_width=True, key="btn_gerar_codigo"):
                codigo = gerar_novo_codigo_acesso(empresa_id, st.session_state.usuario_id)
                
                if codigo:
                    st.success("✅ Código gerado com sucesso!")
                    
                    col_code1, col_code2 = st.columns(2)
                    with col_code1:
                        st.markdown("**🔑 Código:**")
                        st.code(codigo['codigo'], language="text")
                    with col_code2:
                        st.markdown("**🔒 Senha:**")
                        st.code(codigo['senha'], language="text")
                    
                    st.info(f"⏰ Expira em: {codigo['expiracao']}")
                else:
                    st.error("❌ Erro ao gerar código")
    
    # ===== EXPANDER: ENVIAR COTAÇÃO PARA MEMBROS =====
    with st.expander("✈️ Enviar Cotação para Membros", expanded=False):
        st.markdown("Envie uma cotação pronta para um membro da equipe.")
        
        membros_opcoes = {f"{m['nome']} ({m['email']})": m['id'] for m in usuarios if m['id'] != st.session_state.usuario_id}
        
        if membros_opcoes:
            membro_selecionado = st.selectbox(
                "👥 Selecionar membro", 
                options=list(membros_opcoes.keys()), 
                key="membro_cotacao"
            )
            membro_id = membros_opcoes[membro_selecionado]
            
            st.markdown("---")
            st.markdown("### 📋 Dados da Cotação")
            
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                nome_cotacao = st.text_input(
                    "Nome da Cotação", 
                    placeholder="Ex: Viagem SP - RJ", 
                    key="nome_cotacao_envio"
                )
                origem = st.text_input(
                    "Origem", 
                    placeholder="Ex: GRU (São Paulo)", 
                    key="origem_envio"
                )
                destino = st.text_input(
                    "Destino", 
                    placeholder="Ex: SDU (Rio de Janeiro)", 
                    key="destino_envio"
                )
            
            with col_c2:
                companhia = st.selectbox(
                    "Companhia Aérea", 
                    ["LATAM Airlines", "GOL Linhas Aéreas", "Azul Linhas Aéreas", "American Airlines"], 
                    key="companhia_envio"
                )
                tipo_calculo = st.selectbox(
                    "Tipo de Cálculo", 
                    ["Milhas + Taxas", "Deságio", "Pontos"], 
                    key="tipo_calculo_envio"
                )
                valor_total = st.number_input(
                    "Valor Total (R$)", 
                    min_value=0.0, 
                    step=10.0, 
                    key="valor_envio"
                )
            
            observacoes = st.text_area(
                "Observações (opcional)", 
                placeholder="Informações adicionais sobre esta cotação...", 
                height=80, 
                key="obs_envio"
            )
            
            col_btn_envio1, col_btn_envio2, col_btn_envio3 = st.columns([1, 2, 1])
            with col_btn_envio2:
                if st.button("✈️ ENVIAR COTAÇÃO", type="primary", use_container_width=True, key="btn_enviar_cotacao"):
                    if not nome_cotacao or not origem or not destino or valor_total <= 0:
                        st.error("❌ Preencha todos os campos obrigatórios!")
                    else:
                        with st.spinner("Enviando cotação..."):
                            try:
                                sucesso, cotacao_id = criar_cotacao(
                                    usuario_id=membro_id,
                                    nome=nome_cotacao,
                                    origem=origem,
                                    destino=destino
                                )
                                
                                if sucesso:
                                    dados_calculo = {
                                        "usuario_id": membro_id,
                                        "cotacao_id": cotacao_id,
                                        "companhia": companhia,
                                        "tipo_calculo": tipo_calculo,
                                        "milhas_total": 0,
                                        "valor_milheiro": 0,
                                        "taxa_embarque": 0,
                                        "valor_base": valor_total,
                                        "valor_bagagens": 0,
                                        "desagio_percentual": 0,
                                        "total_geral": valor_total,
                                        "moeda": "BRL",
                                        "passageiros": 1,
                                        "bebes": 0,
                                        "num_bagagens": 0
                                    }
                                    
                                    sucesso_salvar, msg = salvar_calculo(dados_calculo)
                                    
                                    if sucesso_salvar:
                                        registrar_evento_seguranca(
                                            st.session_state.usuario_id,
                                            "COTACAO_ENVIADA_MEMBRO",
                                            f"Cotação '{nome_cotacao}' enviada para membro ID {membro_id}",
                                            "INFO",
                                            {"membro_id": membro_id, "valor": valor_total}
                                        )
                                        st.success(f"✅ Cotação enviada com sucesso para {membro_selecionado}!")
                                        st.info(f"💰 Valor: R$ {valor_total:,.2f}")
                                        if observacoes:
                                            st.info(f"📝 Observações: {observacoes}")
                                    else:
                                        st.error(f"❌ Erro ao salvar cálculo: {msg}")
                                else:
                                    st.error(f"❌ Erro ao criar cotação: {cotacao_id}")
                            except Exception as e:
                                st.error(f"❌ Erro: {str(e)}")
        else:
            st.info("📭 Nenhum outro membro na equipe para enviar cotação.")
    
    st.markdown("---")
    
    # ===== LISTA DE MEMBROS =====
    st.subheader("📋 Lista de Membros")
    
    for usuario in usuarios:
        if usuario['id'] == st.session_state.usuario_id:
            continue
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 2])
            
            with col1:
                st.markdown(f"**{usuario['nome']}**")
                st.caption(f"ID: {usuario['id']}")
            
            with col2:
                st.write(usuario['email'])
                st.caption(f"Criado em: {usuario.get('data_criacao', '')[:10] if usuario.get('data_criacao') else 'N/A'}")
            
            with col3:
                nivel = usuario.get('nivel_acesso', 'membro')
                if nivel == 'admin':
                    st.markdown("👑 **Administrador**")
                elif nivel == 'gerente':
                    st.markdown("📋 **Gerente**")
                else:
                    st.markdown("👤 Membro")
            
            with col4:
                if st.button(f"⚙️ Gerenciar", key=f"gerenciar_{usuario['id']}"):
                    with st.popover(f"Gerenciar {usuario['nome']}", use_container_width=True):
                        novo_nivel = st.selectbox(
                            "Nível de acesso",
                            ['membro', 'gerente', 'admin'] if st.session_state.get('nivel_acesso') == 'admin' else ['membro', 'gerente'],
                            index=['membro', 'gerente', 'admin'].index(usuario.get('nivel_acesso', 'membro')) if usuario.get('nivel_acesso', 'membro') in ['membro', 'gerente', 'admin'] else 0,
                            key=f"select_{usuario['id']}"
                        )
                        
                        if st.button("✅ Confirmar", key=f"conf_{usuario['id']}", use_container_width=True):
                            sucesso, msg = atualizar_nivel_acesso(
                                usuario['id'], 
                                novo_nivel, 
                                st.session_state.usuario_id
                            )
                            if sucesso:
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)
            
            st.divider()


# ============================================================================
# HISTÓRICO COMPLETO
# ============================================================================

def _render_historico_geral(empresa_id: int):
    """Histórico de TODOS os membros da empresa"""
    cores = get_cores()
    
    st.subheader("📋 Histórico Completo da Empresa")
    
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        usuarios = get_usuarios_empresa(empresa_id)
        usuarios_opcoes = ["Todos"] + [f"{u['nome']} ({u['email']})" for u in usuarios]
        filtro_usuario = st.selectbox("👤 Filtrar por usuário", usuarios_opcoes, key="filtro_usuario_hist")
    
    with col_f2:
        periodo = st.selectbox(
            "📅 Período",
            ["Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Todos"],
            key="filtro_periodo_hist"
        )
    
    with col_f3:
        limite = st.number_input("📊 Limite de resultados", min_value=10, max_value=1000, value=100, key="limite_hist")
    
    # Processar filtros
    usuario_contexto = None
    if filtro_usuario != "Todos":
        email = filtro_usuario.split('(')[-1].rstrip(')')
        with get_db_cursor() as cursor:
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            result = cursor.fetchone()
            if result:
                usuario_contexto = result['id']
    
    # Calcular datas
    hoje = datetime.now()
    if periodo == "Últimos 7 dias":
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = None
    elif periodo == "Últimos 30 dias":
        data_inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        data_fim = None
    elif periodo == "Este mês":
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        data_fim = None
    elif periodo == "Mês anterior":
        primeiro_mes_anterior = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        ultimo_mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        data_inicio = primeiro_mes_anterior.strftime("%Y-%m-%d")
        data_fim = ultimo_mes_anterior.strftime("%Y-%m-%d")
    else:
        data_inicio = None
        data_fim = None
    
    with st.spinner("Carregando histórico..."):
        historico = listar_historico(
            usuario_id=usuario_contexto if usuario_contexto else st.session_state.usuario_id,
            admin_visualizando=True,
            empresa_id=empresa_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=limite
        )
    
    if not historico:
        st.info("📭 Nenhuma cotação encontrada para os filtros selecionados.")
        return
    
    # Estatísticas
    total_cotacoes = len(historico)
    total_gasto = sum(item.get('total_geral', 0) for item in historico)
    media_por_cotacao = total_gasto / total_cotacoes if total_cotacoes > 0 else 0
    simbolo = get_currency_symbol(st.session_state.get('moeda', 'BRL'))
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("📊 Total de Cotações", total_cotacoes)
    with col_s2:
        st.metric("💰 Total Gasto", f"{simbolo} {total_gasto:,.2f}")
    with col_s3:
        st.metric("📈 Média por Cotação", f"{simbolo} {media_por_cotacao:,.2f}")
    
    # Tabela de dados
    st.subheader("📋 Listagem Detalhada")
    
    dados_tabela = []
    for item in historico:
        dados_tabela.append({
            'ID': item.get('id'),
            'Usuário': item.get('usuario_nome', 'N/A'),
            'Data': item.get('data_calculo', '')[:10] if item.get('data_calculo') else '',
            'Companhia': item.get('companhia', 'N/A'),
            'Rota': f"{item.get('origem', '')} → {item.get('destino', '')}",
            'Passageiros': item.get('passageiros', 1),
            'Total': f"{simbolo} {item.get('total_geral', 0):,.2f}"
        })
    
    df = pd.DataFrame(dados_tabela)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Gráfico de evolução
    if len(historico) > 1:
        st.subheader("📈 Evolução dos Valores")
        
        df_evolucao = pd.DataFrame([
            {'Data': item.get('data_calculo', '')[:10] if item.get('data_calculo') else '', 'Valor': item.get('total_geral', 0)}
            for item in historico
        ])
        df_evolucao = df_evolucao.sort_values('Data')
        
        fig = px.line(
            df_evolucao, 
            x='Data', 
            y='Valor',
            title="Evolução dos Valores das Cotações",
            markers=True
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# EXPORTAR DADOS
# ============================================================================

def _render_exportar_dados(empresa_id: int):
    """Exporta dados de todos os membros da empresa"""
    cores = get_cores()
    
    st.subheader("📤 Exportar Dados da Empresa")
    
    # Opções de exportação
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        periodo_export = st.selectbox(
            "Período para exportar",
            ["Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Todos os dados"],
            key="export_periodo"
        )
    
    with col_op2:
        incluir_usuarios = st.checkbox("Incluir nome dos usuários", value=True, key="export_incluir_usuarios")
    
    # Calcular período
    hoje = datetime.now()
    if periodo_export == "Últimos 7 dias":
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = None
        titulo = "Últimos 7 dias"
    elif periodo_export == "Últimos 30 dias":
        data_inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        data_fim = None
        titulo = "Últimos 30 dias"
    elif periodo_export == "Este mês":
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        data_fim = None
        titulo = f"Mês de {hoje.strftime('%B/%Y')}"
    elif periodo_export == "Mês anterior":
        primeiro_mes_anterior = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        ultimo_mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        data_inicio = primeiro_mes_anterior.strftime("%Y-%m-%d")
        data_fim = ultimo_mes_anterior.strftime("%Y-%m-%d")
        titulo = f"Mês de {primeiro_mes_anterior.strftime('%B/%Y')}"
    else:
        data_inicio = None
        data_fim = None
        titulo = "Todos os dados"
    
    with st.spinner("Carregando dados..."):
        historico = listar_historico(
            usuario_id=st.session_state.usuario_id,
            admin_visualizando=True,
            empresa_id=empresa_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=10000
        )
    
    if not historico:
        st.warning("📭 Nenhum dado encontrado para o período selecionado.")
        return
    
    st.success(f"📊 {len(historico)} cotações encontradas")
    
    # Botões de exportação
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("📥 EXPORTAR PARA CSV", type="primary", use_container_width=True, key="btn_export_csv"):
            with st.spinner("Gerando arquivo CSV..."):
                buffer, nome, qtd = exportar_para_csv(
                    historico, 
                    f"empresa_{st.session_state.empresa_nome}", 
                    titulo
                )
                if buffer:
                    st.download_button(
                        "📥 BAIXAR CSV",
                        buffer,
                        nome,
                        "text/csv",
                        use_container_width=True,
                        key="download_csv"
                    )
                    st.success(f"✅ CSV gerado com {qtd} registros!")
    
    with col_btn2:
        if st.button("📄 GERAR PDF COMPLETO", type="primary", use_container_width=True, key="btn_export_pdf"):
            with st.spinner("Gerando PDF..."):
                try:
                    buffer, nome, qtd = gerar_relatorio_pdf(
                        historico,
                        st.session_state.usuario_nome,
                        titulo,
                        incluir_usuarios=incluir_usuarios
                    )
                    if buffer:
                        st.download_button(
                            "📄 BAIXAR PDF",
                            buffer,
                            nome,
                            "application/pdf",
                            use_container_width=True,
                            key="download_pdf"
                        )
                        st.success(f"✅ PDF gerado com {qtd} registros!")
                    else:
                        st.error("❌ Erro ao gerar PDF. Verifique se o ReportLab está instalado.")
                except Exception as e:
                    st.error(f"❌ Erro ao gerar PDF: {str(e)}")
    
    # Prévia dos dados
    with st.expander("👁️ Prévia dos dados a serem exportados", expanded=False):
        st.dataframe(pd.DataFrame(historico[:10]), use_container_width=True)
        st.caption(f"Mostrando 10 de {len(historico)} registros")


# ============================================================================
# TESTE DO MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTANDO MÓDULO ADMIN_PANEL")
    print("=" * 60)
    
    print("\n✅ MÓDULO ADMIN_PANEL OK!")
    print("=" * 60)