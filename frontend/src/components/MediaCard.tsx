import React from 'react';
import { Play, Star } from 'lucide-react';
import { TMDBSearchResult } from '../types';

interface MediaCardProps {
  media: TMDBSearchResult;
  onClick: (media: TMDBSearchResult) => void;
  variant?: 'grid' | 'list';
}

const genreMap: Record<number, string> = {
  28: 'Ação', 12: 'Aventura', 16: 'Animação', 35: 'Comédia', 80: 'Crime',
  99: 'Documentário', 18: 'Drama', 10751: 'Família', 14: 'Fantasia', 36: 'História',
  27: 'Terror', 10402: 'Música', 9648: 'Mistério', 10749: 'Romance', 878: 'Ficção Científica',
  10770: 'Filme de TV', 53: 'Thriller', 10752: 'Guerra', 37: 'Faroeste',
  10759: 'Ação & Aventura', 10762: 'Kids', 10763: 'Notícias', 10764: 'Reality',
  10765: 'Sci-Fi & Fantasy', 10766: 'Novela', 10767: 'Talk', 10768: 'War & Politics',
};

const TypeBadge: React.FC<{ mediaType: string }> = ({ mediaType }) => (
  <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider
                  ${mediaType === 'movie'
                    ? 'bg-primary/90 text-primary-foreground'
                    : 'bg-sky-500/90 text-white'
                  }`}>
    {mediaType === 'movie' ? 'Filme' : 'Série'}
  </span>
);

export const MediaCard: React.FC<MediaCardProps> = ({ media, onClick, variant = 'grid' }) => {
  const title = media.title || media.name || 'Unknown';
  const year = media.release_date
    ? new Date(media.release_date).getFullYear()
    : media.first_air_date
    ? new Date(media.first_air_date).getFullYear()
    : null;

  const genres = media.genre_ids
    .slice(0, 3)
    .map(id => genreMap[id])
    .filter(Boolean);

  if (variant === 'list') {
    return (
      <div
        className="group flex gap-4 p-4 cursor-pointer rounded-xl bg-card/80 backdrop-blur-sm
                  transition-all duration-300 hover:bg-card/90 hover:shadow-lg"
        onClick={() => onClick(media)}
      >
        <div className="w-24 h-36 flex-shrink-0 rounded-lg overflow-hidden bg-muted">
          {media.poster_path ? (
            <img
              src={`https://image.tmdb.org/t/p/w200${media.poster_path}`}
              alt={title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <span className="text-muted-foreground text-xs">Sem imagem</span>
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-body font-semibold text-lg text-foreground line-clamp-1">
              {title}
            </h3>
            <TypeBadge mediaType={media.media_type} />
          </div>

          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {year && <span>{year}</span>}
            {media.vote_average > 0 && (
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                <span className="font-medium">{media.vote_average.toFixed(1)}</span>
              </div>
            )}
          </div>

          {genres.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {genres.map(genre => (
                <span
                  key={genre}
                  className="px-2 py-0.5 rounded-full bg-muted text-xs text-muted-foreground"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {media.overview && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {media.overview}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="group relative cursor-pointer rounded-xl overflow-hidden
                transition-all duration-300 hover:-translate-y-2
                hover:shadow-2xl hover:shadow-primary/10"
      onClick={() => onClick(media)}
    >
      <div className="aspect-[2/3] relative bg-muted overflow-hidden">
        {media.poster_path ? (
          <img
            src={`https://image.tmdb.org/t/p/w500${media.poster_path}`}
            alt={title}
            className="w-full h-full object-cover
                     group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted">
            <span className="text-muted-foreground text-sm">Sem imagem</span>
          </div>
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent
                      opacity-0 group-hover:opacity-100 transition-opacity duration-300
                      flex flex-col justify-end p-4">
          <div className="transform translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
            <div className="w-12 h-12 rounded-full bg-primary/90 flex items-center justify-center
                          mx-auto mb-3 shadow-lg shadow-primary/30">
              <Play className="w-5 h-5 text-white fill-current ml-0.5" />
            </div>
            <p className="text-white text-xs text-center font-medium line-clamp-2">
              Ver torrents disponíveis
            </p>
          </div>
        </div>

        <div className="absolute top-3 left-3">
          <TypeBadge mediaType={media.media_type} />
        </div>
      </div>

      <div className="p-3 bg-card/80 backdrop-blur-sm">
        <h3 className="font-body font-semibold text-sm text-foreground line-clamp-1 mb-1">
          {title}
        </h3>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          {year && <span>{year}</span>}
          {media.vote_average > 0 && (
            <div className="flex items-center gap-1">
              <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
              <span className="font-medium">{media.vote_average.toFixed(1)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
