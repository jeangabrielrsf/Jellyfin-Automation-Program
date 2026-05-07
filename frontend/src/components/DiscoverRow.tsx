import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { discoverAPI } from '../services/api';
import { MediaCard } from './MediaCard';
import { SectionInfo, DiscoverParams, TMDBSearchResult } from '../types';

interface DiscoverRowProps {
  section: SectionInfo;
  filters: DiscoverParams;
}

export const DiscoverRow: React.FC<DiscoverRowProps> = ({ section, filters }) => {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['discover', 'section', section.id, filters],
    queryFn: async () => {
      const res = await discoverAPI.getSection(section.id, filters);
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="mb-8">
        <h2 className="font-display text-xl font-bold text-foreground mb-3">
          {section.title}
        </h2>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="flex-shrink-0 w-40 aspect-[2/3] rounded-xl bg-muted animate-shimmer"
            />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data || data.results.length === 0) {
    return null;
  }

  const handleClick = (media: TMDBSearchResult) => {
    navigate(`/detail/${media.media_type}/${media.id}`);
  };

  return (
    <div className="mb-8">
      <h2 className="font-display text-xl font-bold text-foreground mb-3">
        {section.title}
      </h2>
      <div className="flex gap-4 overflow-x-auto pb-2 scroll-smooth">
        {data.results.map((media: TMDBSearchResult) => (
          <div key={media.id} className="flex-shrink-0 w-40">
            <MediaCard media={media} onClick={handleClick} />
          </div>
        ))}
      </div>
    </div>
  );
};
