import React, { useState } from 'react';
import { useQuery, skipToken } from '@tanstack/react-query';
import { SearchBar } from '../components/SearchBar';
import { MediaCard } from '../components/MediaCard';
import { TorrentList } from '../components/TorrentList';
import { searchAPI, downloadAPI } from '../services/api';
import { TMDBSearchResult, TorrentResult } from '../types';

const SearchPage: React.FC = () => {
  const [selectedMedia, setSelectedMedia] = useState<TMDBSearchResult | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => searchAPI.searchMedia(searchQuery),
    enabled: !!searchQuery,
  });

  const { data: torrentResults } = useQuery({
    queryKey: ['torrents', selectedMedia?.id],
    queryFn: selectedMedia && ['movie', 'tv'].includes(selectedMedia.media_type)
      ? () =>
          searchAPI.searchTorrents({
            tmdb_id: selectedMedia.id,
            title: selectedMedia.title || selectedMedia.name || '',
            media_type: selectedMedia.media_type,
          })
      : skipToken,
  });

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setSelectedMedia(null);
  };

  const handleMediaClick = (media: TMDBSearchResult) => {
    setSelectedMedia(media);
  };

  const handleDownload = async (torrent: TorrentResult) => {
    if (!selectedMedia) return;
    try {
      await downloadAPI.createDownload({
        tmdb_id: selectedMedia.id,
        title: selectedMedia.title || selectedMedia.name || '',
        media_type: selectedMedia.media_type,
        torrent_name: torrent.title,
        magnet_link: torrent.magnet_url || torrent.download_url || '',
        quality: torrent.quality || '1080p',
        language_preference: torrent.language || 'legendado',
        indexer_used: torrent.indexer,
      });
      alert('Download iniciado com sucesso!');
    } catch (error) {
      console.error('Failed to start download:', error);
      alert('Erro ao iniciar download.');
    }
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

      {/* Torrents */}
      {selectedMedia && (
        <div className="space-y-4 animate-fade-in-up">
          <div className="glass rounded-2xl p-6">
            <h3 className="font-display text-xl font-bold text-foreground mb-1">
              Torrents para: {selectedMedia.title || selectedMedia.name}
            </h3>
            <p className="text-muted-foreground text-sm mb-4">
              Selecione um torrent para iniciar o download
            </p>
            <TorrentList
              torrents={torrentResults?.data || []}
              onDownload={handleDownload}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
