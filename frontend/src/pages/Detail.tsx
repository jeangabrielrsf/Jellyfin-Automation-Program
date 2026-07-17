import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Download, Play, Info, Search, Star, Calendar, Loader2, ChevronDown, Filter, SortAsc, SortDesc } from 'lucide-react';
import { searchAPI } from '../services/api';
import { TorrentResult, TVEpisode } from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { MediaActions } from '@/components/MediaActions';
import { RecommendationsRow } from '@/components/RecommendationsRow';
import { useTorrentFilters } from '@/hooks/useTorrentFilters';
import { useDownload } from '@/hooks/useDownload';

const QUALITY_OPTIONS = ['2160p', '1080p', '720p', '480p'];
const LANGUAGE_OPTIONS = ['Legendado', 'Dublado', 'Dual Áudio'];

const DetailPage: React.FC = () => {
  const { mediaType, id } = useParams<{ mediaType: string; id: string }>();
  const navigate = useNavigate();
  const tmdbId = Number(id);

  const [activeTab, setActiveTab] = useState<'torrents' | 'info'>('info');
  const [selectedSeason, setSelectedSeason] = useState<number | ''>('');
  const [selectedEpisode, setSelectedEpisode] = useState<number | 'temporada-inteira'>('temporada-inteira');
  const [synopsisExpanded, setSynopsisExpanded] = useState(false);
  const [searchParams] = useSearchParams();
  const [trailerOpen, setTrailerOpen] = useState(false);

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

  const { data: seasonDetailData, isLoading: seasonDetailLoading } = useQuery({
    queryKey: ['season-detail', tmdbId, selectedSeason],
    queryFn: () => searchAPI.getTVSeasonDetail(tmdbId, Number(selectedSeason)),
    enabled: isTV && !!tmdbId && selectedSeason !== '',
  });

  const { data: alternativeTitles } = useQuery({
    queryKey: ['alternative-titles', mediaType, tmdbId],
    queryFn: () =>
      mediaType === 'movie'
        ? searchAPI.getMovieAlternativeTitles(tmdbId)
        : searchAPI.getTVAlternativeTitles(tmdbId),
    enabled: !!tmdbId && !!mediaType,
  });

  const { data: torrentResults, isLoading: torrentsLoading, refetch: refetchTorrents } = useQuery({
    queryKey: ['torrents', tmdbId, selectedSeason, selectedEpisode],
    queryFn: () =>
      searchAPI.searchTorrents({
        tmdb_id: tmdbId,
        media_type: effectiveMediaType || 'movie',
        season: selectedSeason ? Number(selectedSeason) : undefined,
        episode: selectedEpisode !== 'temporada-inteira' ? Number(selectedEpisode) : undefined,
      }),
    enabled: !isTV,
  });

  const {
    preferredQuality, setPreferredQuality,
    preferredLanguage, setPreferredLanguage,
    customSearchEnabled, setCustomSearchEnabled,
    customQuery, setCustomQuery,
    selectedTitle, setSelectedTitle,
    selectedQualities, setSelectedQualities,
    selectedLanguages, setSelectedLanguages,
    minSeeds, setMinSeeds,
    freeleechOnly, setFreeleechOnly,
    sortBy, setSortBy,
    sortOrder, setSortOrder,
    titleFilter, setTitleFilter,
    visibleCount, setVisibleCount,
    advancedOptionsOpen, setAdvancedOptionsOpen,
    filteredTorrents, visibleTorrents, hasMoreTorrents,
    PAGE_SIZE,
  } = useTorrentFilters(torrentResults?.data || []);

  const { downloadingTorrents, handleDownload } = useDownload({
    tmdbId,
    detail,
    effectiveMediaType,
    selectedSeason,
    selectedEpisode,
  });

  const handleSearchTorrents = () => {
    if (!isTV) return;
    refetchTorrents();
  };

  const seasons = seasonsData?.data || [];

  const tmdbSearchTerm = useMemo(() => {
    if (selectedTitle) return selectedTitle;
    if (!media) return '';
    if (mediaType === 'movie') {
      return media.original_title || media.title || '';
    }
    return media.original_name || media.name || '';
  }, [media, mediaType, selectedTitle]);

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

  const trailerKey = useMemo(() => {
    const videos = media?.videos?.results;
    if (!videos?.length) return null;

    const youtubeVideos = videos.filter((v: { site: string }) => v.site === 'YouTube');
    const trailers = youtubeVideos.filter((v: { type: string }) => v.type === 'Trailer');
    const teasers = youtubeVideos.filter((v: { type: string }) => v.type === 'Teaser');

    return trailers[0]?.key || teasers[0]?.key || youtubeVideos[0]?.key || null;
  }, [media]);

  const urlQuery = searchParams.get('q') || '';

  React.useEffect(() => {
    if (urlQuery && !customQuery) {
      setCustomQuery(urlQuery);
    }
  }, [urlQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  const episodes: TVEpisode[] = seasonDetailData?.data?.episodes || [];

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
              {media.year} • {media.genres?.map((g: { name: string }) => g.name).join(', ')}
            </p>
            <div>
              <p className={`text-sm text-muted-foreground mt-2 ${synopsisExpanded ? '' : 'line-clamp-3'}`}>
                {media.overview}
              </p>
              {media.overview && media.overview.length > 150 && (
                <button
                  onClick={() => setSynopsisExpanded(!synopsisExpanded)}
                  className="text-xs text-primary mt-1 hover:underline font-medium"
                >
                  {synopsisExpanded ? 'Ler menos' : 'Ler mais'}
                </button>
              )}
            </div>
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
            <div className="flex items-center gap-3 mt-3 flex-wrap">
              {trailerKey ? (
                <button
                  onClick={() => setTrailerOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary hover:bg-primary/30 transition-colors text-sm font-medium"
                >
                  <Play className="w-4 h-4" />
                  Trailer
                </button>
              ) : (
                <span className="flex items-center gap-2 px-4 py-2 rounded-xl bg-muted text-muted-foreground text-sm font-medium cursor-not-allowed">
                  <Play className="w-4 h-4" />
                  Trailer não disponível
                </span>
              )}
              <MediaActions
                mediaType={(effectiveMediaType as 'movie' | 'series' | 'anime')}
                tmdbId={tmdbId}
                title={media.display_title}
                posterPath={media.poster_path}
                backdropPath={media.backdrop_path}
                year={media.year ?? null}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border/50">
        <button
          onClick={() => setActiveTab('info')}
          className={`pb-2 text-sm font-medium transition-colors ${
            activeTab === 'info' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
          }`}
        >
          <Info className="w-4 h-4 inline mr-1" />
          Informações
        </button>
        <button
          onClick={() => setActiveTab('torrents')}
          className={`pb-2 text-sm font-medium transition-colors ${
            activeTab === 'torrents' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
          }`}
        >
          <Play className="w-4 h-4 inline mr-1" />
          Torrents
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
              <div className="flex flex-col sm:flex-row sm:items-end gap-3">
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
                    {seasons.map((s: { season_number: number; name: string; episode_count: number }) => (
                      <option key={s.season_number} value={s.season_number}>
                        {s.name} ({s.episode_count} eps)
                      </option>
                    ))}
                  </select>
                </div>
                {selectedSeason && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedEpisode('temporada-inteira')}
                      className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                        selectedEpisode === 'temporada-inteira'
                          ? 'bg-primary text-primary-foreground'
                          : 'glass border border-border/50 text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Temporada inteira
                    </button>
                  </div>
                )}
              </div>

              {selectedSeason && (
                <div className="space-y-3">
                  {seasonDetailLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-28 animate-shimmer rounded-xl bg-background/50" />
                      ))}
                    </div>
                  ) : episodes.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {episodes.map((ep: TVEpisode) => {
                        const isSelected = selectedEpisode === ep.episode_number;
                        const voteColor = ep.vote_average >= 7 ? 'text-green-400' : ep.vote_average >= 5 ? 'text-yellow-400' : 'text-red-400';

                        return (
                          <button
                            key={ep.episode_number}
                            onClick={() => setSelectedEpisode(ep.episode_number)}
                            className={`flex gap-3 p-3 rounded-xl border text-left transition-all ${
                              isSelected
                                ? 'border-primary bg-primary/10'
                                : 'border-border/30 bg-background/50 hover:border-primary/30'
                            }`}
                          >
                            {ep.still_path ? (
                              <img
                                src={`https://image.tmdb.org/t/p/w185${ep.still_path}`}
                                alt=""
                                className="w-28 h-16 object-cover rounded-lg shrink-0"
                                loading="lazy"
                              />
                            ) : (
                              <div className="w-28 h-16 rounded-lg bg-muted shrink-0 flex items-center justify-center">
                                <Play className="w-6 h-6 text-muted-foreground" />
                              </div>
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">E{String(ep.episode_number).padStart(2, '0')}</span>
                                {ep.vote_average > 0 && (
                                  <span className={`flex items-center gap-0.5 text-xs font-medium ${voteColor}`}>
                                    <Star className="w-3 h-3 fill-current" />
                                    {ep.vote_average.toFixed(1)}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm font-medium text-foreground truncate mt-0.5">
                                {ep.name || `Episódio ${ep.episode_number}`}
                              </p>
                              {ep.air_date && (
                                <div className="flex items-center gap-1 mt-1">
                                  <Calendar className="w-3 h-3 text-muted-foreground" />
                                  <span className="text-xs text-muted-foreground">
                                    {new Date(ep.air_date).toLocaleDateString('pt-BR')}
                                  </span>
                                </div>
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Nenhum episódio disponível para esta temporada.</p>
                  )}
                </div>
              )}

              <button
                onClick={handleSearchTorrents}
                disabled={!selectedSeason}
                className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Buscar Torrents
              </button>

              <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-2 border-t border-border/30">
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

          {/* Server-side filters */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Search className="w-4 h-4" />
              <span>
                Buscando com:{' '}
                <strong className="text-foreground">{effectiveQueryWithSuffix || effectiveQuery || '—'}</strong>
              </span>
            </div>

            {/* Title selector */}
            {alternativeTitles?.data && alternativeTitles.data.length > 0 && (
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Título para busca</label>
                <select
                  value={selectedTitle}
                  onChange={(e) => setSelectedTitle(e.target.value)}
                  className="w-full px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                >
                  <option value="">
                    {media?.title || media?.name || 'Título padrão'}
                  </option>
                  {alternativeTitles.data.map((t, idx) => (
                    <option key={`${t.country}-${idx}`} value={t.title}>
                      {t.title} ({t.country})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Qualidade preferida</label>
                <select
                  value={preferredQuality}
                  onChange={(e) => setPreferredQuality(e.target.value)}
                  className="w-full px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                >
                  {QUALITY_OPTIONS.map(q => (
                    <option key={q} value={q}>{q}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Idioma preferido</label>
                <select
                  value={preferredLanguage}
                  onChange={(e) => setPreferredLanguage(e.target.value)}
                  className="w-full px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                >
                  {LANGUAGE_OPTIONS.map(l => (
                    <option key={l} value={l.toLowerCase()}>{l}</option>
                  ))}
                </select>
              </div>
            </div>

            {!isTV && (
              <button
                onClick={() => refetchTorrents()}
                className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
              >
                Buscar Torrents
              </button>
            )}

            {/* Advanced options accordion */}
            <div className="border-t border-border/30 pt-4">
              <button
                onClick={() => setAdvancedOptionsOpen(!advancedOptionsOpen)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <ChevronDown className={`w-4 h-4 transition-transform ${advancedOptionsOpen ? 'rotate-180' : ''}`} />
                Opções avançadas
              </button>
              {advancedOptionsOpen && (
                <div className="mt-4 space-y-4">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={customSearchEnabled}
                      onChange={(e) => setCustomSearchEnabled(e.target.checked)}
                      className="w-4 h-4 rounded border-border"
                    />
                    <span className="text-sm text-muted-foreground">Busca customizada</span>
                  </label>
                  {customSearchEnabled && (
                    <input
                      type="text"
                      value={customQuery}
                      onChange={(e) => setCustomQuery(e.target.value)}
                      placeholder="Digite o termo de busca desejado..."
                      className="w-full px-4 py-2 rounded-xl glass bg-background/50 border border-border/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Client-side filters */}
          {torrentResults?.data && torrentResults.data.length > 0 && (
            <div className="glass rounded-2xl p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Refinar resultados</span>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Qualidade</label>
                  <div className="flex flex-wrap gap-2">
                    {QUALITY_OPTIONS.map(q => {
                      const isSelected = selectedQualities.includes(q);
                      return (
                        <button
                          key={q}
                          onClick={() => {
                            setSelectedQualities(prev =>
                              isSelected ? prev.filter(x => x !== q) : [...prev, q]
                            );
                          }}
                          className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                            isSelected
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-background/50 text-muted-foreground hover:text-foreground border border-border/50'
                          }`}
                        >
                          {q}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Idioma</label>
                  <div className="flex flex-wrap gap-2">
                    {LANGUAGE_OPTIONS.map(l => {
                      const isSelected = selectedLanguages.includes(l);
                      return (
                        <button
                          key={l}
                          onClick={() => {
                            setSelectedLanguages(prev =>
                              isSelected ? prev.filter(x => x !== l) : [...prev, l]
                            );
                          }}
                          className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                            isSelected
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-background/50 text-muted-foreground hover:text-foreground border border-border/50'
                          }`}
                        >
                          {l}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Seeds mínimos: {minSeeds}</label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={minSeeds}
                      onChange={(e) => setMinSeeds(Number(e.target.value))}
                      className="w-full"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={freeleechOnly}
                        onChange={(e) => setFreeleechOnly(e.target.checked)}
                        className="w-4 h-4 rounded border-border"
                      />
                      <span className="text-sm text-muted-foreground">Apenas Freeleech</span>
                    </label>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Filtrar por título</label>
                  <input
                    type="text"
                    value={titleFilter}
                    onChange={(e) => setTitleFilter(e.target.value)}
                    placeholder="Digite para filtrar..."
                    className="w-full px-4 py-2 rounded-xl glass bg-background/50 border border-border/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                </div>

                <div className="flex items-center gap-4">
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Ordenar por</label>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as 'score' | 'seeds' | 'date' | 'size')}
                      className="px-4 py-2 rounded-xl glass bg-transparent border border-border/50 text-foreground"
                    >
                      <option value="score">Score</option>
                      <option value="seeds">Seeds</option>
                      <option value="date">Data</option>
                      <option value="size">Tamanho</option>
                    </select>
                  </div>
                  <button
                    onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
                    className="mt-6 px-4 py-2 rounded-xl glass border border-border/50 text-foreground hover:bg-background/50 transition-colors"
                  >
                    {sortOrder === 'desc' ? <SortDesc className="w-4 h-4" /> : <SortAsc className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Torrent list */}
          <div className="glass rounded-2xl p-6">
            <h3 className="font-display text-xl font-bold text-foreground mb-4">
              Torrents disponíveis
              {filteredTorrents.length > 0 && (
                <span className="text-sm font-normal text-muted-foreground ml-2">
                  ({filteredTorrents.length} resultados)
                </span>
              )}
            </h3>
            {torrentsLoading ? (
              <div className="h-32 animate-shimmer rounded-xl" />
            ) : filteredTorrents.length > 0 ? (
              <div className="space-y-3">
                {visibleTorrents.map((torrent: TorrentResult) => {
                  const torrentKey = torrent.title + torrent.indexer;
                  const isDownloading = downloadingTorrents.has(torrentKey);
                  const isFreeleech = torrent.download_volume_factor === 0;

                  return (
                    <div
                      key={torrent.title + torrent.indexer}
                      className="flex items-center justify-between p-4 rounded-xl bg-background/50 border border-border/30 hover:border-primary/30 transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-foreground break-all sm:truncate" title={torrent.title}>
                            {torrent.title}
                          </p>
                          {isFreeleech && (
                            <span className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400 font-medium shrink-0">
                              Freeleech
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1 flex-wrap">
                          {torrent.quality && <span>{torrent.quality}</span>}
                          {torrent.language && <span>• {torrent.language}</span>}
                          <span>• {torrent.size}</span>
                          <span className="text-green-400">• {torrent.seeds}S</span>
                          <span className="text-blue-400">/ {torrent.peers}L</span>
                          {torrent.grabs !== undefined && torrent.grabs > 0 && (
                            <span>• {torrent.grabs} downloads</span>
                          )}
                          {torrent.files !== undefined && torrent.files > 0 && (
                            <span>• {torrent.files} arquivos</span>
                          )}
                          {torrent.publish_date && (
                            <span>• {new Date(torrent.publish_date).toLocaleDateString('pt-BR')}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDownload(torrent)}
                        disabled={isDownloading}
                        className="ml-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 shrink-0"
                      >
                        {isDownloading ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Baixando...
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4" />
                            Baixar
                          </>
                        )}
                      </button>
                    </div>
                  );
                })}
                {hasMoreTorrents && (
                  <button
                    onClick={() => setVisibleCount(prev => prev + PAGE_SIZE)}
                    className="w-full py-3 rounded-xl bg-background/50 border border-border/50 text-foreground hover:bg-background/80 transition-colors"
                  >
                    Carregar mais ({filteredTorrents.length - visibleCount} restantes)
                  </button>
                )}
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
          {media.watch_providers && media.watch_providers.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-border/30">
              <h4 className="font-display text-lg font-semibold text-foreground">Onde assistir</h4>
              <div className="flex flex-wrap gap-3">
                {media.watch_providers.map((provider) => (
                  <div
                    key={provider.provider_id}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border border-border/30"
                  >
                    {provider.logo_path && (
                      <img
                        src={`https://image.tmdb.org/t/p/w92${provider.logo_path}`}
                        alt={provider.provider_name}
                        className="w-6 h-6 rounded"
                      />
                    )}
                    <span className="text-sm text-foreground">{provider.provider_name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <RecommendationsRow
        mediaType={(effectiveMediaType as 'movie' | 'series' | 'anime')}
        tmdbId={tmdbId}
      />

      <Dialog open={trailerOpen} onOpenChange={setTrailerOpen}>
        <DialogContent className="sm:max-w-[800px] p-0 bg-black border-none">
          <DialogHeader className="sr-only">
            <DialogTitle>Trailer - {media.display_title}</DialogTitle>
          </DialogHeader>
          <div className="relative w-full" style={{ paddingTop: '56.25%' }}>
            {trailerKey && (
              <iframe
                src={`https://www.youtube.com/embed/${trailerKey}?autoplay=1`}
                className="absolute inset-0 w-full h-full"
                allow="autoplay; encrypted-media"
                allowFullScreen
                title={`Trailer - ${media.display_title}`}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DetailPage;
