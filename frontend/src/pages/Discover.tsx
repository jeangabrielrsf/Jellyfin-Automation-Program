import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Compass } from 'lucide-react';
import { discoverAPI } from '../services/api';
import { DiscoverFilterBar } from '../components/DiscoverFilterBar';
import { DiscoverRow } from '../components/DiscoverRow';
import { DiscoverParams, SectionInfo } from '../types';

const DiscoverPage: React.FC = () => {
  const [genreId, setGenreId] = useState<number | null>(null);
  const [mediaType, setMediaType] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('popularity.desc');

  const filters: DiscoverParams = { genre_id: genreId, media_type: mediaType, sort_by: sortBy };

  const { data: catalog, isLoading: catalogLoading, isError: catalogError } = useQuery({
    queryKey: ['discover', 'sections'],
    queryFn: async () => {
      const res = await discoverAPI.getSections(filters);
      return res.data;
    },
  });

  const { data: genres } = useQuery({
    queryKey: ['discover', 'genres'],
    queryFn: async () => {
      const res = await discoverAPI.getGenres();
      return res.data;
    },
    staleTime: 60 * 60 * 1000,
  });

  return (
    <div className="space-y-2 animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Compass className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            Explorar
          </h1>
          <p className="text-muted-foreground text-sm">
            Descubra novos filmes, séries e animes
          </p>
        </div>
      </div>

      <DiscoverFilterBar
        genreId={genreId}
        mediaType={mediaType}
        sortBy={sortBy}
        genres={genres ?? []}
        onGenreChange={setGenreId}
        onMediaTypeChange={setMediaType}
        onSortChange={setSortBy}
      />

      {catalogLoading && (
        <div className="space-y-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i}>
              <div className="h-7 w-48 bg-muted rounded-md mb-3 animate-shimmer" />
              <div className="flex gap-4 overflow-x-auto">
                {Array.from({ length: 6 }).map((_, j) => (
                  <div
                    key={j}
                    className="flex-shrink-0 w-40 aspect-[2/3] rounded-xl bg-muted animate-shimmer"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {catalogError && (
        <div className="text-center py-16">
          <p className="text-muted-foreground text-lg mb-4">
            Erro ao carregar seções
          </p>
          <button
            onClick={() => window.location.reload()}
            className="text-primary text-sm font-medium hover:underline"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {!catalogLoading && !catalogError && catalog && catalog.sections.length === 0 && (
        <div className="text-center py-16">
          <p className="text-muted-foreground">
            Nenhuma seção disponível com esses filtros
          </p>
        </div>
      )}

      {!catalogLoading && !catalogError && catalog && catalog.sections.map((section: SectionInfo) => (
        <DiscoverRow key={section.id} section={section} filters={filters} />
      ))}
    </div>
  );
};

export default DiscoverPage;
