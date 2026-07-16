import React, { useState, useEffect, useRef } from 'react';
import { Loader2, Filter, X, Check } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Select, SelectItem } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { SearchResults } from '@/components/SearchResults';
import { searchAPI, discoverAPI } from '@/services/api';
import { TMDBSearchResult } from '@/types';

const FILTERS_STORAGE_KEY = 'search_filters_state';

interface FilterState {
  mediaType: string;
  genreIds: number[];
  providerIds: number[];
  yearFrom: string;
  yearTo: string;
  minRating: string;
  sortBy: string;
}

const DEFAULT_FILTERS: FilterState = {
  mediaType: 'all',
  genreIds: [],
  providerIds: [],
  yearFrom: '',
  yearTo: '',
  minRating: '',
  sortBy: 'popularity.desc',
};

const SORT_OPTIONS = [
  { value: 'popularity.desc', label: 'Popularidade' },
  { value: 'vote_average.desc', label: 'Nota' },
  { value: 'vote_count.desc', label: 'Votos' },
  { value: 'release_date.desc', label: 'Lancamento' },
  { value: 'original_title.asc', label: 'Titulo' },
];

const MEDIA_TYPE_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'movie', label: 'Filme' },
  { value: 'series', label: 'Serie' },
  { value: 'anime', label: 'Anime' },
];

interface MultiSelectProps {
  label: string;
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  items: { id: number; name: string }[];
  isLoading?: boolean;
}

const MultiSelect: React.FC<MultiSelectProps> = ({ label, selectedIds, onChange, items, isLoading }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggle = (id: number) => {
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter(x => x !== id)
        : [...selectedIds, id]
    );
  };

  const displayText = selectedIds.length === 0
    ? label
    : `${selectedIds.length} selecionado${selectedIds.length > 1 ? 's' : ''}`;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen(!open)}
        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <span className={selectedIds.length === 0 ? 'text-muted-foreground' : 'text-foreground'}>
          {displayText}
        </span>
        <svg className="h-4 w-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover p-2 shadow-md max-h-60 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : items.length === 0 ? (
            <p className="py-2 text-center text-sm text-muted-foreground">Nenhuma opcao disponivel</p>
          ) : (
            items.map(item => (
              <label
                key={item.id}
                className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
              >
                <div className={`flex h-4 w-4 items-center justify-center rounded border ${
                  selectedIds.includes(item.id)
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-input'
                }`}>
                  {selectedIds.includes(item.id) && <Check className="h-3 w-3" />}
                </div>
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={selectedIds.includes(item.id)}
                  onChange={() => toggle(item.id)}
                />
                <span>{item.name}</span>
              </label>
            ))
          )}
        </div>
      )}
    </div>
  );
};

interface SearchFiltersProps {
  onMediaClick: (media: TMDBSearchResult) => void;
}

