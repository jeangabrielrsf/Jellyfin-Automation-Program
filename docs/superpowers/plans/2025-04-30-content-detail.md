# Content Detail Page — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a content detail page (`/detail/:mediaType/:id`) that shows TMDB info and torrents, supports season/episode selection for TV, restores search scroll state on back-navigation, and converts quality/language settings inputs to selects.

**Architecture:** A new `Detail.tsx` page fetches TMDB details and torrents. For TV shows it fetches seasons from the backend, renders season/episode selectors, and triggers torrent search with the selected params. The `Search.tsx` page saves its state to `sessionStorage` before navigating and restores it on mount. Settings page replaces free-text inputs with shadcn/ui `<Select>` components.

**Tech Stack:** React 18, React Router, TanStack Query, Axios, Tailwind CSS, shadcn/ui

---

## File Structure

| File | Responsibility |
|------|---------------|
| `frontend/src/pages/Detail.tsx` | New detail page with hero, tabs, torrent list, season/episode selectors |
| `frontend/src/App.tsx` | Add `/detail/:mediaType/:id` route |
| `frontend/src/pages/Search.tsx` | Change `MediaCard` onClick to navigate, add scroll restoration |
| `frontend/src/services/api.ts` | Add `getTVSeasons()`, update `searchTorrents()` signature |
| `frontend/src/pages/Settings.tsx` | Convert quality/language inputs to `<Select>` |

---

## Task 1: Update API Client

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Update `searchTorrents` signature and add `getTVSeasons`**

Replace the `searchAPI` object in `frontend/src/services/api.ts` with:

```typescript
export const searchAPI = {
  searchMedia: (query: string, page = 1) =>
    api.get(`/search/?q=${encodeURIComponent(query)}&page=${page}`),
  
  getMovieDetail: (id: number) =>
    api.get(`/search/movie/${id}`),
  
  getTVDetail: (id: number) =>
    api.get(`/search/tv/${id}`),

  getTVSeasons: (id: number) =>
    api.get(`/search/tv/${id}/seasons`),
  
  searchTorrents: (params: {
    tmdb_id: number;
    media_type: string;
    season?: number;
    episode?: number;
    quality?: string;
    language?: string;
  }) => api.get('/search/torrents', {
    params: {
      ...params,
      media_type: mapMediaType(params.media_type),
    }
  }),
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npx tsc --noEmit
```

Expected: No errors from `api.ts`.

- [ ] **Step 3: Commit**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation && git add frontend/src/services/api.ts && git commit -m "feat(frontend): update searchTorrents signature, add getTVSeasons"
```

---

## Task 2: Create Detail Page

**Files:**
- Create: `frontend/src/pages/Detail.tsx`

- [ ] **Step 1: Create the Detail page component**

Create `frontend/src/pages/Detail.tsx`:

```tsx
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Download, Play, Info } from 'lucide-react';
import { searchAPI, downloadAPI } from '../services/api';
import { TorrentResult } from '../types';

