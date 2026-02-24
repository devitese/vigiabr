# Next.js Frontend — Extensive Phased Plan

**Issue:** #10
**Date:** 2026-02-24
**Status:** Draft
**Scope:** MVP (Phase 1) — Mandatario profiles, SCI scores, inconsistency cards, patrimony charts
**Branch:** `feat/10-nextjs-frontend` (from `develop`)
**Package manager:** pnpm

---

## Overview

This plan covers the full implementation of the VigiaBR frontend — a Next.js 15 + React application that presents politician profiles, SCI consistency scores, inconsistency cards, timelines, and patrimony evolution charts. The frontend communicates exclusively via REST API with the FastAPI backend (Issue #9). No direct database access.

The implementation is split into **6 phases**, each building on the previous. Each phase produces a testable, reviewable increment.

---

## Design Language (from PRD)

### Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--ink` | `#0d0d0d` | Primary text |
| `--paper` | `#f5f0e8` | Background (warm off-white) |
| `--red` | `#c0392b` | Accent, badges, high-severity inconsistencies |
| `--red-light` | `#fdf0ee` | Red tint backgrounds |
| `--navy` | `#1a2744` | Headings, nav, primary UI |
| `--navy-light` | `#eef1f7` | Navy tint backgrounds |
| `--gold` | `#b8860b` | Secondary accent, medium-severity |
| `--gold-light` | `#fdf9ee` | Gold tint backgrounds |
| `--gray` | `#6b7280` | Secondary text, metadata |
| `--border` | `#d1c9b8` | Dividers, card borders |

### Typography

| Role | Font | Tailwind class |
|------|------|---------------|
| Display/headings | Playfair Display 700/900 | `font-display` |
| Body text | Source Serif 4, 300/400/600 | `font-serif` |
| Data/metrics/code | IBM Plex Mono 400/600 | `font-mono` |

Google Fonts import: `Playfair+Display:wght@700;900`, `IBM+Plex+Mono:wght@400;600`, `Source+Serif+4:wght@300;400;600`.

### Design Principles

- **Newspaper-like aesthetic**: clean, serious, institutional
- **Monospace for data**: all scores, percentages, monetary values, dates use `font-mono`
- **Serif for prose**: descriptions, explanations, body text
- **Strictly neutral language**: no emojis, no subjective adjectives, no accusatory language
- **Source links always visible**: every data point links to official government portal (opens in new tab)
- **Cards with left border accent**: inconsistency cards use colored left border (red/gold based on severity)

### SCI Score Color Bands

| Range | Color | Label |
|-------|-------|-------|
| 0–250 | Red (`#c0392b`) | Critical |
| 251–500 | Orange (`#e67e22`) | Low |
| 501–750 | Gold (`#b8860b`) | Moderate |
| 751–1000 | Green (`#27ae60`) | High |

---

## API Contract

The frontend codes against the backend API contract (Issue #9). These are the endpoints consumed:

| Endpoint | Method | Response | Frontend usage |
|----------|--------|----------|---------------|
| `GET /search?q={query}` | GET | `{ items: MandatarioSummary[], total: int }` | Search bar autocomplete |
| `GET /mandatarios` | GET | `{ items: MandatarioSummary[], total: int, cursor: str }` | Home featured list |
| `GET /mandatarios/{id}` | GET | `MandatarioProfile` | Profile page header |
| `GET /mandatarios/{id}/sci` | GET | `{ total: int, dimensions: DimensionScore[] }` | SCI gauge + breakdown |
| `GET /mandatarios/{id}/inconsistencias` | GET | `{ items: Inconsistencia[], total: int, cursor: str }` | Inconsistency cards |
| `GET /mandatarios/{id}/timeline` | GET | `{ items: TimelineEvent[], total: int, cursor: str }` | Timeline component |
| `GET /mandatarios/{id}/patrimonio` | GET | `{ items: PatrimonioDataPoint[] }` | Patrimony chart |
| `GET /health` | GET | `{ status: str }` | Health check (for deploy smoke tests) |

### TypeScript Types (derived from pipeline schemas)

```typescript
// lib/types.ts

interface MandatarioSummary {
  id: string;          // UUID
  nome: string;
  cargo: string;       // "Deputado Federal" | "Senador"
  uf: string;          // 2-letter state code
  partido_sigla: string | null;
  sci_score: number | null;  // 0-1000
}

interface MandatarioProfile extends MandatarioSummary {
  id_tse: string;
  nome_civil: string | null;
  mandato_inicio: string | null;  // ISO date
  mandato_fim: string | null;
}

interface DimensionScore {
  dimension: string;   // "patrimonio" | "voto_doador" | etc.
  label: string;       // Human-readable Portuguese label
  score: number;       // Deduction points (0-250)
  max_score: number;   // Maximum possible deduction
}

interface SCIBreakdown {
  total: number;       // 0-1000
  dimensions: DimensionScore[];
}

interface Inconsistencia {
  id: string;
  tipo: string;
  descricao_neutra: string;  // FATO
  metrica: string | null;     // METRICA
  score_impacto: number;      // 0-250
  fontes: string[];           // FONTE (URLs)
  data_deteccao: string;      // ISO date
}

interface TimelineEvent {
  id: string;
  tipo: string;        // "voto" | "despesa" | "declaracao" | "contrato" | "emenda" | "processo"
  data: string;        // ISO datetime
  titulo: string;
  descricao: string | null;
  valor: number | null;
  fonte_url: string | null;
}

interface PatrimonioDataPoint {
  ano_eleicao: number;
  valor_declarado: number;    // Total declared wealth
  salario_acumulado: number;  // Cumulative public salary up to that year
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  next_cursor: string | null;
}
```

---

## Directory Structure (Final State)

```
frontend/
├── package.json
├── pnpm-lock.yaml
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
├── .env.local.example        # NEXT_PUBLIC_API_URL=http://localhost:8000
├── public/
│   ├── favicon.ico
│   └── og-image.png          # Open Graph preview image
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout: html, body, fonts, nav, footer
│   │   ├── page.tsx           # Home: search + featured mandatarios
│   │   ├── not-found.tsx      # Custom 404
│   │   ├── error.tsx          # Global error boundary
│   │   ├── loading.tsx        # Global loading skeleton
│   │   ├── mandatario/
│   │   │   └── [id]/
│   │   │       ├── page.tsx   # SSR profile page
│   │   │       ├── loading.tsx
│   │   │       └── error.tsx
│   │   └── sobre/
│   │       └── page.tsx       # Static "About" page
│   ├── components/
│   │   ├── nav.tsx
│   │   ├── footer.tsx
│   │   ├── sci-gauge.tsx
│   │   ├── sci-dimension-bar.tsx
│   │   ├── inconsistency-card.tsx
│   │   ├── inconsistency-list.tsx
│   │   ├── timeline.tsx
│   │   ├── timeline-item.tsx
│   │   ├── patrimony-chart.tsx
│   │   ├── search-bar.tsx
│   │   ├── mandatario-summary.tsx
│   │   └── skeleton.tsx       # Reusable loading skeletons
│   ├── lib/
│   │   ├── api.ts             # Fetch wrapper (server + client)
│   │   ├── types.ts           # TypeScript types matching API schemas
│   │   ├── constants.ts       # SCI bands, color mappings, dimension labels
│   │   └── utils.ts           # formatCurrency, formatDate, getSCIColor
│   └── styles/
│       └── globals.css        # Tailwind directives + CSS custom properties
└── __tests__/                 # Component tests (Vitest + Testing Library)
    ├── setup.ts
    ├── sci-gauge.test.tsx
    ├── inconsistency-card.test.tsx
    ├── search-bar.test.tsx
    └── utils.test.ts
```

---

## Phase 1: Project Scaffolding & Design System

**Goal:** Set up the Next.js project with all tooling, fonts, Tailwind config, and shared utilities. No pages yet — just the foundation.

### 1.1 Initialize Next.js project

```bash
cd frontend/
pnpm create next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

### 1.2 Install dependencies

```bash
# Core
pnpm add recharts

# Dev
pnpm add -D @testing-library/react @testing-library/jest-dom vitest @vitejs/plugin-react jsdom
```

### 1.3 Configure Tailwind (`tailwind.config.ts`)

- Define custom colors: `ink`, `paper`, `red`, `red-light`, `navy`, `navy-light`, `gold`, `gold-light`, `gray`, `border`
- Define custom fonts: `display` (Playfair Display), `serif` (Source Serif 4), `mono` (IBM Plex Mono)
- Set `content` paths to `./src/**/*.{ts,tsx}`

### 1.4 Configure globals.css

- Tailwind directives (`@tailwind base`, `components`, `utilities`)
- CSS custom properties matching PRD (as fallback/reference)
- Google Fonts import via `next/font/google` (preferred over CSS import for performance)
- Base styles: `body { background: paper; font-family: serif; color: ink; }`

### 1.5 Create `lib/types.ts`

All TypeScript interfaces matching the API contract (as defined above).

### 1.6 Create `lib/constants.ts`

```typescript
export const SCI_BANDS = [
  { min: 0, max: 250, color: '#c0392b', label: 'Critico', bg: 'bg-red-light' },
  { min: 251, max: 500, color: '#e67e22', label: 'Baixo', bg: 'bg-orange-100' },
  { min: 501, max: 750, color: '#b8860b', label: 'Moderado', bg: 'bg-gold-light' },
  { min: 751, max: 1000, color: '#27ae60', label: 'Alto', bg: 'bg-green-100' },
] as const;

export const DIMENSION_LABELS: Record<string, string> = {
  patrimonio: 'Patrimonio vs Renda',
  voto_doador: 'Voto x Setor Doador',
  contrato_familiar: 'Contrato Familiar',
  emenda_vinculo: 'Emenda x Vinculo',
  gabinete_familiar: 'Gabinete Familiar',
  voto_pos_doacao: 'Voto Pos-Doacao',
};
```

### 1.7 Create `lib/utils.ts`

```typescript
export function formatCurrency(value: number): string;      // R$ 1.234.567,89
export function formatDate(isoDate: string): string;         // 15 jan 2024
export function formatDateTime(isoDate: string): string;     // 15 jan 2024 14:30
export function getSCIColor(score: number): string;          // returns hex color
export function getSCILabel(score: number): string;          // returns band label
export function getSCIBand(score: number): SCIBand;          // returns full band object
```

### 1.8 Create `lib/api.ts`

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T>;

// Typed API functions
export async function searchMandatarios(query: string): Promise<PaginatedResponse<MandatarioSummary>>;
export async function getMandatario(id: string): Promise<MandatarioProfile>;
export async function getMandatarioSCI(id: string): Promise<SCIBreakdown>;
export async function getMandatarioInconsistencias(id: string, cursor?: string): Promise<PaginatedResponse<Inconsistencia>>;
export async function getMandatarioTimeline(id: string, cursor?: string): Promise<PaginatedResponse<TimelineEvent>>;
export async function getMandatarioPatrimonio(id: string): Promise<PatrimonioDataPoint[]>;
export async function getFeaturedMandatarios(): Promise<{ highest: MandatarioSummary[], lowest: MandatarioSummary[] }>;
```

### 1.9 Create `.env.local.example`

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 1.10 Configure `next.config.ts`

- Enable `output: 'standalone'` (for Docker deployment)
- Configure `images.remotePatterns` if needed
- Set `reactStrictMode: true`

### Deliverables

- [ ] Next.js 15 project initialized with App Router
- [ ] Tailwind configured with VigiaBR design tokens
- [ ] Google Fonts loaded via `next/font/google`
- [ ] `lib/types.ts` — all TypeScript interfaces
- [ ] `lib/constants.ts` — SCI bands, dimension labels
- [ ] `lib/utils.ts` — formatting utilities
- [ ] `lib/api.ts` — typed API client
- [ ] `.env.local.example` with API URL
- [ ] `next.config.ts` with standalone output
- [ ] Vitest configured and running (empty test suite passes)

### Testing gate

```bash
pnpm build   # Compiles without errors
pnpm test    # Vitest passes (setup test)
pnpm lint    # ESLint passes
```

---

## Phase 2: Layout Shell & Navigation

**Goal:** Build the root layout, navigation bar, footer, and global error/loading states. After this phase, navigating to any route shows the app shell.

### 2.1 Root Layout (`app/layout.tsx`)

- `<html lang="pt-BR">` with font classes
- Load fonts via `next/font/google`: Playfair Display, Source Serif 4, IBM Plex Mono
- `<body>` with `bg-paper text-ink font-serif` classes
- Render `<Nav />` at top, `{children}` in main, `<Footer />` at bottom
- Metadata: `title: "VigiaBR — Transparencia Publica"`, `description`, Open Graph tags

### 2.2 Nav Component (`components/nav.tsx`)

- Sticky top bar, navy background
- Left: "VigiaBR" wordmark in `font-display` (link to `/`)
- Right: Links to `/sobre`
- Mobile: hamburger menu (simple CSS toggle, no JS library)
- Active link indicator (underline accent)

### 2.3 Footer Component (`components/footer.tsx`)

- Navy background, warm paper text
- Three columns:
  - **VigiaBR** — tagline: "Transparencia e um direito, nao um privilegio."
  - **Links** — Sobre, GitHub repo, Metodologia
  - **Legal** — "Dados publicos oficiais. Licenca AGPL-3.0."
- Copyright year (dynamic)

### 2.4 Global Loading (`app/loading.tsx`)

- Skeleton placeholder matching the page layout
- Animated pulse effect (Tailwind `animate-pulse`)

### 2.5 Global Error (`app/error.tsx`)

- Client component with `reset()` function
- Neutral error message: "Ocorreu um erro ao carregar esta pagina."
- "Tentar novamente" button

### 2.6 Not Found (`app/not-found.tsx`)

- "Pagina nao encontrada" message
- Link back to home

### 2.7 Skeleton Component (`components/skeleton.tsx`)

- Reusable `<Skeleton width height className />` component
- Used across all loading states

### Deliverables

- [ ] Root layout with fonts, metadata, nav, footer
- [ ] `<Nav />` — responsive, sticky, with links
- [ ] `<Footer />` — three-column, dark background
- [ ] Global loading, error, not-found pages
- [ ] `<Skeleton />` reusable component

### Testing gate

```bash
pnpm build    # All pages compile
pnpm dev      # Nav and footer render on all routes
```

---

## Phase 3: Core Components (No Data Fetching)

**Goal:** Build all presentational components in isolation, using hardcoded mock data. Each component is self-contained and testable.

### 3.1 SCI Gauge (`components/sci-gauge.tsx`)

**Props:** `{ score: number | null }`

Visual design:
- Large number display (`font-mono text-5xl font-semibold`)
- Color matches SCI band (red/orange/gold/green)
- Horizontal bar showing position on 0–1000 scale
- Band label below ("Critico" / "Baixo" / "Moderado" / "Alto")
- If `score === null`: show "Sem dados" in gray

Accessibility:
- `role="meter"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- `aria-label="Score de Consistencia: {score} de 1000"`

### 3.2 SCI Dimension Bar (`components/sci-dimension-bar.tsx`)

**Props:** `{ dimension: DimensionScore }`

- Label (Portuguese, from `DIMENSION_LABELS`)
- Horizontal progress bar showing `score / max_score`
- Numeric value in `font-mono`
- Color gradient (green when low deduction, red when high)

### 3.3 Inconsistency Card (`components/inconsistency-card.tsx`)

**Props:** `{ inconsistencia: Inconsistencia }`

Visual design:
- Card with left border accent (color based on `score_impacto` severity)
- Three labeled sections:
  - **FATO**: `descricao_neutra` (serif, regular weight)
  - **METRICA**: `metrica` (monospace, semibold)
  - **FONTE**: Each URL in `fontes[]` as a link (monospace, small, opens in new tab)
- Score impact badge in top-right corner (`font-mono`)
- Detection date in footer (`font-mono text-gray`)

Accessibility:
- `<article>` element with `aria-label`
- Source links have `rel="noopener noreferrer"` and `target="_blank"`

### 3.4 Inconsistency List (`components/inconsistency-list.tsx`)

**Props:** `{ inconsistencias: Inconsistencia[], onLoadMore?: () => void, hasMore?: boolean }`

- Renders list of `<InconsistencyCard />` components
- "Carregar mais" button when `hasMore` is true
- Empty state: "Nenhuma inconsistencia detectada."

### 3.5 Timeline (`components/timeline.tsx`)

**Props:** `{ events: TimelineEvent[], onLoadMore?: () => void, hasMore?: boolean }`

Visual design:
- Vertical timeline with left-side date markers
- Each event is a `<TimelineItem />`
- Grouped by year (year dividers)
- "Carregar mais" button at bottom

### 3.6 Timeline Item (`components/timeline-item.tsx`)

**Props:** `{ event: TimelineEvent }`

- Icon/badge by event type (color-coded dot)
- Date in `font-mono`
- Title in bold
- Description (if present)
- Value in `font-mono` (if present, formatted as currency)
- Source link (if present)

Event type color mapping:
| Type | Color |
|------|-------|
| `voto` | Navy |
| `despesa` | Gold |
| `declaracao` | Green |
| `contrato` | Red |
| `emenda` | Orange |
| `processo` | Gray |

### 3.7 Patrimony Chart (`components/patrimony-chart.tsx`)

**Props:** `{ data: PatrimonioDataPoint[] }`

- Recharts `<LineChart>` with two lines:
  - Blue line: `valor_declarado` (declared wealth)
  - Gray dashed line: `salario_acumulado` (cumulative salary)
- X-axis: election years
- Y-axis: BRL value (formatted with abbreviations: R$ 1,2M)
- Tooltip showing exact values
- Legend at bottom
- Responsive (`<ResponsiveContainer>`)
- Empty state if no data

### 3.8 Search Bar (`components/search-bar.tsx`)

**Props:** `{ onSearch?: (query: string) => void, variant?: 'hero' | 'nav' }`

- Text input with search icon
- Debounced input (300ms) — `useEffect` with timeout, no external library
- `hero` variant: large, centered, prominent (for home page)
- `nav` variant: compact (for navigation bar — Phase 2+ integration)
- Dropdown suggestions list (rendered when results exist)
- Each suggestion renders `<MandatarioSummary />` as a link
- Keyboard navigation: arrow keys + enter
- Loading spinner while fetching

Accessibility:
- `role="combobox"` with `aria-expanded`, `aria-controls`
- `aria-activedescendant` for keyboard navigation
- Results in `role="listbox"` with `role="option"` children

### 3.9 Mandatario Summary Card (`components/mandatario-summary.tsx`)

**Props:** `{ mandatario: MandatarioSummary }`

- Compact card for search results and featured lists
- Name (serif, bold)
- Party + UF badge (`font-mono`, small)
- Cargo label
- SCI score mini-badge (colored dot + number)
- Entire card is a `<Link>` to `/mandatario/{id}`

### Deliverables

- [ ] `<SCIGauge />` — score display with color band and meter role
- [ ] `<SCIDimensionBar />` — individual dimension breakdown
- [ ] `<InconsistencyCard />` — FATO/METRICA/FONTE card
- [ ] `<InconsistencyList />` — paginated list of cards
- [ ] `<Timeline />` — vertical timeline with year grouping
- [ ] `<TimelineItem />` — individual event
- [ ] `<PatrimonyChart />` — Recharts dual-line chart
- [ ] `<SearchBar />` — debounced autocomplete with keyboard nav
- [ ] `<MandatarioSummary />` — compact result card

### Testing gate

```bash
pnpm test     # Component tests pass for all 9 components
pnpm build    # Compiles without errors
```

### Component tests to write

| Test file | Coverage |
|-----------|----------|
| `sci-gauge.test.tsx` | Renders score, correct color, null state, meter role |
| `inconsistency-card.test.tsx` | Renders FATO/METRICA/FONTE, links open in new tab, severity color |
| `search-bar.test.tsx` | Debounce fires, keyboard navigation, combobox role |
| `utils.test.ts` | `formatCurrency`, `formatDate`, `getSCIColor`, `getSCIBand` |

---

## Phase 4: Pages — Data Integration

**Goal:** Wire up the pages to the API client. After this phase, the app is functional end-to-end (assuming backend is running).

### 4.1 Home Page (`app/page.tsx`)

**Server Component** (SSR for SEO).

Sections:
1. **Hero**: Large heading "VigiaBR", subheading, `<SearchBar variant="hero" />`
2. **Featured — Lowest SCI**: Grid of `<MandatarioSummary />` cards for mandatarios with lowest SCI scores
3. **Featured — Highest SCI**: Grid of `<MandatarioSummary />` cards for mandatarios with highest SCI scores

Data fetching:
- `getFeaturedMandatarios()` called server-side in the page component
- Results passed as props to client-side search bar

Layout:
- Hero section: navy background, white text, centered
- Featured sections: paper background, 3-column grid (responsive: 1 col mobile, 2 col tablet, 3 col desktop)

### 4.2 Profile Page (`app/mandatario/[id]/page.tsx`)

**Server Component** with parallel data fetching.

```typescript
// Parallel fetch for all profile data
const [mandatario, sci, inconsistencias, timeline, patrimonio] = await Promise.all([
  getMandatario(id),
  getMandatarioSCI(id),
  getMandatarioInconsistencias(id),
  getMandatarioTimeline(id),
  getMandatarioPatrimonio(id),
]);
```

Page sections (top to bottom):
1. **Header**: Name, party, UF, cargo, mandate period
2. **SCI Score**: `<SCIGauge />` + `<SCIDimensionBar />` for each dimension
3. **Patrimony**: `<PatrimonyChart />`
4. **Inconsistencies**: `<InconsistencyList />`
5. **Timeline**: `<Timeline />`

Metadata (dynamic):
```typescript
export async function generateMetadata({ params }): Promise<Metadata> {
  const m = await getMandatario(params.id);
  return {
    title: `${m.nome} — VigiaBR`,
    description: `Perfil de consistencia de ${m.nome} (${m.partido_sigla}/${m.uf})`,
    openGraph: { title: `${m.nome} — Score SCI: ${m.sci_score}` },
  };
}
```

### 4.3 Profile Loading (`app/mandatario/[id]/loading.tsx`)

- Skeleton layout matching the profile page structure
- Animated placeholders for gauge, chart, cards, timeline

### 4.4 Profile Error (`app/mandatario/[id]/error.tsx`)

- Client component
- "Erro ao carregar o perfil deste mandatario."
- Retry button

### 4.5 About Page (`app/sobre/page.tsx`)

**Static page** (no data fetching). Content:

1. **O que e o VigiaBR** — Platform description
2. **Metodologia** — How the SCI is calculated (6 dimensions table)
3. **Fontes de Dados** — Table of all data sources with links
4. **Linguagem** — Explanation of the FATO/METRICA/FONTE pattern
5. **Aspectos Legais** — LGPD compliance, LAI basis
6. **Codigo Aberto** — Link to GitHub repo, AGPL-3.0 license explanation
7. **Contato** — How to report issues or contribute

### 4.6 Client-Side Pagination (Inconsistencies + Timeline)

The profile page renders the first page of data server-side. Further pages are loaded client-side:

- Wrap `<InconsistencyList />` and `<Timeline />` in client components
- "Carregar mais" button triggers `fetch` to the next cursor
- Appends new items to the existing list
- Preserves scroll position

### Deliverables

- [ ] Home page — hero + search + featured mandatarios
- [ ] Profile page — full SSR with parallel data fetching
- [ ] Profile loading/error states
- [ ] About page — static content
- [ ] Client-side pagination for inconsistencies and timeline
- [ ] Dynamic metadata for SEO

### Testing gate

```bash
pnpm build               # All pages compile with SSR
pnpm dev                 # Pages render with mock/real API
pnpm test                # All tests pass
```

---

## Phase 5: Responsiveness, Accessibility & Polish

**Goal:** Ensure the app works on mobile, meets WCAG 2.1 AA, and handles all edge cases.

### 5.1 Responsive Design (Mobile-First)

| Breakpoint | Layout changes |
|-----------|---------------|
| `< 640px` (mobile) | Single column, stacked sections, hero search full-width, hamburger nav |
| `640–1024px` (tablet) | 2-column grids, side-by-side SCI gauge + dimensions |
| `> 1024px` (desktop) | 3-column featured grid, full-width timeline |

Key responsive adjustments:
- Nav: hamburger menu on mobile, inline links on desktop
- Search bar: full-width on mobile, constrained on desktop
- Profile: stacked on mobile, 2-column (SCI left, chart right) on tablet+
- Patrimony chart: smaller height on mobile, full on desktop
- Inconsistency cards: full-width always (content is king)

### 5.2 Accessibility (WCAG 2.1 AA)

| Requirement | Implementation |
|-------------|---------------|
| Color contrast | All text meets 4.5:1 ratio (navy on paper = 13.4:1) |
| Keyboard navigation | All interactive elements focusable, visible focus ring |
| Screen reader | Semantic HTML, ARIA labels on charts and gauges |
| Skip to content | `<a href="#main" className="sr-only focus:not-sr-only">` |
| Reduced motion | `prefers-reduced-motion` disables animations |
| Alt text | Chart has `aria-label` with data summary |
| Focus management | Search dropdown manages focus with `aria-activedescendant` |
| Landmarks | `<header>`, `<main>`, `<footer>`, `<nav>` elements |

### 5.3 Edge Cases

| Scenario | Handling |
|----------|---------|
| Mandatario has no SCI score | "Score nao calculado" gray state |
| Mandatario has no inconsistencies | "Nenhuma inconsistencia detectada." |
| Mandatario has no patrimony data | Chart hidden, "Dados patrimoniais indisponiveis." |
| Empty search results | "Nenhum mandatario encontrado para '{query}'." |
| API is down | Error boundary with retry |
| Very long names | Truncate with `text-ellipsis` |
| Very large monetary values | Abbreviate (R$ 1,2M, R$ 3,4B) |

### 5.4 Performance Optimizations

- `next/font/google` for font loading (avoids FOUT)
- `next/image` for any images (if applicable later)
- Recharts lazy-loaded (`dynamic(() => import(...)`, `{ ssr: false }`)
- Search debounce (300ms)
- Cursor-based pagination (no offset overhead)
- `output: 'standalone'` for minimal Docker image

### Deliverables

- [ ] Responsive layout at all breakpoints
- [ ] Keyboard navigation on all interactive elements
- [ ] ARIA attributes on gauge, chart, search combobox
- [ ] Skip-to-content link
- [ ] Reduced motion support
- [ ] Edge case handling for empty/null states
- [ ] Recharts lazy-loaded for bundle size

### Testing gate

```bash
pnpm build                # Production build succeeds
pnpm test                 # All tests pass
# Manual checks:
# - Chrome DevTools mobile simulator (375px, 768px, 1280px)
# - Lighthouse accessibility audit > 90
# - Keyboard-only navigation through all interactive elements
```

---

## Phase 6: Testing & Build Verification

**Goal:** Write comprehensive tests, ensure build passes, and prepare for PR.

### 6.1 Unit Tests (`__tests__/utils.test.ts`)

| Function | Test cases |
|----------|-----------|
| `formatCurrency(1234567.89)` | `"R$ 1.234.567,89"` |
| `formatCurrency(0)` | `"R$ 0,00"` |
| `formatDate("2024-01-15")` | `"15 jan 2024"` |
| `getSCIColor(100)` | `"#c0392b"` (red) |
| `getSCIColor(600)` | `"#b8860b"` (gold) |
| `getSCIColor(900)` | `"#27ae60"` (green) |
| `getSCIBand(0)` | `{ min: 0, max: 250, ... }` |

### 6.2 Component Tests

| Component | Test cases |
|-----------|-----------|
| `SCIGauge` | Renders score value, applies correct color class, shows "Sem dados" for null, has meter role |
| `InconsistencyCard` | Renders FATO text, METRICA text, source links, correct border color, links open in new tab |
| `SearchBar` | Debounce delays, fires callback, keyboard up/down navigates, enter selects, combobox role |
| `MandatarioSummary` | Renders name, party, UF, SCI badge, links to profile |
| `PatrimonyChart` | Renders without crashing, handles empty data |

### 6.3 Build Verification

```bash
pnpm lint          # ESLint clean
pnpm type-check    # tsc --noEmit passes (add to package.json scripts)
pnpm build         # Production build succeeds
pnpm test          # All tests pass
```

### 6.4 PR Checklist

- [ ] All files in `frontend/` — no changes outside this directory
- [ ] `package.json` has all scripts: `dev`, `build`, `start`, `lint`, `test`, `type-check`
- [ ] `.env.local.example` documents required env vars
- [ ] No hardcoded API URLs (all via `NEXT_PUBLIC_API_URL`)
- [ ] No emojis in UI text
- [ ] All source links use `target="_blank" rel="noopener noreferrer"`
- [ ] All monetary values formatted in BRL
- [ ] All dates in Portuguese format
- [ ] No accusatory or subjective language in any UI text
- [ ] Responsive at 375px, 768px, 1280px
- [ ] Keyboard navigable
- [ ] `pnpm build` succeeds with `output: 'standalone'`

### Deliverables

- [ ] 10+ unit tests for utilities
- [ ] 5+ component tests
- [ ] All linting/type-checking passes
- [ ] Production build succeeds
- [ ] PR created targeting `develop`

---

## Dependency Map

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6
 (scaffold)  (layout)    (components) (pages)     (polish)    (test+PR)
```

All phases are sequential. Each phase builds on the previous.

**External dependencies:**
- Phase 4 requires the backend API contract to be finalized (can use mock data/MSW until backend is ready)
- No dependency on scoring (Front 1) or deploy (Front 4)

---

## Mock Data Strategy

Until the backend (Issue #9) is running, the frontend uses mock data for development:

Create `src/lib/mock-data.ts` with realistic sample data for:
- 5 mandatarios (mix of high/low SCI scores)
- 10 inconsistencies (various types and severities)
- 20 timeline events (all types)
- Patrimony data for 4 election years (2014, 2018, 2022, 2026)

The API client (`lib/api.ts`) can be configured to return mock data when `NEXT_PUBLIC_API_URL` is not set, or a separate MSW (Mock Service Worker) setup can intercept fetch calls in development.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Backend API not ready | Mock data strategy; code against contract, not implementation |
| Recharts SSR issues | Lazy-load chart with `dynamic(import, { ssr: false })` |
| Google Fonts blocking render | Use `next/font/google` with `display: swap` |
| Large bundle size | Analyze with `@next/bundle-analyzer`; lazy-load chart |
| SCI score calculation changes | Frontend reads scores from API; no local calculation |
| Design inconsistency | All colors/fonts defined once in `tailwind.config.ts` and `constants.ts` |

---

## Summary

| Phase | Files | Key Deliverable |
|-------|-------|----------------|
| 1 | ~10 | Scaffolding, design tokens, API client, types |
| 2 | ~6 | Nav, footer, layout shell, error states |
| 3 | ~12 | All 9 presentational components + tests |
| 4 | ~8 | Home, profile, about pages with data fetching |
| 5 | ~3 | Responsive, a11y, edge cases, performance |
| 6 | ~5 | Tests, build verification, PR checklist |
| **Total** | **~44** | **Complete MVP frontend** |
