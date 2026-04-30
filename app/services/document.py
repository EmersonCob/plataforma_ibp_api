import hashlib
import html
from datetime import UTC, datetime
from io import BytesIO

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.contract import Contract
from app.services.contract_rendering import COMMUNICATION_PARAGRAPHS, CONSULTATION_CONDITIONS
from app.services.storage import storage_service


class DocumentService:
    def generate_signed_pdf(self, db: Session, contract: Contract) -> Contract:
        if not contract.signature:
            raise AppError("Contrato ainda nao possui assinatura", 400, "contract_not_signed")
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
            raise AppError("Contrato ainda nao possui assinatura", 400, "contract_not_signed")

        snapshot = contract.form_snapshot or {}
        patient = snapshot.get("patient") or {}
        responsible = snapshot.get("financial_responsible") or {}

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.6 * cm,
            leftMargin=1.6 * cm,
            topMargin=1.4 * cm,
            bottomMargin=1.4 * cm,
            title=contract.title,
        )
        styles = self._styles()

        story = [
            Paragraph("IBP - Instituto Brasileiro de Psiquiatria", styles["brand"]),
            Paragraph(html.escape(contract.title), styles["title"]),
            Paragraph("Documento final assinado digitalmente", styles["subtitle"]),
            Spacer(1, 0.45 * cm),
            self._meta_table(contract, signature),
            Spacer(1, 0.45 * cm),
            Paragraph("Dados do paciente", styles["section"]),
            self._data_table(
                [
                    ("Nome", patient.get("name")),
                    ("CPF", patient.get("cpf")),
                    ("Identidade", patient.get("identity_number")),
                    ("Data de nascimento", self._format_date(patient.get("birth_date"))),
                    ("Telefone", patient.get("phone")),
                    ("Endereco", patient.get("address")),
                ]
            ),
            Spacer(1, 0.35 * cm),
            Paragraph("Responsavel pelo pagamento", styles["section"]),
            self._data_table(
                [
                    ("Nome", responsible.get("name")),
                    ("CPF", responsible.get("cpf")),
                    ("Telefone", responsible.get("phone")),
                ]
            ),
            Spacer(1, 0.35 * cm),
            Paragraph("Termo de responsabilidade", styles["section"]),
            Paragraph(
                (
                    "Para cumprimento das exigencias da Receita Federal (DMED), e obrigatoria a "
                    "apresentacao dos dados do paciente e do responsavel financeiro. O IBP garante "
                    "que tais informacoes serao utilizadas exclusivamente para fins fiscais e emissao de nota."
                ),
                styles["body"],
            ),
            Spacer(1, 0.2 * cm),
            Paragraph("Condicoes da consulta psiquiatrica", styles["section"]),
        ]

        for item in CONSULTATION_CONDITIONS:
            story.append(Paragraph(f"- {html.escape(item)}", styles["body"]))

        story.extend(
            [
                Spacer(1, 0.2 * cm),
                Paragraph("Natureza do servico", styles["section"]),
                Paragraph(
                    "A clinica nao dispoe de estrutura para atendimentos imediatos ou situacoes agudas.",
                    styles["body"],
                ),
                Paragraph(
                    (
                        "Em casos de urgencia ou emergencia (como agravamento subito, risco fisico ou psiquico, "
                        "ideacao suicida ou agitacao intensa), o paciente deve procurar imediatamente: UPA, Hospital ou SAMU (192)."
                    ),
                    styles["body"],
                ),
                Spacer(1, 0.2 * cm),
                Paragraph("Comunicacao", styles["section"]),
            ]
        )

        for paragraph in COMMUNICATION_PARAGRAPHS:
            story.append(Paragraph(html.escape(paragraph), styles["body"]))

        story.extend(
            [
                Spacer(1, 0.25 * cm),
                Paragraph("Declaracao de ciencia e concordancia", styles["section"]),
                Paragraph(
                    "Declaro que recebi as informacoes de forma clara e estou de acordo com os termos deste contrato.",
                    styles["body"],
                ),
                Paragraph(
                    f"Data e hora do aceite: {html.escape(signature.signed_at.strftime('%d/%m/%Y %H:%M'))}",
                    styles["bodyStrong"],
                ),
                Spacer(1, 0.28 * cm),
                self._signature_table(patient, responsible, signature),
                PageBreak(),
                Paragraph("Evidencias da assinatura", styles["section"]),
                Spacer(1, 0.3 * cm),
            ]
        )

        face_photo = self._image_for_pdf(signature.face_photo_path, width=6.8 * cm, height=6.8 * cm)
        signature_image = self._image_for_pdf(signature.signature_image_path, width=7.6 * cm, height=3.0 * cm)
        evidence_table = Table(
            [
                ["Foto enviada para confirmacao", "Assinatura digital"],
                [face_photo, signature_image],
            ],
            colWidths=[8.4 * cm, 8.4 * cm],
        )
        evidence_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F2EE")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#16362F")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C7D8D1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D8E5E0")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(evidence_table)
        story.append(Spacer(1, 0.45 * cm))
        story.append(Paragraph(f"IP de origem: {html.escape(signature.ip_address or 'nao informado')}", styles["caption"]))
        story.append(Paragraph(f"User-Agent: {html.escape(signature.user_agent or 'nao informado')}", styles["caption"]))

        doc.build(story)
        return buffer.getvalue()

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="brand",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=colors.HexColor("#0F5B52"),
                spaceAfter=6,
            )
        )
        styles.add(
            ParagraphStyle(
                name="title",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=19,
                leading=22,
                textColor=colors.HexColor("#1C2B25"),
                spaceAfter=5,
            )
        )
        styles.add(
            ParagraphStyle(
                name="subtitle",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#586771"),
                spaceAfter=6,
            )
        )
        styles.add(
            ParagraphStyle(
                name="section",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=14,
                textColor=colors.HexColor("#17342F"),
                spaceAfter=6,
                spaceBefore=2,
            )
        )
        styles.add(
            ParagraphStyle(
                name="body",
                parent=styles["BodyText"],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#24333A"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="bodyStrong",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#24333A"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="signatureCell",
                parent=styles["BodyText"],
                fontSize=9,
                leading=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#24333A"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="caption",
                parent=styles["Normal"],
                fontSize=8.5,
                leading=11,
                textColor=colors.HexColor("#586771"),
            )
        )
        return styles

    def _meta_table(self, contract: Contract, signature) -> Table:
        rows = [
            ["Contrato", contract.title],
            ["Identificador", contract.id],
            ["Versao assinada", str(contract.current_version)],
            ["Assinante", signature.signer_name],
            ["Perfil de assinatura", self._role_label(signature.signer_role)],
            ["Assinado em", signature.signed_at.strftime("%d/%m/%Y %H:%M")],
        ]
        table = Table(rows, colWidths=[4.0 * cm, 12.2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F6F3")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#24333A")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D8E5E0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5EEEA")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def _data_table(self, rows: list[tuple[str, str | None]]) -> Table:
        data = [[label, self._safe_text(value)] for label, value in rows]
        table = Table(data, colWidths=[4.0 * cm, 12.2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFCFB")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#24333A")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E5E0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5EEEA")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def _signature_table(self, patient: dict, responsible: dict, signature) -> Table:
        signature_image = self._image_for_pdf(signature.signature_image_path, width=5.2 * cm, height=2.1 * cm)
        selected_role = signature.signer_role or "paciente"

        patient_block = self._signature_block(
            title="Paciente",
            name=patient.get("name"),
            signature_image=signature_image if selected_role == "paciente" else None,
            signed_at=signature.signed_at if selected_role == "paciente" else None,
        )
        responsible_block = self._signature_block(
            title="Responsavel",
            name=responsible.get("name"),
            signature_image=signature_image if selected_role == "responsavel" else None,
            signed_at=signature.signed_at if selected_role == "responsavel" else None,
        )
        table = Table([[patient_block, responsible_block]], colWidths=[8.2 * cm, 8.2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D8E5E0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5EEEA")),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    def _signature_block(self, *, title: str, name: str | None, signature_image, signed_at: datetime | None):
        styles = self._styles()
        content = [Paragraph(title, styles["bodyStrong"]), Spacer(1, 0.12 * cm)]
        if signature_image is not None:
            content.extend([signature_image, Spacer(1, 0.08 * cm)])
            timestamp = signed_at.strftime("%d/%m/%Y %H:%M") if signed_at else "-"
            content.append(Paragraph(f"Assinado em {timestamp}", styles["signatureCell"]))
        else:
            content.extend(
                [
                    Paragraph("<br/><br/><br/>_______________________________", styles["signatureCell"]),
                    Paragraph("Campo sem assinatura digital registrada", styles["signatureCell"]),
                ]
            )
        content.append(Spacer(1, 0.12 * cm))
        content.append(Paragraph(html.escape(name or "Nao informado"), styles["signatureCell"]))
        return content

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
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return Image(output, width=width, height=height)

    @staticmethod
    def _safe_text(value: str | None) -> str:
        return html.escape(value or "Nao informado")

    @staticmethod
    def _format_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(f"{value}T00:00:00").strftime("%d/%m/%Y")
        except ValueError:
            return value

    @staticmethod
    def _role_label(value: str | None) -> str:
        if value == "responsavel":
            return "Responsavel"
        if value == "paciente":
            return "Paciente"
        return "Nao informado"


document_service = DocumentService()
