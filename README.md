# Plataforma IBP API

API principal da plataforma para pacientes, contratos, assinatura pública, auditoria, notificações e prontuário.

## Escopo

Este diretório concentra a aplicação administrativa principal da plataforma, referenciada no projeto como `plataforma_ibp_api`.

## Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Redis
- MinIO/S3 compatível para fotos, assinaturas e PDFs
- JWT
- ReportLab para PDF

## Como rodar

1. Crie e ative um ambiente virtual Python.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Instale as dependências.

```bash
pip install -r requirements.txt
```

3. Copie o arquivo de ambiente e ajuste as variáveis.

```bash
copy .env.example .env
```

4. Inicie a API.

```bash
uvicorn app.main:app --reload
```

## Módulos principais

- `clients`: cadastro, foto, status e exclusão controlada de pacientes.
- `contracts`: geração, versionamento e assinatura de contratos.
- `public_signatures`: fluxo público de assinatura com foto e evidências.
- `prontuario`: histórico inicial de atendimentos vinculado ao paciente e ao usuário autor.
- `notifications`: registro de gatilhos e integrações futuras.

## Observação

Como o projeto recria a estrutura do banco a partir dos modelos, mudanças estruturais recentes como `photo_path` em pacientes e `prontuario_entries` exigem recriação das tabelas quando o ambiente ainda estiver usando a estrutura anterior.
