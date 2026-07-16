import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DownloadDetailDialog } from './DownloadDetailDialog';
import type { Download } from '@/types';

describe('DownloadDetailDialog', () => {
  const mockDownload: Download = {
    id: 1,
    tmdb_id: 123,
    title: 'Test Movie',
    type: 'movie',
    torrent_name: 'Test.Movie.2024.1080p.BluRay.x264',
    torrent_hash: 'abc123def456',
    magnet_link: 'magnet:?xt=urn:btih:abc123',
    quality: '1080p',
    language_preference: 'Legendado',
    status: 'downloading',
    progress: 0.65,
    speed: '2.5 MB/s',
    eta: '5 min',
    source_folder: '/downloads/movies',
    destination_folder: '/media/movies',
    indexer_used: 'TestIndexer',
    size: '2.5 GB',
    seeds: 15,
    peers: 30,
    season: 1,
    episode: 5,
    created_at: '2024-01-15T10:00:00Z',
  };

  it('renders nothing when download is null', () => {
    render(<DownloadDetailDialog download={null} />);
    expect(screen.queryByText('Detalhes do Download')).not.toBeInTheDocument();
  });

  it('renders dialog content when download is provided', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('Detalhes do Download')).toBeInTheDocument();
    expect(screen.getByText('Test.Movie.2024.1080p.BluRay.x264')).toBeInTheDocument();
  });

  it('displays torrent name', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('Test.Movie.2024.1080p.BluRay.x264')).toBeInTheDocument();
  });

  it('displays status', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('downloading')).toBeInTheDocument();
  });

  it('displays quality', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('1080p')).toBeInTheDocument();
  });

  it('displays language', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('Legendado')).toBeInTheDocument();
  });

  it('displays size', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('2.5 GB')).toBeInTheDocument();
  });

  it('displays seeds and peers', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('15 / 30')).toBeInTheDocument();
  });

  it('displays progress when downloading', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('2.5 MB/s')).toBeInTheDocument();
    expect(screen.getByText('ETA: 5 min')).toBeInTheDocument();
  });

  it('displays source folder when present', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('/downloads/movies')).toBeInTheDocument();
  });

  it('displays destination folder when present', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('/media/movies')).toBeInTheDocument();
  });

  it('displays season and episode when present', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText(/Temporada 1/)).toBeInTheDocument();
    expect(screen.getByText(/Episódio 5/)).toBeInTheDocument();
  });

  it('displays magnet link when present', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('magnet:?xt=urn:btih:abc123')).toBeInTheDocument();
  });

  it('displays indexer when present', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('TestIndexer')).toBeInTheDocument();
  });

  it('displays error message when present', () => {
    const downloadWithError: Download = {
      ...mockDownload,
      status: 'failed',
      error_message: 'Connection timeout',
    };
    render(<DownloadDetailDialog download={downloadWithError} />);
    expect(screen.getByText('Erro')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  it('displays created at date', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText(/15\/01\/2024/)).toBeInTheDocument();
  });

  it('displays hash', () => {
    render(<DownloadDetailDialog download={mockDownload} />);
    expect(screen.getByText('abc123def456')).toBeInTheDocument();
  });

  it('displays placeholder when torrent name is missing', () => {
    const downloadWithoutName: Download = { ...mockDownload, torrent_name: undefined };
    render(<DownloadDetailDialog download={downloadWithoutName} />);
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });
});
