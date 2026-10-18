from __future__ import annotations

from datetime import datetime
import io
import json
import logging
from typing import Any
from zoneinfo import ZoneInfo

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.audit_log import SystemAuditLog

logger = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")


class AuditNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic page count, headers, and footers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#0f172a"))
            self.drawString(36, 562, "NETBACKUP — SYSTEM AUDIT & SECURITY MONITORING REPORT")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawRightString(806, 562, "CONFIDENTIAL / INTERNAL USE ONLY")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 556, 806, 556)

        # Running Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 38, 806, 38)

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(36, 26, "PT LUCKY MOM INDONESIA — IT INFRASTRUCTURE & CYBER DEFENSE")
        page_str = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(806, 26, page_str)
        self.restoreState()


class AuditExportService:
    @staticmethod
    def export_excel(
        logs: list[SystemAuditLog],
        stats: dict[str, Any],
        period_label: str = "Semua Riwayat",
    ) -> bytes:
        wb = openpyxl.Workbook()

        # Styles
        font_title = Font(name="Calibri", size=14, bold=True, color="1E293B")
        font_sub = Font(name="Calibri", size=10, italic=True, color="64748B")
        font_th = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        font_data = Font(name="Calibri", size=9)
        font_bold = Font(name="Calibri", size=9, bold=True)

        fill_header = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        fill_crit = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        fill_warn = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        fill_err = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid")
        fill_info = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
        fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        border_thin = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # ---------------------------------------------------------------------
        # Sheet 1: Audit Log Records
        # ---------------------------------------------------------------------
        ws_logs = wb.active
        ws_logs.title = "Audit Logs"
        ws_logs.views.sheetView[0].showGridLines = True

        # Header Titles
        ws_logs["A1"] = "NETBACKUP — LAPORAN AUDIT & KEAMANAN SISTEM"
        ws_logs["A1"].font = font_title
        ws_logs["A2"] = f"Periode: {period_label} | Dicetak: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')} | PT Lucky Mom Indonesia"
        ws_logs["A2"].font = font_sub

        headers = [
            "No",
            "Waktu (WIB)",
            "Kategori",
            "Severity",
            "Event Type",
            "IP Sumber",
            "Aktor / Username",
            "Endpoint",
            "Pesan / Aktivitas",
            "Detail Insiden (JSON)",
        ]

        for col_idx, th in enumerate(headers, 1):
            cell = ws_logs.cell(row=4, column=col_idx, value=th)
            cell.font = font_th
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = border_thin

        ws_logs.row_dimensions[4].height = 24

        for row_idx, log in enumerate(logs, 5):
            local_time = log.created_at.astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S")
            sev = (log.severity or "").upper()
            details_str = json.dumps(log.details, ensure_ascii=False) if log.details else ""

            row_data = [
                row_idx - 4,
                local_time,
                log.category,
                sev,
                log.event_type,
                log.source_ip or "-",
                log.username or "-",
                log.endpoint or "-",
                log.message,
                details_str,
            ]

            sev_fill = None
            if sev == "CRITICAL":
                sev_fill = fill_crit
            elif sev == "WARNING":
                sev_fill = fill_warn
            elif sev == "ERROR":
                sev_fill = fill_err
            elif sev == "INFO":
                sev_fill = fill_info
            elif (row_idx % 2) == 0:
                sev_fill = fill_zebra

            for col_idx, val in enumerate(row_data, 1):
                cell = ws_logs.cell(row=row_idx, column=col_idx, value=val)
                cell.font = font_bold if col_idx in [1, 4] else font_data
                cell.border = border_thin
                cell.alignment = align_center if col_idx in [1, 2, 3, 4, 6] else align_left
                if sev_fill:
                    cell.fill = sev_fill

            ws_logs.row_dimensions[row_idx].height = 20

        # Auto fit column widths
        col_widths = {1: 6, 2: 20, 3: 15, 4: 12, 5: 25, 6: 18, 7: 18, 8: 25, 9: 45, 10: 40}
        for col_idx, width in col_widths.items():
            ws_logs.column_dimensions[get_column_letter(col_idx)].width = width

        ws_logs.auto_filter.ref = f"A4:J{max(4 + len(logs), 4)}"

        # ---------------------------------------------------------------------
        # Sheet 2: Executive Summary & Statistics
        # ---------------------------------------------------------------------
        ws_sum = wb.create_sheet(title="Executive Summary")
        ws_sum.views.sheetView[0].showGridLines = True

        ws_sum["A1"] = "RINGKASAN EKSEKUTIF PEMANTAUAN LOG & INSIDEN"
        ws_sum["A1"].font = font_title
        ws_sum["A2"] = f"Periode: {period_label} | Total Log Dianalisis: {stats.get('total_logs', 0)}"
        ws_sum["A2"].font = font_sub

        # KPI Table
        kpi_headers = ["Indikator Kinerja Utama", "Nilai Agregat"]
        for col_idx, th in enumerate(kpi_headers, 1):
            cell = ws_sum.cell(row=4, column=col_idx, value=th)
            cell.font = font_th
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = border_thin

        kpi_metrics = [
            ("Total Seluruh Log Tercatat", stats.get("total_logs", 0)),
            ("Insiden Keamanan / Ancaman (Security Alerts)", stats.get("security_incidents", 0)),
            ("Percobaan Login Gagal (Failed Logins)", stats.get("failed_logins", 0)),
            ("Kegagalan Sistem / Error Teknis", stats.get("system_errors", 0)),
        ]

        for r_idx, (label, val) in enumerate(kpi_metrics, 5):
            c1 = ws_sum.cell(row=r_idx, column=1, value=label)
            c2 = ws_sum.cell(row=r_idx, column=2, value=val)
            c1.font = font_bold
            c2.font = font_bold
            c1.border = border_thin
            c2.border = border_thin
            c2.alignment = align_center
            if "Keamanan" in label and val > 0:
                c1.fill = fill_crit
                c2.fill = fill_crit

        # Category Breakdown
        ws_sum["D4"] = "Kategori Log"
        ws_sum["E4"] = "Jumlah Event"
        ws_sum["D4"].font = font_th
        ws_sum["E4"].font = font_th
        ws_sum["D4"].fill = fill_header
        ws_sum["E4"].fill = fill_header
        ws_sum["D4"].border = border_thin
        ws_sum["E4"].border = border_thin

        cat_data = stats.get("category_breakdown", {})
        for r_idx, (cat, cnt) in enumerate(cat_data.items(), 5):
            c1 = ws_sum.cell(row=r_idx, column=4, value=cat)
            c2 = ws_sum.cell(row=r_idx, column=5, value=cnt)
            c1.font = font_data
            c2.font = font_bold
            c1.border = border_thin
            c2.border = border_thin
            c2.alignment = align_center

        ws_sum.column_dimensions["A"].width = 35
        ws_sum.column_dimensions["B"].width = 18
        ws_sum.column_dimensions["D"].width = 20
        ws_sum.column_dimensions["E"].width = 18

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def export_pdf(
        logs: list[SystemAuditLog],
        stats: dict[str, Any],
        period_label: str = "Semua Riwayat",
    ) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=45,
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
        )
        style_sub = ParagraphStyle(
            "DocSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64748b"),
        )
        style_th = ParagraphStyle(
            "TableHead",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1,
        )
        style_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1e293b"),
        )
        style_cell_center = ParagraphStyle(
            "TableCellCenter",
            parent=style_cell,
            alignment=1,
        )
        style_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=style_cell,
            fontName="Helvetica-Bold",
        )

        story = []

        # Header Title
        story.append(Paragraph("NETBACKUP — LAPORAN AUDIT & KEAMANAN SISTEM", style_title))
        printed_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
        story.append(
            Paragraph(
                f"PT LUCKY MOM INDONESIA &nbsp;|&nbsp; <b>Periode:</b> {period_label} &nbsp;|&nbsp; <b>Waktu Cetak:</b> {printed_time}",
                style_sub,
            )
        )
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

        # KPI Metrics Cards (Table)
        kpi_data = [
            [
                Paragraph("<b>TOTAL LOG TERCATAT</b>", style_cell_center),
                Paragraph("<b>INSIDEN KEAMANAN (ALERTS)</b>", style_cell_center),
                Paragraph("<b>LOGIN GAGAL</b>", style_cell_center),
                Paragraph("<b>SYSTEM ERRORS</b>", style_cell_center),
            ],
            [
                Paragraph(f"<font size=14><b>{stats.get('total_logs', 0)}</b></font>", style_cell_center),
                Paragraph(f"<font size=14 color='#dc2626'><b>{stats.get('security_incidents', 0)}</b></font>", style_cell_center),
                Paragraph(f"<font size=14 color='#d97706'><b>{stats.get('failed_logins', 0)}</b></font>", style_cell_center),
                Paragraph(f"<font size=14 color='#b91c1c'><b>{stats.get('system_errors', 0)}</b></font>", style_cell_center),
            ],
        ]
        t_kpi = Table(kpi_data, colWidths=[192, 192, 192, 192])
        t_kpi.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(t_kpi)
        story.append(Spacer(1, 14))

        # Table of Audit Log Records
        story.append(Paragraph(f"<b>Daftar Riwayat Kejadian ({len(logs)} rekaman ditampilkan):</b>", style_cell_bold))
        story.append(Spacer(1, 6))

        table_headers = [
            Paragraph("No", style_th),
            Paragraph("Waktu (WIB)", style_th),
            Paragraph("Kategori", style_th),
            Paragraph("Severity", style_th),
            Paragraph("Event Type", style_th),
            Paragraph("IP Sumber", style_th),
            Paragraph("Aktor", style_th),
            Paragraph("Deskripsi & Pesan Insiden", style_th),
        ]
        rows = [table_headers]

        for idx, log in enumerate(logs, 1):
            local_time = log.created_at.astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S")
            sev = (log.severity or "").upper()
            sev_color = "#15803d" if sev == "INFO" else ("#b45309" if sev == "WARNING" else "#b91c1c")

            rows.append([
                Paragraph(str(idx), style_cell_center),
                Paragraph(local_time, style_cell_center),
                Paragraph(log.category, style_cell_center),
                Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", style_cell_center),
                Paragraph(f"<b>{log.event_type}</b>", style_cell),
                Paragraph(log.source_ip or "-", style_cell_center),
                Paragraph(log.username or "-", style_cell_center),
                Paragraph(log.message[:140] + ("..." if len(log.message) > 140 else ""), style_cell),
            ])

        # Widths total: 25 + 90 + 70 + 60 + 110 + 85 + 75 + 255 = 770 pt (fits landscape A4)
        t_logs = Table(rows, colWidths=[25, 90, 70, 60, 110, 85, 75, 255], repeatRows=1)
        t_logs.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ])
        )
        story.append(t_logs)
        story.append(Spacer(1, 20))

        # Signature Block
        sig_data = [
            [
                Paragraph("<b>Dibuat & Diverifikasi Oleh:</b><br/><br/><br/><br/>( ____________________________ )<br/>Administrator Jaringan / NOC", style_cell_center),
                Paragraph("<b>Mengetahui / Menyetujui:</b><br/><br/><br/><br/>( ____________________________ )<br/>Head of IT Infrastructure / Dosen Penguji TA", style_cell_center),
            ]
        ]
        t_sig = Table(sig_data, colWidths=[385, 385])
        t_sig.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(t_sig)

        doc.build(story, canvasmaker=AuditNumberedCanvas)
        return buf.getvalue()
