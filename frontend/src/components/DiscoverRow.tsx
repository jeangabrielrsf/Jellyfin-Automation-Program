import React, { useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { discoverAPI } from '../services/api';
import { MediaCard } from './MediaCard';
import { SectionInfo, DiscoverParams, TMDBSearchResult } from '../types';

interface DiscoverRowProps {
  section: SectionInfo;
  filters: DiscoverParams;
}

const SCROLL_STEP = 600;

interface ScrollArrowProps {
  direction: 'left' | 'right';
  onClick: () => void;
}

const ScrollArrow: React.FC<ScrollArrowProps> = ({ direction, onClick }) => {
  const Icon = direction === 'left' ? ChevronLeft : ChevronRight;
  const positionClass = direction === 'left' ? 'left-0' : 'right-0';
  const ariaLabel = direction === 'left' ? 'scroll left' : 'scroll right';

  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel}
      className={`absolute ${positionClass} top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-black/50 hover:bg-black/70 text-white rounded-full flex items-center justify-center opacity-0 group-hover/row:opacity-100 transition-opacity`}
    >
      <Icon className="w-6 h-6" />
    </button>
  );
};

export const DiscoverRow: React.FC<DiscoverRowProps> = ({ section, filters }) => {
  const navigate = useNavigate();
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['discover', 'section', section.id, filters],
    queryFn: async () => {
      const res = await discoverAPI.getSection(section.id, filters);
      return res.data;
    },
  });

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = direction === 'left' ? -SCROLL_STEP : SCROLL_STEP;
      scrollContainerRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
  };

  if (isLoading) {
    return (
      <div className="mb-8">
        <h2 className="font-display text-xl font-bold text-foreground mb-3">
          {section.title}
        </h2>
        <div className="flex gap-3 sm:gap-4 overflow-x-auto pb-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="flex-shrink-0 w-32 sm:w-36 md:w-40 aspect-[2/3] rounded-xl bg-muted animate-shimmer"
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
    <div className="mb-8 group/row">
      <h2 className="font-display text-xl font-bold text-foreground mb-3">
        {section.title}
      </h2>
      <div className="relative">
        <ScrollArrow direction="left" onClick={() => scroll('left')} />
        
        <div
          ref={scrollContainerRef}
          className="flex gap-3 sm:gap-4 overflow-x-auto pb-2 scroll-smooth scrollbar-hide"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {data.results.map((media: TMDBSearchResult) => (
            <div key={media.id} className="flex-shrink-0 w-32 sm:w-36 md:w-40">
              <MediaCard media={media} onClick={handleClick} />
            </div>
          ))}
        </div>
        
        <ScrollArrow direction="right" onClick={() => scroll('right')} />
      </div>
    </div>
  );
};