const DetailPage: React.FC = () => {
  const { mediaType, id } = useParams<{ mediaType: string; id: string }>();
  const navigate = useNavigate();
  const tmdbId = Number(id);

  const [activeTab, setActiveTab] = useState<'torrents' | 'info'>('torrents');
  const [selectedSeason, setSelectedSeason] = useState<number | ''>('');
  const [selectedEpisode, setSelectedEpisode] = useState<number | 'temporada-inteira'>('temporada-inteira');

  const isTV = mediaType === 'tv';

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['detail', mediaType, tmdbId],
    queryFn: () =>
      mediaType === 'movie'
        ? searchAPI.getMovieDetail(tmdbId)
        : searchAPI.getTVDetail(tmdbId),
    enabled: !!tmdbId && !!mediaType,
  });

  const { data: seasonsData } = useQuery({
    queryKey: ['seasons', tmdbId],
    queryFn: () => searchAPI.getTVSeasons(tmdbId),
    enabled: isTV && !!tmdbId,
  });

  const { data: torrentResults, isLoading: torrentsLoading, refetch: refetchTorrents } = useQuery({
    queryKey: ['torrents', tmdbId, selectedSeason, selectedEpisode],
    queryFn: () =>
      searchAPI.searchTorrents({
        tmdb_id: tmdbId,
        media_type: mediaType || 'movie',
        season: selectedSeason ? Number(selectedSeason) : undefined,
        episode: selectedEpisode !== 'temporada-inteira' ? Number(selectedEpisode) : undefined,
      }),
    enabled: !isTV, // TV torrents only load after user clicks "Buscar"
  });

  const handleSearchTorrents = () => {
    if (!isTV) return;
    refetchTorrents();
  };

  const handleDownload = async (torrent: TorrentResult) => {
    try {
      await downloadAPI.createDownload({
        tmdb_id: tmdbId,
        title: detail?.data?.display_title || '',
        media_type: mediaType || 'movie',
        torrent_name: torrent.title,
        magnet_link: torrent.magnet_url || torrent.download_url || '',
        quality: torrent.quality || '1080p',
        language_preference: torrent.language || 'legendado',
        indexer_used: torrent.indexer,
      });
      alert('Download iniciado com sucesso!');
    } catch (error) {
      console.error('Failed to start download:', error);
      alert('Erro ao iniciar download.');
    }
  };

  const media = detail?.data;
  const seasons = seasonsData?.data || [];

  const episodeOptions = React.useMemo(() => {
    if (!selectedSeason) return [];
    const season = seasons.find((s: any) => s.season_number === Number(selectedSeason));
    if (!season) return [];
    return Array.from({ length: season.episode_count }, (_, i) => i + 1);
  }, [selectedSeason, seasons]);

  if (detailLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="h-64 animate-shimmer rounded-2xl" />
        <div className="h-32 animate-shimmer rounded-2xl" />
      </div>
    );
  }

  if (!media) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Conteúdo não encontrado.</p>
        <button onClick={() => navigate(-1)} className="mt-4 text-primary hover:underline">
          Voltar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar
      </button>

      {/* Hero */}
      <div className="relative rounded-2xl overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(https://image.tmdb.org/t/p/w1280${media.backdrop_path || media.poster_path})`,
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
        <div className="relative p-6 md:p-10 flex gap-6 items-end">
          {media.poster_path && (
            <img
              src={`https://image.tmdb.org/t/p/w300${media.poster_path}`}
              alt={media.display_title}
              className="w-32 md:w-48 rounded-xl shadow-lg hidden md:block"
            />
          )}
          <div className="flex-1">
            <h1 className="font-display text-3xl md:text-4xl font-bold text-foreground">
              {media.display_title}
            </h1>
            <p className="text-muted-foreground mt-1">
              {media.year} • {media.genres?.map((g: any) => g.name).join(', ')}
            </p>
            <p className="text-sm text-muted-foreground mt-2 line-clamp-3">
              {media.overview}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border/50">
        <button
          onClick={() => setActiveTab('torrents')}
          className={`pb-2 text-sm font-medium transition-colors ${
            activeTab === 'torrents' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
          }`}
        >
          <Play className="w-4 h-4 inline mr-1" />
          Torrents
        </button>
        <button
          onClick={() => setActiveTab('info')}
          className={`pb-2 text-sm font-medium transition-colors ${
            activeTab === 'info' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
          }`}
        >
          <Info className="w-4 h-4 inline mr-1" />
          Informações
        </button>
      </div>

      {/* Torrents tab */}
      {activeTab === 'torrents' && (
        <div className="space-y-6">
          {isTV && (
            <div className="glass rounded-2xl p-6 space-y-4">
              <h3 className="font-display text-lg font-bold text-foreground">
                Selecionar Temporada / Episódio
              </h3>
              <div className="flex flex-wrap gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Temporada</label>
                  <select
                    value={selectedSeason}
                    onChange={(e) => {
                      setSelectedSeason(e.target.value ? Number(e.target.value) : '');
                      setSelectedEpisode('temporada-inteira');
                    }}
                    className="px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                  >
                    <option value="">Selecionar...</option>
                    {seasons.map((s: any) => (
                      <option key={s.season_number} value={s.season_number}>
                        {s.name} ({s.episode_count} eps)
                      </option>
                    ))}
                  </select>
                </div>
                {selectedSeason && (
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Episódio</label>
                    <select
                      value={selectedEpisode}
                      onChange={(e) => setSelectedEpisode(e.target.value === 'temporada-inteira' ? 'temporada-inteira' : Number(e.target.value))}
                      className="px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                    >
                      <option value="temporada-inteira">Temporada inteira</option>
                      {episodeOptions.map((ep: number) => (
                        <option key={ep} value={ep}>Episódio {ep}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
              <button
                onClick={handleSearchTorrents}
                disabled={!selectedSeason}
                className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Buscar Torrents
              </button>
            </div>
          )}

          <div className="glass rounded-2xl p-6">
            <h3 className="font-display text-xl font-bold text-foreground mb-4">
              Torrents disponíveis
            </h3>
            {torrentsLoading ? (
              <div className="h-32 animate-shimmer rounded-xl" />
            ) : torrentResults?.data?.length ? (
              <div className="space-y-3">
                {torrentResults.data.map((torrent: TorrentResult) => (
                  <div
                    key={torrent.title + torrent.indexer}
                    className="flex items-center justify-between p-4 rounded-xl bg-background/50 border border-border/30 hover:border-primary/30 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">{torrent.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {torrent.quality} • {torrent.language} • {torrent.size} • {torrent.seeds}S / {torrent.peers}L
                      </p>
                    </div>
                    <button
                      onClick={() => handleDownload(torrent)}
                      className="ml-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-2 shrink-0"
                    >
                      <Download className="w-4 h-4" />
                      Baixar
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                {isTV ? 'Selecione uma temporada e clique em "Buscar Torrents".' : 'Nenhum torrent encontrado.'}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Info tab */}
      {activeTab === 'info' && (
        <div className="glass rounded-2xl p-6 space-y-4">
          <h3 className="font-display text-xl font-bold text-foreground">Sinopse</h3>
          <p className="text-muted-foreground leading-relaxed">{media.overview}</p>
          {media.runtime && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Duração:</span> {media.runtime} min
            </p>
          )}
          {media.number_of_seasons && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Temporadas:</span> {media.number_of_seasons}
            </p>
          )}
          {media.status && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Status:</span> {media.status}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default DetailPage;
```

- [ ] **Step 2: Add the route in `App.tsx`**

In `frontend/src/App.tsx`, add the import:

```typescript
import DetailPage from './pages/Detail';
```

And add the route inside `<Routes>`:

```tsx
<Route path="/detail/:mediaType/:id" element={<DetailPage />} />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation && git add frontend/src/pages/Detail.tsx frontend/src/App.tsx && git commit -m "feat(frontend): add Detail page with hero, tabs, season/episode selectors"
```

---

## Task 3: Update Search Page Navigation + Scroll Restoration

**Files:**
- Modify: `frontend/src/pages/Search.tsx`

- [ ] **Step 1: Update `Search.tsx` to navigate on click and restore state**

Replace the entire content of `frontend/src/pages/Search.tsx` with:

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, skipToken } from '@tanstack/react-query';
import { SearchBar } from '../components/SearchBar';
import { MediaCard } from '../components/MediaCard';
import { searchAPI } from '../services/api';
import { TMDBSearchResult } from '../types';

const STORAGE_KEY = 'search_state';

const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => searchAPI.searchMedia(searchQuery),
    enabled: !!searchQuery,
  });

  useEffect(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const { query, scrollY } = JSON.parse(saved);
        if (query) {
          setSearchQuery(query);
        }
        if (scrollY !== undefined) {
          requestAnimationFrame(() => {
            window.scrollTo(0, scrollY);
          });
        }
        sessionStorage.removeItem(STORAGE_KEY);
      } catch {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleMediaClick = (media: TMDBSearchResult) => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        query: searchQuery,
        scrollY: window.scrollY,
      })
    );
    navigate(`/detail/${media.media_type}/${media.id}`);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Buscar Conteúdo
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Pesquise por filmes, séries ou animes no banco de dados do TMDB
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} isLoading={isSearching} />

      {/* Results */}
      {searchResults?.data?.results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-xl font-bold text-foreground">
              Resultados
            </h3>
            <span className="text-sm text-muted-foreground">
              {searchResults.data.results.length} encontrados
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {searchResults.data.results.map((media: TMDBSearchResult) => (
              <MediaCard
                key={media.id}
                media={media}
                onClick={handleMediaClick}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npx tsc --noEmit
```

Expected: No errors. Note: `TorrentList` import is removed because it's no longer used on this page.

- [ ] **Step 3: Commit**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation && git add frontend/src/pages/Search.tsx && git commit -m "feat(frontend): navigate to detail page on media click, add scroll restoration"
```

---

## Task 4: Convert Settings Inputs to Selects

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Import shadcn/ui Select components**

Add to the imports at the top of `frontend/src/pages/Settings.tsx`:

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
```

- [ ] **Step 2: Replace the preference inputs with Selects**

In the `settingGroups` array, keep the structure but we will special-render the preference group. Alternatively, replace the inner render logic for `default_quality` and `default_language`.

Replace the setting rendering block inside `SettingsPage` (around lines 100-124) with:

```tsx
              {group.settings.map((setting) => (
                <div key={setting.key} className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    {setting.label}
                  </label>
                  <div className="relative group">
                    {setting.key === 'default_quality' ? (
                      <Select
                        defaultValue={currentValues[setting.key] || '1080p'}
                        onValueChange={(value) => handleUpdate(setting.key, value)}
                      >
                        <SelectTrigger className="w-full px-4 py-3 rounded-xl glass bg-transparent border border-border/50 text-foreground">
                          <SelectValue placeholder="Selecionar qualidade" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="720p">720p</SelectItem>
                          <SelectItem value="1080p">1080p</SelectItem>
                          <SelectItem value="1440p">1440p</SelectItem>
                          <SelectItem value="2160p">2160p</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : setting.key === 'default_language' ? (
                      <Select
                        defaultValue={currentValues[setting.key] || 'legendado'}
                        onValueChange={(value) => handleUpdate(setting.key, value)}
                      >
                        <SelectTrigger className="w-full px-4 py-3 rounded-xl glass bg-transparent border border-border/50 text-foreground">
                          <SelectValue placeholder="Selecionar idioma" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="legendado">Legendado</SelectItem>
                          <SelectItem value="dublado">Dublado</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <input
                        type="text"
                        defaultValue={currentValues[setting.key] || ''}
                        placeholder={setting.placeholder}
                        onBlur={(e) => handleUpdate(setting.key, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl glass bg-transparent
                                 border border-border/50
                                 focus:outline-none focus:ring-2 focus:ring-primary/30
                                 focus:border-primary/30
                                 text-foreground placeholder:text-muted-foreground/50
                                 font-mono text-sm
                                 transition-all duration-200"
                      />
                    )}
                    {updateMutation.isPending && updateMutation.variables?.key === setting.key && (
                      <Save className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary animate-pulse" />
                    )}
                  </div>
                </div>
              ))}
```

- [ ] **Step 3: Verify TypeScript compiles and build passes**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npx tsc --noEmit && npm run build
```

Expected: No TypeScript errors and build succeeds.

- [ ] **Step 4: Run linter**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run lint
```

Expected: No lint errors (or only pre-existing ones).

- [ ] **Step 5: Commit**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation && git add frontend/src/pages/Settings.tsx && git commit -m "feat(frontend): convert quality and language settings to selects"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - Detail page (`/detail/:mediaType/:id`) → Task 2
   - Hero + tabs (Torrents / Informações) → Task 2
   - Season/episode selectors for TV → Task 2
   - Scroll restoration on back-navigation → Task 3
   - Settings quality/language selects → Task 4
   - Dual title search support (API signature update) → Task 1

2. **Placeholder scan:** No TBD, TODO, or vague steps found.

3. **Type consistency:**
   - `searchTorrents` params use `season?: number` and `episode?: number` in both `api.ts` and `Detail.tsx`.
   - `selectedSeason` and `selectedEpisode` state types are consistent.
