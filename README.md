# Plataforma IBP API

API principal da plataforma.

## Responsabilidades

Esta aplicacao continua sendo dona de:

- autenticacao e login
- refresh token
- usuarios
- permissoes
- pacientes
- contratos
- assinaturas
- documentos assinados
- auditoria principal
- prontuario

## Fora do escopo desta API

Nao e mais desejavel concentrar aqui detalhes internos de canais de comunicacao, como:

- provedores de WhatsApp
- webchat publico
- webhooks de canais
- n8n
- fila de atendimento humano
- conversas e mensagens da Central de Atendimento

Esse escopo foi movido para `plataforma_ibp_api_canais`.

## Relacao com a API de canais

O dominio de contratos continua aqui.

Quando um evento de contrato precisar gerar mensagem externa, esta API pode:

1. montar o payload do dominio de contrato
2. registrar o evento local de notificacao
3. encaminhar o outbound para `plataforma_ibp_api_canais` via endpoint interno

Assim, a API principal nao precisa conhecer detalhes de WhatsApp Official, Evolution ou Z-API.

## Modulos principais

- `auth`
- `users`
- `clients`
- `contracts`
- `public_signatures`
- `notifications`
- `prontuario`

## Prontuario

O CRUD de prontuario continua disponivel no backend, mas a interface de prontuario foi mantida fora desta entrega.

O prontuario deve ser tratado como a terceira frente da plataforma, separada de:

1. Contratos e Pacientes
2. Central de Atendimento

## Variaveis de ambiente

Exemplo em `.env.example`.

Variaveis relevantes desta etapa:

- `CHANNELS_API_BASE_URL`
- `CHANNELS_API_INTERNAL_TOKEN`
- `TRUST_PROXY_HEADERS`

Referencia QA atual para `CHANNELS_API_BASE_URL`:

- `https://ibp-api-canais-qa.jbtechinnova.com/api/v1`

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

## Validacao

```bash
python -m pytest tests -q
python -m compileall app
```

## Observacoes de seguranca

- `TRUST_PROXY_HEADERS=false` por padrao. So habilite atras de proxy confiavel.
- credenciais reais nao devem ficar em `.env` versionado
- a notificacao de contrato continua registrando evento local, mas o envio para canais externos passa a depender da API de canais quando configurada
