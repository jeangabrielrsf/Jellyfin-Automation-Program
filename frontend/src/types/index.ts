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
  display_title?: string;
  year?: number;
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
  rt_rating?: string;
  rt_url?: string;
  videos?: {
    results?: Array<{
      key: string;
      site: string;
      type: string;
      name: string;
    }>;
  };
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
  publish_date?: string;
  grabs?: number;
  download_volume_factor?: number;
  files?: number;
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

export interface SectionInfo {
  id: string
  title: string
  media_type: string
}

export interface DiscoverSection extends SectionInfo {
  results: TMDBSearchResult[]
  total_results: number
}

export interface Genre {
  id: number
  name: string
}

export interface StreamingProvider {
  id: number
  name: string
  logo_path: string | null
}

export interface TVEpisode {
  episode_number: number;
  name: string;
  overview: string;
  still_path: string | null;
  air_date: string | null;
  vote_average: number;
  runtime: number | null;
}

export interface TVSeasonDetail {
  id: number;
  name: string;
  season_number: number;
  overview: string;
  episodes: TVEpisode[];
}

export type ListKind = 'watched' | 'watchlist';
export type UserMediaType = 'movie' | 'series' | 'anime';

export interface ListStatus {
  watched: boolean;
  watchlist: boolean;
}

export interface ListItem {
  id: number;
  kind: ListKind;
  media_type: UserMediaType;
  tmdb_id: number;
  title: string;
  poster_path: string | null;
  backdrop_path: string | null;
  year: number | null;
  created_at: string;
}

export interface Recommendation {
  id: number;
  title?: string;
  name?: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  media_type: 'movie' | 'tv';
  genre_ids: number[];
}

export interface TMDBSearchResponse {
  page: number;
  results: TMDBSearchResult[];
  total_pages: number;
  total_results: number;
}

export interface TVSeason {
  season_number: number;
  name: string;
  episode_count: number;
}

export interface AlternativeTitle {
  country: string;
  title: string;
}

export interface DownloadCreateResponse extends Download {
  already_exists?: boolean;
  updated_at?: string;
  completed_at?: string;
}

export interface CancelDownloadResponse {
  message: string;
  files_deleted: boolean;
}

export interface MessageResponse {
  message: string;
}

export interface ClearDownloadsResponse {
  deleted: number;
  skipped: number;
  files_deleted: boolean;
}

export type SettingsResponse = Record<string, string>;

export interface SettingUpdateResponse {
  key: string;
  value: string;
}

export interface RootResponse {
  root: string;
}

export interface DirsResponse {
  path: string;
  dirs: string[];
  parent: string | null;
}

export interface DiskSpaceResponse {
  total_bytes: number;
  free_bytes: number;
  used_bytes: number;
  disks_count: number;
}

export interface LogsResponse {
  logs: string[];
  total: number;
  returned: number;
}

export interface SectionCatalog {
  banner?: BannerMedia;
  sections: SectionInfo[];
}

export interface BannerMedia {
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
  genres: string[];
  providers: string[];
  runtime?: number;
  display_title?: string;
  year?: number;
}