export const SearchFilters: React.FC<SearchFiltersProps> = ({ onMediaClick }) => {
  const [filters, setFilters] = useState<FilterState>(() => {
    try {
      const saved = sessionStorage.getItem(FILTERS_STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch { /* ignore */ }
    return DEFAULT_FILTERS;
  });
  const [appliedFilters, setAppliedFilters] = useState<FilterState | null>(null);

  const { data: genres, isLoading: genresLoading } = useQuery({
    queryKey: ['discover', 'genres'],
    queryFn: () => discoverAPI.getGenres().then(r => r.data),
  });

  const { data: providers, isLoading: providersLoading } = useQuery({
    queryKey: ['discover', 'providers'],
    queryFn: () => discoverAPI.getProviders().then(r => r.data),
  });

  const { data: discoverResults, isLoading: isSearching } = useQuery({
    queryKey: ['discover', appliedFilters],
    queryFn: () => {
      if (!appliedFilters) return Promise.resolve(null);
      const params: Record<string, unknown> = {
        sort_by: appliedFilters.sortBy,
        page: 1,
      };
      if (appliedFilters.mediaType !== 'all') {
        params.media_type = appliedFilters.mediaType === 'series' ? 'tv' : appliedFilters.mediaType;
      }
      if (appliedFilters.genreIds.length > 0) params.genre_ids = appliedFilters.genreIds;
      if (appliedFilters.providerIds.length > 0) params.watch_provider_ids = appliedFilters.providerIds;
      if (appliedFilters.yearFrom) {
        const yearFrom = parseInt(appliedFilters.yearFrom);
        if (!isNaN(yearFrom)) params.year_from = yearFrom;
      }
      if (appliedFilters.yearTo) {
        const yearTo = parseInt(appliedFilters.yearTo);
        if (!isNaN(yearTo)) params.year_to = yearTo;
      }
      if (appliedFilters.minRating) {
        const minRating = parseFloat(appliedFilters.minRating);
        if (!isNaN(minRating)) params.min_rating = minRating;
      }
      return searchAPI.discoverMedia(params as Parameters<typeof searchAPI.discoverMedia>[0]).then(r => r.data);
    },
    enabled: !!appliedFilters,
  });

  useEffect(() => {
    sessionStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  const updateFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const validateYearRange = (): boolean => {
    const currentYear = new Date().getFullYear();
    if (filters.yearFrom) {
      const from = parseInt(filters.yearFrom);
      if (isNaN(from) || from < 1900 || from > currentYear) return false;
    }
    if (filters.yearTo) {
      const to = parseInt(filters.yearTo);
      if (isNaN(to) || to < 1900 || to > currentYear) return false;
    }
    if (filters.yearFrom && filters.yearTo) {
      const from = parseInt(filters.yearFrom);
      const to = parseInt(filters.yearTo);
      if (from > to) return false;
    }
    return true;
  };

  const validateMinRating = (): boolean => {
    if (filters.minRating) {
      const rating = parseFloat(filters.minRating);
      if (isNaN(rating) || rating < 0 || rating > 10) return false;
    }
    return true;
  };

  const handleApply = () => {
    if (!validateYearRange() || !validateMinRating()) return;
    setAppliedFilters({ ...filters });
  };

  const handleClear = () => {
    setFilters(DEFAULT_FILTERS);
    setAppliedFilters(null);
  };

  const results = discoverResults?.results;
  const hasResults = results && results.length > 0;
  const hasApplied = !!appliedFilters && !isSearching;

  return (
    <div className="space-y-6">
      <div className="glass rounded-2xl p-6 space-y-6">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-primary" />
          <h3 className="font-display text-lg font-bold text-foreground">Filtros</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label htmlFor="media-type" className="text-sm font-medium text-foreground">Tipo de midia</label>
            <Select
              id="media-type"
              value={filters.mediaType}
              onChange={(e) => updateFilter('mediaType', e.target.value)}
            >
              {MEDIA_TYPE_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Genero</label>
            <MultiSelect
              label="Genero"
              selectedIds={filters.genreIds}
              onChange={(ids) => updateFilter('genreIds', ids)}
              items={genres || []}
              isLoading={genresLoading}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Provider de streaming</label>
            <MultiSelect
              label="Provider"
              selectedIds={filters.providerIds}
              onChange={(ids) => updateFilter('providerIds', ids)}
              items={providers || []}
              isLoading={providersLoading}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Faixa de ano</label>
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="De"
                min={1900}
                max={new Date().getFullYear()}
                value={filters.yearFrom}
                onChange={(e) => updateFilter('yearFrom', e.target.value)}
              />
              <Input
                type="number"
                placeholder="Ate"
                min={1900}
                max={new Date().getFullYear()}
                value={filters.yearTo}
                onChange={(e) => updateFilter('yearTo', e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="min-rating" className="text-sm font-medium text-foreground">Nota minima</label>
            <Input
              id="min-rating"
              type="number"
              placeholder="0.0 - 10.0"
              min={0}
              max={10}
              step={0.1}
              value={filters.minRating}
              onChange={(e) => updateFilter('minRating', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="sort-by" className="text-sm font-medium text-foreground">Ordenacao</label>
            <Select
              id="sort-by"
              value={filters.sortBy}
              onChange={(e) => updateFilter('sortBy', e.target.value)}
            >
              {SORT_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </Select>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={handleApply}
            disabled={isSearching || !validateYearRange()}
            className="px-6"
          >
            {isSearching ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Buscando...
              </>
            ) : (
              'Aplicar filtros'
            )}
          </Button>
          <Button
            variant="outline"
            onClick={handleClear}
          >
            <X className="w-4 h-4 mr-2" />
            Limpar filtros
          </Button>
        </div>
      </div>

      {isSearching && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="aspect-[2/3] rounded-lg bg-muted animate-pulse" />
              <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
              <div className="h-3 w-1/2 rounded bg-muted animate-pulse" />
            </div>
          ))}
        </div>
      )}

      {hasResults && (
        <SearchResults
          results={results}
          onMediaClick={onMediaClick}
        />
      )}

      {hasApplied && !hasResults && (
        <div className="text-center py-16 space-y-6">
          <div className="w-20 h-20 mx-auto rounded-full bg-muted flex items-center justify-center">
            <Filter className="w-10 h-10 text-muted-foreground" />
          </div>
          <div className="space-y-2">
            <h3 className="font-display text-2xl font-bold text-foreground">Nenhum resultado encontrado</h3>
            <ul className="text-muted-foreground space-y-1">
              <li>Tente remover alguns filtros</li>
              <li>Busque por outro termo</li>
              <li>Veja sugestoes populares</li>
            </ul>
          </div>
          <Button variant="outline" onClick={handleClear}>
            Limpar filtros
          </Button>
        </div>
      )}
    </div>
  );
};
