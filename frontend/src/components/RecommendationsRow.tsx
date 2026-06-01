import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { recommendationsAPI } from '@/services/api';
import type { Recommendation, UserMediaType } from '@/types';

interface RecommendationsRowProps {
  mediaType: UserMediaType;
  tmdbId: number;
}

const RecommendationCard: React.FC<{ item: Recommendation }> = ({ item }) => {
  const title = item.title || item.name || 'Sem título';
  const year =
    (item.release_date || item.first_air_date || '').slice(0, 4) || null;
  const detailPath =
    item.media_type === 'movie'
      ? `/detail/movie/${item.id}`
      : `/detail/tv/${item.id}`;
  return (
    <Link
      to={detailPath}
      className="shrink-0 w-36 sm:w-44 rounded-xl overflow-hidden border border-border/30 bg-background/50 hover:border-primary/30 transition-colors"
    >
      {item.poster_path ? (
        <img
          src={`https://image.tmdb.org/t/p/w300${item.poster_path}`}
          alt={title}
          className="w-full h-52 object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-52 bg-muted flex items-center justify-center text-muted-foreground text-sm">
          Sem imagem
        </div>
      )}
      <div className="p-2 space-y-1">
        <p className="text-sm font-medium text-foreground line-clamp-2">{title}</p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{year || '—'}</span>
          {item.vote_average > 0 && (
            <span className="flex items-center gap-0.5">
              <Star className="w-3 h-3 fill-current" />
              {item.vote_average.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
};

export const RecommendationsRow: React.FC<RecommendationsRowProps> = ({
  mediaType,
  tmdbId,
}) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['recommendations', mediaType, tmdbId],
    queryFn: () => recommendationsAPI.get(mediaType, tmdbId, 10).then((r) => r.data),
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading || isError) return null;
  if (!data || data.length === 0) return null;

  return (
    <section className="space-y-3">
      <h3 className="font-display text-lg font-bold text-foreground">Recomendações</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {data.map((rec) => (
          <RecommendationCard key={`${rec.media_type}-${rec.id}`} item={rec} />
        ))}
      </div>
    </section>
  );
};
