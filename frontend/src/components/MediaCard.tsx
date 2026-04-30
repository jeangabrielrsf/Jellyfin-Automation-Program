import React from 'react';
import { Play, Star } from 'lucide-react';
import { TMDBSearchResult } from '../types';

interface MediaCardProps {
  media: TMDBSearchResult;
  onClick: (media: TMDBSearchResult) => void;
}

export const MediaCard: React.FC<MediaCardProps> = ({ media, onClick }) => {
  const title = media.title || media.name || 'Unknown';
  const year = media.release_date
    ? new Date(media.release_date).getFullYear()
    : media.first_air_date
    ? new Date(media.first_air_date).getFullYear()
    : null;

  return (
    <div
      className="group relative cursor-pointer rounded-xl overflow-hidden
                transition-all duration-300 hover:-translate-y-2
                hover:shadow-2xl hover:shadow-primary/10"
      onClick={() => onClick(media)}
    >
      {/* Poster */}
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

        {/* Hover overlay */}
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

        {/* Type badge */}
        <div className="absolute top-3 left-3">
          <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                         ${media.media_type === 'movie'
                           ? 'bg-primary/90 text-primary-foreground'
                           : 'bg-sky-500/90 text-white'
                         }`}>
            {media.media_type === 'movie' ? 'Filme' : 'Série'}
          </span>
        </div>
      </div>

      {/* Info */}
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
