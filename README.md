# VigiaBR

Plataforma open-source de monitoramento de transparencia de agentes publicos brasileiros. O VigiaBR coleta dados oficiais publicamente disponiveis, calcula um **Score de Consistencia (SCI)** — um indice de 0 a 1000 que mede a consistencia entre registros oficiais — e apresenta os resultados com rastreabilidade completa das fontes.

**Principio fundamental:** Nunca acusar ou inferir. Apenas apresentar fatos (FATO), metricas (METRICA) e fontes (FONTE) com links diretos para os dados oficiais.

[![Licenca: AGPL-3.0](https://img.shields.io/badge/Licen%C3%A7a-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)

---

## Sumario

- [Visao Geral](#visao-geral)
- [Arquitetura](#arquitetura)
- [Fontes de Dados](#fontes-de-dados)
- [Score SCI](#score-sci)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Primeiros Passos](#primeiros-passos)
- [Executando o Pipeline](#executando-o-pipeline)
- [Testes](#testes)
- [Contribuindo](#contribuindo)
- [Roadmap](#roadmap)
- [Licenca](#licenca)

---

## Visao Geral

O Brasil publica grandes volumes de dados publicos sobre agentes eleitos — declaracoes de bens, registros de votacao, doacoes de campanha, contratos governamentais, participacoes societarias e muito mais. Esses dados estao espalhados por dezenas de portais com formatos diferentes e sem cruzamento entre si.

O VigiaBR preenche essa lacuna:

1. **Extraindo** dados de 7 fontes publicas oficiais usando spiders Scrapy e downloaders em massa
2. **Transformando** dados brutos em registros normalizados, validados e em conformidade com a LGPD (todo PII hasheado com SHA-256)
3. **Carregando** no PostgreSQL (consultas tabulares) e Neo4j (relacionamentos em grafo)
4. **Pontuando** a consistencia entre registros usando o algoritmo SCI
5. **Apresentando** os resultados via interface web com visualizacoes interativas de grafos

---

## Arquitetura

```
[Fontes Oficiais]           [Extracao]                [Processamento]           [Persistencia]

API Camara ──────┐
API Senado ──────┤
Dumps TSE ───────┤          Spiders Scrapy    →  data/raw/{fonte}/    →  Transformadores  → PostgreSQL
API CGU ─────────┤→         & downloaders        YYYY-MM-DD/             Validadores         Neo4j
Dump CNPJ ───────┤          em massa             *.jsonl                 (dedup, hash PII)   SQLite/DuckDB
Querido Diario ──┤                                                       Loaders             (CNPJ)
API CNJ ─────────┘                                                       (upsert em lote)

                            [Plataforma]
                            DAGs Airflow orquestram: extrair → processar por fonte
                            Docker Compose executa todos os servicos
                            Grafana + Prometheus monitora a saude
```

### Stack Tecnologico

| Camada | Tecnologia |
|--------|-----------|
| Coleta de Dados | Python, Scrapy, httpx |
| Orquestracao do Pipeline | Apache Airflow |
| Banco de Dados de Grafos | Neo4j Community (Cypher) |
| Banco de Dados Relacional | PostgreSQL 16 |
| ML / Scoring | scikit-learn, XGBoost |
| NLP (local) | Ollama, Mistral |
| API Backend | FastAPI |
| Frontend | Next.js, React |
| Visualizacao de Grafos | Cytoscape.js |
| BD Local CNPJ | SQLite, DuckDB |
| Infraestrutura | Docker, Caddy |
| Monitoramento | Grafana, Prometheus |
| Gerenciador de Pacotes | uv (workspace monorepo) |

### Modelo de Grafos (Neo4j)

Tipos de nos principais: `:Mandatario` (politico), `:Partido`, `:Empresa`, `:BemPatrimonial` (bens), `:Emenda`, `:ContratoGov`, `:Votacao`, `:ProjetoLei`, `:ProcessoJudicial`, `:Inconsistencia`

Relacionamentos principais: `FILIADO_A`, `VOTOU`, `TEM_FAMILIAR`, `CONTRATOU`, `SOCIO_DE`, `RECEBEU_DOACAO`

---

## Fontes de Dados

Todos os dados sao publicamente acessiveis sob a Lei de Acesso a Informacao (LAI).

| Fonte | Portal | Dados |
|-------|--------|-------|
| Camara dos Deputados | [dadosabertos.camara.leg.br](https://dadosabertos.camara.leg.br) | Votacoes, gastos CEAP, projetos de lei |
| Senado Federal | [legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos) | Votacoes, projetos de lei, comissoes |
| TSE | [dadosabertos.tse.jus.br](https://dadosabertos.tse.jus.br) | Declaracoes de bens, doacoes de campanha |
| Portal da Transparencia (CGU) | [portaldatransparencia.gov.br/api](https://portaldatransparencia.gov.br/api-de-dados) | Emendas, contratos, CEIS |
| Receita Federal CNPJ | [arquivos.receitafederal.gov.br](https://arquivos.receitafederal.gov.br) | Participacoes societarias (~30GB dump mensal) |
| Querido Diario | [queridodiario.ok.org.br](https://queridodiario.ok.org.br) | Nomeacoes DAS, diario oficial |
| CNJ DataJud | [datajud.cnj.jus.br](https://datajud.cnj.jus.br) | Processos judiciais publicos |

---

## Score SCI

O Score de Consistencia (SCI) e um indice composto de 0 a 1000 que mede o quao consistentes sao os registros oficiais de um politico em multiplas dimensoes.

| Dimensao | Descricao |
|----------|-----------|
| Evolucao patrimonial vs salario | O crescimento patrimonial declarado esta alinhado com a renda conhecida? |
| Correlacao de votos com setor de doadores | Os padroes de votacao favorecem setores dos doadores de campanha? |
| Contratos com empresas familiares | Empresas ligadas a familiares recebem contratos governamentais? |
| Vinculacao de beneficiarios de emendas | Os recursos de emendas fluem para entidades conectadas? |
| Contratacao de familiares em gabinete | Familiares sao contratados com recursos publicos? |
| Mudanca de voto apos doacao | O comportamento de votacao mudou apos receber doacoes? |

> O SCI nao implica irregularidade. Ele evidencia padroes estatisticos para escrutinio publico com rastreabilidade completa das fontes.
>
> **Nota:** Os pesos de cada dimensao ainda estao sendo definidos por calculo estatistico e serao publicados quando o modelo estiver validado.

---

## Estrutura do Projeto

```
vigiabr/
├── pipeline/
│   ├── pyproject.toml              # Raiz do workspace uv
│   ├── contracts/                  # Contratos de dados compartilhados
│   │   ├── raw_formats/            # JSON Schema por fonte
│   │   ├── pg_ddl.sql              # Definicoes de tabelas PostgreSQL
│   │   ├── neo4j_constraints.cypher
│   │   └── data_flow.md
│   │
│   ├── schemas/                    # Schemas de banco e tipos compartilhados
│   │   ├── models/                 # Modelos Pydantic (um por entidade)
│   │   ├── alembic/                # Migracoes PostgreSQL
│   │   ├── neo4j/                  # Constraints e indices Cypher
│   │   └── pii/                    # Hash de CPF (SHA-256, LGPD)
│   │
│   ├── extraction/                 # Spiders Scrapy e downloaders em massa
│   │   ├── vigiabr_spiders/        # Projeto Scrapy
│   │   │   └── spiders/            # Um spider por fonte
│   │   ├── bulk/                   # Downloaders em massa CNPJ e TSE
│   │   └── tests/
│   │
│   ├── processing/                 # Transformar, validar, carregar
│   │   ├── processing/
│   │   │   ├── transformers/       # JSON bruto → modelos Pydantic
│   │   │   ├── validators/         # Dedup, hash de PII
│   │   │   └── loaders/            # Upsert em lote PostgreSQL, Neo4j, DuckDB
│   │   └── tests/
│   │
│   └── platform/                   # Infraestrutura e orquestracao
│       ├── docker/                 # Docker Compose e Dockerfiles
│       ├── airflow/                # DAGs (uma por fonte)
│       ├── monitoring/             # Dashboards Grafana, config Prometheus
│       └── scripts/                # Scripts de setup para desenvolvimento
│
├── CLAUDE.md
├── README.md
└── .gitignore
```

O pipeline usa um **workspace monorepo uv** com tres pacotes Python:

| Pacote | Caminho | Descricao |
|--------|---------|-----------|
| `vigiabr-schemas` | `pipeline/schemas/` | Modelos Pydantic, migracoes Alembic, utilitarios de PII |
| `vigiabr-extraction` | `pipeline/extraction/` | Spiders Scrapy e downloaders em massa |
| `vigiabr-processing` | `pipeline/processing/` | Transformadores, validadores e loaders de banco |

Os dados fluem atraves de contratos baseados em arquivos — a extracao escreve arquivos JSONL em `pipeline/data/raw/`, o processamento os le. Nao ha imports Python diretos entre os dois.

---

## Primeiros Passos

### Pre-requisitos

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (gerenciador de pacotes)
- **Docker** e **Docker Compose** (para bancos de dados e servicos)

### Instalacao

```bash
# Clonar o repositorio
git clone https://github.com/devitese/vigiabr.git
cd vigiabr

# Instalar todas as dependencias do pipeline (resolve o workspace)
cd pipeline
uv sync

# Iniciar os servicos de infraestrutura
cd platform/docker
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Executar migracoes do banco de dados
uv run --project ../schemas alembic -c ../schemas/alembic/alembic.ini upgrade head

# Aplicar constraints do Neo4j
# (requer Neo4j rodando via Docker Compose)
```

---

## Executando o Pipeline

### Extracao — Executar Spiders

```bash
# Executar um spider especifico
uv run --project pipeline/extraction scrapy crawl camara_deputados

# Spiders disponiveis:
#   camara_deputados    — API REST da Camara dos Deputados
#   senado_federal      — API REST do Senado Federal
#   tse_patrimonio      — Declaracoes de bens do TSE
#   transparencia_cgu   — Portal da Transparencia/CGU
#   querido_diario      — Entradas do Querido Diario
#   cnj_datajud         — Processos do CNJ DataJud
```

```bash
# Executar downloaders em massa
uv run --project pipeline/extraction python -m bulk.cnpj_downloader
uv run --project pipeline/extraction python -m bulk.tse_dump_downloader
```

A saida dos spiders e gravada em `pipeline/data/raw/{fonte}/YYYY-MM-DD/*.jsonl`.

### Processamento — Transformar e Carregar

```bash
# Processar uma fonte especifica
uv run --project pipeline/processing python -m processing.run camara

# Fontes: camara, senado, tse, transparencia, cnpj, querido_diario, cnj
```

### Orquestracao — DAGs do Airflow

Ao executar via Airflow (Docker Compose), cada fonte tem sua propria DAG que encadeia as etapas de extracao e processamento. Acione as DAGs pela interface do Airflow ou pela CLI.

---

## Testes

```bash
# Executar todos os testes do workspace
cd pipeline
uv run pytest

# Executar testes de um pacote especifico
uv run --project schemas pytest
uv run --project extraction pytest
uv run --project processing pytest
```

Os testes de extracao usam fixtures HTTP gravadas (sem chamadas de rede). Os testes de processamento usam bancos de dados em memoria.

---

## Contribuindo

1. **Crie uma Issue no GitHub** descrevendo a alteracao
2. **Crie uma branch a partir de `develop`** usando a convencao: `tipo/numero-da-issue-descricao-curta`
   - Exemplo: `feat/42-add-sci-endpoint`
3. **Use conventional commits**: `tipo(escopo): descricao`
   - Tipos: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`, `revert`
4. **Execute os testes** antes de fazer push
5. **Abra um PR apontando para `develop`** (nunca diretamente para `master`)

### Fluxo Git

- `master` — producao (protegida, apenas deploy)
- `develop` — branch de integracao (todos os PRs apontam para ca)
- Estrategia de merge: squash merge para `develop`, merge commit de `develop` para `master`

### Conformidade LGPD

Todo PII (especialmente numeros de CPF) **deve** ser hasheado com SHA-256 antes do armazenamento. Nunca armazene identificadores pessoais reversiveis. Veja `pipeline/schemas/pii/` para o utilitario de hash.

---

## Roadmap

| Fase | Escopo | Status |
|------|--------|--------|
| **Fase 1 (MVP)** | Congresso Federal (Camara + Senado) — pipelines, SCI basico, perfis, cards de inconsistencia | Em Andamento |
| **Fase 2** | Grafos interativos, visoes de familiares, scoring com ML, analise de discurso com NLP | Planejado |
| **Fase 3** | Deputados estaduais, comparacao/ranking, API publica, exportacao PDF | Planejado |
| **Fase 4** | Vereadores municipais, aplicativo mobile | Planejado |

---

## Licenca

Este projeto e licenciado sob a [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) (AGPL-3.0).

Voce e livre para usar, modificar e distribuir este software, desde que versoes modificadas disponibilizadas pela rede tambem disponibilizem seu codigo-fonte sob a mesma licenca.
