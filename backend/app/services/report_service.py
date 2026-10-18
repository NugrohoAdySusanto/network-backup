from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.backup_job import BackupJob
from app.models.device import Device
from app.models.snapshot import Snapshot

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count
    along with corporate headers and footers on every page.
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
            self.setFillColor(colors.HexColor("#142b39"))
            self.drawString(36, 562, "NETWORK CONFIGURATION BACKUP & AUDIT REPORT")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#647784"))
            self.drawRightString(805, 562, "PT LUCKY MOM INDONESIA : NOC")
            self.setStrokeColor(colors.HexColor("#dfe7ea"))
            self.setLineWidth(0.6)
            self.line(36, 555, 805, 555)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#dfe7ea"))
        self.setLineWidth(0.6)
        self.line(36, 32, 805, 32)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#647784"))
        self.drawString(
            36,
            22,
            "CONFIDENTIAL - FOR INTERNAL IT & NETWORK OPERATIONS USE ONLY - TA OPSI 3",
        )

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.setFont("Helvetica-Bold", 7.5)
        self.drawRightString(805, 22, page_str)

        self.restoreState()


class ReportService:
    """
    Service responsible for querying backup execution history within a specified
    date range and generating standardized Excel (.xlsx), CSV, or PDF audit reports.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def query_jobs(
        self,
        start_dt: datetime,
        end_dt: datetime,
        device_id: int | None = None,
        status: str | None = None,
    ) -> list[BackupJob]:
        stmt = (
            select(BackupJob)
            .options(
                joinedload(BackupJob.device),
                joinedload(BackupJob.snapshot).joinedload(Snapshot.config_object),
            )
            .where(
                BackupJob.created_at >= start_dt,
                BackupJob.created_at <= end_dt,
            )
        )

        if device_id:
            stmt = stmt.where(BackupJob.device_id == device_id)

        if status:
            s_clean = status.lower()
            if s_clean == "success":
                stmt = stmt.where(
                    BackupJob.state.in_(["SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"])
                )
            elif s_clean == "failed":
                stmt = stmt.where(
                    BackupJob.state.in_(
                        ["FAILED", "SKIPPED_DEVICE_DOWN", "SKIPPED_STATUS_UNKNOWN"]
                    )
                )

        stmt = stmt.order_by(BackupJob.created_at.desc())
        return list(self.db.scalars(stmt).unique().all())

    def generate_excel(
        self,
        start_dt: datetime,
        end_dt: datetime,
        device_id: int | None = None,
        status: str | None = None,
        user_name: str = "Admin",
    ) -> tuple[bytes, str]:
        """
        Generate a professional, fully styled Microsoft Excel (.xlsx) workbook
        with auto-fitted column widths, corporate headers, KPI blocks, and auto-filters.
        """
        jobs = self.query_jobs(start_dt, end_dt, device_id, status)
        total_devices_count = self.db.query(Device).count()

        start_wib = start_dt.astimezone(WIB)
        end_wib = end_dt.astimezone(WIB)
        now_wib = datetime.now(timezone.utc).astimezone(WIB)

        start_str = start_wib.strftime("%Y%m%d_%H%M")
        end_str = end_wib.strftime("%Y%m%d_%H%M")
        filename = f"network_backup_report_{start_str}_{end_str}.xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Audit Execution Log"

        # Explicitly enable gridlines
        ws.views.sheetView[0].showGridLines = True

        # Styles definition
        font_title = Font(name="Calibri", size=14, bold=True, color="123C53")
        font_subtitle = Font(name="Calibri", size=11, bold=True, color="142B39")
        font_meta = Font(name="Calibri", size=9, italic=True, color="647784")

        font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="123C53", end_color="123C53", fill_type="solid")

        font_kpi_label = Font(name="Calibri", size=8, bold=True, color="647784")
        font_kpi_val = Font(name="Calibri", size=13, bold=True, color="142B39")
        fill_kpi = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        font_data = Font(name="Calibri", size=9, color="142B39")
        font_data_bold = Font(name="Calibri", size=9, bold=True, color="142B39")
        font_mono = Font(name="Consolas", size=9, color="334155")

        font_success = Font(name="Calibri", size=9, bold=True, color="15803D")
        font_failed = Font(name="Calibri", size=9, bold=True, color="B91C1C")
        font_skipped = Font(name="Calibri", size=9, bold=True, color="B45309")

        thin_side = Side(border_style="thin", color="CBD5E1")
        border_all = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        border_header = Border(left=thin_side, right=thin_side, top=thin_side, bottom=Side(border_style="medium", color="0C2B3D"))

        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        # 1. Title & Corporate Metadata
        ws["A1"] = "PT LUCKY MOM INDONESIA : NETWORK OPERATIONS CENTER"
        ws["A1"].font = font_title

        ws["A2"] = "Network Configuration Backup & Audit Report"
        ws["A2"].font = font_subtitle

        ws["A3"] = (
            f"Period: {start_wib.strftime('%d %b %Y %H:%M')} - {end_wib.strftime('%d %b %Y %H:%M')} (WIB) | "
            f"Generated: {now_wib.strftime('%d %b %Y %H:%M:%S')} WIB | By: {user_name}"
        )
        ws["A3"].font = font_meta

        # Calculate metrics
        total_jobs = len(jobs)
        success_no_change = sum(1 for j in jobs if j.state == "SUCCESS_NO_CHANGE")
        success_changed = sum(1 for j in jobs if j.state == "SUCCESS_CHANGED")
        total_success = success_no_change + success_changed
        total_failed = sum(1 for j in jobs if j.state == "FAILED")
        total_skipped = sum(1 for j in jobs if j.state in ("SKIPPED_DEVICE_DOWN", "SKIPPED_STATUS_UNKNOWN"))
        success_rate = (total_success / total_jobs * 100.0) if total_jobs > 0 else 0.0

        # 2. KPI Summary Boxes (Rows 5 & 6)
        kpi_metrics = [
            ("MONITORED DEVICES", str(total_devices_count), "B5", "B6"),
            ("TOTAL BACKUP JOBS", str(total_jobs), "D5", "D6"),
            ("SUCCESS RATE", f"{success_rate:.1f}%", "F5", "F6"),
            ("NO-CHANGE (CAS DEDUP)", str(success_no_change), "H5", "H6"),
            ("CONFIG CHANGED", str(success_changed), "J5", "J6"),
            ("FAILED / SKIPPED", f"{total_failed} / {total_skipped}", "L5", "L6"),
        ]

        for label, val, c_top, c_bot in kpi_metrics:
            cell_top = ws[c_top]
            cell_bot = ws[c_bot]
            cell_top.value = label
            cell_top.font = font_kpi_label
            cell_top.alignment = align_center
            cell_top.fill = fill_kpi
            cell_top.border = border_all

            cell_bot.value = val
            cell_bot.font = font_kpi_val
            cell_bot.alignment = align_center
            cell_bot.fill = fill_kpi
            cell_bot.border = border_all

        # 3. Main Table Headers (Row 8)
        headers = [
            "No",
            "Execution Time (WIB)",
            "Device Hostname",
            "Management IP",
            "Vendor",
            "Model",
            "Driver Key",
            "Trigger Type",
            "Status",
            "Change Detection",
            "Zabbix Status",
            "Raw Size (KB)",
            "Normalized Size (KB)",
            "Content SHA-256",
            "Object SHA-256 (S3 Checksum)",
            "Duration (s)",
            "Failure Stage",
            "Failure Code",
            "Failure Diagnostics",
        ]

        header_row_idx = 8
        for col_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=header_row_idx, column=col_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = border_header

        ws.row_dimensions[header_row_idx].height = 24

        # 4. Data Rows (Row 9+)
        current_row = 9
        for idx, j in enumerate(jobs, start=1):
            created_wib = j.created_at.astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S") if j.created_at else "-"
            hostname = j.device.hostname if j.device else "-"
            ip = str(j.device.ip_address) if j.device else "-"
            vendor = j.device.vendor or "-" if j.device else "-"
            model = j.device.model or "-" if j.device else "-"
            driver = j.driver_key or "-"
            trigger = "Scheduled" if j.trigger_type == "scheduled" else "Manual"
            status_val = j.state
            change_val = j.change_status or "-"
            zabbix_stat = (j.zabbix_status_at_start or "-").upper()
            raw_kb = round(j.raw_size_bytes / 1024.0, 1) if j.raw_size_bytes else 0.0
            norm_kb = round(j.normalized_size_bytes / 1024.0, 1) if j.normalized_size_bytes else 0.0
            content_sha = j.content_sha256 or "-"
            obj_sha = j.snapshot.config_object.object_sha256 if (j.snapshot and j.snapshot.config_object) else "-"
            dur_s = round(j.duration_ms / 1000.0, 2) if j.duration_ms else 0.0
            fail_stage = j.failure_stage or "-"
            fail_code = j.failure_code or "-"
            fail_msg = j.failure_message or "-"

            row_data = [
                idx,
                created_wib,
                hostname,
                ip,
                vendor,
                model,
                driver,
                trigger,
                status_val,
                change_val,
                zabbix_stat,
                raw_kb,
                norm_kb,
                content_sha,
                obj_sha,
                dur_s,
                fail_stage,
                fail_code,
                fail_msg,
            ]

            fill_row = fill_zebra if idx % 2 == 0 else fill_white
            ws.row_dimensions[current_row].height = 20

            for col_idx, val in enumerate(row_data, start=1):
                c = ws.cell(row=current_row, column=col_idx, value=val)
                c.fill = fill_row
                c.border = border_all
                c.font = font_data

                # Column-specific formatting and alignments
                if col_idx == 1:  # No
                    c.alignment = align_center
                elif col_idx == 2:  # Time
                    c.alignment = align_center
                    c.font = font_mono
                elif col_idx == 3:  # Hostname
                    c.alignment = align_left
                    c.font = font_data_bold
                elif col_idx in (4, 14, 15):  # IP & SHAs
                    c.alignment = align_center
                    c.font = font_mono
                elif col_idx in (8, 10, 11):  # Trigger, Change, Zabbix
                    c.alignment = align_center
                elif col_idx == 9:  # Status
                    c.alignment = align_center
                    if "SUCCESS" in status_val:
                        c.font = font_success
                    elif "SKIPPED" in status_val:
                        c.font = font_skipped
                    else:
                        c.font = font_failed
                elif col_idx in (12, 13, 16):  # Numbers
                    c.alignment = align_right
                    c.number_format = "#,##0.0" if col_idx != 16 else "#,##0.00"
                else:
                    c.alignment = align_left

            current_row += 1

        # Auto-fit Column Widths cleanly
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            # Find max length among cells in column (from header row down)
            max_len = 0
            for cell in col:
                if cell.row >= header_row_idx and cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
            # Add padding
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # Freeze panes at data start
        ws.freeze_panes = "A9"

        # Enable auto-filter across headers
        ws.auto_filter.ref = f"A8:{get_column_letter(len(headers))}{max(current_row - 1, 8)}"

        # Save workbook to memory
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue(), filename

    def generate_csv(
        self,
        start_dt: datetime,
        end_dt: datetime,
        device_id: int | None = None,
        status: str | None = None,
    ) -> tuple[str, str]:
        jobs = self.query_jobs(start_dt, end_dt, device_id, status)

        start_str = start_dt.astimezone(WIB).strftime("%Y%m%d_%H%M")
        end_str = end_dt.astimezone(WIB).strftime("%Y%m%d_%H%M")
        filename = f"network_backup_report_{start_str}_{end_str}.csv"

        out = io.StringIO()
        # UTF-8 BOM for immediate Microsoft Excel UTF-8 support
        out.write("\ufeff")

        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "Job ID",
                "Execution Time (WIB)",
                "Device Hostname",
                "Management IP",
                "Vendor",
                "Model",
                "Driver Key",
                "Trigger Type",
                "Status",
                "Change Status",
                "Zabbix Status",
                "Raw Size (Bytes)",
                "Normalized Size (Bytes)",
                "Content SHA-256",
                "Object SHA-256",
                "Duration (s)",
                "Failure Stage",
                "Failure Code",
                "Failure Message",
            ]
        )

        for j in jobs:
            created_wib = (
                j.created_at.astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S")
                if j.created_at
                else ""
            )
            hostname = j.device.hostname if j.device else ""
            ip = str(j.device.ip_address) if j.device else ""
            vendor = j.device.vendor or "" if j.device else ""
            model = j.device.model or "" if j.device else ""
            object_sha = (
                j.snapshot.config_object.object_sha256
                if (j.snapshot and j.snapshot.config_object)
                else ""
            )
            duration_s = f"{(j.duration_ms / 1000.0):.2f}" if j.duration_ms else "0.00"

            writer.writerow(
                [
                    str(j.id),
                    created_wib,
                    hostname,
                    ip,
                    vendor,
                    model,
                    j.driver_key or "",
                    j.trigger_type,
                    j.state,
                    j.change_status or "",
                    j.zabbix_status_at_start or "",
                    j.raw_size_bytes or 0,
                    j.normalized_size_bytes or 0,
                    j.content_sha256 or "",
                    object_sha,
                    duration_s,
                    j.failure_stage or "",
                    j.failure_code or "",
                    j.failure_message or "",
                ]
            )

        return out.getvalue(), filename

    def generate_pdf(
        self,
        start_dt: datetime,
        end_dt: datetime,
        device_id: int | None = None,
        status: str | None = None,
        user_name: str = "Admin",
    ) -> tuple[bytes, str]:
        jobs = self.query_jobs(start_dt, end_dt, device_id, status)
        total_devices_count = self.db.query(Device).count()

        start_wib = start_dt.astimezone(WIB)
        end_wib = end_dt.astimezone(WIB)
        now_wib = datetime.now(timezone.utc).astimezone(WIB)

        start_str = start_wib.strftime("%Y%m%d_%H%M")
        end_str = end_wib.strftime("%Y%m%d_%H%M")
        filename = f"network_backup_report_{start_str}_{end_str}.pdf"

        # Aggregated Metrics Calculation
        total_jobs = len(jobs)
        success_no_change = sum(1 for j in jobs if j.state == "SUCCESS_NO_CHANGE")
        success_changed = sum(1 for j in jobs if j.state == "SUCCESS_CHANGED")
        total_success = success_no_change + success_changed
        total_failed = sum(1 for j in jobs if j.state == "FAILED")
        total_skipped = sum(
            1 for j in jobs if j.state in ("SKIPPED_DEVICE_DOWN", "SKIPPED_STATUS_UNKNOWN")
        )
        total_unsuccessful = total_failed + total_skipped

        success_rate = (total_success / total_jobs * 100.0) if total_jobs > 0 else 0.0

        # Vendor Aggregation
        vendor_data: dict[str, dict[str, int]] = {}
        for j in jobs:
            v_name = (j.device.vendor.strip() if j.device and j.device.vendor else "Unknown").title()
            if v_name not in vendor_data:
                vendor_data[v_name] = {"total": 0, "success": 0, "failed": 0}
            vendor_data[v_name]["total"] += 1
            if j.state in ("SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"):
                vendor_data[v_name]["success"] += 1
            else:
                vendor_data[v_name]["failed"] += 1

        # PDF Setup (A4 Landscape: 841.89 x 595.27 points)
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#142b39"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#647784"),
        )
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#123c53"),
            spaceAfter=6,
        )

        # Crisp White Table Header style for dark headers
        th_white = ParagraphStyle(
            "TableHeaderWhite",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
            alignment=0,
        )

        # Cell styles
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#142b39"),
        )
        cell_normal = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#142b39"),
        )
        cell_mono = ParagraphStyle(
            "CellMono",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#334155"),
        )

        # Dedicated Non-Overlapping KPI Card Styles
        kpi_title_style = ParagraphStyle(
            "KPITitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#647784"),
        )
        kpi_sub_style = ParagraphStyle(
            "KPISub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#647784"),
        )

        def make_kpi_val_style(color_hex: str) -> ParagraphStyle:
            return ParagraphStyle(
                f"KPIVal_{color_hex}",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=18,
                spaceBefore=3,
                spaceAfter=3,
                textColor=colors.HexColor(color_hex),
            )

        story = []

        # =========================================================================
        # 1. HEADER SECTION
        # =========================================================================
        header_table_data = [
            [
                Paragraph("<b>PT LUCKY MOM INDONESIA</b><br/><font size='7' color='#647784'>NETWORK OPERATIONS CENTER (NOC) &amp; INFRASTRUCTURE</font>", subtitle_style),
                Paragraph("<font size='8' color='#647784'><b>TIMEZONE:</b> Asia/Jakarta (WIB)</font>", subtitle_style),
            ],
            [
                Paragraph("<b>NETWORK CONFIGURATION BACKUP &amp; AUDIT REPORT</b>", title_style),
                Paragraph(
                    f"<b>Report Period:</b> {start_wib.strftime('%d %b %Y %H:%M')} - {end_wib.strftime('%d %b %Y %H:%M')}<br/>"
                    f"<b>Generated At:</b> {now_wib.strftime('%d %b %Y %H:%M:%S')} WIB<br/>"
                    f"<b>Generated By:</b> {user_name} (Admin)",
                    subtitle_style,
                ),
            ],
        ]
        header_table = Table(header_table_data, colWidths=[470, 299])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#123c53"), spaceAfter=12))

        # =========================================================================
        # 2. EXECUTIVE SUMMARY & KPI CARDS (NO OVERLAPPING TEXT)
        # =========================================================================
        rate_color = "#168453" if success_rate >= 90 else ("#b45309" if success_rate >= 70 else "#c84040")

        # Each cell contains a list of 3 separate flowable paragraphs with distinct leading
        kpi_data = [
            [
                [
                    Paragraph("MONITORED DEVICES", kpi_title_style),
                    Paragraph(str(total_devices_count), make_kpi_val_style("#142b39")),
                    Paragraph("Synced from Zabbix", kpi_sub_style),
                ],
                [
                    Paragraph("TOTAL JOBS RUN", kpi_title_style),
                    Paragraph(str(total_jobs), make_kpi_val_style("#142b39")),
                    Paragraph("Executed in Period", kpi_sub_style),
                ],
                [
                    Paragraph("SUCCESS RATE", kpi_title_style),
                    Paragraph(f"{success_rate:.1f}%", make_kpi_val_style(rate_color)),
                    Paragraph(f"{total_success} of {total_jobs} Successful", kpi_sub_style),
                ],
                [
                    Paragraph("NO-CHANGE (CAS)", kpi_title_style),
                    Paragraph(str(success_no_change), make_kpi_val_style("#0284c7")),
                    Paragraph("Deduplicated S3 Storage", kpi_sub_style),
                ],
                [
                    Paragraph("CONFIG CHANGED", kpi_title_style),
                    Paragraph(str(success_changed), make_kpi_val_style("#168453")),
                    Paragraph("New Snapshot Created", kpi_sub_style),
                ],
                [
                    Paragraph("FAILED / SKIPPED", kpi_title_style),
                    Paragraph(str(total_unsuccessful), make_kpi_val_style("#c84040" if total_unsuccessful > 0 else "#647784")),
                    Paragraph(f"{total_failed} Failed, {total_skipped} Skipped", kpi_sub_style),
                ],
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[128, 128, 128, 128, 128, 129])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#dfe7ea")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfe7ea")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # =========================================================================
        # 3. CHARTS / DIAGRAMS & UNDERLYING TABULAR DATA
        # =========================================================================
        story.append(Paragraph("1. Analytical Charts &amp; Distribution Metrics", section_style))

        # Chart 1: Outcome Distribution Pie Chart
        d1 = Drawing(160, 105)
        pie1 = Pie()
        pie1.x = 10
        pie1.y = 8
        pie1.width = 90
        pie1.height = 90

        pie1_data = []
        pie1_colors = []
        pie1_labels_legend = []

        if success_no_change > 0:
            pie1_data.append(success_no_change)
            pie1_colors.append(colors.HexColor("#0284c7"))  # Sky Blue
            pie1_labels_legend.append("No Change")
        if success_changed > 0:
            pie1_data.append(success_changed)
            pie1_colors.append(colors.HexColor("#168453"))  # Green
            pie1_labels_legend.append("Changed")
        if total_failed > 0:
            pie1_data.append(total_failed)
            pie1_colors.append(colors.HexColor("#c84040"))  # Red
            pie1_labels_legend.append("Failed")
        if total_skipped > 0:
            pie1_data.append(total_skipped)
            pie1_colors.append(colors.HexColor("#b45309"))  # Amber
            pie1_labels_legend.append("Skipped")

        if not pie1_data:
            pie1_data = [1]
            pie1_colors = [colors.HexColor("#94a3b8")]
            pie1_labels_legend = ["No Activity"]

        pie1.data = pie1_data
        pie1.slices.strokeWidth = 0.5
        pie1.slices.strokeColor = colors.white
        for idx, col in enumerate(pie1_colors):
            pie1.slices[idx].fillColor = col

        d1.add(pie1)

        # Legend for Pie 1
        legend1 = Legend()
        legend1.x = 105
        legend1.y = 85
        legend1.dx = 8
        legend1.dy = 8
        legend1.fontName = "Helvetica"
        legend1.fontSize = 7
        legend1.boxAnchor = "nw"
        legend1.columnMaximum = 4
        legend1.colorNamePairs = list(zip(pie1_colors, pie1_labels_legend))
        d1.add(legend1)

        # Table 1: Underlying Data for Outcome Distribution
        t1_rows = [
            [
                Paragraph("<b>Execution Outcome</b>", cell_bold),
                Paragraph("<b>Count</b>", cell_bold),
                Paragraph("<b>Ratio (%)</b>", cell_bold),
            ],
            [
                Paragraph("<font color='#0284c7'>■</font> Success (No Change)", cell_normal),
                Paragraph(str(success_no_change), cell_normal),
                Paragraph(f"{(success_no_change / total_jobs * 100):.1f}%" if total_jobs > 0 else "0.0%", cell_normal),
            ],
            [
                Paragraph("<font color='#168453'>■</font> Success (Changed)", cell_normal),
                Paragraph(str(success_changed), cell_normal),
                Paragraph(f"{(success_changed / total_jobs * 100):.1f}%" if total_jobs > 0 else "0.0%", cell_normal),
            ],
            [
                Paragraph("<font color='#c84040'>■</font> Failed (Error)", cell_normal),
                Paragraph(str(total_failed), cell_normal),
                Paragraph(f"{(total_failed / total_jobs * 100):.1f}%" if total_jobs > 0 else "0.0%", cell_normal),
            ],
            [
                Paragraph("<font color='#b45309'>■</font> Skipped (Down/Unknown)", cell_normal),
                Paragraph(str(total_skipped), cell_normal),
                Paragraph(f"{(total_skipped / total_jobs * 100):.1f}%" if total_jobs > 0 else "0.0%", cell_normal),
            ],
            [
                Paragraph("<b>Total Executions</b>", cell_bold),
                Paragraph(f"<b>{total_jobs}</b>", cell_bold),
                Paragraph("<b>100.0%</b>", cell_bold),
            ],
        ]
        table_outcome = Table(t1_rows, colWidths=[125, 45, 45])
        table_outcome.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ]
            )
        )

        # Chart 2: Vendor Breakdown
        d2 = Drawing(160, 105)
        pie2 = Pie()
        pie2.x = 10
        pie2.y = 8
        pie2.width = 90
        pie2.height = 90

        v_palette = [
            colors.HexColor("#3b82f6"),  # Blue
            colors.HexColor("#8b5cf6"),  # Purple
            colors.HexColor("#10b981"),  # Emerald
            colors.HexColor("#f59e0b"),  # Amber
            colors.HexColor("#ec4899"),  # Pink
        ]
        pie2_data = []
        pie2_colors = []
        pie2_labels_legend = []

        for idx, (v_name, v_metrics) in enumerate(vendor_data.items()):
            pie2_data.append(v_metrics["total"])
            c = v_palette[idx % len(v_palette)]
            pie2_colors.append(c)
            pie2_labels_legend.append(v_name[:10])

        if not pie2_data:
            pie2_data = [1]
            pie2_colors = [colors.HexColor("#94a3b8")]
            pie2_labels_legend = ["No Vendor"]

        pie2.data = pie2_data
        pie2.slices.strokeWidth = 0.5
        pie2.slices.strokeColor = colors.white
        for idx, col in enumerate(pie2_colors):
            pie2.slices[idx].fillColor = col

        d2.add(pie2)

        legend2 = Legend()
        legend2.x = 105
        legend2.y = 85
        legend2.dx = 8
        legend2.dy = 8
        legend2.fontName = "Helvetica"
        legend2.fontSize = 7
        legend2.boxAnchor = "nw"
        legend2.columnMaximum = 5
        legend2.colorNamePairs = list(zip(pie2_colors, pie2_labels_legend))
        d2.add(legend2)

        # Table 2: Underlying Data for Vendor Distribution
        t2_rows = [
            [
                Paragraph("<b>Vendor</b>", cell_bold),
                Paragraph("<b>Total</b>", cell_bold),
                Paragraph("<b>Success</b>", cell_bold),
                Paragraph("<b>Failed</b>", cell_bold),
                Paragraph("<b>SLA (%)</b>", cell_bold),
            ]
        ]
        for v_name, v_metrics in vendor_data.items():
            v_rate = (v_metrics["success"] / v_metrics["total"] * 100) if v_metrics["total"] > 0 else 0
            t2_rows.append(
                [
                    Paragraph(f"<b>{v_name}</b>", cell_normal),
                    Paragraph(str(v_metrics["total"]), cell_normal),
                    Paragraph(str(v_metrics["success"]), cell_normal),
                    Paragraph(str(v_metrics["failed"]), cell_normal),
                    Paragraph(f"{v_rate:.1f}%", cell_normal),
                ]
            )

        if len(t2_rows) == 1:
            t2_rows.append([Paragraph("No Data", cell_normal), Paragraph("0", cell_normal), Paragraph("0", cell_normal), Paragraph("0", cell_normal), Paragraph("-", cell_normal)])

        table_vendor = Table(t2_rows, colWidths=[70, 32, 35, 35, 43])
        table_vendor.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ]
            )
        )

        # Two-column container combining charts and underlying tables
        charts_combo_data = [
            [
                Paragraph("<b>Figure 1: Outcome Breakdown</b>", subtitle_style),
                "",
                Paragraph("<b>Figure 2: Distribution by Vendor</b>", subtitle_style),
                "",
            ],
            [
                d1,
                table_outcome,
                d2,
                table_vendor,
            ],
        ]
        charts_combo_table = Table(charts_combo_data, colWidths=[165, 220, 165, 219])
        charts_combo_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("SPAN", (0, 0), (1, 0)),
                    ("SPAN", (2, 0), (3, 0)),
                ]
            )
        )
        story.append(charts_combo_table)
        story.append(Spacer(1, 14))

        # =========================================================================
        # 4. INCIDENT & FAILURE LOG (AUDIT SECTION)
        # =========================================================================
        failed_jobs = [j for j in jobs if j.state in ("FAILED", "SKIPPED_DEVICE_DOWN", "SKIPPED_STATUS_UNKNOWN")]
        story.append(Paragraph(f"2. Incident &amp; Failure Log ({len(failed_jobs)} event{'s' if len(failed_jobs) != 1 else ''})", section_style))

        if failed_jobs:
            incident_rows = [
                [
                    Paragraph("<b>Time (WIB)</b>", cell_bold),
                    Paragraph("<b>Device Hostname</b>", cell_bold),
                    Paragraph("<b>IP Address</b>", cell_bold),
                    Paragraph("<b>State</b>", cell_bold),
                    Paragraph("<b>Failure Stage</b>", cell_bold),
                    Paragraph("<b>Error Code &amp; Diagnostics</b>", cell_bold),
                ]
            ]
            for fj in failed_jobs[:15]:
                f_time = fj.created_at.astimezone(WIB).strftime("%Y-%m-%d %H:%M") if fj.created_at else "-"
                f_host = fj.device.hostname if fj.device else "-"
                f_ip = str(fj.device.ip_address) if fj.device else "-"
                f_state = fj.state
                f_stage = fj.failure_stage or "-"
                f_msg = f"<b>{fj.failure_code or 'UNKNOWN'}</b>: {fj.failure_message or '-'}"
                incident_rows.append(
                    [
                        Paragraph(f_time, cell_normal),
                        Paragraph(f_host, cell_bold),
                        Paragraph(f_ip, cell_mono),
                        Paragraph(f"<font color='#c84040'><b>{f_state}</b></font>", cell_normal),
                        Paragraph(f_stage, cell_normal),
                        Paragraph(f_msg, cell_normal),
                    ]
                )
            incident_table = Table(incident_rows, colWidths=[90, 130, 85, 110, 100, 254])
            incident_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(incident_table)
        else:
            good_box = Table(
                [[
                    Paragraph(
                        "<b>100% OPERATIONAL RELIABILITY:</b> No failed or skipped backup jobs were recorded in the selected time range. "
                        "All network devices synchronized and backed up configurations successfully without transport or validation errors.",
                        cell_normal,
                    )
                ]],
                colWidths=[769],
            )
            good_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )
            story.append(good_box)

        story.append(Spacer(1, 14))

        # =========================================================================
        # 5. DETAILED BACKUP EXECUTION TABLE (CRISP WHITE HEADERS)
        # =========================================================================
        story.append(Paragraph(f"3. Detailed Backup Execution Records ({total_jobs} total records)", section_style))

        # Note: th_white ensures table header titles are bright white on dark #1e293b background!
        detail_rows = [
            [
                Paragraph("<b>#</b>", th_white),
                Paragraph("<b>Execution Time (WIB)</b>", th_white),
                Paragraph("<b>Device Hostname</b>", th_white),
                Paragraph("<b>IP Address</b>", th_white),
                Paragraph("<b>Vendor / Model</b>", th_white),
                Paragraph("<b>Type</b>", th_white),
                Paragraph("<b>Status</b>", th_white),
                Paragraph("<b>Change</b>", th_white),
                Paragraph("<b>Content SHA-256</b>", th_white),
                Paragraph("<b>Size</b>", th_white),
                Paragraph("<b>Duration</b>", th_white),
            ]
        ]

        if jobs:
            for idx, j in enumerate(jobs, start=1):
                j_time = j.created_at.astimezone(WIB).strftime("%Y-%m-%d %H:%M") if j.created_at else "-"
                j_host = j.device.hostname if j.device else "-"
                j_ip = str(j.device.ip_address) if j.device else "-"
                v_str = f"{j.device.vendor or ''} {j.device.model or ''}".strip() or "-"
                j_type = "Sched" if j.trigger_type == "scheduled" else "Manual"

                # Result badge styling
                if "SUCCESS" in j.state:
                    state_html = f"<font color='#168453'><b>{j.state}</b></font>"
                elif "SKIPPED" in j.state:
                    state_html = f"<font color='#b45309'><b>{j.state}</b></font>"
                else:
                    state_html = f"<font color='#c84040'><b>{j.state}</b></font>"

                # Change badge
                if j.change_status == "changed":
                    chg_html = "<font color='#168453'>Changed</font>"
                elif j.change_status == "no_change":
                    chg_html = "<font color='#0284c7'>No Change</font>"
                elif j.change_status == "baseline":
                    chg_html = "<font color='#8b5cf6'>Baseline</font>"
                else:
                    chg_html = "-"

                sha_disp = j.content_sha256[:10] + "..." if j.content_sha256 else "-"
                size_disp = f"{(j.normalized_size_bytes / 1024.0):.1f} KB" if j.normalized_size_bytes else "-"
                dur_disp = f"{(j.duration_ms / 1000.0):.1f}s" if j.duration_ms else "-"

                detail_rows.append(
                    [
                        Paragraph(str(idx), cell_normal),
                        Paragraph(j_time, cell_normal),
                        Paragraph(j_host, cell_bold),
                        Paragraph(j_ip, cell_mono),
                        Paragraph(v_str, cell_normal),
                        Paragraph(j_type, cell_normal),
                        Paragraph(state_html, cell_normal),
                        Paragraph(chg_html, cell_normal),
                        Paragraph(sha_disp, cell_mono),
                        Paragraph(size_disp, cell_normal),
                        Paragraph(dur_disp, cell_normal),
                    ]
                )
        else:
            detail_rows.append([Paragraph("No backup execution records match the selected date range.", cell_normal)] + [""] * 10)

        # Total available width = 769 points
        detail_col_widths = [20, 85, 115, 75, 110, 42, 115, 62, 75, 40, 30]
        detail_table = Table(detail_rows, colWidths=detail_col_widths, repeatRows=1)
        detail_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        story.append(detail_table)
        story.append(Spacer(1, 20))

        # =========================================================================
        # 6. SIGNATURE & APPROVAL BLOCK
        # =========================================================================
        sig_data = [
            [
                Paragraph("<b>Prepared By:</b><br/><br/><br/>_____________________________________<br/><b>" + user_name + "</b><br/><font size='7' color='#647784'>Network Operations Engineer</font>", cell_normal),
                Paragraph("<b>Verified &amp; Acknowledged By:</b><br/><br/><br/>_____________________________________<br/><b>IT Infrastructure &amp; Security Supervisor</b><br/><font size='7' color='#647784'>PT Lucky Mom Indonesia</font>", cell_normal),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[384, 385])
        sig_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(KeepTogether(sig_table))

        # Build Document
        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue(), filename
