import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { recommendationsAPI } from '@/services/api';
import { MediaCard } from './MediaCard';
import type { TMDBSearchResult, UserMediaType } from '@/types';

interface RecommendationsRowProps {
  mediaType: UserMediaType;
  tmdbId: number;
}

export const RecommendationsRow: React.FC<RecommendationsRowProps> = ({
  mediaType,
  tmdbId,
}) => {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['recommendations', mediaType, tmdbId],
    queryFn: () => recommendationsAPI.get(mediaType, tmdbId, 10).then((r) => r.data),
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading || isError) return null;
  if (!data || data.length === 0) return null;

  const handleClick = (media: TMDBSearchResult) => {
    const routeType = media.media_type === 'movie' ? 'movie' : 'tv';
    navigate(`/detail/${routeType}/${media.id}`);
  };

  return (
    <section className="space-y-3">
      <h3 className="font-display text-lg font-bold text-foreground">Recomendações</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {data.map((rec) => (
          <div key={`${rec.media_type}-${rec.id}`} className="shrink-0 w-36 sm:w-44">
            <MediaCard media={rec} onClick={handleClick} />
          </div>
        ))}
      </div>
    </section>
  );
};
