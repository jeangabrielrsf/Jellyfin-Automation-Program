import React, { useState, useEffect } from 'react';
import { LayoutGrid, List } from 'lucide-react';
import { MediaCard } from './MediaCard';
import { TMDBSearchResult } from '../types';

interface SearchResultsProps {
  results: TMDBSearchResult[];
  onMediaClick: (media: TMDBSearchResult) => void;
}

const RESULTS_PER_PAGE = 20;
const VIEW_MODE_KEY = 'search_view_mode';

export const SearchResults: React.FC<SearchResultsProps> = ({ results, onMediaClick }) => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => {
    const saved = sessionStorage.getItem(VIEW_MODE_KEY);
    return (saved === 'list' ? 'list' : 'grid');
  });
  const [displayCount, setDisplayCount] = useState(RESULTS_PER_PAGE);

  useEffect(() => {
    sessionStorage.setItem(VIEW_MODE_KEY, viewMode);
  }, [viewMode]);

  useEffect(() => {
    setDisplayCount(RESULTS_PER_PAGE);
  }, [results]);

  const displayedResults = results.slice(0, displayCount);
  const hasMore = displayCount < results.length;

  const handleLoadMore = () => {
    setDisplayCount(prev => prev + RESULTS_PER_PAGE);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-xl font-bold text-foreground">
          Resultados
        </h3>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            {results.length} encontrados
          </span>
          <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
            <button
              onClick={() => setViewMode('grid')}
              aria-label="Visualização em grade"
              data-active={viewMode === 'grid'}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'grid'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              aria-label="Visualização em lista"
              data-active={viewMode === 'list'}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'list'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {viewMode === 'grid' ? (
        <div
          data-testid="results-grid"
          className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4"
        >
          {displayedResults.map(media => (
            <MediaCard
              key={media.id}
              media={media}
              onClick={onMediaClick}
              variant="grid"
            />
          ))}
        </div>
      ) : (
        <div data-testid="results-list" className="space-y-3">
          {displayedResults.map(media => (
            <MediaCard
              key={media.id}
              media={media}
              onClick={onMediaClick}
              variant="list"
            />
          ))}
        </div>
      )}

      {hasMore && (
        <div className="flex justify-center pt-4">
          <button
            onClick={handleLoadMore}
            className="px-6 py-3 rounded-xl bg-primary text-primary-foreground
                     font-medium text-sm
                     hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                     active:scale-[0.98]
                     transition-all duration-200"
          >
            Carregar mais
          </button>
        </div>
      )}
    </div>
  );
};
