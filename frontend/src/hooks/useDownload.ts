import { useState } from 'react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { downloadAPI } from '@/services/api';
import { TorrentResult } from '@/types';

interface UseDownloadParams {
  tmdbId: number;
  detail: { data?: { display_title?: string } } | undefined;
  effectiveMediaType: string;
  selectedSeason: number | '';
  selectedEpisode: number | 'temporada-inteira';
}

export function useDownload({
  tmdbId,
  detail,
  effectiveMediaType,
  selectedSeason,
  selectedEpisode,
}: UseDownloadParams) {
  const [downloadingTorrents, setDownloadingTorrents] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  const handleDownload = async (torrent: TorrentResult) => {
    const torrentKey = torrent.title + torrent.indexer;
    if (downloadingTorrents.has(torrentKey)) return;

    setDownloadingTorrents(prev => new Set(prev).add(torrentKey));
    try {
      const response = await downloadAPI.createDownload({
        tmdb_id: tmdbId,
        title: detail?.data?.display_title || '',
        media_type: effectiveMediaType || 'movie',
        torrent_name: torrent.title,
        magnet_link: torrent.magnet_url || undefined,
        download_url: torrent.download_url || undefined,
        quality: torrent.quality || '1080p',
        language_preference: torrent.language || 'legendado',
        indexer_used: torrent.indexer,
        size: torrent.size,
        seeds: torrent.seeds,
        peers: torrent.peers,
        season: selectedSeason ? Number(selectedSeason) : undefined,
        episode: selectedEpisode !== 'temporada-inteira' ? Number(selectedEpisode) : undefined,
      });

      const alreadyExists = response.data?.already_exists;
      if (alreadyExists) {
        toast.info('Torrent já estava na fila de downloads');
      } else {
        toast.success('Download iniciado com sucesso!');
      }

      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      queryClient.invalidateQueries({ queryKey: ['detail-downloads', tmdbId] });
    } catch (error) {
      console.error('Failed to start download:', error);
      toast.error('Erro ao iniciar download.');
    } finally {
      setDownloadingTorrents(prev => {
        const next = new Set(prev);
        next.delete(torrentKey);
        return next;
      });
    }
  };

  return { downloadingTorrents, handleDownload };
}
