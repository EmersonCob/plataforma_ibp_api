from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.models.client import Client

DEFAULT_CONTRACT_TITLE = "Termo de Responsabilidade e Contrato de Consulta"

RESPONSIBILITY_PARAGRAPH = (
    "Para cumprimento das exigências da Receita Federal (DMED), é obrigatória a apresentação dos "
    "dados do paciente e do responsável financeiro, quando houver. O IBP garante que tais "
    "informações serão utilizadas exclusivamente para fins fiscais e para emissão de nota."
)

CONSULTATION_CONDITIONS = [
    "Os atendimentos são realizados em regime ambulatorial, com acompanhamento programado.",
    "Não se trata de serviço de urgência ou emergência.",
    "Não há retorno gratuito: cada consulta é considerada um novo atendimento.",
    "O paciente declara estar ciente e de acordo com essas condições.",
]

SERVICE_NATURE_PARAGRAPHS = [
    "A clínica não dispõe de estrutura para atendimentos imediatos ou situações agudas.",
    (
        "Em casos de urgência ou emergência, como agravamento súbito, risco físico ou psíquico, "
        "ideação suicida ou agitação intensa, o paciente deve procurar imediatamente UPA, Hospital "
        "ou SAMU (192)."
    ),
]

COMMUNICATION_PARAGRAPHS = [
    (
        "A clínica disponibiliza canais de comunicação, como aplicativos de mensagens (ex.: "
        "WhatsApp), com o objetivo de oferecer acolhimento, orientações gerais, apoio em dúvidas "
        "pontuais e tratar de questões administrativas."
    ),
    (
        "Prezamos por um atendimento atencioso e respeitoso; porém, devido à alta demanda, as "
        "respostas podem não ser imediatas, podendo ocorrer tempo de espera para retorno."
    ),
    (
        "Esse canal não substitui a consulta médica, sendo fundamental o agendamento de atendimento "
        "sempre que houver necessidade de avaliação clínica mais detalhada."
    ),
    (
        "Esse meio não deve ser utilizado em situações de urgência ou emergência. Caso haja "
        "agravamento do quadro, sofrimento intenso ou qualquer situação que exija avaliação "
        "imediata, orientamos que o paciente procure diretamente um serviço de urgência/emergência "
        "para um cuidado mais rápido e seguro."
    ),
]

SCIENCE_DECLARATION = (
    "Declaro que recebi as informações de forma clara, compreendi o conteúdo deste contrato e estou "
    "de acordo com os termos apresentados."
)

DEFAULT_TEMPLATE_TEXT = """TERMO DE RESPONSABILIDADE E CONTRATO DE CONSULTA
IBP - Instituto Brasileiro de Psiquiatria

1. QUALIFICAÇÃO DO PACIENTE
Nome: __________________________________________
CPF: ___________________________________________
Data de nascimento: ____________________________
Telefone: ______________________________________
Endereço: ______________________________________

2. RESPONSÁVEL FINANCEIRO, QUANDO HOUVER
Nome: __________________________________________
CPF: ___________________________________________
Telefone: ______________________________________

3. TERMO DE RESPONSABILIDADE
Para cumprimento das exigências da Receita Federal (DMED), é obrigatória a apresentação dos dados
do paciente e do responsável financeiro, quando houver. O IBP garante que tais informações serão
utilizadas exclusivamente para fins fiscais e para emissão de nota.

4. CONDIÇÕES DA CONSULTA PSIQUIÁTRICA
- Os atendimentos são realizados em regime ambulatorial, com acompanhamento programado.
- Não se trata de serviço de urgência ou emergência.
- Não há retorno gratuito: cada consulta é considerada um novo atendimento.
- O paciente declara estar ciente e de acordo com essas condições.

5. NATUREZA DO SERVIÇO
A clínica não dispõe de estrutura para atendimentos imediatos ou situações agudas.
Em casos de urgência ou emergência, como agravamento súbito, risco físico ou psíquico, ideação
suicida ou agitação intensa, o paciente deve procurar imediatamente UPA, Hospital ou SAMU (192).

6. COMUNICAÇÃO
A clínica disponibiliza canais de comunicação, como aplicativos de mensagens (ex.: WhatsApp), com
o objetivo de oferecer acolhimento, orientações gerais, apoio em dúvidas pontuais e tratar de
questões administrativas.
Prezamos por um atendimento atencioso e respeitoso; porém, devido à alta demanda, as respostas
podem não ser imediatas, podendo ocorrer tempo de espera para retorno.
Esse canal não substitui a consulta médica, sendo fundamental o agendamento de atendimento sempre
que houver necessidade de avaliação clínica mais detalhada.
Esse meio não deve ser utilizado em situações de urgência ou emergência. Caso haja agravamento do
quadro, sofrimento intenso ou qualquer situação que exija avaliação imediata, orientamos que o
paciente procure diretamente um serviço de urgência/emergência para um cuidado mais rápido e seguro.

7. DECLARAÇÃO DE CIÊNCIA E CONCORDÂNCIA
Declaro que recebi as informações de forma clara, compreendi o conteúdo deste contrato e estou de
acordo com os termos apresentados.
Local e data: __________________________________
Assinatura eletrônica: _________________________
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
        "1. QUALIFICAÇÃO DO PACIENTE",
        f"Nome: {_display_value(patient.get('name'))}",
        f"CPF: {_display_value(patient.get('cpf'))}",
        f"Data de nascimento: {_display_date(patient.get('birth_date'))}",
        f"Telefone: {_display_value(patient.get('phone'))}",
        f"Endereço: {_display_value(patient.get('address'))}",
        "",
        "2. RESPONSÁVEL FINANCEIRO, QUANDO HOUVER",
        f"Nome: {_display_value(responsible.get('name'))}",
        f"CPF: {_display_value(responsible.get('cpf'))}",
        f"Telefone: {_display_value(responsible.get('phone'))}",
        "",
        "3. TERMO DE RESPONSABILIDADE",
        RESPONSIBILITY_PARAGRAPH,
        "",
        "4. CONDIÇÕES DA CONSULTA PSIQUIÁTRICA",
        *[f"- {item}" for item in CONSULTATION_CONDITIONS],
        "",
        "5. NATUREZA DO SERVIÇO",
        *SERVICE_NATURE_PARAGRAPHS,
        "",
        "6. COMUNICAÇÃO",
        *COMMUNICATION_PARAGRAPHS,
        "",
        "7. DECLARAÇÃO DE CIÊNCIA E CONCORDÂNCIA",
        SCIENCE_DECLARATION,
        "Local e data: preenchimento automático no momento da assinatura digital.",
        "Assinatura eletrônica: registrada na versão final do documento.",
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
    return cleaned or "Não informado"


def _display_date(value: Any) -> str:
    iso = _date_to_iso(value)
    if not iso:
        return "Não informado"
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
