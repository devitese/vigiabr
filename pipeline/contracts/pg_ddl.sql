-- VigiaBR — Target PostgreSQL Schema (contract)
-- This DDL defines the target table shapes.
-- Actual migrations are managed by Alembic in pipeline/schemas/alembic/.

-- Base convention: all tables have id (UUID PK), created_at, updated_at

CREATE TABLE mandatarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_tse          VARCHAR(20) UNIQUE NOT NULL,
    nome            VARCHAR(255) NOT NULL,
    nome_civil      VARCHAR(255),
    cargo           VARCHAR(100) NOT NULL,
    uf              CHAR(2) NOT NULL,
    partido_sigla   VARCHAR(20),
    mandato_inicio  DATE,
    mandato_fim     DATE,
    sci_score       INTEGER CHECK (sci_score BETWEEN 0 AND 1000),
    cpf_hash        CHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE partidos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sigla               VARCHAR(20) UNIQUE NOT NULL,
    nome                VARCHAR(255) NOT NULL,
    numero_eleitoral    INTEGER UNIQUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pessoas_fisicas (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        VARCHAR(255) NOT NULL,
    cpf_hash    CHAR(64) UNIQUE NOT NULL,
    tipo        VARCHAR(50) NOT NULL CHECK (tipo IN ('Familiar', 'Assessor', 'Socio', 'Doador', 'Outro')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE empresas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cnpj            VARCHAR(18) UNIQUE NOT NULL,
    razao_social    VARCHAR(500) NOT NULL,
    cnae            VARCHAR(10),
    situacao        VARCHAR(50),
    data_abertura   DATE,
    capital_social  NUMERIC(18,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bens_patrimoniais (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mandatario_id           UUID REFERENCES mandatarios(id),
    mandatario_id_externo   VARCHAR(20),
    tipo                    VARCHAR(100) NOT NULL,
    descricao               TEXT,
    valor_declarado         NUMERIC(18,2) NOT NULL,
    ano_eleicao             INTEGER NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX bens_patrimoniais_ext_uq
    ON bens_patrimoniais (mandatario_id_externo, tipo, ano_eleicao);

CREATE TABLE emendas (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero      VARCHAR(50) UNIQUE NOT NULL,
    tipo        VARCHAR(100),
    valor_pago  NUMERIC(18,2),
    ano         INTEGER NOT NULL,
    funcao      VARCHAR(100),
    autor_id    UUID REFERENCES mandatarios(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE contratos_gov (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero              VARCHAR(100) UNIQUE NOT NULL,
    objeto              TEXT,
    valor               NUMERIC(18,2),
    orgao_contratante   VARCHAR(255),
    data_assinatura     DATE,
    empresa_id          UUID REFERENCES empresas(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE votacoes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_externo          VARCHAR(100) UNIQUE NOT NULL,
    data                TIMESTAMPTZ NOT NULL,
    descricao           TEXT,
    tipo_proposicao     VARCHAR(50),
    resultado           VARCHAR(50),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE projetos_lei (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero      INTEGER NOT NULL,
    ano         INTEGER NOT NULL,
    tipo        VARCHAR(20) NOT NULL,
    ementa      TEXT,
    tema        VARCHAR(100),
    situacao    VARCHAR(100),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tipo, numero, ano)
);

CREATE TABLE processos_judiciais (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero_cnj      VARCHAR(25) UNIQUE NOT NULL,
    tipo            VARCHAR(100),
    tribunal        VARCHAR(50) NOT NULL,
    situacao        VARCHAR(100),
    valor_causa     NUMERIC(18,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inconsistencias (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo            VARCHAR(100) NOT NULL,
    descricao_neutra TEXT NOT NULL,
    metrica         VARCHAR(255),
    score_impacto   INTEGER NOT NULL CHECK (score_impacto BETWEEN 0 AND 250),
    fontes          TEXT[] NOT NULL DEFAULT '{}',
    data_deteccao   DATE NOT NULL DEFAULT CURRENT_DATE,
    mandatario_id   UUID REFERENCES mandatarios(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Junction / relationship tables

CREATE TABLE mandatario_votos (
    mandatario_id   UUID NOT NULL REFERENCES mandatarios(id),
    votacao_id      UUID NOT NULL REFERENCES votacoes(id),
    voto            VARCHAR(20) NOT NULL CHECK (voto IN ('Sim', 'Não', 'Abstenção', 'Ausente', 'Obstrução')),
    data            TIMESTAMPTZ,
    PRIMARY KEY (mandatario_id, votacao_id)
);

CREATE TABLE mandatario_familiares (
    mandatario_id       UUID NOT NULL REFERENCES mandatarios(id),
    pessoa_fisica_id    UUID NOT NULL REFERENCES pessoas_fisicas(id),
    grau                VARCHAR(50) NOT NULL,
    PRIMARY KEY (mandatario_id, pessoa_fisica_id)
);

CREATE TABLE mandatario_contratacoes (
    mandatario_id       UUID NOT NULL REFERENCES mandatarios(id),
    pessoa_fisica_id    UUID NOT NULL REFERENCES pessoas_fisicas(id),
    cargo               VARCHAR(100),
    salario             NUMERIC(12,2),
    data_inicio         DATE,
    gabinete            BOOLEAN DEFAULT false,
    PRIMARY KEY (mandatario_id, pessoa_fisica_id)
);

CREATE TABLE pessoa_empresa_socios (
    pessoa_fisica_id    UUID NOT NULL REFERENCES pessoas_fisicas(id),
    empresa_id          UUID NOT NULL REFERENCES empresas(id),
    percentual_cotas    NUMERIC(6,2),
    data_entrada        DATE,
    data_saida          DATE,
    PRIMARY KEY (pessoa_fisica_id, empresa_id)
);

CREATE TABLE mandatario_filiacoes (
    mandatario_id   UUID NOT NULL REFERENCES mandatarios(id),
    partido_id      UUID NOT NULL REFERENCES partidos(id),
    data_filiacao   DATE,
    data_desfiliacao DATE,
    PRIMARY KEY (mandatario_id, partido_id, data_filiacao)
);

CREATE TABLE doacoes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mandatario_id   UUID NOT NULL REFERENCES mandatarios(id),
    valor           NUMERIC(18,2) NOT NULL,
    data            DATE,
    eleicao_ano     INTEGER,
    origem          VARCHAR(10) CHECK (origem IN ('PF', 'PJ', 'Partido', 'Candidato')),
    doador_nome     VARCHAR(255),
    doador_cpf_cnpj_hash CHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
