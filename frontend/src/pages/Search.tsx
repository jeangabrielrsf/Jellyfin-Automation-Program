import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Loader2, Film, Tv, Sparkles } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { SearchResults } from '@/components/SearchResults';
import { searchAPI } from '@/services/api';
import { TMDBSearchResult } from '@/types';

const STORAGE_KEY = 'search_state';

const EmptyState: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  children?: React.ReactNode;
}> = ({ icon, title, description, children }) => (
  <div className="text-center py-16 space-y-6">
    <div className="w-20 h-20 mx-auto rounded-full bg-muted flex items-center justify-center">
      {icon}
    </div>
    <div className="space-y-2">
      <h3 className="font-display text-2xl font-bold text-foreground">{title}</h3>
      <p className="text-muted-foreground max-w-md mx-auto">{description}</p>
    </div>
    {children}
  </div>
);

const suggestions = [
  {
    icon: Film,
    title: 'Filmes Populares',
    description: 'Veja os filmes mais assistidos',
    path: '/discover',
  },
  {
    icon: Sparkles,
    title: 'Animes da Temporada',
    description: 'Descubra animes em destaque',
    path: '/discover',
  },
  {
    icon: Tv,
    title: 'Séries em Alta',
    description: 'Séries mais populares agora',
    path: '/discover',
  },
];

const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [inputValue, setInputValue] = useState('');

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
          setInputValue(query);
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      setSearchQuery(inputValue.trim());
    }
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

  const results = searchResults?.data?.results;
  const hasResults = results && results.length > 0;
  const hasSearched = !!searchQuery && !isSearching;

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Buscar Conteúdo
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Pesquise por filmes, séries ou animes no banco de dados do TMDB
        </p>
      </div>

      <Tabs defaultValue="texto" className="w-full">
        <TabsList className="grid w-full max-w-md mx-auto grid-cols-2">
          <TabsTrigger value="texto">Texto</TabsTrigger>
          <TabsTrigger value="filtros">Filtros</TabsTrigger>
        </TabsList>

        <TabsContent value="texto" className="space-y-6 mt-6">
          <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
            <div className="relative group">
              <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-xl opacity-0
                            group-focus-within:opacity-100 transition-opacity duration-500" />
              <div className="relative flex flex-col sm:flex-row items-stretch glass rounded-2xl
                            focus-within:ring-2 focus-within:ring-primary/30
                            focus-within:border-primary/30
                            transition-all duration-300 overflow-hidden">
                <div className="flex items-center flex-1">
                  <Search className="w-6 h-6 text-muted-foreground ml-5 shrink-0" />
                  <input
                    type="text"
                    placeholder="Buscar filmes, séries ou animes..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    className="flex-1 bg-transparent border-none outline-none
                             px-4 py-5 text-foreground placeholder:text-muted-foreground/60
                             font-body text-lg"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSearching || !inputValue.trim()}
                  className="sm:ml-2 mx-3 mb-3 sm:mb-3 sm:mr-3 px-8 py-4 rounded-xl bg-primary text-primary-foreground
                           font-medium text-base
                           hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                           active:scale-[0.98]
                           disabled:opacity-50 disabled:cursor-not-allowed
                           transition-all duration-200 flex items-center justify-center gap-2"
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Buscando</span>
                    </>
                  ) : (
                    <span>Buscar</span>
                  )}
                </button>
              </div>
            </div>
          </form>

          {hasResults && (
            <SearchResults
              results={results}
              onMediaClick={handleMediaClick}
            />
          )}

          {hasSearched && !hasResults && (
            <EmptyState
              icon={<Search className="w-10 h-10 text-muted-foreground" />}
              title="Nenhum resultado encontrado"
              description="Tente buscar outro termo ou explore nossas sugestões abaixo"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto pt-4">
                {suggestions.map(({ icon: Icon, title, description, path }) => (
                  <button
                    key={title}
                    onClick={() => navigate(path)}
                    className="p-6 rounded-xl bg-card/80 backdrop-blur-sm border border-border/50
                             hover:bg-card hover:border-primary/30 hover:shadow-lg
                             transition-all duration-300 group"
                  >
                    <Icon className="w-8 h-8 text-primary mb-3 mx-auto group-hover:scale-110 transition-transform" />
                    <h4 className="font-semibold text-foreground mb-1">{title}</h4>
                    <p className="text-sm text-muted-foreground">{description}</p>
                  </button>
                ))}
              </div>
            </EmptyState>
          )}

          {!searchQuery && (
            <EmptyState
              icon={<Search className="w-10 h-10 text-muted-foreground" />}
              title="Comece digitando sua busca"
              description="Digite o nome de um filme, série ou anime para encontrar resultados"
            />
          )}
        </TabsContent>

        <TabsContent value="filtros" className="mt-6">
          <EmptyState
            icon={<Sparkles className="w-10 h-10 text-muted-foreground" />}
            title="Em breve"
            description="Sistema de filtros avançado será implementado em breve"
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SearchPage;
