import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Download, Play, Info, Search, SearchCheck } from 'lucide-react';
import { toast } from 'sonner';
import { searchAPI, downloadAPI } from '../services/api';
import { TorrentResult } from '../types';

const DetailPage: React.FC = () => {
  const { mediaType, id } = useParams<{ mediaType: string; id: string }>();
  const navigate = useNavigate();
  const tmdbId = Number(id);

  const [activeTab, setActiveTab] = useState<'torrents' | 'info'>('torrents');
  const [selectedSeason, setSelectedSeason] = useState<number | ''>('');
  const [selectedEpisode, setSelectedEpisode] = useState<number | 'temporada-inteira'>('temporada-inteira');
  const [customSearchEnabled, setCustomSearchEnabled] = useState(false);
  const [customQuery, setCustomQuery] = useState('');
  const [searchParams] = useSearchParams();

  const isTV = mediaType === 'tv';

  const [effectiveMediaType, setEffectiveMediaType] = useState(mediaType || 'movie');

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['detail', mediaType, tmdbId],
    queryFn: () =>
      mediaType === 'movie'
        ? searchAPI.getMovieDetail(tmdbId)
        : searchAPI.getTVDetail(tmdbId),
    enabled: !!tmdbId && !!mediaType,
  });

  const media = detail?.data;

  useEffect(() => {
    if (media?.genres) {
      const hasAnimation = media.genres.some(
        (g: { name?: string }) => g.name?.toLowerCase() === 'animation'
      );
      setEffectiveMediaType(isTV && hasAnimation ? 'anime' : (mediaType || 'movie'));
    }
  }, [media, mediaType, isTV]);

  const { data: seasonsData } = useQuery({
    queryKey: ['seasons', tmdbId],
    queryFn: () => searchAPI.getTVSeasons(tmdbId),
    enabled: isTV && !!tmdbId,
  });

  const { data: torrentResults, isLoading: torrentsLoading, refetch: refetchTorrents } = useQuery({
    queryKey: ['torrents', tmdbId, selectedSeason, selectedEpisode, customSearchEnabled, customQuery],
    queryFn: () =>
      searchAPI.searchTorrents({
        tmdb_id: tmdbId,
        media_type: effectiveMediaType || 'movie',
        season: selectedSeason ? Number(selectedSeason) : undefined,
        episode: selectedEpisode !== 'temporada-inteira' ? Number(selectedEpisode) : undefined,
        query: customSearchEnabled && customQuery.trim() ? customQuery.trim() : undefined,
      }),
    enabled: !isTV, // TV torrents only load after user clicks "Buscar"
  });

  const handleSearchTorrents = () => {
    if (!isTV) return;
    refetchTorrents();
  };

  const handleDownload = async (torrent: TorrentResult) => {
    try {
      await downloadAPI.createDownload({
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
      toast.success('Download iniciado com sucesso!');
    } catch (error) {
      console.error('Failed to start download:', error);
      toast.error('Erro ao iniciar download.');
    }
  };

  const seasons = seasonsData?.data || [];

  const tmdbSearchTerm = useMemo(() => {
    if (!media) return '';
    if (mediaType === 'movie') {
      return media.original_title || media.title || '';
    }
    return media.original_name || media.name || '';
  }, [media, mediaType]);

  const effectiveQuery = useMemo(() => {
    if (customSearchEnabled && customQuery.trim()) {
      return customQuery.trim();
    }
    return tmdbSearchTerm;
  }, [customSearchEnabled, customQuery, tmdbSearchTerm]);

  const querySuffix = useMemo(() => {
    if (selectedSeason && selectedEpisode !== 'temporada-inteira') {
      return ` S${String(selectedSeason).padStart(2, '0')}E${String(selectedEpisode).padStart(2, '0')}`;
    }
    if (selectedSeason) {
      return ` S${String(selectedSeason).padStart(2, '0')}`;
    }
    return '';
  }, [selectedSeason, selectedEpisode]);

  const effectiveQueryWithSuffix = `${effectiveQuery}${querySuffix}`;

  const urlQuery = searchParams.get('q') || '';

  React.useEffect(() => {
    if (urlQuery && !customQuery) {
      setCustomQuery(urlQuery);
    }
  }, [urlQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  const episodeOptions = React.useMemo(() => {
    if (!selectedSeason) return [];
    const season = seasons.find((s: any) => s.season_number === Number(selectedSeason));
    if (!season) return [];
    return Array.from({ length: season.episode_count }, (_, i) => i + 1);
  }, [selectedSeason, seasons]);

  if (detailLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="h-64 animate-shimmer rounded-2xl" />
        <div className="h-32 animate-shimmer rounded-2xl" />
      </div>
    );
  }

  if (!media) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Conteúdo não encontrado.</p>
        <button onClick={() => navigate(-1)} className="mt-4 text-primary hover:underline">
          Voltar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar
      </button>

      {/* Hero */}
      <div className="relative rounded-2xl overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(https://image.tmdb.org/t/p/w1280${media.backdrop_path || media.poster_path})`,
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
        <div className="relative p-6 md:p-10 flex gap-6 items-end">
          {media.poster_path && (
            <img
              src={`https://image.tmdb.org/t/p/w300${media.poster_path}`}
              alt={media.display_title}
              className="w-32 md:w-48 rounded-xl shadow-lg hidden md:block"
            />
          )}
          <div className="flex-1">
            <h1 className="font-display text-3xl md:text-4xl font-bold text-foreground">
              {media.display_title}
            </h1>
            <p className="text-muted-foreground mt-1">
              {media.year} • {media.genres?.map((g: any) => g.name).join(', ')}
            </p>
            <p className="text-sm text-muted-foreground mt-2 line-clamp-3">
              {media.overview}
            </p>
            {media.rt_rating && (
              <div className="flex items-center gap-2 mt-3">
                <span className="text-lg">
                  {parseInt(media.rt_rating) >= 60 ? '🍅' : '💀'}
                </span>
                <a
                  href={media.rt_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-white/80 hover:text-white underline underline-offset-2 transition-colors"
                >
                  {media.rt_rating} no Rotten Tomatoes
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border/50">
        <button
          onClick={() => setActiveTab('torrents')}
          className={`pb-2 text-sm font-medium transition-colors ${
            activeTab === 'torrents' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
          }`}
        >
          <Play className="w-4 h-4 inline mr-1" />
          Torrents
        </button>
        <button
          onClick={() => setActiveTab('info')}
          className={`pb-2 text-sm font-medium transition-colors ${
            activeTab === 'info' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
          }`}
        >
          <Info className="w-4 h-4 inline mr-1" />
          Informações
        </button>
      </div>

      {/* Torrents tab */}
      {activeTab === 'torrents' && (
        <div className="space-y-6">
          {isTV && (
            <div className="glass rounded-2xl p-6 space-y-4">
              <h3 className="font-display text-lg font-bold text-foreground">
                Selecionar Temporada / Episódio
              </h3>
              <div className="flex flex-wrap gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Temporada</label>
                  <select
                    value={selectedSeason}
                    onChange={(e) => {
                      setSelectedSeason(e.target.value ? Number(e.target.value) : '');
                      setSelectedEpisode('temporada-inteira');
                    }}
                    className="px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                  >
                    <option value="">Selecionar...</option>
                    {seasons.map((s: any) => (
                      <option key={s.season_number} value={s.season_number}>
                        {s.name} ({s.episode_count} eps)
                      </option>
                    ))}
                  </select>
                </div>
                {selectedSeason && (
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Episódio</label>
                    <select
                      value={selectedEpisode}
                      onChange={(e) => setSelectedEpisode(e.target.value === 'temporada-inteira' ? 'temporada-inteira' : Number(e.target.value))}
                      className="px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                    >
                      <option value="temporada-inteira">Temporada inteira</option>
                      {episodeOptions.map((ep: number) => (
                        <option key={ep} value={ep}>Episódio {ep}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
              <button
                onClick={handleSearchTorrents}
                disabled={!selectedSeason}
                className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Buscar Torrents
              </button>

              <div className="flex items-center gap-3 pt-2 border-t border-border/30">
                <label className="text-sm text-muted-foreground">Tipo de conteúdo:</label>
                <div className="flex rounded-xl border border-border/50 overflow-hidden">
                  <button
                    onClick={() => setEffectiveMediaType('series')}
                    className={`px-4 py-1.5 text-sm transition-colors ${
                      effectiveMediaType === 'series'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-transparent text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Série
                  </button>
                  <button
                    onClick={() => setEffectiveMediaType('anime')}
                    className={`px-4 py-1.5 text-sm transition-colors ${
                      effectiveMediaType === 'anime'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-transparent text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Anime
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Search term info and custom search toggle */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {customSearchEnabled ? (
                  <SearchCheck className="w-4 h-4 text-primary" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                <span>
                  Buscando com:{' '}
                  <strong className="text-foreground">{effectiveQueryWithSuffix || effectiveQuery || '—'}</strong>
                </span>
              </div>
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <span className="text-sm text-muted-foreground">Busca customizada</span>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={customSearchEnabled}
                    onChange={(e) => setCustomSearchEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-muted rounded-full peer-checked:bg-primary transition-colors" />
                  <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-background rounded-full transition-transform peer-checked:translate-x-4 shadow-sm" />
                </div>
              </label>
            </div>
            {customSearchEnabled && (
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Termo de busca customizado</label>
                <input
                  type="text"
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                  placeholder="Digite o termo de busca desejado..."
                  className="w-full px-4 py-2 rounded-xl glass bg-background/50 border border-border/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
                />
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-6">
            <h3 className="font-display text-xl font-bold text-foreground mb-4">
              Torrents disponíveis
            </h3>
            {torrentsLoading ? (
              <div className="h-32 animate-shimmer rounded-xl" />
            ) : torrentResults?.data?.length ? (
              <div className="space-y-3">
                {torrentResults.data.map((torrent: TorrentResult) => (
                  <div
                    key={torrent.title + torrent.indexer}
                    className="flex items-center justify-between p-4 rounded-xl bg-background/50 border border-border/30 hover:border-primary/30 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">{torrent.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {torrent.quality} • {torrent.language} • {torrent.size} • {torrent.seeds}S / {torrent.peers}L
                      </p>
                    </div>
                    <button
                      onClick={() => handleDownload(torrent)}
                      className="ml-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-2 shrink-0"
                    >
                      <Download className="w-4 h-4" />
                      Baixar
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                {isTV ? 'Selecione uma temporada e clique em "Buscar Torrents".' : 'Nenhum torrent encontrado.'}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Info tab */}
      {activeTab === 'info' && (
        <div className="glass rounded-2xl p-6 space-y-4">
          <h3 className="font-display text-xl font-bold text-foreground">Sinopse</h3>
          <p className="text-muted-foreground leading-relaxed">{media.overview}</p>
          {media.runtime && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Duração:</span> {media.runtime} min
            </p>
          )}
          {media.number_of_seasons && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Temporadas:</span> {media.number_of_seasons}
            </p>
          )}
          {media.status && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Status:</span> {media.status}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default DetailPage;
