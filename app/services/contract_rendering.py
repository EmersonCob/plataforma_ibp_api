from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.models.client import Client

DEFAULT_CONTRACT_TITLE = "Termo de Responsabilidade e Contrato de Consulta"

CONSULTATION_CONDITIONS = [
    "Os atendimentos sao realizados em regime ambulatorial, com acompanhamento programado.",
    "Nao se trata de servico de urgencia ou emergencia.",
    "Nao ha retorno gratuito: cada consulta e considerada um novo atendimento.",
    "O paciente declara estar ciente e de acordo com essas condicoes.",
]

COMMUNICATION_PARAGRAPHS = [
    (
        "A clinica disponibiliza canais de comunicacao, como aplicativos de mensagens "
        "(ex.: WhatsApp), com o objetivo de oferecer acolhimento, orientacoes gerais "
        "e apoio em duvidas pontuais, alem de tratar de questoes administrativas."
    ),
    (
        "Prezamos por um atendimento atencioso e respeitoso, porem, devido a alta demanda, "
        "as respostas podem nao ser imediatas, podendo ocorrer tempo de espera para retorno."
    ),
    (
        "Esse canal nao substitui a consulta medica, sendo fundamental o agendamento de "
        "atendimento sempre que houver necessidade de avaliacao clinica mais detalhada."
    ),
    (
        "Esse meio nao deve ser utilizado em situacoes de urgencia ou emergencia. Caso haja "
        "agravamento do quadro, sofrimento intenso ou qualquer situacao que exija avaliacao "
        "imediata, orientamos que o paciente procure diretamente um servico de urgencia/"
        "emergencia para um cuidado mais rapido e seguro."
    ),
]

DEFAULT_TEMPLATE_TEXT = """TERMO DE RESPONSABILIDADE E CONTRATO DE CONSULTA
IBP - Instituto Brasileiro de Psiquiatria

DADOS DO PACIENTE
Nome: __________________________________________
CPF: ___________________________________________
Identidade: _____________________________________
Data de Nascimento: _____________________________
Telefone: _______________________________________
Endereco: ______________________________________

RESPONSAVEL PELO PAGAMENTO (SE APLICAVEL)
Nome: __________________________________________
CPF: ___________________________________________
Telefone: _______________________________________

TERMO DE RESPONSABILIDADE
Para cumprimento das exigencias da Receita Federal (DMED), e obrigatoria a apresentacao dos dados
do paciente e do responsavel financeiro. O IBP garante que tais informacoes serao utilizadas
exclusivamente para fins fiscais e emissao de nota.

CONDICOES DA CONSULTA PSIQUIATRICA
- Os atendimentos sao realizados em regime ambulatorial, com acompanhamento programado.
- Nao se trata de servico de urgencia ou emergencia.
- Nao ha retorno gratuito: cada consulta e considerada um novo atendimento.
- O paciente declara estar ciente e de acordo com essas condicoes.

NATUREZA DO SERVICO
A clinica nao dispoe de estrutura para atendimentos imediatos ou situacoes agudas.
Em casos de urgencia ou emergencia (como agravamento subito, risco fisico ou psiquico, ideacao suicida
ou agitacao intensa), o paciente deve procurar imediatamente: UPA, Hospital ou SAMU (192).

COMUNICACAO
A clinica disponibiliza canais de comunicacao, como aplicativos de mensagens (ex.: WhatsApp), com o
objetivo de oferecer acolhimento, orientacoes gerais e apoio em duvidas pontuais, alem de tratar de
questoes administrativas.
Prezamos por um atendimento atencioso e respeitoso, porem, devido a alta demanda, as respostas
podem nao ser imediatas, podendo ocorrer tempo de espera para retorno.
Esse canal nao substitui a consulta medica, sendo fundamental o agendamento de atendimento sempre
que houver necessidade de avaliacao clinica mais detalhada.
Esse meio nao deve ser utilizado em situacoes de urgencia ou emergencia. Caso haja agravamento do
quadro, sofrimento intenso ou qualquer situacao que exija avaliacao imediata, orientamos que o
paciente procure diretamente um servico de urgencia/emergencia para um cuidado mais rapido e seguro.

DECLARACAO DE CIENCIA E CONCORDANCIA
Declaro que recebi as informacoes de forma clara e estou de acordo com os termos deste contrato.
Local e Data: __________________________________
Assinatura do Paciente: __________________________
Assinatura do Responsavel: _______________________
"""


def build_contract_snapshot_from_client(client: Client) -> dict[str, Any]:
    responsible = {
        "name": _clean_optional(getattr(client, "financial_responsible_name", None)),
        "cpf": _clean_optional(getattr(client, "financial_responsible_cpf", None)),
        "phone": _clean_optional(getattr(client, "financial_responsible_phone", None)),
    }
    if not any(responsible.values()):
        responsible_payload = None
    else:
        responsible_payload = responsible

    return {
        "patient": {
            "name": client.full_name,
            "cpf": _clean_optional(client.cpf),
            "identity_number": _clean_optional(getattr(client, "identity_number", None)),
            "birth_date": _date_to_iso(client.birth_date),
            "phone": _clean_optional(client.phone),
            "address": build_client_contract_address(client),
        },
        "financial_responsible": responsible_payload,
    }


