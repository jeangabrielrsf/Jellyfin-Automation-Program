import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
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
    <Card 
      className="cursor-pointer hover:shadow-lg transition-shadow overflow-hidden"
      onClick={() => onClick(media)}
    >
      <div className="aspect-[2/3] relative bg-muted">
        {media.poster_path ? (
          <img
            src={`https://image.tmdb.org/t/p/w500${media.poster_path}`}
            alt={title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            Sem imagem
          </div>
        )}
      </div>
      <CardHeader className="p-4">
        <CardTitle className="text-lg truncate">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <div className="flex items-center justify-between">
          <Badge variant="secondary">
            {media.media_type === 'movie' ? 'Filme' : 'Série'}
          </Badge>
          {year && (
            <span className="text-sm text-muted-foreground">{year}</span>
          )}
        </div>
        {media.vote_average > 0 && (
          <div className="mt-2 text-sm text-muted-foreground">
            ★ {media.vote_average.toFixed(1)}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
