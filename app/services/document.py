import hashlib
import html
from datetime import UTC, datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.contract import Contract
from app.services.storage import storage_service


class DocumentService:
    def generate_signed_pdf(self, db: Session, contract: Contract) -> Contract:
        if not contract.signature:
            raise AppError("Contrato ainda não possui assinatura", 400, "contract_not_signed")
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
            raise AppError("Contrato ainda não possui assinatura", 400, "contract_not_signed")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm,
            title=contract.title,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Plataforma IBP", styles["Title"]),
            Paragraph("Documento final assinado", styles["Heading2"]),
            Spacer(1, 0.4 * cm),
            Paragraph(f"<b>Contrato:</b> {html.escape(contract.title)}", styles["Normal"]),
            Paragraph(f"<b>Identificador:</b> {contract.id}", styles["Normal"]),
            Paragraph(f"<b>Cliente/Assinante:</b> {html.escape(signature.signer_name)}", styles["Normal"]),
            Paragraph(f"<b>Data e hora da assinatura:</b> {signature.signed_at.isoformat()}", styles["Normal"]),
            Paragraph(f"<b>Versão assinada:</b> {contract.current_version}", styles["Normal"]),
            Spacer(1, 0.6 * cm),
            Paragraph("Conteúdo do contrato", styles["Heading2"]),
        ]

        for paragraph in contract.content.splitlines():
            text = html.escape(paragraph.strip()) or "&nbsp;"
            story.append(Paragraph(text, styles["BodyText"]))
            story.append(Spacer(1, 0.12 * cm))

        story.extend([PageBreak(), Paragraph("Evidências da assinatura", styles["Heading2"]), Spacer(1, 0.4 * cm)])

        face_photo = self._image_for_pdf(signature.face_photo_path, width=6 * cm, height=6 * cm)
        signature_image = self._image_for_pdf(signature.signature_image_path, width=8 * cm, height=3 * cm)
        evidence_table = Table(
            [
                ["Foto enviada para confirmação", "Assinatura digital"],
                [face_photo, signature_image],
            ],
            colWidths=[8 * cm, 8 * cm],
        )
        evidence_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F7F5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(evidence_table)
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(f"IP: {html.escape(signature.ip_address or 'não informado')}", styles["Normal"]))
        story.append(Paragraph(f"User-Agent: {html.escape(signature.user_agent or 'não informado')}", styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()

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


document_service = DocumentService()
