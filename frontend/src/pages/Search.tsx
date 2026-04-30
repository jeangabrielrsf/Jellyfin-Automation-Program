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
    queryFn: selectedMedia
      ? () =>
          searchAPI.searchTorrents({
            tmdb_id: selectedMedia.id,
            title: selectedMedia.title || selectedMedia.name || '',
            type: selectedMedia.media_type,
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
        type: selectedMedia.media_type,
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
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Buscar Conteúdo</h2>
      
      <SearchBar onSearch={handleSearch} isLoading={isSearching} />

      {searchResults?.data?.results && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {searchResults.data.results.map((media: TMDBSearchResult) => (
            <MediaCard
              key={media.id}
              media={media}
              onClick={handleMediaClick}
            />
          ))}
        </div>
      )}

      {selectedMedia && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold">
            Torrents para: {selectedMedia.title || selectedMedia.name}
          </h3>
          <TorrentList
            torrents={torrentResults?.data || []}
            onDownload={handleDownload}
          />
        </div>
      )}
    </div>
  );
};

export default SearchPage;
