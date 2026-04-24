"""
application/report_generator.py
==============================
Servicio encargado de generar el informe académico en PDF.
Utiliza fpdf2 para el diseño y soporta caracteres Unicode.
"""

import logging
from typing import Any
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
from domain.models import ScrapedData

logger = logging.getLogger(__name__)

class PersonalityReportPDF(FPDF):
    def header(self):
        # Logo o Título Superior
        self.set_font("helvetica", "B", 16)
        self.set_text_color(41, 128, 185) # Azul institucional
        self.cell(0, 10, "INFORME PSICOLÓGICO DIGITAL - BIG FIVE (OCEAN)", ln=True, align="C")
        self.set_font("helvetica", "I", 10)
        self.set_text_color(127, 140, 141) # Gris
        self.cell(0, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(149, 165, 166)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}} - Análisis Académico de Personalidad en Redes Sociales", align="C")

    def chapter_title(self, title, color=(44, 62, 80)):
        self.set_font("helvetica", "B", 12)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f"  {title}", ln=True, fill=True)
        self.ln(5)

    def trait_row(self, label, score, interpretation, evidence):
        # Resetear X al margen izquierdo
        self.set_x(self.l_margin)
        
        # Título del rasgo y Score
        self.set_font("helvetica", "B", 11)
        self.set_text_color(52, 73, 94)
        self.cell(0, 8, f"{label}: {int(score*100)}%", ln=True)
        
        # Barra de progreso simplificada
        x_start = self.get_x()
        y_start = self.get_y()
        self.set_fill_color(236, 240, 241)
        self.rect(x_start, y_start, 100, 3, "F")
        fill_width = score * 100
        if score > 0.7: self.set_fill_color(46, 204, 113)
        elif score > 0.4: self.set_fill_color(241, 196, 15)
        else: self.set_fill_color(231, 76, 60)
        self.rect(x_start, y_start, fill_width, 3, "F")
        self.ln(6)
        
        # Texto descriptivo - Asegurar X inicial
        self.set_x(self.l_margin)
        self.set_font("helvetica", "", 10)
        self.set_text_color(44, 62, 80)
        self.multi_cell(0, 6, f"Interpretacion: {interpretation}")
        
        self.set_x(self.l_margin)
        self.set_font("helvetica", "I", 9)
        self.set_text_color(127, 140, 141)
        ev_text = ", ".join(evidence) if isinstance(evidence, list) else str(evidence)
        self.multi_cell(0, 5, f"Evidencia: {ev_text}")
        self.ln(5)

class ReportGeneratorUseCase:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _clean_text(self, text: Any) -> str:
        """Elimina emojis y caracteres no compatibles con fuentes estándar de PDF."""
        if not text: return "N/A"
        # Mantener solo caracteres ASCII básicos
        return "".join(c for c in str(text) if ord(c) < 128)

    def execute(self, data: dict) -> str:
        """Genera el PDF y devuelve la ruta del archivo."""
        username = data.get("profile", {}).get("username", "unknown")
        filename = f"Reporte_Personalidad_{username}.pdf"
        file_path = self.output_dir / filename

        pdf = PersonalityReportPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # --- 1. Información del Perfil ---
        pdf.chapter_title("1. INFORMACION DEL PERFIL")
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(44, 62, 80)
        profile = data.get("profile", {})
        pdf.cell(0, 8, f"Usuario: @{self._clean_text(profile.get('username'))}", ln=True)
        pdf.cell(0, 8, f"Nombre Completo: {self._clean_text(profile.get('full_name'))}", ln=True)
        pdf.cell(0, 8, f"Seguidores: {profile.get('followers_count')} | Seguidos: {profile.get('following_count')}", ln=True)
        pdf.multi_cell(0, 8, f"Biografia: {self._clean_text(profile.get('bio'))}")
        pdf.ln(5)

        # --- 2. Análisis de Personalidad (OCEAN) ---
        pdf.chapter_title("2. ANALISIS DE RASGOS (MODELO BIG FIVE)")
        
        personality = data.get("personality_report", {})
        summary = personality.get("summary", "No se pudo generar un resumen detallado.")
        pdf.set_font("helvetica", "I", 10)
        pdf.set_text_color(52, 73, 94)
        pdf.multi_cell(0, 6, self._clean_text(summary))
        pdf.ln(5)

        traits = personality.get("traits", {})
        ocean_map = {
            "openness": "Apertura a la Experiencia",
            "conscientiousness": "Responsabilidad",
            "extraversion": "Extraversion",
            "agreeableness": "Amabilidad",
            "neuroticism": "Neuroticismo"
        }

        for key, label in ocean_map.items():
            trait = traits.get(key, {})
            pdf.trait_row(
                label, 
                trait.get("score", 0), 
                self._clean_text(trait.get("interpretation", "Sin datos")), 
                [self._clean_text(e) for e in trait.get("evidence", [])]
            )

        # --- 3. Notas Académicas ---
        pdf.chapter_title("3. NOTAS ACADEMICAS Y SESGOS", color=(52, 73, 94))
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(44, 62, 80)
        pdf.multi_cell(0, 6, f"Notas: {self._clean_text(personality.get('academic_notes'))}")
        pdf.ln(3)
        biases = personality.get("potential_biases", [])
        if biases:
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 8, "Sesgos detectados:", ln=True)
            pdf.set_font("helvetica", "", 10)
            for b in biases:
                # Usamos multi_cell para que el texto largo no se salga del margen
                pdf.multi_cell(0, 6, f" - {self._clean_text(b)}")
                pdf.ln(1)

        pdf.output(str(file_path))
        logger.info(f"📄 Reporte PDF generado con éxito: {file_path}")
        return str(file_path)