def normalize_contract_snapshot(snapshot: Any, *, client: Client) -> dict[str, Any]:
    base = build_contract_snapshot_from_client(client)
    incoming = snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else (snapshot or {})

    patient_base = dict(base["patient"])
    patient_incoming = incoming.get("patient") or {}
    patient = {
        "name": _clean_optional(patient_incoming.get("name")) or patient_base["name"],
        "cpf": _clean_optional(patient_incoming.get("cpf")) or patient_base.get("cpf"),
        "identity_number": _clean_optional(patient_incoming.get("identity_number")) or patient_base.get("identity_number"),
        "birth_date": _date_to_iso(patient_incoming.get("birth_date")) or patient_base.get("birth_date"),
        "phone": _clean_optional(patient_incoming.get("phone")) or patient_base.get("phone"),
        "address": _clean_optional(patient_incoming.get("address")) or patient_base.get("address"),
    }

    responsible_base = base.get("financial_responsible") or {}
    responsible_incoming = incoming.get("financial_responsible") or {}
    responsible = {
        "name": _clean_optional(responsible_incoming.get("name")) or responsible_base.get("name"),
        "cpf": _clean_optional(responsible_incoming.get("cpf")) or responsible_base.get("cpf"),
        "phone": _clean_optional(responsible_incoming.get("phone")) or responsible_base.get("phone"),
    }
    if not any(responsible.values()):
        responsible_payload = None
    else:
        responsible_payload = responsible

    return {
        "patient": patient,
        "financial_responsible": responsible_payload,
    }


def render_contract_text(snapshot: dict[str, Any]) -> str:
    patient = snapshot.get("patient") or {}
    responsible = snapshot.get("financial_responsible") or {}

    lines = [
        "TERMO DE RESPONSABILIDADE E CONTRATO DE CONSULTA",
        "IBP - Instituto Brasileiro de Psiquiatria",
        "",
        "DADOS DO PACIENTE",
        f"Nome: {_display_value(patient.get('name'))}",
        f"CPF: {_display_value(patient.get('cpf'))}",
        f"Identidade: {_display_value(patient.get('identity_number'))}",
        f"Data de Nascimento: {_display_date(patient.get('birth_date'))}",
        f"Telefone: {_display_value(patient.get('phone'))}",
        f"Endereco: {_display_value(patient.get('address'))}",
        "",
        "RESPONSAVEL PELO PAGAMENTO (SE APLICAVEL)",
        f"Nome: {_display_value(responsible.get('name'))}",
        f"CPF: {_display_value(responsible.get('cpf'))}",
        f"Telefone: {_display_value(responsible.get('phone'))}",
        "",
        "TERMO DE RESPONSABILIDADE",
        (
            "Para cumprimento das exigencias da Receita Federal (DMED), e obrigatoria a apresentacao "
            "dos dados do paciente e do responsavel financeiro. O IBP garante que tais informacoes "
            "serao utilizadas exclusivamente para fins fiscais e emissao de nota."
        ),
        "",
        "CONDICOES DA CONSULTA PSIQUIATRICA",
        *[f"- {item}" for item in CONSULTATION_CONDITIONS],
        "",
        "NATUREZA DO SERVICO",
        "A clinica nao dispoe de estrutura para atendimentos imediatos ou situacoes agudas.",
        (
            "Em casos de urgencia ou emergencia (como agravamento subito, risco fisico ou psiquico, "
            "ideacao suicida ou agitacao intensa), o paciente deve procurar imediatamente: UPA, Hospital ou SAMU (192)."
        ),
        "",
        "COMUNICACAO",
        *COMMUNICATION_PARAGRAPHS,
        "",
        "DECLARACAO DE CIENCIA E CONCORDANCIA",
        "Declaro que recebi as informacoes de forma clara e estou de acordo com os termos deste contrato.",
        "Local e Data: __________________________________",
        "Assinatura do Paciente: __________________________",
        "Assinatura do Responsavel: _______________________",
    ]
    return "\n".join(lines)


def build_client_contract_address(client: Client) -> str | None:
    first_line = ", ".join(filter(None, [_clean_optional(client.address_street), _clean_optional(client.address_number)]))
    if client.address_complement:
        first_line = ", ".join(filter(None, [first_line, _clean_optional(client.address_complement)]))
    second_line = " - ".join(filter(None, [_clean_optional(client.neighborhood), _clean_optional(client.city)]))
    third_line = " / ".join(filter(None, [_clean_optional(client.state), _clean_optional(client.zip_code)]))
    parts = [part for part in [first_line, second_line, third_line] if part]
    if parts:
        return ", ".join(parts)
    return _clean_optional(client.address)


def resolve_signer_name(snapshot: dict[str, Any] | None, signer_role: str) -> str | None:
    if signer_role == "responsavel":
        responsible = (snapshot or {}).get("financial_responsible") or {}
        return _clean_optional(responsible.get("name"))
    patient = (snapshot or {}).get("patient") or {}
    return _clean_optional(patient.get("name"))


def _display_value(value: Any) -> str:
    cleaned = _clean_optional(value)
    return cleaned or "Nao informado"


def _display_date(value: Any) -> str:
    iso = _date_to_iso(value)
    if not iso:
        return "Nao informado"
    try:
        parsed = date.fromisoformat(iso)
    except ValueError:
        return iso
    return parsed.strftime("%d/%m/%Y")


def _date_to_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)
