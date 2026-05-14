import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="relative group">
        <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-xl opacity-0
                      group-focus-within:opacity-100 transition-opacity duration-500" />
        <div className="relative flex flex-col sm:flex-row items-stretch glass rounded-2xl
                      focus-within:ring-2 focus-within:ring-primary/30
                      focus-within:border-primary/30
                      transition-all duration-300 overflow-hidden">
          <div className="flex items-center flex-1">
            <Search className="w-5 h-5 text-muted-foreground ml-4 shrink-0" />
            <input
              type="text"
              placeholder="Buscar filmes, séries ou animes..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent border-none outline-none
                       px-3 py-4 text-foreground placeholder:text-muted-foreground/60
                       font-body text-base"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="sm:ml-2 mx-2 mb-2 sm:mb-2 sm:mr-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground
                     font-medium text-sm
                     hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                     active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all duration-200 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Buscando</span>
              </>
            ) : (
              <span>Buscar</span>
            )}
          </button>
        </div>
      </div>
    </form>
  );
};
