"""
Módulo de relatórios de custo e venda - DBMILESX
Versão com formatação brasileira e imagens proporcionais
CORRIGIDO: Datas nos relatórios e ocultar volta quando somente ida
"""

import io
import os
import sys
import base64
import tempfile
import traceback
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import locale
import json  # <--- ADICIONAR ESTA LINHA NO INÍCIO DO ARQUIVO


# Configurar logger
logger = logging.getLogger(__name__)

# Importar funções do utils
try:
    from utils import carregar_imagem_companhia, get_currency_symbol, get_colors
    logger.info("✅ Funções importadas do utils.py")
except ImportError as e:
    logger.error(f"❌ Erro ao importar do utils.py: {e}")
    
    # Funções fallback caso a importação falhe
    def get_currency_symbol(currency_code: str) -> str:
        symbols = {"BRL": "R$", "USD": "US$", "EUR": "€", "GBP": "£"}
        return symbols.get(currency_code, currency_code)
    
    def carregar_imagem_companhia(nome_companhia):
        """Versão fallback simplificada"""
        from PIL import Image, ImageDraw, ImageFont
        
        # Cores das companhias
        cores = {
            "latam": "#1E88E5", "gol": "#FF6B00", 
            "azul": "#00B0FF", "american": "#002D72"
        }
        
        companhia_lower = nome_companhia.lower()
        cor = "#3d8bfd"
        texto = nome_companhia.upper()
        
        for key, cor_key in cores.items():
            if key in companhia_lower:
                cor = cor_key
                texto = key.upper()
                break
        
        img = Image.new('RGB', (250, 120), color=cor)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (250 - text_width) / 2
        y = (120 - text_height) / 2
        
        draw.text((x, y), texto, fill="white", font=font)
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

# Tentar configurar locale brasileiro para formatação de números
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # Se não conseguir, usaremos formatação manual

def formatar_valor_br(valor: float) -> str:
    """Formata valor no padrão brasileiro (1.234,56)"""
    if valor == 0:
        return "0,00"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_milhas(milhas: float) -> str:
    """Formata milhas com 3 casas decimais (1.234,567)"""
    if milhas == 0:
        return "0,000"
    return f"{milhas:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")

def encontrar_imagem_companhia(nome_companhia: str) -> Optional[str]:
    """
    Encontra o arquivo de imagem da companhia na pasta raiz
    """
    nome_lower = nome_companhia.lower()
    
    # Mapeamento de possíveis nomes para arquivos
    mapa_companhias = {
        'latam': ['latam.png', 'latam.jpg', 'latam.jpeg'],
        'gol': ['gol.png', 'gol.jpg', 'gol.jpeg'],
        'azul': ['azul.png', 'azul.jpg', 'azul.jpeg'],
        'american': ['american.png', 'american.jpg', 'american.jpeg', 'american airlines.png']
    }
    
    # Procurar correspondência
    for chave, arquivos in mapa_companhias.items():
        if chave in nome_lower:
            for arquivo in arquivos:
                if os.path.exists(arquivo):
                    return arquivo
    
    # Verificar arquivos direto
    arquivos_direto = [f"{nome_lower}.png", f"{nome_lower}.jpg", "companhia.png"]
    for arquivo in arquivos_direto:
        if os.path.exists(arquivo):
            return arquivo
    
    return None

