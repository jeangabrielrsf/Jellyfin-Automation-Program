# ADR 0005: Connect API layer to TypeScript types

## Status

Aceito

## Contexto

A camada de API (`frontend/src/services/api.ts`) tem 20+ métodos que retornam `AxiosResponse<any>` — o type system não provê segurança end-to-end. Tipos ricos existem em `types/index.ts` (`TMDBSearchResult`, `TMDBDetail`, `TorrentResult`, `Download`, `AppSettings`, `DiscoverSection`, `Genre`, `StreamingProvider`, `TVEpisode`, `TVSeasonDetail`, `ListStatus`, `ListItem`, `Recommendation`), mas não estão conectados aos métodos da API.

Consumers acessam `.data` e assumem o tipo — 20+ call sites espalhados. Alguns métodos já têm generics (`getMovieAlternativeTitles`, `getTVAlternativeTitles`, `getProviders`, `listsAPI`, `recommendationsAPI`), mas a maioria não.

Isso viola leverage — o type system poderia capturar erros de contrato entre backend e frontend, mas está desativado pela falta de generics.

## Decisão

Adicionar generics em todos os métodos da API, mantendo `.data` nos consumers.

### Estratégia

```typescript
// Antes
export const searchAPI = {
  searchMedia: (query: string, page = 1) =>
    api.get(`/search/?q=${encodeURIComponent(query)}&page=${page}`),
};

// Depois
export const searchAPI = {
  searchMedia: (query: string, page = 1) =>
    api.get<TMDBSearchResult[]>(`/search/?q=${encodeURIComponent(query)}&page=${page}`),
};
```

Consumers continuam acessando `response.data`, mas agora com tipo correto:

```typescript
// Antes (tipo implícito any)
const results = response.data;

// Depois (tipo explícito TMDBSearchResult[])
const results: TMDBSearchResult[] = response.data;
```

### Tipos faltantes

Criar tipos em `types/index.ts` para métodos que não têm tipos correspondentes:

- `getTVSeasons` → `TVSeason`
- `getRoot`, `getDirs` (filesystemAPI) → `FilesystemNode`
- `getLogs` → `LogEntry`
- `getSettings` → `Setting[]` ou `Record<string, string>` (depende do backend)

### Descoberta de tipos

Para cada tipo faltante, usar três fontes:

1. **Backend** — ler routers/models do FastAPI para ver a estrutura completa
2. **Frontend** — procurar onde o método é chamado e ver quais campos são acessados
3. **Documentação oficial** — se for retorno de API externa (TMDB, Jackett, qBittorrent), consultar a documentação oficial

Isso garante:
- Tipo correto (backend + docs oficiais)
- Tipo pragmático (frontend mostra o que é usado)
- Tipo documentado (docs oficiais como fonte de verdade)

## Consequências

### Positivas

- **Leverage:** uma seam tipada, N consumers
- **Testabilidade:** type errors capturados em compile time, não runtime
- **Interface shrinks:** implementation absorve o mapeamento entre backend e frontend
- **Delete `.data` access** — se no futuro quiser refatorar para wrapper functions, pode fazer sem quebrar nada

### Negativas

- Requer trabalho de descoberta de tipos (ler backend, frontend, docs)
- Alguns tipos podem ser grandes (ex: `TMDBDetail` tem 20+ campos) — mas isso reflete a realidade da API

### Riscos

- Se o backend mudar o contrato, o type system vai capturar — mas precisa rodar `tsc` para ver os erros
- Tipos podem ficar desatualizados se o backend evoluir sem atualizar o frontend — mitigado pelo type system (compilação falha)

## Alternativas Consideradas

**Alternativa 1: Wrapper functions que extraem `.data`**

Criar funções que extraem `.data` automaticamente:

```typescript
const get = <T>(...) => api.get<T>(...).then(r => r.data);
```

Consumers recebem o tipo diretamente: `const data = await searchAPI.searchMedia(...)`.

Rejeitada: não muda a estrutura do código — consumers continuam acessando `.data`. Se no futuro quiser remover `.data`, pode fazer com helper sem quebrar nada.

**Alternativa 2: Interceptor global do Axios**

Interceptor global extrai `.data` de todas as respostas. Todos os consumers recebem o tipo diretamente.

Rejeitada: pode causar problemas com tipos específicos ou quando precisa de headers/status. Perde acesso a metadados HTTP.

**Alternativa 3: Usar `any` temporariamente**

Adicionar generics com `any` onde falta tipo, criar TODO para depois.

Rejeitada: o objetivo desse refactor é type safety end-to-end — deixar buracos com `any` derrota o propósito.

**Alternativa 4: Tipar apenas o que já existe**

Só adicionar generics nos métodos que já têm tipos correspondentes em `types/index.ts`. Deixar os outros sem tipo por agora.

Rejeitada: cria inconsistência — alguns métodos tipados, outros não. Type safety parcial é pior que type safety completa.

## Implementação

Arquivos a criar/modificar:

- `frontend/src/types/index.ts` — adicionar tipos faltantes (`TVSeason`, `FilesystemNode`, `LogEntry`, etc.)
- `frontend/src/services/api.ts` — adicionar generics em todos os métodos
- 20+ call sites — não precisam mudar (continuam acessando `.data`), mas agora com tipo correto

### Descoberta de tipos

Para cada tipo faltante:

1. Ler backend (`backend/app/routers/*.py`, `backend/app/models/*.py`) para ver a estrutura completa
2. Procurar onde o método é chamado no frontend (`grep -r "searchAPI.getTVSeasons"`) e ver quais campos são acessados
3. Se for API externa (TMDB, Jackett, qBittorrent), consultar documentação oficial
