import axios from 'axios';
import type {
  ListKind, UserMediaType, ListStatus, ListItem, Recommendation,
  TMDBSearchResponse, TMDBDetail, TVSeason, TVSeasonDetail, AlternativeTitle,
  TorrentResult, Download, DownloadCreateResponse, CancelDownloadResponse,
  MessageResponse, ClearDownloadsResponse, SettingsResponse, SettingUpdateResponse,
  RootResponse, DirsResponse, DiskSpaceResponse, LogsResponse,
  SectionCatalog, DiscoverSection, Genre, StreamingProvider,
} from '@/types';

export type { DiskSpaceResponse };

const mapMediaType = (mediaType: string): string => {
  if (mediaType === 'tv') return 'series';
  return mediaType;
};

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchAPI = {
  searchMedia: (query: string, page = 1) =>
    api.get<TMDBSearchResponse>(`/search/?q=${encodeURIComponent(query)}&page=${page}`),

  discoverMedia: (params: {
    media_type?: string;
    genre_ids?: number[];
    watch_provider_ids?: number[];
    year_from?: number;
    year_to?: number;
    min_rating?: number;
    sort_by?: string;
    page?: number;
  }) => api.get<TMDBSearchResponse>('/search/discover/', { params }),
  
  getMovieDetail: (id: number) =>
    api.get<TMDBDetail>(`/search/movie/${id}`),
  
  getTVDetail: (id: number) =>
    api.get<TMDBDetail>(`/search/tv/${id}`),

  getTVSeasons: (id: number) =>
    api.get<TVSeason[]>(`/search/tv/${id}/seasons`),

  getTVSeasonDetail: (id: number, seasonNumber: number) =>
    api.get<TVSeasonDetail>(`/search/tv/${id}/season/${seasonNumber}`),

  getMovieAlternativeTitles: (id: number) =>
    api.get<AlternativeTitle[]>(`/search/movie/${id}/alternative-titles`),

  getTVAlternativeTitles: (id: number) =>
    api.get<AlternativeTitle[]>(`/search/tv/${id}/alternative-titles`),
  
  searchTorrents: (params: {
    tmdb_id: number;
    media_type: string;
    season?: number;
    episode?: number;
    quality?: string;
    language?: string;
    query?: string;
  }) => {
    const apiParams: Record<string, unknown> = {
      ...params,
      media_type: mapMediaType(params.media_type),
    };
    if (params.query) {
      apiParams.query = params.query;
    }
    return api.get<TorrentResult[]>('/search/torrents', { params: apiParams });
  },
};

export const downloadAPI = {
  listDownloads: (status?: string) =>
    api.get<Download[]>('/downloads/', { params: { status } }),
  
  createDownload: (data: {
    tmdb_id: number;
    title: string;
    media_type: string;
    torrent_name: string;
    magnet_link?: string;
    download_url?: string;
    quality?: string;
    language_preference?: string;
    indexer_used?: string;
    size?: string;
    seeds?: number;
    peers?: number;
    season?: number;
    episode?: number;
  }) => api.post<DownloadCreateResponse>('/downloads/', {
    ...data,
    media_type: mapMediaType(data.media_type),
  }),
  
  cancelDownload: (id: number, deleteFiles?: boolean) =>
    api.delete<CancelDownloadResponse>(`/downloads/${id}`, { params: { delete_files: deleteFiles } }),

  pauseDownload: (id: number) =>
    api.post<MessageResponse>(`/downloads/${id}/pause`),

  resumeDownload: (id: number) =>
    api.post<MessageResponse>(`/downloads/${id}/resume`),

  clearDownloads: (deleteFiles?: boolean) =>
    api.delete<ClearDownloadsResponse>('/downloads/', { params: { delete_files: deleteFiles } }),
};

export const settingsAPI = {
  getSettings: () => api.get<SettingsResponse>('/settings'),
  updateSetting: (key: string, value: string) =>
    api.put<SettingUpdateResponse>(`/settings/${key}`, value),
};

export const filesystemAPI = {
  getRoot: () => api.get<RootResponse>('/filesystem/root'),
  getDirs: (path: string) => api.get<DirsResponse>('/filesystem/dirs', { params: { path } }),
  getDiskSpace: () => api.get<DiskSpaceResponse>('/filesystem/disk-space/'),
};

export const logsAPI = {
  getLogs: (params?: { level?: string; lines?: number; search?: string }) =>
    api.get<LogsResponse>('/logs/', { params }),
};

export const discoverAPI = {
  getSections: () => api.get<SectionCatalog>('/discover/sections/'),

  getSection: (id: string) => api.get<DiscoverSection>(`/discover/sections/${id}/`),

  getGenres: () => api.get<Genre[]>('/discover/genres/'),

  getProviders: () => api.get<StreamingProvider[]>('/discover/providers/'),
};

export const listsAPI = {
  getStatus: (mediaType: UserMediaType, tmdbId: number) =>
    api.get<ListStatus>(`/lists/status/${mapMediaType(mediaType)}/${tmdbId}/`),

  add: (
    kind: ListKind,
    mediaType: UserMediaType,
    tmdbId: number,
    payload?: {
      title: string;
      poster_path: string | null;
      backdrop_path: string | null;
      year: number | null;
    },
  ) => api.post<void>(`/lists/${kind}/${mapMediaType(mediaType)}/${tmdbId}/`, payload ?? null),

  remove: (kind: ListKind, mediaType: UserMediaType, tmdbId: number) =>
    api.delete<void>(`/lists/${kind}/${mapMediaType(mediaType)}/${tmdbId}/`),

  listWatchlist: () => api.get<ListItem[]>('/lists/watchlist/'),
  listWatched: () => api.get<ListItem[]>('/lists/watched/'),
};

export const recommendationsAPI = {
  get: (mediaType: UserMediaType, tmdbId: number, limit = 10) =>
    api.get<Recommendation[]>(`/recommendations/${mapMediaType(mediaType)}/${tmdbId}/`, { params: { limit } }),
};

export default api;
