import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { SearchBar } from '../components/SearchBar';
import { MediaCard } from '../components/MediaCard';
import { searchAPI } from '../services/api';
import { TMDBSearchResult } from '../types';

const STORAGE_KEY = 'search_state';

const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => searchAPI.searchMedia(searchQuery),
    enabled: !!searchQuery,
  });

  useEffect(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const { query, scrollY } = JSON.parse(saved);
        if (query) {
          setSearchQuery(query);
        }
        if (scrollY !== undefined) {
          requestAnimationFrame(() => {
            window.scrollTo(0, scrollY);
          });
        }
        sessionStorage.removeItem(STORAGE_KEY);
      } catch {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleMediaClick = (media: TMDBSearchResult) => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        query: searchQuery,
        scrollY: window.scrollY,
      })
    );
    const params = new URLSearchParams({ q: searchQuery });
    navigate(`/detail/${media.media_type}/${media.id}?${params.toString()}`);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Buscar Conteúdo
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Pesquise por filmes, séries ou animes no banco de dados do TMDB
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} isLoading={isSearching} />

      {/* Results */}
      {searchResults?.data?.results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-xl font-bold text-foreground">
              Resultados
            </h3>
            <span className="text-sm text-muted-foreground">
              {searchResults.data.results.length} encontrados
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {searchResults.data.results.map((media: TMDBSearchResult) => (
              <MediaCard
                key={media.id}
                media={media}
                onClick={handleMediaClick}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
