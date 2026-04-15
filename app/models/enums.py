from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"


class ClientStatus(StrEnum):
    ativo = "ativo"
    inativo = "inativo"


class ContractStatus(StrEnum):
    rascunho = "rascunho"
    em_edicao = "em_edicao"
    gerado = "gerado"
    enviado = "enviado"
    visualizado = "visualizado"
    aguardando_assinatura = "aguardando_assinatura"
    assinado = "assinado"
    cancelado = "cancelado"
    expirado = "expirado"


class SignatureStatus(StrEnum):
    completed = "completed"
    rejected = "rejected"


class ActorType(StrEnum):
    admin = "admin"
    public_signer = "public_signer"
    system = "system"


class NotificationChannel(StrEnum):
    whatsapp = "whatsapp"
    email = "email"
    webhook = "webhook"


class NotificationStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"

