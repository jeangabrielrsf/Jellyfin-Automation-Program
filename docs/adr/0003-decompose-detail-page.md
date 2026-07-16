# ADR 0003: Decompor Detail.tsx god-page

## Status

Aceito

## Contexto

O `Detail.tsx` (914 linhas) é uma god-page que mistura múltiplas responsabilidades:

- 20+ `useState` calls (linhas 22-47)
- 6 `useQuery` calls (linhas 49-114)
- `useEffect`s sincronizando estado (linhas 60-76) — `preferredQuality` → `selectedQualities`, `preferredLanguage` → `selectedLanguages`
- Lógica de download com `Set<string>` para tracking (linhas 121-150)
- `useMemo` de 50 linhas filtrando e ordenando torrents (linhas 193-248)
- ~600 linhas de JSX

Isso viola locality — a lógica de Filtros Client-side e Busca de Torrents está espalhada em uma página que também cuida de apresentação, hero section, season/episode picker, e trailer dialog.

## Decisão

Extrair dois hooks customizados antes de extrair componentes visuais:

### `useTorrentFilters`

Encapsula todo o estado de filtros e lógica de filtragem:

**State (server-side):**
- `preferredQuality`, `preferredLanguage`
- `customSearchEnabled`, `customQuery`
- `selectedTitle`

**State (client-side):**
- `selectedQualities`, `selectedLanguages`
- `minSeeds`, `freeleechOnly`
- `sortBy`, `sortOrder`
- `titleFilter`, `visibleCount`
- `advancedOptionsOpen`

**Effects:**
- Sync `preferredQuality` → `selectedQualities`
- Sync `preferredLanguage` → `selectedLanguages`
- Reset `visibleCount` quando filtros mudam

**Computation:**
- O `useMemo` de 50 linhas que filtra e ordena os torrents

**Input:**
- Recebe `torrents: TorrentResult[]` como parâmetro (não faz data fetching)

**Retorno:**
```ts
{
  // server-side
  preferredQuality, setPreferredQuality,
  preferredLanguage, setPreferredLanguage,
  customSearchEnabled, setCustomSearchEnabled,
  customQuery, setCustomQuery,
  selectedTitle, setSelectedTitle,
  // client-side
  selectedQualities, setSelectedQualities,
  selectedLanguages, setSelectedLanguages,
  minSeeds, setMinSeeds,
  freeleechOnly, setFreeleechOnly,
  sortBy, setSortBy,
  sortOrder, setSortOrder,
  titleFilter, setTitleFilter,
  visibleCount, setVisibleCount,
  advancedOptionsOpen, setAdvancedOptionsOpen,
  // computed
  filteredTorrents,
}
```

### `useDownload`

Encapsula a lógica de download:

**State:**
- `downloadingTorrents: Set<string>` — tracking de torrents em progresso

**Lógica:**
- `handleDownload(torrent: TorrentResult)` — constrói payload, chama `downloadAPI.createDownload()`, mostra toast, gerencia o Set

**Abordagem:**
- `async/await` manual (não `useMutation`)

**Motivo para não usar `useMutation`:**
- O `downloadingTorrents` Set gerencia múltiplos downloads simultâneos, cada um com seu próprio estado. `useMutation` gerencia UMA mutation por vez.
- A lógica `already_exists` é condicional — precisa de acesso ao `response.data`.
- O payload é complexo e depende de contexto externo (`tmdbId`, `detail`, `selectedSeason`, `selectedEpisode`, `effectiveMediaType`).
- Adiciona uma camada de indireção sem benefício claro.

**Retorno:**
```ts
{
  downloadingTorrents,
  handleDownload,
}
```

### Localização

`frontend/src/hooks/` — diretório existente, mantém consistência com o padrão atual. Esses hooks são específicos da página Detail agora, mas a lógica pode ser reutilizada em outras páginas (Search, Downloads) no futuro.

### Escopo

Parar na extração de hooks. A extração de componentes visuais (`SeasonEpisodePicker`, `TorrentFilterPanel`, `MediaHero`) é um passo separado que pode ser feito depois, quando houver mais clareza sobre quais componentes são reutilizáveis.

## Consequências

### Positivas

- **Locality:** lógica de filtros concentra em `useTorrentFilters`, testável sem renderizar 600 linhas de JSX
- **Leverage:** hooks reutilizáveis em outras páginas
- **Interface shrinks:** Detail.tsx cai de 914 para ~600 linhas, mas o pior (20 useState, effects de sync, useMemo de 50 linhas) foi extraído
- **Testabilidade:** hooks podem ser testados com `renderHook()` sem precisar mockar 6 API endpoints

### Negativas

- Detail.tsx ainda tem ~600 linhas de JSX — não resolveu completamente a god-page
- Dois novos arquivos para manter

### Riscos

- Se o `useTorrentFilters` crescer muito (ex: precisar de paginação server-side), pode precisar ser refatorado
- A extração de componentes visuais ficou para depois — pode nunca acontecer se não houver pressão

## Alternativas Consideradas

**Alternativa 1: Extrair componentes visuais primeiro**

Criar `SeasonEpisodePicker`, `TorrentFilterPanel`, `MediaHero` antes dos hooks.

Rejeitada: componentes visuais dependem do estado de filtros. Extrair hooks primeiro estabiliza a lógica de negócio; depois os componentes visuais consomem os hooks.

**Alternativa 2: Reescrever tudo de uma vez**

Refatorar o Detail.tsx inteiro com a nova estrutura em um único PR.

Rejeitada: risco alto de quebrar a UI. Extrair hooks primeiro é um passo incremental e reversível.

**Alternativa 3: Usar `useMutation` no `useDownload`**

Substituir `async/await` manual por `useMutation` do TanStack Query.

Rejeitada: o `downloadingTorrents` Set gerencia múltiplos downloads simultâneos, a lógica `already_exists` é condicional, e o payload é complexo. `useMutation` adiciona indireção sem benefício claro.

**Alternativa 4: Feature-based hooks (`frontend/src/features/torrents/hooks/`)**

Organizar hooks por domínio em vez de colocá-los em `hooks/`.

Rejeitada: estrutura feature-based não existe ainda. Colocar em `hooks/` mantém consistência com o padrão atual e permite reuso futuro sem reorganização.

## Implementação

Arquivos a criar/modificar:

- `frontend/src/hooks/useTorrentFilters.ts` (novo)
- `frontend/src/hooks/useDownload.ts` (novo)
- `frontend/src/pages/Detail.tsx` — substituir useState/useEffect/useMemo por hooks
