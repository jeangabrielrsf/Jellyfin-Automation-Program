import React from 'react';
import { Select, SelectItem } from './ui/select';
import { Genre, StreamingProvider } from '../types';

const CONTENT_TYPES = [
  { value: '', label: 'Todos' },
  { value: 'movie', label: 'Filme' },
  { value: 'series', label: 'Série' },
  { value: 'anime', label: 'Anime' },
];

const SORT_OPTIONS = [
  { value: 'popularity.desc', label: 'Popularidade' },
  { value: 'vote_average.desc', label: 'Nota' },
  { value: 'primary_release_date.desc', label: 'Lançamento' },
];

interface DiscoverFilterBarProps {
  genreId: number | null;
  mediaType: string | null;
  watchProviderId: number | null;
  sortBy: string;
  genres: Genre[];
  providers: StreamingProvider[];
  onGenreChange: (genreId: number | null) => void;
  onMediaTypeChange: (mediaType: string | null) => void;
  onWatchProviderChange: (providerId: number | null) => void;
  onSortChange: (sortBy: string) => void;
}

export const DiscoverFilterBar: React.FC<DiscoverFilterBarProps> = ({
  genreId,
  mediaType,
  watchProviderId,
  sortBy,
  genres,
  providers,
  onGenreChange,
  onMediaTypeChange,
  onWatchProviderChange,
  onSortChange,
}) => {
  return (
    <div className="flex flex-wrap gap-3 mb-8">
      <Select
        value={genreId ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onGenreChange(val ? Number(val) : null);
        }}
        className="w-48"
      >
        <SelectItem value="">Todos os gêneros</SelectItem>
        {genres.map((g) => (
          <SelectItem key={g.id} value={String(g.id)}>
            {g.name}
          </SelectItem>
        ))}
      </Select>

      <Select
        value={mediaType ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onMediaTypeChange(val || null);
        }}
        className="w-36"
      >
        {CONTENT_TYPES.map((ct) => (
          <SelectItem key={ct.value} value={ct.value}>
            {ct.label}
          </SelectItem>
        ))}
      </Select>

      <Select
        value={watchProviderId ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onWatchProviderChange(val ? Number(val) : null);
        }}
        className="w-48"
      >
        <SelectItem value="">Todos os streamings</SelectItem>
        {providers.map((p) => (
          <SelectItem key={p.id} value={String(p.id)}>
            {p.name}
          </SelectItem>
        ))}
      </Select>

      <Select
        value={sortBy}
        onChange={(e) => onSortChange(e.target.value)}
        className="w-44"
      >
        {SORT_OPTIONS.map((so) => (
          <SelectItem key={so.value} value={so.value}>
            {so.label}
          </SelectItem>
        ))}
      </Select>
    </div>
  );
};
