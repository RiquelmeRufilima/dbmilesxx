"""
configuracoes.py - Página de Configurações do Sistema DBMILESX
Gerenciamento completo de aparência, segurança, conta e 2FA
"""

import streamlit as st
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Importações do projeto
from database import criar_conexao
from securitymax import (
    security,
    get_colors,
    pagina_configurar_2fa,
    verificar_2fa_login,
    TwoFactorAuth,
    validate_password_strength,
    hash_password,
    verify_password
)

logger = logging.getLogger(__name__)


def pagina_configuracoes():
    """
    Página de configurações completa com abas:
    - Aparência (temas, cores, moeda)
    - Segurança (alterar senha)
    - Conta (informações do usuário)
    - 2FA (autenticação de dois fatores)
    """
    
    # Verificar se usuário está logado
    if not st.session_state.get('logado', False):
        st.warning("⚠️ Você precisa estar logado para acessar as configurações.")
        if st.button("🔐 Ir para Login"):
            st.session_state.pagina = 'login'
            st.rerun()
        return
    
    cores = get_colors()
    
    # Título e botão voltar
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cores['destaque']}, {cores['destaque']}dd); 
                padding: 20px; 
                border-radius: 15px; 
                margin-bottom: 25px;">
        <h1 style="color: white; margin: 0;">⚙️ Configurações do Sistema</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0;">
            Personalize sua experiência no DBMILESX
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão voltar
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Voltar ao Início", use_container_width=True, key="btn_voltar_config"):
            st.session_state.pagina = 'inicio'
            st.rerun()
    
    # ============= ABAS PRINCIPAIS =============
    tab_aparencia, tab_seguranca, tab_conta, tab_2fa = st.tabs([
        "🎨 Aparência", "🔐 Segurança", "👤 Conta", "📱 Autenticação 2FA"
    ])
    
    # ============= ABA 1: APARÊNCIA =============
    with tab_aparencia:
        _render_aba_aparencia(cores)
    
    # ============= ABA 2: SEGURANÇA =============
    with tab_seguranca:
        _render_aba_seguranca(cores)
    
    # ============= ABA 3: CONTA =============
    with tab_conta:
        _render_aba_conta(cores)
    
    # ============= ABA 4: 2FA =============
    with tab_2fa:
        _render_aba_2fa()


