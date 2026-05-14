import axios from 'axios';
// Types used implicitly by API consumers

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
    api.get(`/search/?q=${encodeURIComponent(query)}&page=${page}`),
  
  getMovieDetail: (id: number) =>
    api.get(`/search/movie/${id}`),
  
  getTVDetail: (id: number) =>
    api.get(`/search/tv/${id}`),

  getTVSeasons: (id: number) =>
    api.get(`/search/tv/${id}/seasons`),

  getTVSeasonDetail: (id: number, seasonNumber: number) =>
    api.get(`/search/tv/${id}/season/${seasonNumber}`),
  
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
    return api.get('/search/torrents', { params: apiParams });
  },
};

export const downloadAPI = {
  listDownloads: (status?: string) =>
    api.get('/downloads/', { params: { status } }),
  
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
  }) => api.post('/downloads/', {
    ...data,
    media_type: mapMediaType(data.media_type),
  }),
  
  cancelDownload: (id: number) =>
    api.delete(`/downloads/${id}`),

  pauseDownload: (id: number) =>
    api.post(`/downloads/${id}/pause`),

  resumeDownload: (id: number) =>
    api.post(`/downloads/${id}/resume`),

  clearDownloads: () =>
    api.delete('/downloads/'),
};

export const settingsAPI = {
  getSettings: () => api.get('/settings'),
  updateSetting: (key: string, value: any) =>
    api.put(`/settings/${key}`, value),
};

export const filesystemAPI = {
  getRoot: () => api.get('/filesystem/root'),
  getDirs: (path: string) => api.get('/filesystem/dirs', { params: { path } }),
};

export const logsAPI = {
  getLogs: (params?: { level?: string; lines?: number; search?: string }) =>
    api.get('/logs/', { params }),
};

export const discoverAPI = {
  getSections: (params?: {
    genre_id?: number | null;
    media_type?: string | null;
    sort_by?: string;
    watch_provider_id?: number | null;
  }) => api.get('/discover/sections/', { params }),

  getSection: (id: string, params?: {
    genre_id?: number | null;
    media_type?: string | null;
    sort_by?: string;
    watch_provider_id?: number | null;
  }) => api.get(`/discover/sections/${id}/`, { params }),

  getGenres: () => api.get('/discover/genres/'),

  getProviders: () => api.get<Array<{ id: number; name: string; logo_path: string | null }>>('/discover/providers/'),
};

export default api;