def gerar_relatorio_custo_pdf(cotacao: Dict[str, Any], 
                             usuario_nome: str) -> Tuple[Optional[io.BytesIO], Optional[str]]:
    """
    Gera relatório de CUSTO em PDF com todos os detalhes da cotação
    CORRIGIDO: Inclui datas e oculta volta quando somente ida
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Criar buffer para PDF
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        # Elementos do documento
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#3d8bfd'),
            alignment=TA_CENTER,
            spaceAfter=0.5*cm
        )
        
        style_subtitle = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceAfter=1*cm
        )
        
        style_section = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_LEFT,
            spaceAfter=0.3*cm,
            spaceBefore=0.8*cm
        )
        
        style_label = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_LEFT
        )
        
        style_value = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        style_value_right = ParagraphStyle(
            'ValueRight',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        style_total = ParagraphStyle(
            'Total',
            parent=styles['Normal'],
            fontSize=18,
            textColor=colors.HexColor('#3d8bfd'),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        style_companhia_nome = ParagraphStyle(
            'CompanhiaNome',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=0.3*cm
        )
        
        style_observacao = ParagraphStyle(
            'Observacao',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT,
            leftIndent=0.5*cm,
            rightIndent=0.5*cm
        )
        
        # ============= TÍTULO =============
        titulo = Paragraph("📋 RELATÓRIO DE CUSTO - DBMILESX", style_title)
        elements.append(titulo)
        
        # Data de emissão
        data_emissao = datetime.now().strftime("%d/%m/%Y %H:%M")
        subtitulo = Paragraph(f"Emissão: {data_emissao} | Usuário: {usuario_nome}", style_subtitle)
        elements.append(subtitulo)
        elements.append(Spacer(1, 0.5*cm))
        
        # ============= LOGO E NOME DA COMPANHIA =============
        companhia = cotacao.get('companhia', '')
        imagem_path = encontrar_imagem_companhia(companhia)
        
        if imagem_path:
            try:
                # Carregar imagem e manter proporção
                from reportlab.lib.utils import ImageReader
                img_reader = ImageReader(imagem_path)
                img_width, img_height = img_reader.getSize()
                
                # Definir largura máxima de 5cm e altura proporcional
                max_width = 5 * cm
                proporcao = max_width / img_width
                new_width = max_width
                new_height = img_height * proporcao
                
                # Limitar altura máxima a 2.5cm para não ficar muito grande
                if new_height > 2.5 * cm:
                    new_height = 2.5 * cm
                    new_width = img_width * (new_height / img_height)
                
                img = Image(imagem_path, width=new_width, height=new_height)
                img.hAlign = TA_CENTER
                elements.append(img)
                elements.append(Spacer(1, 0.2*cm))
            except Exception as e:
                logger.warning(f"Erro ao carregar imagem {imagem_path}: {e}")
        
        # Nome da companhia em destaque
        elements.append(Paragraph(companhia, style_companhia_nome))
        elements.append(Spacer(1, 0.3*cm))
        
        # ============= EXTRAIR DATAS DOS METADADOS =============
        metadata = cotacao.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        tipo_viagem = metadata.get('tipo_viagem', cotacao.get('tipo_viagem', 'Ida e Volta'))
        data_ida = metadata.get('data_ida', 'Não informada')
        data_volta = metadata.get('data_volta', 'Não informada')
        
        # ============= DADOS DA COTAÇÃO =============
        elements.append(Paragraph("📌 DADOS DA COTAÇÃO", style_section))
        
        nome_cotacao = cotacao.get('nome_cotacao', 'Cotação')
        origem = cotacao.get('origem', 'N/A')
        destino = cotacao.get('destino', 'N/A')
        data_calculo = cotacao.get('data_calculo', '')
        data_formatada = data_calculo[:16].replace('T', ' ') if data_calculo and len(data_calculo) >= 16 else datetime.now().strftime("%d/%m/%Y %H:%M")
        
        header_data = [
            [Paragraph("<b>Nome da Cotação</b>", style_label), Paragraph(nome_cotacao, style_value)],
            [Paragraph("<b>Rota</b>", style_label), Paragraph(f"{origem} → {destino}", style_value)],
            [Paragraph("<b>Tipo de Viagem</b>", style_label), Paragraph(tipo_viagem, style_value)],
            [Paragraph("<b>Data de Ida</b>", style_label), Paragraph(data_ida, style_value)],
        ]
        
        # Adicionar data de volta apenas se não for somente ida
        if tipo_viagem != "Somente Ida" and data_volta != "Não informada":
            header_data.append([Paragraph("<b>Data de Volta</b>", style_label), Paragraph(data_volta, style_value)])
        
        header_data.append([Paragraph("<b>Data/Hora Cálculo</b>", style_label), Paragraph(data_formatada, style_value)])
        
        header_table = Table(header_data, colWidths=[5*cm, 12*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # ============= DADOS DA COMPANHIA =============
        elements.append(Paragraph("✈️ DADOS DA COMPANHIA", style_section))
        
        tipo_calculo = cotacao.get('tipo_calculo', 'N/A')
        
        comp_data = [
            [Paragraph("<b>Tipo de Cálculo</b>", style_label), Paragraph(tipo_calculo, style_value)],
        ]
        
        # ===== Informações específicas da LATAM =====
        if 'LATAM' in companhia.upper() and 'tipo_tarifa' in cotacao:
            tipo_tarifa = cotacao.get('tipo_tarifa', 'Standard')
            comp_data.append([Paragraph("<b>Tarifa LATAM</b>", style_label), Paragraph(tipo_tarifa, style_value)])
            
            if tipo_tarifa == 'Standard':
                bagagens_inclusas = cotacao.get('bagagens_inclusas', 0)
                comp_data.append([Paragraph("<b>Bagagens Inclusas</b>", style_label), 
                                 Paragraph(f"{bagagens_inclusas} bagagem(ns) (1 por passageiro)", style_value)])
        
        comp_table = Table(comp_data, colWidths=[5*cm, 12*cm])
        comp_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(comp_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # ============= VIAJANTES =============
        elements.append(Paragraph("👥 VIAJANTES", style_section))
        
        passageiros = cotacao.get('passageiros', 1) or 1
        bebes = cotacao.get('bebes', 0) or 0
        num_bagagens = cotacao.get('num_bagagens', 0) or 0
        
        viajantes_data = [
            [Paragraph("<b>Passageiros Pagantes</b>", style_label), Paragraph(str(passageiros), style_value_right)],
            [Paragraph("<b>Bebês (até 2 anos)</b>", style_label), Paragraph(str(bebes), style_value_right)],
            [Paragraph("<b>Total de Viajantes</b>", style_label), Paragraph(str(passageiros + bebes), style_value_right)],
        ]
        
        # ===== Bagagens adicionais LATAM =====
        if 'LATAM' in companhia.upper() and 'bagagens_adicionais' in cotacao:
            bagagens_adicionais = cotacao.get('bagagens_adicionais', 0)
            viajantes_data.append([Paragraph("<b>Bagagens Adicionais</b>", style_label), 
                                   Paragraph(str(bagagens_adicionais), style_value_right)])
        else:
            viajantes_data.append([Paragraph("<b>Bagagens Despachadas</b>", style_label), 
                                   Paragraph(str(num_bagagens), style_value_right)])
        
        viajantes_table = Table(viajantes_data, colWidths=[8*cm, 8*cm])
        viajantes_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(viajantes_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # ============= VALORES =============
        elements.append(Paragraph("💰 DETALHAMENTO DOS VALORES", style_section))
        
        simbolo = get_currency_symbol(cotacao.get('moeda', 'BRL'))
        
        milhas_total = cotacao.get('milhas_total', 0)
        valor_milheiro = cotacao.get('valor_milheiro', 0)
        taxa_embarque = cotacao.get('taxa_embarque', 0)
        valor_bagagens = cotacao.get('valor_bagagens', 0)
        desagio_percentual = cotacao.get('desagio_percentual', 0)
        total_geral = cotacao.get('total_geral', 0)
        valor_por_pax = total_geral / max(passageiros, 1)
        
        valores_data = []
        
        # ===== Milhas =====
        if milhas_total > 0:
            if 'LATAM' in companhia.upper():
                # LATAM: Mostrar milhas por passageiro e total
                milhas_por_pax = cotacao.get('milhas_por_pax', milhas_total / passageiros if passageiros > 0 else milhas_total)
                valores_data.append([
                    Paragraph("Milhas por Passageiro", style_label), 
                    Paragraph(formatar_milhas(milhas_por_pax), style_value_right)
                ])
                valores_data.append([
                    Paragraph("Milhas Totais", style_label), 
                    Paragraph(formatar_milhas(milhas_total), style_value_right)
                ])
            else:
                # Outras companhias: Milhas são totais
                valores_data.append([
                    Paragraph("Milhas/Pontos Totais", style_label), 
                    Paragraph(formatar_milhas(milhas_total), style_value_right)
                ])
        
        if valor_milheiro > 0:
            valores_data.append([
                Paragraph(f"Valor por Milheiro ({simbolo})", style_label), 
                Paragraph(f"{simbolo} {formatar_valor_br(valor_milheiro)}", style_value_right)
            ])
        
        # ===== Desconto Azul =====
        if 'AZUL' in companhia.upper() and 'desconto_taxa_aplicado' in cotacao:
            desconto = cotacao.get('desconto_taxa_aplicado', 0)
            if desconto > 0:
                valores_data.append([
                    Paragraph("🎁 Desconto Azul (5% OFF taxa)", style_label), 
                    Paragraph(f"- {simbolo} {formatar_valor_br(desconto)}", style_value_right)
                ])
                # Usar taxa com desconto no lugar da taxa original
                taxa_para_mostrar = cotacao.get('taxa_com_desconto', taxa_embarque * passageiros)
                valores_data.append([
                    Paragraph(f"Taxa de Embarque c/ desconto ({passageiros} pax)", style_label), 
                    Paragraph(f"{simbolo} {formatar_valor_br(taxa_para_mostrar)}", style_value_right)
                ])
            else:
                valores_data.append([
                    Paragraph(f"Taxa de Embarque ({passageiros} pax)", style_label), 
                    Paragraph(f"{simbolo} {formatar_valor_br(taxa_embarque * passageiros)}", style_value_right)
                ])
        else:
            if taxa_embarque > 0:
                valores_data.append([
                    Paragraph(f"Taxa de Embarque ({passageiros} pax)", style_label), 
                    Paragraph(f"{simbolo} {formatar_valor_br(taxa_embarque * passageiros)}", style_value_right)
                ])
        
        if desagio_percentual > 0:
            valores_data.append([
                Paragraph("Deságio Aplicado (%)", style_label), 
                Paragraph(f"{desagio_percentual:.1f}%", style_value_right)
            ])
        
        if valor_bagagens > 0:
            if 'LATAM' in companhia.upper() and 'bagagens_adicionais' in cotacao:
                bagagens_adicionais = cotacao.get('bagagens_adicionais', 0)
                valores_data.append([
                    Paragraph(f"Bagagens Adicionais ({bagagens_adicionais} uni)", style_label), 
                    Paragraph(f"{simbolo} {formatar_valor_br(valor_bagagens)}", style_value_right)
                ])
            else:
                valores_data.append([
                    Paragraph(f"Valor das Bagagens ({num_bagagens} uni)", style_label), 
                    Paragraph(f"{simbolo} {formatar_valor_br(valor_bagagens)}", style_value_right)
                ])
        
        # Subtotal antes do total
        subtotal = total_geral - valor_bagagens if 'LATAM' in companhia.upper() else total_geral - valor_bagagens
        if len(valores_data) > 0:
            valores_data.append([
                Paragraph("<b>SUBTOTAL</b>", style_label), 
                Paragraph(f"<b>{simbolo} {formatar_valor_br(subtotal)}</b>", style_value_right)
            ])
        
        valores_data.append([
            Paragraph("<b>TOTAL GERAL</b>", style_label), 
            Paragraph(f"<b>{simbolo} {formatar_valor_br(total_geral)}</b>", style_value_right)
        ])
        
        valores_table = Table(valores_data, colWidths=[8*cm, 8*cm])
        valores_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (-2, -1), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ('LINEABOVE', (0, -1), (0, -1), 1, colors.HexColor('#CCCCCC')),
        ]))
        elements.append(valores_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # ============= VALOR POR PASSAGEIRO =============
        pax_data = [
            [Paragraph("<b>VALOR POR PASSAGEIRO</b>", style_label), 
             Paragraph(f"{simbolo} {formatar_valor_br(valor_por_pax)}", style_total)],
        ]
        
        pax_table = Table(pax_data, colWidths=[8*cm, 8*cm])
        pax_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f8ff')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#3d8bfd')),
        ]))
        elements.append(pax_table)
        
        # ============= OBSERVAÇÕES =============
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("📝 OBSERVAÇÕES", style_section))
        
        obs_lines = [
            f"• Esta cotação foi gerada pelo sistema DBMILESX em {data_emissao}",
            f"• Tipo de viagem: {tipo_viagem}",
            f"• Data de ida: {data_ida}",
        ]
        
        if tipo_viagem != "Somente Ida" and data_volta != "Não informada":
            obs_lines.append(f"• Data de volta: {data_volta}")
        
        if 'LATAM' in companhia.upper():
            if tipo_tarifa == 'Standard':
                obs_lines.append("• Tarifa Standard: 1 bagagem despachada por passageiro já está INCLUSA no valor")
            obs_lines.append("• Bagagens adicionais foram calculadas separadamente")
        
        if 'AZUL' in companhia.upper() and 'desconto_taxa_aplicado' in cotacao and cotacao.get('desconto_taxa_aplicado', 0) > 0:
            obs_lines.append("• Desconto de 5% na taxa de embarque aplicado (Promoção Azul Pontos + Dinheiro)")
        
        obs_lines.append("• Os valores apresentados são apenas para fins de CUSTO interno")
        obs_lines.append("• Bebês não pagam passagem, apenas taxas quando aplicável")
        
        obs_text = "<br/>".join(obs_lines)
        
        obs = Paragraph(obs_text, style_observacao)
        elements.append(obs)
        
        # ============= RODAPÉ =============
        elements.append(Spacer(1, 1*cm))
        rodape_texto = "DBMILESX - Sistema de Cotação Aérea | Relatório de CUSTO (uso interno)"
        rodape = Paragraph(rodape_texto, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER))
        elements.append(rodape)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"CUSTO_{cotacao.get('nome_cotacao', 'cotacao')}_{timestamp}.pdf"
        
        return buffer, nome_arquivo
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de custo: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def gerar_relatorio_venda_pdf(cotacao, valor_venda, nome_vendedor, logo_empresa=None):
    """
    Gera relatório de VENDA profissional para o cliente
    CORRIGIDO: Inclui datas e oculta volta quando somente ida
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        import io
        from datetime import datetime
        import tempfile
        import os
        import base64
        import json
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Cores refinadas
        cor_primaria = colors.HexColor('#1e3c72')  # Azul escuro
        cor_destaque = colors.HexColor('#2E7D32')  # Verde mais suave
        cor_borda = colors.HexColor('#e0e0e0')
        cor_fundo = colors.HexColor('#fafafa')
        
        # Dados da cotação
        passageiros = cotacao.get('passageiros', 1) or 1
        bebes = cotacao.get('bebes', 0) or 0
        num_bagagens = cotacao.get('num_bagagens', 0) or 0
        companhia = cotacao.get('companhia', 'LATAM Airlines')
        origem = cotacao.get('origem', '???')
        destino = cotacao.get('destino', '???')
        nome_cotacao = cotacao.get('nome_cotacao', 'Cotação')
        data_calculo = cotacao.get('data_calculo', '')
        data_formatada = data_calculo[:10] if data_calculo and len(data_calculo) >= 10 else datetime.now().strftime("%d/%m/%Y")
        simbolo = get_currency_symbol(cotacao.get('moeda', 'BRL'))
        
        # ===== EXTRAIR DATAS DOS METADADOS =====
        metadata = cotacao.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        tipo_viagem = metadata.get('tipo_viagem', cotacao.get('tipo_viagem', 'Ida e Volta'))
        data_ida = metadata.get('data_ida', 'Não informada')
        data_volta = metadata.get('data_volta', 'Não informada')
        
        # ===== CABEÇALHO COM LOGOS =====
        cabecalho = []
        
        # Logo da empresa (esquerda)
        if logo_empresa and os.path.exists(logo_empresa):
            try:
                img_empresa = Image(logo_empresa, width=4*cm, height=2*cm, kind='proportional')
                cabecalho.append(img_empresa)
            except:
                cabecalho.append(Paragraph("", styles['Normal']))
        else:
            cabecalho.append(Paragraph("", styles['Normal']))
        
        # Título central refinado
        cabecalho.append(Paragraph(
            "<para align='center'><font size='22' color='#1e3c72'><b>ORÇAMENTO</b></font><br/>"
            "<font size='10' color='#666666'>Sistema de Cotação Aérea</font></para>",
            styles['Normal']
        ))
        
        # Logo da companhia (direita)
        logo_companhia_path = None
        logo_adicionada = False
        
        try:
            from utils import carregar_imagem_companhia
            
            codigo = 'latam'
            if 'gol' in companhia.lower():
                codigo = 'gol'
            elif 'azul' in companhia.lower():
                codigo = 'azul'
            elif 'american' in companhia.lower():
                codigo = 'american'
            
            logo_base64 = carregar_imagem_companhia(codigo)
            
            if logo_base64 and len(logo_base64) > 100:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    tmp.write(base64.b64decode(logo_base64))
                    logo_companhia_path = tmp.name
                
                if os.path.exists(logo_companhia_path):
                    img_companhia = Image(logo_companhia_path, width=4*cm, height=2*cm, kind='proportional')
                    cabecalho.append(img_companhia)
                    logo_adicionada = True
        except:
            pass
        
        if not logo_adicionada:
            cabecalho.append(Paragraph("", styles['Normal']))
        
        # Tabela do cabeçalho
        tabela_cabecalho = Table([cabecalho], colWidths=[5*cm, 6*cm, 5*cm])
        tabela_cabecalho.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(tabela_cabecalho)
        story.append(Spacer(1, 0.5*cm))
        
        # Linha decorativa sutil
        story.append(Table([[""]], colWidths=[16*cm], rowHeights=[0.02*cm]))
        story.append(Spacer(1, 0.5*cm))
        
        # Informação do vendedor
        story.append(Paragraph(
            f"<para align='right'><font size='9' color='#666666'>Preparado por: {nome_vendedor} • {datetime.now().strftime('%d/%m/%Y %H:%M')}</font></para>",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.3*cm))
        
        # ===== CARD DA COMPANHIA =====
        card_companhia = Table(
            [[Paragraph(f"<para align='center'><font size='14' color='#1e3c72'><b>{companhia}</b></font></para>", styles['Normal'])]],
            colWidths=[16*cm]
        )
        card_companhia.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cor_fundo),
            ('BOX', (0, 0), (-1, -1), 1, cor_borda),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(card_companhia)
        story.append(Spacer(1, 0.5*cm))
        
        # ===== DADOS DO VOO EM GRID =====
        dados_voo = [
            [Paragraph("<b>📍 Origem</b>", styles['Normal']), origem,
             Paragraph("<b>🎯 Destino</b>", styles['Normal']), destino],
            [Paragraph("<b>✈️ Tipo</b>", styles['Normal']), tipo_viagem,
             Paragraph("<b>📅 Ida</b>", styles['Normal']), data_ida],
        ]
        
        # Adicionar data de volta apenas se não for somente ida
        if tipo_viagem != "Somente Ida" and data_volta != "Não informada":
            dados_voo.append([
                Paragraph("<b>📅 Volta</b>", styles['Normal']), data_volta,
                Paragraph("<b>👥 Pax</b>", styles['Normal']), str(passageiros)
            ])
        else:
            dados_voo.append([
                Paragraph("<b>📅 Volta</b>", styles['Normal']), "N/A",
                Paragraph("<b>👥 Pax</b>", styles['Normal']), str(passageiros)
            ])
        
        dados_voo.append([
            Paragraph("<b>👶 Bebês</b>", styles['Normal']), str(bebes),
            Paragraph("<b>🧳 Bagagens</b>", styles['Normal']), str(num_bagagens)
        ])
        
        tabela_voo = Table(dados_voo, colWidths=[2.5*cm, 4*cm, 2.5*cm, 4*cm])
        tabela_voo.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, cor_borda),
            ('GRID', (0, 0), (-1, -1), 1, cor_borda),
        ]))
        story.append(tabela_voo)
        story.append(Spacer(1, 0.5*cm))
        
        # ===== VALORES =====
        story.append(Paragraph(
            "<para align='left'><font size='14' color='#1e3c72'><b>💰 DETALHAMENTO</b></font></para>",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.3*cm))
        
        valor_por_pax = valor_venda / max(passageiros, 1)
        
        # Formatação brasileira
        valor_venda_str = f"{valor_venda:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        valor_por_pax_str = f"{valor_por_pax:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Tabela de valores com design refinado
        if passageiros > 1:
            dados_valores = [
                ["Descrição", "Valor Total", f"Por Passageiro ({passageiros} pax)"],
                ["Passagens Aéreas", f"{simbolo} {valor_venda_str}", f"{simbolo} {valor_por_pax_str}"],
            ]
            col_widths = [6*cm, 5*cm, 5*cm]
        else:
            dados_valores = [
                ["Descrição", "Valor Total"],
                ["Passagens Aéreas", f"{simbolo} {valor_venda_str}"],
            ]
            col_widths = [10*cm, 6*cm]
        
        tabela_valores = Table(dados_valores, colWidths=col_widths)
        tabela_valores.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), cor_primaria),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, cor_borda),
            ('GRID', (0, 0), (-1, -1), 1, cor_borda),
        ]))
        
        # Se tiver mais de uma coluna, alinha a última à direita
        if passageiros > 1:
            tabela_valores.setStyle(TableStyle([
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ]))
        
        story.append(tabela_valores)
        story.append(Spacer(1, 0.5*cm))
        
        # ===== TOTAL EM DESTAQUE =====
        story.append(Paragraph(
            "<para align='center'><font size='12' color='#666666'><b>TOTAL DO ORÇAMENTO</b></font></para>",
            styles['Normal']
        ))
        
        story.append(Paragraph(
            f"<para align='center'><font size='32' color='#1e3c72'><b>{simbolo} {valor_venda_str}</b></font></para>",
            styles['Normal']
        ))
        
        if passageiros > 1:
            story.append(Paragraph(
                f"<para align='center'><font size='12' color='#666666'>Valor por passageiro: {simbolo} {valor_por_pax_str}</font></para>",
                styles['Normal']
            ))
        
        story.append(Spacer(1, 0.8*cm))
        
        # ===== INFORMAÇÕES EM CARD =====
        info_card = []
        informacoes = [
            f"📅 Viagem: {tipo_viagem} • Ida: {data_ida}",
        ]
        
        if tipo_viagem != "Somente Ida" and data_volta != "Não informada":
            informacoes.append(f"📅 Volta: {data_volta}")
        
        informacoes.extend([
            "📅 Orçamento válido por 7 dias",
            "💰 Valores incluem taxas de embarque",
            "👶 Bebês não pagam passagem (apenas taxas)",
            "✈️ Consulte disponibilidade antes da emissão"
        ])
        
        for info in informacoes:
            info_card.append([Paragraph(f"<font size='9'>{info}</font>", styles['Normal'])])
        
        tabela_info = Table(info_card, colWidths=[16*cm])
        tabela_info.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cor_fundo),
            ('BOX', (0, 0), (-1, -1), 1, cor_borda),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(tabela_info)
        story.append(Spacer(1, 1*cm))
        
        # ===== ASSINATURAS =====
        assinaturas = Table([
            ["_________________________", "_________________________"],
            ["Cliente", "DBMILESX"]
        ], colWidths=[8*cm, 8*cm])
        assinaturas.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, 1), 'CENTER'),
            ('ALIGN', (1, 1), (1, 1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.gray),
        ]))
        story.append(assinaturas)
        
        # ===== RODAPÉ =====
        story.append(Spacer(1, 0.8*cm))
        story.append(Paragraph(
            f"<para align='center'><font size='7' color='#999999'>Documento gerado pelo sistema DBMILESX • {datetime.now().strftime('%d/%m/%Y %H:%M')}</font></para>",
            styles['Normal']
        ))
        
        # Gerar PDF
        doc.build(story)
        buffer.seek(0)
        
        # Limpar arquivo temporário da logo
        if logo_companhia_path and os.path.exists(logo_companhia_path):
            try:
                os.unlink(logo_companhia_path)
            except:
                pass
        
        # Nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"ORCAMENTO_{nome_cotacao.replace(' ', '_')}_{timestamp}.pdf"
        
        return buffer, nome_arquivo
        
    except Exception as e:
        print(f"❌ Erro detalhado: {e}")
        import traceback
        traceback.print_exc()
        return None, None