def _render_aba_aparencia(cores: Dict[str, str]):
    """Renderiza a aba de aparência com temas, cores e moeda"""
    
    st.markdown("### 🎨 Personalização da Interface")
    st.caption("Escolha o tema, cores e moeda do sistema")
    
    # Sub-abas para organização
    sub_tab_temas, sub_tab_cores, sub_tab_moeda = st.tabs([
        "🎨 Temas", "🎭 Cores Personalizadas", "💰 Moeda"
    ])
    
    # ===== SUB-ABA: TEMAS =====
    with sub_tab_temas:
        st.markdown("#### Modo de Visualização")
        
        tema_atual = st.session_state.get('tema', 'escuro')
        
        col_tema1, col_tema2 = st.columns(2)
        
        with col_tema1:
            tema_escuro = st.button(
                "🌙 **Modo Escuro**\n\nIdeal para uso noturno",
                use_container_width=True,
                type="primary" if tema_atual == 'escuro' else "secondary",
                key="tema_escuro"
            )
            if tema_escuro:
                st.session_state.tema = 'escuro'
                _salvar_tema('escuro')
                st.rerun()
        
        with col_tema2:
            tema_claro = st.button(
                "☀️ **Modo Claro**\n\nIdeal para ambientes claros",
                use_container_width=True,
                type="primary" if tema_atual == 'claro' else "secondary",
                key="tema_claro"
            )
            if tema_claro:
                st.session_state.tema = 'claro'
                _salvar_tema('claro')
                st.rerun()
        
        # Preview do tema
        st.markdown("#### 👁️ Pré-visualização")
        bg_color = "#1e1e1e" if st.session_state.tema == 'escuro' else "#ffffff"
        text_color = "#ffffff" if st.session_state.tema == 'escuro' else "#333333"
        card_bg = "#2d2d2d" if st.session_state.tema == 'escuro' else "#f5f5f5"
        
        st.markdown(f"""
        <div style="background: {card_bg}; border-radius: 15px; padding: 20px; margin: 10px 0;">
            <div style="background: {bg_color}; border-radius: 10px; padding: 20px;">
                <h3 style="color: {cores['destaque']};">Título de Exemplo</h3>
                <p style="color: {text_color};">Este é um texto de exemplo com o tema atual.</p>
                <div style="display: flex; gap: 10px;">
                    <span style="background: {cores['destaque']}; color: white; padding: 8px 16px; border-radius: 8px;">Botão Principal</span>
                    <span style="background: #4CAF50; color: white; padding: 8px 16px; border-radius: 8px;">Sucesso</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ===== SUB-ABA: CORES PERSONALIZADAS =====
    with sub_tab_cores:
        st.markdown("#### Cores Personalizadas")
        st.caption("Personalize as cores do sistema (funciona apenas no tema escuro)")
        
        col_cor1, col_cor2 = st.columns(2)
        
        with col_cor1:
            cor_primaria = st.color_picker(
                "**Cor Primária**",
                value=st.session_state.get('cor_primaria', '#3d8bfd'),
                key="cor_primaria"
            )
            
            cor_secundaria = st.color_picker(
                "**Cor Secundária**",
                value=st.session_state.get('cor_secundaria', '#5c9cff'),
                key="cor_secundaria"
            )
        
        with col_cor2:
            cor_sucesso = st.color_picker(
                "**Cor de Sucesso**",
                value=st.session_state.get('cor_sucesso', '#4CAF50'),
                key="cor_sucesso"
            )
            
            cor_erro = st.color_picker(
                "**Cor de Erro**",
                value=st.session_state.get('cor_erro', '#f44336'),
                key="cor_erro"
            )
        
        # Preview das cores
        st.markdown("#### 👁️ Preview das Cores")
        st.markdown(f"""
        <div style="display: flex; gap: 15px; flex-wrap: wrap; padding: 20px; background: {cores['card']}; border-radius: 15px;">
            <div style="background: {cor_primaria}; padding: 10px 20px; border-radius: 8px; color: white;">Primária</div>
            <div style="background: {cor_secundaria}; padding: 10px 20px; border-radius: 8px; color: white;">Secundária</div>
            <div style="background: {cor_sucesso}; padding: 10px 20px; border-radius: 8px; color: white;">Sucesso</div>
            <div style="background: {cor_erro}; padding: 10px 20px; border-radius: 8px; color: white;">Erro</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("💾 Salvar Cores Personalizadas", type="primary", use_container_width=True):
            st.session_state.cor_primaria = cor_primaria
            st.session_state.cor_secundaria = cor_secundaria
            st.session_state.cor_sucesso = cor_sucesso
            st.session_state.cor_erro = cor_erro
            _salvar_cores_personalizadas(cor_primaria, cor_secundaria, cor_sucesso, cor_erro)
            st.success("✅ Cores salvas com sucesso!")
            time.sleep(1)
            st.rerun()
    
    # ===== SUB-ABA: MOEDA =====
    with sub_tab_moeda:
        st.markdown("#### Moeda Principal")
        st.caption("Define a moeda usada para exibir valores no sistema")
        
        moeda_atual = st.session_state.get('moeda', 'BRL')
        
        moedas = {
            "BRL": {"nome": "Real Brasileiro", "simbolo": "R$", "emoji": "🇧🇷"},
            "USD": {"nome": "Dólar Americano", "simbolo": "$", "emoji": "🇺🇸"},
            "EUR": {"nome": "Euro", "simbolo": "€", "emoji": "🇪🇺"},
            "GBP": {"nome": "Libra Esterlina", "simbolo": "£", "emoji": "🇬🇧"}
        }
        
        # Grid de moedas
        cols = st.columns(4)
        for i, (codigo, info) in enumerate(moedas.items()):
            with cols[i]:
                is_selected = moeda_atual == codigo
                st.markdown(f"""
                <div style="
                    text-align: center;
                    padding: 15px;
                    background: {cores['card']};
                    border-radius: 12px;
                    border: 2px solid {cores['destaque'] if is_selected else cores['borda']};
                    margin-bottom: 10px;
                ">
                    <div style="font-size: 2rem;">{info['emoji']}</div>
                    <div style="font-weight: bold;">{info['simbolo']}</div>
                    <div style="font-size: 0.8rem;">{info['nome'][:15]}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Usar {codigo}", key=f"moeda_{codigo}", use_container_width=True):
                    st.session_state.moeda = codigo
                    _salvar_moeda(codigo)
                    st.success(f"✅ Moeda alterada para {info['nome']}")
                    time.sleep(1)
                    st.rerun()
        
        st.info(f"💡 Moeda atual: **{moedas[moeda_atual]['nome']}** ({moedas[moeda_atual]['simbolo']})")


def _render_aba_seguranca(cores: Dict[str, str]):
    """Renderiza a aba de segurança (alterar senha)"""
    
    st.markdown("### 🔐 Alterar Senha")
    st.caption("Mantenha sua conta segura alterando sua senha regularmente")
    
    # Dicas de segurança
    st.markdown(f"""
    <div style="
        background: {cores['info']}15;
        border-left: 4px solid {cores['info']};
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <strong>🔒 Recomendações de segurança:</strong>
        <ul style="margin: 10px 0 0 20px;">
            <li>Use pelo menos 8 caracteres</li>
            <li>Inclua letras maiúsculas e minúsculas</li>
            <li>Adicione números e caracteres especiais (!@#$%*)</li>
            <li>Não use senhas óbvias como "123456" ou "senha"</li>
            <li>Não reutilize senhas de outros serviços</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_alterar_senha"):
        col1, col2 = st.columns(2)
        
        with col1:
            senha_atual = st.text_input(
                "**Senha Atual**",
                type="password",
                placeholder="Digite sua senha atual",
                help="Confirmamos sua identidade com a senha atual"
            )
        
        with col2:
            # Validação da senha atual em tempo real
            if senha_atual:
                if _verificar_senha_atual(senha_atual):
                    st.success("✅ Senha atual correta")
                else:
                    st.error("❌ Senha atual incorreta")
        
        st.markdown("---")
        
        col3, col4 = st.columns(2)
        
        with col3:
            nova_senha = st.text_input(
                "**Nova Senha**",
                type="password",
                placeholder="Mínimo 8 caracteres",
                help="Digite sua nova senha"
            )
        
        with col4:
            confirmar_senha = st.text_input(
                "**Confirmar Nova Senha**",
                type="password",
                placeholder="Repita a nova senha",
                help="Digite novamente a nova senha"
            )
        
        # Medidor de força da senha
        if nova_senha:
            validacao = validate_password_strength(nova_senha)
            progresso = validacao['score'] / validacao['max_score']
            
            st.progress(progresso, text=f"Força: {validacao['classification']}")
            
            # Feedback detalhado
            with st.expander("📋 Ver requisitos da senha"):
                for msg in validacao['feedback']:
                    if "✓" in msg:
                        st.success(msg)
                    else:
                        st.warning(msg)
        
        # Botão de submit
        submitted = st.form_submit_button(
            "🔄 Alterar Senha",
            type="primary",
            use_container_width=True,
            disabled=not all([senha_atual, nova_senha, confirmar_senha])
        )
        
        if submitted:
            # Validações
            if not _verificar_senha_atual(senha_atual):
                st.error("❌ Senha atual incorreta!")
                
            elif nova_senha != confirmar_senha:
                st.error("❌ As novas senhas não coincidem!")
                
            elif len(nova_senha) < 8:
                st.error("❌ A nova senha deve ter no mínimo 8 caracteres!")
                
            else:
                validacao = validate_password_strength(nova_senha)
                if not validacao['valid']:
                    st.warning("⚠️ A nova senha é muito fraca!")
                    
                    col_confirm1, col_confirm2 = st.columns(2)
                    with col_confirm1:
                        if st.button("✅ Mesmo assim, quero continuar"):
                            _atualizar_senha(nova_senha)
                    with col_confirm2:
                        if st.button("❌ Cancelar"):
                            st.rerun()
                else:
                    _atualizar_senha(nova_senha)


def _render_aba_conta(cores: Dict[str, str]):
    """Renderiza a aba de informações da conta"""
    
    st.markdown("### 👤 Informações da Conta")
    st.caption("Gerencie seus dados pessoais")
    
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nome, email, data_criacao, telefone, cargo 
            FROM usuarios 
            WHERE id = ?
        ''', (st.session_state.usuario_id,))
        dados = cursor.fetchone()
        
        if dados:
            nome, email, data_criacao, telefone, cargo = dados
            
            # Card de informações
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.markdown(f"""
                <div style="background: {cores['card']}; padding: 20px; border-radius: 15px;">
                    <h4>📋 Dados Pessoais</h4>
                    <p><strong>👤 Nome:</strong> {nome}</p>
                    <p><strong>📧 Email:</strong> {email}</p>
                    <p><strong>📅 Membro desde:</strong> {_formatar_data(data_criacao)}</p>
                    <p><strong>🆔 ID:</strong> <code>{st.session_state.usuario_id}</code></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_info2:
                st.markdown(f"""
                <div style="background: {cores['card']}; padding: 20px; border-radius: 15px;">
                    <h4>📊 Estatísticas</h4>
                    <p><strong>📋 Cotações criadas:</strong> {_contar_cotacoes()}</p>
                    <p><strong>🧮 Cálculos realizados:</strong> {_contar_calculos()}</p>
                    <p><strong>🔐 Nível de acesso:</strong> {st.session_state.get('nivel_acesso', 'membro').upper()}</p>
                    <p><strong>⏱️ Última atividade:</strong> {_formatar_data(st.session_state.last_activity)}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Editar nome
            st.markdown("### ✏️ Editar Nome")
            
            with st.form("form_editar_nome"):
                novo_nome = st.text_input(
                    "**Novo Nome**",
                    value=nome,
                    placeholder="Digite seu novo nome",
                    help="Mínimo 3 caracteres"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Salvar Nome", type="primary", use_container_width=True):
                        if len(novo_nome.strip()) >= 3:
                            cursor.execute(
                                'UPDATE usuarios SET nome = ? WHERE id = ?',
                                (novo_nome.strip(), st.session_state.usuario_id)
                            )
                            conn.commit()
                            st.session_state.usuario_nome = novo_nome.strip()
                            st.success("✅ Nome atualizado!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Nome deve ter pelo menos 3 caracteres")
                
                with col_btn2:
                    if st.form_submit_button("↺ Cancelar", use_container_width=True):
                        st.rerun()
            
            conn.close()
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        logger.error(f"Erro na aba conta: {e}")


def _render_aba_2fa():
    """Renderiza a aba de autenticação de dois fatores"""
    try:
        pagina_configurar_2fa()
    except Exception as e:
        st.error(f"❌ Erro ao carregar configuração 2FA: {e}")
        st.info("""
        A Autenticação de Dois Fatores (2FA) adiciona uma camada extra de segurança à sua conta.
        
        **Para configurar:**
        1. Instale o Google Authenticator ou Microsoft Authenticator
        2. Escaneie o código QR
        3. Digite o código gerado
        """)


# ============= FUNÇÕES AUXILIARES =============

def _salvar_tema(tema: str):
    """Salva o tema no banco de dados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios SET tema_preferido = ? WHERE id = ?
        ''', (tema, st.session_state.usuario_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar tema: {e}")


def _salvar_cores_personalizadas(primaria, secundaria, sucesso, erro):
    """Salva as cores personalizadas no banco"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios 
            SET cor_primaria = ?, cor_secundaria = ?, cor_sucesso = ?, cor_erro = ?
            WHERE id = ?
        ''', (primaria, secundaria, sucesso, erro, st.session_state.usuario_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar cores: {e}")


def _salvar_moeda(moeda: str):
    """Salva a moeda no banco de dados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios SET moeda_preferida = ? WHERE id = ?
        ''', (moeda, st.session_state.usuario_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar moeda: {e}")


def _verificar_senha_atual(senha: str) -> bool:
    """Verifica se a senha atual está correta"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('SELECT senha_hash FROM usuarios WHERE id = ?', (st.session_state.usuario_id,))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado and verify_password(senha, resultado[0]):
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar senha: {e}")
        return False


def _atualizar_senha(nova_senha: str):
    """Atualiza a senha do usuário"""
    try:
        novo_hash = hash_password(nova_senha)
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios SET senha_hash = ? WHERE id = ?
        ''', (novo_hash, st.session_state.usuario_id))
        conn.commit()
        conn.close()
        
        st.success("""
        ✅ **Senha alterada com sucesso!**
        
        Sua senha foi atualizada. Para maior segurança, recomendamos fazer logout e login novamente.
        """)
        
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erro ao atualizar senha: {e}")
        logger.error(f"Erro ao atualizar senha: {e}")


def _contar_cotacoes() -> int:
    """Conta o número de cotações do usuário"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cotacoes WHERE usuario_id = ?', (st.session_state.usuario_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


def _contar_calculos() -> int:
    """Conta o número de cálculos do usuário"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM historico_cotacoes WHERE usuario_id = ?', (st.session_state.usuario_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


def _formatar_data(data) -> str:
    """Formata data para exibição"""
    if not data:
        return "Não disponível"
    try:
        if isinstance(data, str):
            return data[:16] if len(data) > 16 else data
        elif isinstance(data, (int, float)):
            return datetime.fromtimestamp(data).strftime("%d/%m/%Y %H:%M")
        elif hasattr(data, 'strftime'):
            return data.strftime("%d/%m/%Y %H:%M")
        return str(data)
    except:
        return "Data inválida"


# ============= PONTO DE ENTRADA PARA TESTE =============

if __name__ == "__main__":
    # Teste isolado do módulo
    st.set_page_config(page_title="Configurações DBMILESX", layout="wide")
    
    # Simular login para teste
    if 'usuario_id' not in st.session_state:
        st.session_state.usuario_id = 1
        st.session_state.usuario_nome = "Usuário Teste"
        st.session_state.usuario_email = "teste@dbmilesx.com"
        st.session_state.logado = True
        st.session_state.tema = 'escuro'
        st.session_state.moeda = 'BRL'
        st.session_state.last_activity = time.time()
    
    pagina_configuracoes()