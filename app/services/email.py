import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailService:
    def send_password_reset_email(self, user: User, reset_url: str, expires_minutes: int) -> bool:
        html, text = self._render_password_reset(user, reset_url, expires_minutes)
        return self._send(
            to_email=user.email,
            subject="Redefinição de senha - IBP Saúde Mental",
            html=html,
            text=text,
        )

    def send_welcome_email(self, user: User, initial_password: str) -> bool:
        html, text = self._render_welcome(user, initial_password)
        return self._send(
            to_email=user.email,
            subject="Seu acesso à Plataforma IBP",
            html=html,
            text=text,
        )

    def _send(self, *, to_email: str, subject: str, html: str, text: str) -> bool:
        if not settings.smtp_host or not settings.smtp_from_email:
            logger.warning("SMTP not configured; transactional email was not sent to %s", to_email)
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((settings.smtp_from_name, str(settings.smtp_from_email)))
        message["To"] = to_email
        message.set_content(text)
        message.add_alternative(html, subtype="html")

        try:
            if settings.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds,
                    context=context,
                ) as smtp:
                    self._login_if_needed(smtp)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds,
                ) as smtp:
                    if settings.smtp_use_tls:
                        smtp.starttls(context=ssl.create_default_context())
                    self._login_if_needed(smtp)
                    smtp.send_message(message)
        except Exception:
            logger.exception("Failed to send transactional email to %s", to_email)
            return False

        logger.info("Transactional email sent to %s", to_email)
        return True

    def _login_if_needed(self, smtp: smtplib.SMTP) -> None:
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)

    def _render_password_reset(self, user: User, reset_url: str, expires_minutes: int) -> tuple[str, str]:
        intro = (
            "Recebemos uma solicitação para redefinir a senha do seu acesso. "
            "Use o botão abaixo para criar uma nova senha com segurança."
        )
        details = [
            ("Conta", user.email),
            ("Validade do link", f"{expires_minutes} minutos"),
        ]
        html = self._render_layout(
            title=f"Olá, {user.name}.",
            intro=intro,
            details=details,
            action_label="Redefinir senha",
            action_url=reset_url,
            note="Se você não solicitou esta alteração, ignore este e-mail. Sua senha atual continuará válida.",
        )
        text = (
            f"Olá, {user.name}.\n\n"
            f"{intro}\n\n"
            f"Conta: {user.email}\n"
            f"Validade do link: {expires_minutes} minutos\n"
            f"Link: {reset_url}\n\n"
            "Se você não solicitou esta alteração, ignore este e-mail."
        )
        return html, text

    def _render_welcome(self, user: User, initial_password: str) -> tuple[str, str]:
        login_url = f"{settings.frontend_app_url.rstrip('/')}/login"
        intro = (
            "Seu acesso à plataforma da clínica foi criado. Use as credenciais abaixo para entrar "
            "e altere a senha no primeiro acesso, se a política interna da clínica solicitar."
        )
        details = [
            ("Nome", user.name),
            ("E-mail/login", user.email),
            ("Senha inicial", initial_password),
        ]
        html = self._render_layout(
            title=f"Bem-vindo(a), {user.name}.",
            intro=intro,
            details=details,
            action_label="Acessar plataforma",
            action_url=login_url,
            note="Guarde estas informações com segurança e não compartilhe sua senha.",
        )
        text = (
            f"Bem-vindo(a), {user.name}.\n\n"
            f"{intro}\n\n"
            f"Nome: {user.name}\n"
            f"E-mail/login: {user.email}\n"
            f"Senha inicial: {initial_password}\n"
            f"Acesso: {login_url}\n\n"
            "Guarde estas informações com segurança e não compartilhe sua senha."
        )
        return html, text

    def _render_layout(
        self,
        *,
        title: str,
        intro: str,
        details: list[tuple[str, str]],
        action_label: str,
        action_url: str,
        note: str,
    ) -> str:
        rows = "".join(
            f"""
            <tr>
              <td class="label">{escape(label)}</td>
              <td class="value">{escape(value)}</td>
            </tr>
            """
            for label, value in details
        )

        return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body {{ margin: 0; background: #f4f8f6; color: #1d2930; font-family: Arial, Helvetica, sans-serif; }}
      .wrap {{ width: 100%; padding: 28px 0; }}
      .panel {{ width: min(600px, calc(100% - 28px)); margin: 0 auto; border: 1px solid #d8e3df; border-radius: 8px; overflow: hidden; background: #ffffff; }}
      .header {{ padding: 26px 28px; background: #17342f; color: #ffffff; }}
      .brand {{ margin: 0; font-size: 20px; font-weight: 800; }}
      .sub {{ margin: 6px 0 0; color: #d7e0de; }}
      .content {{ padding: 28px; }}
      h1 {{ margin: 0 0 12px; color: #18262d; font-size: 26px; line-height: 1.2; }}
      p {{ margin: 0 0 18px; color: #5c6971; font-size: 16px; line-height: 1.65; }}
      table {{ width: 100%; margin: 18px 0 24px; border-collapse: collapse; }}
      td {{ padding: 12px 0; border-bottom: 1px solid #edf2f0; vertical-align: top; }}
      .label {{ width: 38%; color: #65727c; font-size: 14px; font-weight: 700; }}
      .value {{ color: #1d2930; font-size: 15px; font-weight: 700; word-break: break-word; }}
      .button {{ display: inline-block; border-radius: 8px; padding: 13px 18px; background: #0e6f68; color: #ffffff !important; font-weight: 800; text-decoration: none; }}
      .note {{ margin-top: 22px; border-left: 4px solid #b06f4f; padding: 12px 14px; background: #fff8f3; color: #5c4638; }}
      .footer {{ padding: 18px 28px; background: #f4f8f6; color: #65727c; font-size: 13px; line-height: 1.55; }}
      @media (max-width: 520px) {{
        .content, .header, .footer {{ padding-right: 20px; padding-left: 20px; }}
        h1 {{ font-size: 22px; }}
        .label, .value {{ display: block; width: 100%; }}
        .value {{ padding-top: 4px; }}
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="panel">
        <div class="header">
          <p class="brand">IBP Saúde Mental</p>
          <p class="sub">Cuidado, sigilo e organização em saúde mental</p>
        </div>
        <div class="content">
          <h1>{escape(title)}</h1>
          <p>{escape(intro)}</p>
          <table role="presentation">{rows}</table>
          <a class="button" href="{escape(action_url)}">{escape(action_label)}</a>
          <p class="note">{escape(note)}</p>
        </div>
        <div class="footer">
          Esta é uma mensagem automática da Plataforma IBP. Em caso de dúvida, entre em contato com a administração da clínica.
        </div>
      </div>
    </div>
  </body>
</html>"""


email_service = EmailService()
