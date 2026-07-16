import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Star } from 'lucide-react';
import { TMDBSearchResult } from '../types';

interface DiscoverBannerProps {
  media: TMDBSearchResult | null;
}

export const DiscoverBanner: React.FC<DiscoverBannerProps> = ({ media }) => {
  const navigate = useNavigate();

  if (!media) {
    return null;
  }

  const title = media.display_title || media.title || media.name || 'Unknown';
  const year = media.year || (media.release_date
    ? new Date(media.release_date).getFullYear()
    : media.first_air_date
    ? new Date(media.first_air_date).getFullYear()
    : null);

  const handleClick = () => {
    navigate(`/detail/${media.media_type}/${media.id}`);
  };

  return (
    <div className="relative w-full h-[500px] md:h-[600px] rounded-xl overflow-hidden mb-8 group">
      {media.backdrop_path && (
        <img
          src={`https://image.tmdb.org/t/p/original${media.backdrop_path}`}
          alt={title}
          className="absolute inset-0 w-full h-full object-cover"
        />
      )}
      
      <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent" />
      
      <div className="absolute inset-0 flex items-end">
        <div className="container mx-auto px-4 sm:px-6 lg:px-12 pb-12">
          <div className="max-w-2xl space-y-4">
            <h1 className="font-display text-4xl md:text-5xl font-bold text-white">
              {title}
            </h1>
            
            <div className="flex items-center gap-4 text-white/90 text-sm">
              {year && <span>{year}</span>}
              {media.vote_average > 0 && (
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  <span className="font-medium">{media.vote_average.toFixed(1)}</span>
                </div>
              )}
            </div>
            
            {media.overview && (
              <p className="text-white/80 text-sm md:text-base line-clamp-3">
                {media.overview}
              </p>
            )}
            
            <button
              onClick={handleClick}
              className="px-6 py-3 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-lg transition-colors"
            >
              Ver detalhes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
