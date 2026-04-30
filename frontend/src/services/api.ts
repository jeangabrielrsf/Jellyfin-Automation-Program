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
  
  searchTorrents: (params: {
    tmdb_id: number;
    media_type: string;
    season?: number;
    episode?: number;
    quality?: string;
    language?: string;
  }) => api.get('/search/torrents', {
    params: {
      ...params,
      media_type: mapMediaType(params.media_type),
    }
  }),
};

export const downloadAPI = {
  listDownloads: (status?: string) =>
    api.get('/downloads', { params: { status } }),
  
  createDownload: (data: {
    tmdb_id: number;
    title: string;
    media_type: string;
    torrent_name: string;
    magnet_link: string;
    quality?: string;
    language_preference?: string;
    indexer_used?: string;
  }) => api.post('/downloads', {
    ...data,
    media_type: mapMediaType(data.media_type),
  }),
  
  cancelDownload: (id: number) =>
    api.delete(`/downloads/${id}`),

  pauseDownload: (id: number) =>
    api.post(`/downloads/${id}/pause`),

  resumeDownload: (id: number) =>
    api.post(`/downloads/${id}/resume`),
};

export const settingsAPI = {
  getSettings: () => api.get('/settings'),
  updateSetting: (key: string, value: any) =>
    api.put(`/settings/${key}`, value),
};

export const logsAPI = {
  getLogs: (params?: { level?: string; lines?: number; search?: string }) =>
    api.get('/logs', { params }),
};

export default api;
