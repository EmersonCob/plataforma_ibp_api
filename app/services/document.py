import hashlib
import html
from datetime import UTC, date, datetime
from io import BytesIO

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.datetime_utils import format_display_datetime
from app.core.errors import AppError
from app.models.contract import Contract
from app.services.contract_rendering import (
    COMMUNICATION_PARAGRAPHS,
    CONSULTATION_CONDITIONS,
    RESPONSIBILITY_PARAGRAPH,
    SCIENCE_DECLARATION,
    SERVICE_NATURE_PARAGRAPHS,
)
from app.services.storage import storage_service


class DocumentService:
    def generate_signed_pdf(self, db: Session, contract: Contract) -> Contract:
        if not contract.signature:
            raise AppError("Contrato ainda não possui assinatura.", 400, "contract_not_signed")
        if contract.signed_document_path:
            return contract

        signature = contract.signature
        generated_at = datetime.now(UTC)
        content_hash = hashlib.sha256(contract.content.encode("utf-8")).hexdigest()

        pdf_bytes = self._render_pdf(contract)
        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
        object_name = f"contracts/{contract.id}/signed/final-v{contract.current_version}.pdf"
        storage_service.upload_bytes(object_name, pdf_bytes, "application/pdf")

        contract.signed_document_path = object_name
        contract.signed_document_hash = pdf_hash
        contract.final_metadata = {
            "generated_at": generated_at.isoformat(),
            "signed_version": contract.current_version,
            "content_sha256": content_hash,
            "pdf_sha256": pdf_hash,
            "signature_id": signature.id,
            "signer_name": signature.signer_name,
            "signer_role": signature.signer_role,
            "signed_at": signature.signed_at.isoformat(),
            "face_photo_path": signature.face_photo_path,
            "signature_image_path": signature.signature_image_path,
            "ip_address": signature.ip_address,
            "user_agent": signature.user_agent,
        }
        db.flush()
        return contract

    def _render_pdf(self, contract: Contract) -> bytes:
        signature = contract.signature
        if not signature:
            raise AppError("Contrato ainda não possui assinatura.", 400, "contract_not_signed")

        snapshot = contract.form_snapshot or {}
        patient = snapshot.get("patient") or {}
        responsible = snapshot.get("financial_responsible") or {}

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=3 * cm,
            topMargin=3 * cm,
            bottomMargin=2 * cm,
            title=contract.title,
        )
        styles = self._styles()

        story = [
            Paragraph("IBP - Instituto Brasileiro de Psiquiatria", styles["contractBrand"]),
            Paragraph(html.escape(contract.title), styles["contractTitle"]),
            Spacer(1, 0.15 * cm),
            Paragraph(self._metadata_line(contract, signature), styles["contractMeta"]),
            Spacer(1, 0.35 * cm),
            Paragraph("1. Qualificação do paciente", styles["contractSection"]),
            self._data_table(
                [
                    ("Nome", patient.get("name")),
                    ("CPF", patient.get("cpf")),
                    ("Data de nascimento", self._format_date(patient.get("birth_date"))),
                    ("Telefone", patient.get("phone")),
                    ("Endereço", patient.get("address")),
                ],
                doc.width,
                styles,
            ),
        ]

        if any((responsible.get("name"), responsible.get("cpf"), responsible.get("phone"))):
            story.extend(
                [
                    Spacer(1, 0.28 * cm),
                    Paragraph("2. Responsável financeiro, quando houver", styles["contractSection"]),
                    self._data_table(
                        [
                            ("Nome", responsible.get("name")),
                            ("CPF", responsible.get("cpf")),
                            ("Telefone", responsible.get("phone")),
                        ],
                        doc.width,
                        styles,
                    ),
                ]
            )

        story.extend(
            [
                Spacer(1, 0.28 * cm),
                Paragraph("3. Termo de responsabilidade", styles["contractSection"]),
                Paragraph(html.escape(RESPONSIBILITY_PARAGRAPH), styles["contractBody"]),
                Spacer(1, 0.18 * cm),
                Paragraph("4. Condições da consulta psiquiátrica", styles["contractSection"]),
            ]
        )
        for item in CONSULTATION_CONDITIONS:
            story.append(Paragraph(f"&bull; {html.escape(item)}", styles["contractBullet"]))

        story.extend(
            [
                Spacer(1, 0.18 * cm),
                Paragraph("5. Natureza do serviço", styles["contractSection"]),
            ]
        )
        for paragraph in SERVICE_NATURE_PARAGRAPHS:
            story.append(Paragraph(html.escape(paragraph), styles["contractBody"]))

        story.extend(
            [
                Spacer(1, 0.18 * cm),
                Paragraph("6. Comunicação", styles["contractSection"]),
            ]
        )
        for paragraph in COMMUNICATION_PARAGRAPHS:
            story.append(Paragraph(html.escape(paragraph), styles["contractBody"]))

        story.extend(
            [
                Spacer(1, 0.18 * cm),
                Paragraph("7. Declaração de ciência e concordância", styles["contractSection"]),
                Paragraph(html.escape(SCIENCE_DECLARATION), styles["contractBody"]),
                Paragraph(
                    f"Assinatura eletrônica registrada em {html.escape(format_display_datetime(signature.signed_at))} (horário de Brasília).",
                    styles["contractBodyStrong"],
                ),
                Spacer(1, 0.28 * cm),
                Paragraph("Evidências da assinatura", styles["contractSection"]),
                self._evidence_table(signature, patient, responsible, doc.width, styles),
                Spacer(1, 0.22 * cm),
                Paragraph(f"IP de origem: {html.escape(signature.ip_address or 'Não informado')}", styles["contractCaption"]),
                Paragraph(f"Navegador: {html.escape(signature.user_agent or 'Não informado')}", styles["contractCaption"]),
            ]
        )

        doc.build(story)
        return buffer.getvalue()

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="contractBrand",
                parent=styles["Normal"],
                fontName="Times-Bold",
                fontSize=10.5,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#213631"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractTitle",
                parent=styles["Title"],
                fontName="Times-Bold",
                fontSize=14.5,
                leading=18,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#101918"),
                spaceAfter=0,
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractMeta",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7.8,
                leading=10,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#66757E"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractSection",
                parent=styles["Heading2"],
                fontName="Times-Bold",
                fontSize=11.2,
                leading=13,
                textColor=colors.HexColor("#162524"),
                spaceAfter=5,
                spaceBefore=2,
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractBody",
                parent=styles["BodyText"],
                fontName="Times-Roman",
                fontSize=10.5,
                leading=16,
                alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#1E2B29"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractBodyStrong",
                parent=styles["BodyText"],
                fontName="Times-Bold",
                fontSize=10.5,
                leading=16,
                alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#1E2B29"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractBullet",
                parent=styles["BodyText"],
                fontName="Times-Roman",
                fontSize=10.5,
                leading=16,
                leftIndent=12,
                firstLineIndent=-8,
                alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#1E2B29"),
                spaceAfter=3,
            )
        )
        styles.add(
            ParagraphStyle(
                name="tableLabel",
                parent=styles["BodyText"],
                fontName="Times-Bold",
                fontSize=9.4,
                leading=12,
                textColor=colors.HexColor("#203330"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="tableValue",
                parent=styles["BodyText"],
                fontName="Times-Roman",
                fontSize=9.4,
                leading=12,
                textColor=colors.HexColor("#24343B"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="evidenceTitle",
                parent=styles["BodyText"],
                fontName="Times-Bold",
                fontSize=10,
                leading=12,
                textColor=colors.HexColor("#182A28"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="contractCaption",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.2,
                leading=10.4,
                textColor=colors.HexColor("#66757E"),
            )
        )
        return styles

    def _metadata_line(self, contract: Contract, signature) -> str:
        metadata = " | ".join(
            [
                f"Identificador: {contract.id}",
                f"Perfil: {self._role_label(signature.signer_role)}",
                f"Assinante: {signature.signer_name}",
                f"Data e hora: {format_display_datetime(signature.signed_at)}",
            ]
        )
        return html.escape(metadata)

    def _data_table(self, rows: list[tuple[str, str | None]], width: float, styles) -> Table:
        label_width = 4.3 * cm
        data = [
            [
                Paragraph(html.escape(label), styles["tableLabel"]),
                Paragraph(self._safe_text(value), styles["tableValue"]),
            ]
            for label, value in rows
        ]
        table = Table(data, colWidths=[label_width, width - label_width])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.55, colors.HexColor("#C9D2CF")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E2")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _evidence_table(self, signature, patient: dict, responsible: dict, width: float, styles) -> Table:
        signer_label = self._role_label(signature.signer_role)
        signer_name = signature.signer_name or self._resolve_signer_display_name(signature.signer_role, patient, responsible)

        face_photo = self._image_for_pdf(signature.face_photo_path, width=4.8 * cm, height=6.3 * cm)
        signature_image = self._image_for_pdf(signature.signature_image_path, width=7.6 * cm, height=2.6 * cm)

        photo_cell = [
            Paragraph("Foto de verificação", styles["evidenceTitle"]),
            Spacer(1, 0.12 * cm),
            face_photo,
        ]
        signature_cell = [
            Paragraph("Assinatura digital", styles["evidenceTitle"]),
            Spacer(1, 0.12 * cm),
            signature_image,
            Spacer(1, 0.2 * cm),
            Paragraph(html.escape(signer_name or "Não informado"), styles["tableLabel"]),
            Paragraph(html.escape(signer_label), styles["contractCaption"]),
            Paragraph(
                html.escape(f"Registrada em {format_display_datetime(signature.signed_at)} (horário de Brasília)"),
                styles["contractCaption"],
            ),
        ]

        left_width = 5.5 * cm
        table = Table([[photo_cell, signature_cell]], colWidths=[left_width, width - left_width])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.55, colors.HexColor("#C9D2CF")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return table

    def _image_for_pdf(self, object_name: str, *, width: float, height: float) -> Image:
        raw = BytesIO(storage_service.get_bytes(object_name))
        image = PILImage.open(raw)
        if image.mode not in {"RGB", "L"}:
            background = PILImage.new("RGB", image.size, "#ffffff")
            if image.mode == "RGBA":
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")

        fitted_width, fitted_height = self._fit_size(image.size[0], image.size[1], width, height)
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return Image(output, width=fitted_width, height=fitted_height)

    @staticmethod
    def _fit_size(source_width: int, source_height: int, max_width: float, max_height: float) -> tuple[float, float]:
        if source_width <= 0 or source_height <= 0:
            return max_width, max_height
        scale = min(max_width / source_width, max_height / source_height)
        return source_width * scale, source_height * scale

    @staticmethod
    def _safe_text(value: str | None) -> str:
        return html.escape(value or "Não informado")

    @staticmethod
    def _format_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value).strftime("%d/%m/%Y")
        except ValueError:
            return value

    @staticmethod
    def _role_label(value: str | None) -> str:
        if value == "responsavel":
            return "Responsável financeiro"
        if value == "paciente":
            return "Paciente"
        return "Assinante"

    @staticmethod
    def _resolve_signer_display_name(role: str | None, patient: dict, responsible: dict) -> str | None:
        if role == "responsavel":
            return responsible.get("name")
        return patient.get("name")


document_service = DocumentService()
