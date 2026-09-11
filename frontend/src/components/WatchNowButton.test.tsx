import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { WatchNowButton } from './WatchNowButton';
import { findWatchableDownload } from '@/lib/watchableDownload';
import type { Download } from '@/types';

const baseDownload: Download = {
  id: 1,
  tmdb_id: 100,
  title: 'Test Movie',
  type: 'movie',
  quality: '1080p',
  language_preference: 'Legendado',
  status: 'completed',
  progress: 100,
  created_at: '2026-01-01T00:00:00Z',
};

const withStatus = (status: string, id = 1): Download => ({ ...baseDownload, id, status });

const renderButton = (downloads: Download[]) =>
  render(
    <MemoryRouter>
      <WatchNowButton downloads={downloads} />
    </MemoryRouter>
  );

describe('WatchNowButton', () => {
  it('renders an Assistir link for a completed download', () => {
    renderButton([withStatus('completed')]);

    const link = screen.getByRole('link', { name: /assistir/i });
    expect(link).toHaveAttribute('href', '/watch/1');
  });

  it('renders an Assistir link for an organized download', () => {
    renderButton([withStatus('organized')]);

    const link = screen.getByRole('link', { name: /assistir/i });
    expect(link).toHaveAttribute('href', '/watch/1');
  });

  it('does not render for unwatchable statuses', () => {
    const unwatchable = ['pending', 'downloading', 'failed', 'cancelled', 'cleared'];

    for (const status of unwatchable) {
      renderButton([withStatus(status)]);
      expect(screen.queryByRole('link', { name: /assistir/i })).not.toBeInTheDocument();
    }
  });

  it('does not render when there are no downloads', () => {
    renderButton([]);

    expect(screen.queryByRole('link', { name: /assistir/i })).not.toBeInTheDocument();
  });

  it('does not render when only unwatchable downloads exist', () => {
    renderButton([withStatus('pending'), withStatus('failed', 2)]);

    expect(screen.queryByRole('link', { name: /assistir/i })).not.toBeInTheDocument();
  });

  it('links to the first watchable download when several exist', () => {
    renderButton([withStatus('downloading', 7), withStatus('organized', 8), withStatus('completed', 9)]);

    const link = screen.getByRole('link', { name: /assistir/i });
    expect(link).toHaveAttribute('href', '/watch/8');
  });
});

describe('findWatchableDownload', () => {
  it('returns the first completed/organized download, skipping unwatchable ones', () => {
    const downloads = [withStatus('pending', 1), withStatus('organized', 2), withStatus('completed', 3)];
    expect(findWatchableDownload(downloads)?.id).toBe(2);
  });

  it('returns null when nothing is watchable', () => {
    expect(findWatchableDownload([withStatus('pending'), withStatus('cleared')])).toBeNull();
  });

  it('returns null for an empty list', () => {
    expect(findWatchableDownload([])).toBeNull();
  });
});
