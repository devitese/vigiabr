# Contribuindo com o VigiaBR

Obrigado pelo interesse no VigiaBR! Este projeto monitora a consistencia de registros publicos de agentes eleitos brasileiros usando exclusivamente dados oficiais e publicos. Cada contribuicao fortalece a transparencia democratica.

**Licenca**: O VigiaBR e licenciado sob [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Ao contribuir, voce concorda que seu trabalho sera distribuido sob esta licenca.

---

## Sumario

- [Codigo de Conduta](#codigo-de-conduta)
- [Primeiros Passos](#primeiros-passos)
  - [Pre-requisitos](#pre-requisitos)
  - [Configuracao do Repositorio](#configuracao-do-repositorio)
  - [Servicos de Infraestrutura](#servicos-de-infraestrutura)
  - [Executando Testes](#executando-testes)
  - [Linting](#linting)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Fluxo Git](#fluxo-git)
  - [Estrategia de Branches](#estrategia-de-branches)
  - [Desenvolvimento Issue-First](#desenvolvimento-issue-first)
  - [Mensagens de Commit](#mensagens-de-commit)
  - [Pull Requests](#pull-requests)
- [Padroes de Codigo](#padroes-de-codigo)
  - [Python](#python)
  - [Privacidade de Dados (LGPD)](#privacidade-de-dados-lgpd)
  - [Neutralidade Editorial](#neutralidade-editorial)
- [Visao Geral da Arquitetura](#visao-geral-da-arquitetura)
  - [Pipeline de Dados](#pipeline-de-dados)
  - [Pacotes do Workspace](#pacotes-do-workspace)
  - [Schemas de Banco de Dados](#schemas-de-banco-de-dados)
- [Adicionando um Novo Spider](#adicionando-um-novo-spider)
- [Adicionando uma Nova Etapa de Processamento](#adicionando-uma-nova-etapa-de-processamento)
- [Migracoes de Banco de Dados](#migracoes-de-banco-de-dados)
- [Reportando Bugs](#reportando-bugs)
- [Sugerindo Funcionalidades](#sugerindo-funcionalidades)
- [Vulnerabilidades de Seguranca](#vulnerabilidades-de-seguranca)

---

## Codigo de Conduta

Seja respeitoso, construtivo e inclusivo. Seguimos o [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Assedio, discriminacao e discursos de ma-fe nao serao tolerados.

---

## Primeiros Passos

### Pre-requisitos

| Ferramenta | Versao | Finalidade |
|------------|--------|------------|
| Python | >= 3.12 | Runtime para todo o codigo do pipeline |
| [uv](https://docs.astral.sh/uv/) | latest | Gerenciador de pacotes e workspace |
| Docker + Docker Compose | latest | PostgreSQL, Neo4j, Airflow, monitoramento |
| Git | >= 2.40 | Controle de versao |

### Configuracao do Repositorio

```bash
# Clonar o repositorio
git clone https://github.com/devitese/vigiabr.git
cd vigiabr

# Mudar para a branch develop (todo trabalho comeca aqui)
git checkout develop

# Criar o ambiente virtual e instalar todos os pacotes do workspace
cd pipeline
uv sync

# Verificar a instalacao
uv run pytest
```

O comando `uv sync` instala os tres pacotes do workspace (`schemas`, `extraction`, `processing`) junto com suas dependencias de desenvolvimento em um unico ambiente virtual em `pipeline/.venv`.

### Servicos de Infraestrutura

Inicie a stack de desenvolvimento local:

```bash
cd pipeline/platform/docker

# Iniciar todos os servicos (PostgreSQL, Neo4j, Airflow, Prometheus, Grafana)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Credenciais padrao de desenvolvimento (definidas em `docker-compose.dev.yml`):

| Servico | URL | Usuario | Senha |
|---------|-----|---------|-------|
| PostgreSQL | `localhost:5432` | `vigiabr` | `vigiabr` |
| Neo4j Browser | `http://localhost:7474` | `neo4j` | `vigiabr` |
| Airflow | `http://localhost:8080` | `admin` | `admin` |
| Grafana | `http://localhost:3000` | `admin` | `vigiabr` |
| Prometheus | `http://localhost:9090` | — | — |

Para parar os servicos:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

Adicione `-v` para tambem remover os volumes persistentes (dados dos bancos).

### Executando Testes

```bash
cd pipeline

# Executar todos os testes de todos os pacotes do workspace
uv run pytest

# Executar testes de um pacote especifico
uv run pytest schemas/tests/
uv run pytest extraction/tests/
uv run pytest processing/tests/

# Executar um unico arquivo de teste
uv run pytest extraction/tests/test_camara_deputados.py

# Saida detalhada
uv run pytest -v
```

### Linting

Usamos [Ruff](https://docs.astral.sh/ruff/) para linting e formatacao (target: Python 3.12, comprimento de linha: 100).

```bash
cd pipeline

# Verificar erros de lint
uv run ruff check .

# Corrigir automaticamente problemas corrigiveis
uv run ruff check --fix .

# Formatar codigo
uv run ruff format .

# Verificar formatacao sem modificar
uv run ruff format --check .
```

---

## Estrutura do Projeto

```
vigiabr/
├── pipeline/                 # Pipeline de dados (implementado)
│   ├── pyproject.toml        # Definicao raiz do workspace (uv)
│   ├── uv.lock               # Dependencias travadas
│   ├── schemas/              # Schemas de banco, modelos Pydantic, tipos compartilhados
│   ├── extraction/           # Spiders Scrapy e downloaders em massa
│   ├── processing/           # Transformacao, analise, validacao e carga
│   │   └── processing/
│   │       ├── transformers/ # JSON bruto → modelos Pydantic
│   │       ├── analyzers/    # Deteccao de anomalias (Benford, HHI, valores redondos)
│   │       ├── validators/   # Dedup, hash de PII
│   │       └── loaders/      # Upsert em lote PostgreSQL, Neo4j, DuckDB
│   ├── contracts/            # Contratos de dados (DDL, constraints Cypher, docs de fluxo)
│   └── platform/             # Docker, Airflow, monitoramento
│
├── scoring/                  # Motor de scoring SCI (planejado)
│   ├── dimensions/           # Calculadores por dimensao
│   ├── queries/              # Cypher e SQL para travessias
│   └── tests/
│
├── backend/                  # API FastAPI (planejado)
│   ├── app/                  # Routers, services, schemas, db
│   └── tests/
│
├── frontend/                 # Frontend Next.js + React (planejado)
│   ├── src/                  # Pages, components, lib, styles
│   └── public/
│
├── deploy/                   # Deploy e CI/CD (planejado)
│   ├── docker/               # Docker Compose prod e Dockerfiles
│   ├── caddy/                # Proxy reverso + auto-HTTPS
│   ├── ci/                   # GitHub Actions
│   ├── e2e/                  # Testes end-to-end
│   └── scripts/
│
├── docs/plans/               # Documentos de design e planejamento
├── CLAUDE.md
├── CONTRIBUTING.md           # Este arquivo
├── README.md
└── VigiaBR-PRD-v1.0.html    # Documento de Requisitos do Produto
```

---

## Fluxo Git

### Estrategia de Branches

```
main (producao — protegida, apenas deploy)
 └── develop (branch de integracao — todos os PRs apontam para ca)
      ├── feat/42-sci-endpoint
      ├── fix/51-spider-timeout
      └── docs/55-api-reference
```

- **`main`**: Branch de producao. Recebe apenas merge commits de `develop`. Nunca commite diretamente.
- **`develop`**: Branch de integracao. Todas as branches de feature originam aqui, todos os PRs apontam para ca.
- **Branches de feature**: Nomeadas como `tipo/numero-da-issue-descricao-curta`.

### Desenvolvimento Issue-First

**Sempre crie uma Issue no GitHub antes de comecar o trabalho.** Isso garante:

1. O trabalho e rastreavel e descobrivel.
2. Outros podem ver no que voce esta trabalhando.
3. A branch e o PR estao vinculados a uma descricao clara.

```bash
# Exemplo de fluxo de trabalho
# 1. Criar uma issue no GitHub (ou via CLI)
gh issue create --title "Adicionar spider de declaracao de bens do TSE" --body "..."

# 2. Anotar o numero da issue (ex: #42)

# 3. Criar sua branch a partir de develop
git checkout develop
git pull origin develop
git checkout -b feat/42-tse-wealth-spider
```

### Mensagens de Commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```
tipo(escopo): descricao curta

Corpo opcional explicando o "por que" por tras da mudanca.

Refs #42
```

**Tipos**: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`, `revert`

**Escopos** (exemplos): `extraction`, `processing`, `schemas`, `docker`, `ci`

Exemplos:

```
feat(extraction): adicionar spider de declaracao de bens do TSE

Coleta dados de dadosabertos.tse.jus.br para declaracoes anuais de bens.
Grava JSON bruto em pipeline/data/tse_bens/.

Refs #42
```

```
fix(processing): tratar CNPJ nulo no loader de empresas

O dump da Receita Federal ocasionalmente tem campos CNPJ em branco
para empresas sob protecao judicial. Pular essas linhas
em vez de levantar um erro de validacao.

Fixes #51
```

### Pull Requests

1. **Um PR por workstream** — nao misture alteracoes nao relacionadas.
2. **Aponte para `develop`** — nunca abra um PR contra `main`.
3. **Squash merge** — PRs sao squash-merged em `develop`.
4. **Execute os testes antes do push** — `uv run pytest` deve passar.
5. **Execute o linter antes do push** — `uv run ruff check .` deve estar limpo.

Template de descricao do PR:

```markdown
## Resumo
- Breve descricao do que mudou e por que

## Issue Relacionada
Closes #<numero-da-issue>

## Plano de Testes
- [ ] Testes novos/atualizados passam (`uv run pytest`)
- [ ] Linting passa (`uv run ruff check .`)
- [ ] Etapas de verificacao manual (se aplicavel)

## Screenshots / Logs
(se aplicavel)
```

---

## Padroes de Codigo

### Python

- **Versao alvo**: Python 3.12+
- **Comprimento de linha**: 100 caracteres
- **Linter/Formatador**: Ruff (configurado no `pyproject.toml` de cada pacote)
- **Type hints**: Use anotacoes de tipo para assinaturas de funcao. Modelos Pydantic aplicam validacao em runtime.
- **Imports**: Ruff cuida da ordenacao de imports. Deixe ele fazer o trabalho.
- **Build system**: Hatchling para todos os pacotes.
- **Dependencias**: Gerenciadas via `uv`. Adicione dependencias de runtime no `pyproject.toml` do pacote relevante em `[project.dependencies]`. Adicione ferramentas apenas de desenvolvimento em `[dependency-groups.dev]`.

### Privacidade de Dados (LGPD)

O VigiaBR esta em conformidade com a Lei Geral de Protecao de Dados (LGPD). **Isso e inegociavel:**

- **Numeros de CPF devem ser hasheados com SHA-256** antes do armazenamento. Use o modulo `pii` em `pipeline/schemas/` para todo hashing.
- **Nunca armazene identificadores pessoais reversiveis** em qualquer banco de dados, log ou arquivo de saida.
- **Nunca registre PII em logs** — nem em logs do Scrapy, nem em logs de tasks do Airflow, nem em mensagens de erro.
- Se precisar debugar com dados reais, hasheie primeiro ou use dados sinteticos de teste.

### Neutralidade Editorial

O VigiaBR apresenta fatos, nunca acusacoes. Todo texto voltado ao usuario deve seguir estas regras:

- Use o enquadramento **FATO** (fato), **METRICA** (metrica) e **FONTE** (fonte).
- Sempre inclua um link direto para a fonte oficial dos dados.
- Nunca use linguagem que implique culpa, irregularidade ou intencao.
- Nunca editorialize. Se uma metrica parece suspeita, apresente os numeros e deixe os leitores tirarem suas conclusoes.

---

## Visao Geral da Arquitetura

### Pipeline de Dados

```
Spiders Scrapy → JSON/CSV bruto → DAGs Airflow → Transformar → Analisar → Validar → Carregar
                                                                              ↓           ↓
                                                                         PostgreSQL    Neo4j
                                                                         (tabular)    (grafo)
```

1. **Extracao** (`pipeline/extraction/`): Spiders Scrapy coletam dados de APIs e portais oficiais. Downloaders em massa tratam datasets grandes (ex: dump CNPJ da Receita Federal).
2. **Processamento** (`pipeline/processing/`): Transforma dados brutos em modelos Pydantic validados, executa analise de anomalias (Benford, HHI, valores redondos), e carrega no PostgreSQL e Neo4j.
3. **Schemas** (`pipeline/schemas/`): Modelos SQLAlchemy compartilhados, tipos Pydantic, utilitarios de hash de PII e migracoes Alembic.

### Camada de Aplicacao (planejada)

4. **Scoring** (`scoring/`): Motor SCI — le PostgreSQL e Neo4j, calcula score 0-1000 por mandatario, gera registros de Inconsistencia.
5. **Backend** (`backend/`): API REST FastAPI — serve dados de mandatarios, SCI, inconsistencias, timeline.
6. **Frontend** (`frontend/`): Next.js + React — renderiza perfis, gauge SCI, cards de inconsistencia, graficos de patrimonio.
7. **Deploy** (`deploy/`): Docker Compose prod, Caddy (HTTPS), GitHub Actions CI/CD, testes E2E.

### Pacotes do Workspace

O diretorio `pipeline/` e um [workspace uv](https://docs.astral.sh/uv/concepts/workspaces/) com tres pacotes membros:

| Pacote | Nome PyPI | Descricao |
|--------|-----------|-----------|
| `schemas/` | `vigiabr-schemas` | Modelos SQLAlchemy, tipos Pydantic, migracoes Alembic, hash de PII |
| `extraction/` | `vigiabr-extraction` | Spiders Scrapy, downloaders em massa |
| `processing/` | `vigiabr-processing` | Transformacao, analise de anomalias, validacao e carga |

Tanto `extraction` quanto `processing` dependem de `schemas` como dependencia do workspace.

Pacotes da camada de aplicacao (planejados):

| Pacote | Nome PyPI | Descricao |
|--------|-----------|-----------|
| `scoring/` | `vigiabr-scoring` | Motor SCI, dimensoes, detector de inconsistencias |
| `backend/` | `vigiabr-backend` | API REST FastAPI |

### Schemas de Banco de Dados

- **DDL PostgreSQL**: `pipeline/contracts/pg_ddl.sql`
- **Constraints Neo4j**: `pipeline/contracts/neo4j_constraints.cypher`
- **Documentacao de fluxo de dados**: `pipeline/contracts/data_flow.md`
- **Migracoes Alembic**: `pipeline/schemas/alembic/`

---

## Adicionando um Novo Spider

1. **Crie uma issue** descrevendo a fonte de dados, endpoints e formato de saida esperado.
2. Verifique `pipeline/contracts/raw_formats/` para especificacoes de formato existentes. Adicione uma se for uma nova fonte de dados.
3. Crie o spider em `pipeline/extraction/vigiabr_spiders/`:

```python
# pipeline/extraction/vigiabr_spiders/minha_fonte.py
import scrapy
from models.raw import MeuModeloBruto  # Modelo Pydantic do schemas


class MinhaFonteSpider(scrapy.Spider):
    name = "minha_fonte"
    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {"Accept": "application/json"},
    }

    def start_requests(self):
        yield scrapy.Request("https://api.fonte-oficial.gov.br/endpoint")

    def parse(self, response):
        data = response.json()
        for item in data["results"]:
            yield MeuModeloBruto(**item).model_dump()
```

4. Adicione testes em `pipeline/extraction/tests/`.
5. Execute `uv run pytest extraction/tests/` e `uv run ruff check extraction/`.

---

## Adicionando uma Nova Etapa de Processamento

1. Defina ou atualize o modelo Pydantic em `pipeline/schemas/models/`.
2. Se a etapa escreve no PostgreSQL, adicione ou atualize o modelo SQLAlchemy e crie uma migracao Alembic.
3. Implemente a logica de transformacao/carga em `pipeline/processing/processing/`.
4. Adicione testes em `pipeline/processing/tests/`.
5. Documente o fluxo de dados em `pipeline/contracts/data_flow.md` se estiver adicionando um novo caminho no pipeline.

---

## Migracoes de Banco de Dados

Usamos [Alembic](https://alembic.sqlalchemy.org/) para migracoes de schema do PostgreSQL:

```bash
cd pipeline/schemas

# Gerar uma nova migracao apos modificar modelos SQLAlchemy
uv run alembic -c alembic/alembic.ini revision --autogenerate -m "add wealth_declarations table"

# Aplicar migracoes
uv run alembic -c alembic/alembic.ini upgrade head

# Reverter uma migracao
uv run alembic -c alembic/alembic.ini downgrade -1
```

Para alteracoes em constraints do Neo4j, atualize `pipeline/contracts/neo4j_constraints.cypher` e anote as mudancas no seu PR.

---

## Reportando Bugs

[Abra uma issue](https://github.com/devitese/vigiabr/issues/new) com:

- **Titulo**: Descricao clara e concisa do problema.
- **Passos para reproduzir**: Comandos exatos, dados de entrada ou URLs.
- **Comportamento esperado**: O que deveria acontecer.
- **Comportamento real**: O que realmente acontece (inclua logs/tracebacks).
- **Ambiente**: SO, versao do Python, versao do Docker, versoes relevantes dos servicos.

---

## Sugerindo Funcionalidades

Abra uma issue com a label `enhancement`. Inclua:

- **Declaracao do problema**: Qual necessidade do usuario ou lacuna isso endereca?
- **Solucao proposta**: Como voce imagina o funcionamento.
- **Fonte de dados**: Se envolve novos dados, link para a API/portal oficial.
- **Alternativas consideradas**: Outras abordagens que voce considerou.

Para funcionalidades maiores, considere escrever um documento de design em `docs/plans/` como parte da sua proposta.

---

## Vulnerabilidades de Seguranca

**Nao abra uma issue publica para vulnerabilidades de seguranca.** Em vez disso, envie um email diretamente aos mantenedores. Inclua:

- Descricao da vulnerabilidade.
- Passos para reproduzir.
- Impacto potencial.

Responderemos em ate 48 horas e coordenaremos uma correcao antes da divulgacao publica.

---

Obrigado por contribuir com a transparencia democratica no Brasil.
