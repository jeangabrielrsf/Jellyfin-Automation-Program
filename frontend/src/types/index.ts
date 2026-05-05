export interface TMDBSearchResult {
  id: number;
  title?: string;
  name?: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  media_type: string;
  genre_ids: number[];
}

export interface TMDBDetail {
  id: number;
  title?: string;
  original_title?: string;
  name?: string;
  original_name?: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  genres: Array<{ id: number; name: string }>;
  runtime?: number;
  number_of_seasons?: number;
  number_of_episodes?: number;
  status?: string;
  tagline?: string;
  display_title: string;
  year?: number;
}

export interface TorrentResult {
  title: string;
  indexer: string;
  size: string;
  seeds: number;
  peers: number;
  download_url: string;
  magnet_url?: string;
  quality?: string;
  language?: string;
  release_group?: string;
  score: number;
}

export interface Download {
  id: number;
  tmdb_id: number;
  title: string;
  type: 'movie' | 'series' | 'anime';
  torrent_name?: string;
  torrent_hash?: string;
  magnet_link?: string;
  quality: string;
  language_preference: string;
  status: string;
  progress: number;
  speed?: string;
  eta?: string;
  source_folder?: string;
  destination_folder?: string;
  indexer_used?: string;
  size?: string;
  seeds?: number;
  peers?: number;
  season?: number;
  episode?: number;
  error_message?: string;
  created_at: string;
}

export interface AppSettings {
  movies_path: string;
  series_path: string;
  animes_path: string;
  default_quality: string;
  default_language: string;
  qbittorrent_host: string;
  jackett_url: string;
  jellyfin_url: string;
  log_level: string;
}
