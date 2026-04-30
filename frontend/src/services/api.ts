import axios from 'axios';
// Types used implicitly by API consumers

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
  
  searchTorrents: (params: {
    tmdb_id: number;
    title: string;
    type: string;
    quality?: string;
    language?: string;
  }) => api.get('/search/torrents', { params }),
};

export const downloadAPI = {
  listDownloads: (status?: string) =>
    api.get('/downloads', { params: { status } }),
  
  createDownload: (data: {
    tmdb_id: number;
    title: string;
    type: string;
    torrent_name: string;
    magnet_link: string;
    quality?: string;
    language_preference?: string;
    indexer_used?: string;
  }) => api.post('/downloads', data),
  
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
