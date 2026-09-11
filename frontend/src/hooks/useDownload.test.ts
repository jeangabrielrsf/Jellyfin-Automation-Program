import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AxiosResponse } from 'axios';
import { useDownload } from './useDownload';
import { TorrentResult } from '@/types';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

vi.mock('@/services/api', () => ({
  downloadAPI: {
    createDownload: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

import { downloadAPI } from '@/services/api';
import { toast } from 'sonner';

const mockedCreateDownload = vi.mocked(downloadAPI.createDownload);
const mockedToastSuccess = vi.mocked(toast.success);
const mockedToastError = vi.mocked(toast.error);
const mockedToastInfo = vi.mocked(toast.info);

function mockResponse(data: Record<string, unknown> = {}): AxiosResponse {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as AxiosResponse['config'] };
}

function makeTorrent(overrides: Partial<TorrentResult> = {}): TorrentResult {
  return {
    title: 'Test Torrent',
    indexer: 'TestIndexer',
    size: '1.5 GB',
    seeds: 10,
    peers: 5,
    download_url: 'http://example.com/torrent',
    score: 80,
    quality: '1080p',
    language: 'Legendado',
    download_volume_factor: 1,
    publish_date: '2024-01-15',
    ...overrides,
  };
}

const defaultParams = {
  tmdbId: 123,
  detail: { data: { display_title: 'Test Movie' } } as { data?: { display_title?: string } },
  effectiveMediaType: 'movie',
  selectedSeason: '' as number | '',
  selectedEpisode: 'temporada-inteira' as number | 'temporada-inteira',
};

describe('useDownload', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('returns an empty downloadingTorrents set', () => {
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });
      expect(result.current.downloadingTorrents.size).toBe(0);
    });

    it('returns handleDownload function', () => {
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });
      expect(typeof result.current.handleDownload).toBe('function');
    });
  });

  describe('handleDownload - success', () => {
    it('calls downloadAPI.createDownload with correct payload for movie', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent({ magnet_url: 'magnet:?xt=...' });
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith({
        tmdb_id: 123,
        title: 'Test Movie',
        media_type: 'movie',
        torrent_name: 'Test Torrent',
        magnet_link: 'magnet:?xt=...',
        download_url: 'http://example.com/torrent',
        quality: '1080p',
        language_preference: 'Legendado',
        indexer_used: 'TestIndexer',
        size: '1.5 GB',
        seeds: 10,
        peers: 5,
        season: undefined,
        episode: undefined,
      });
    });

    it('shows success toast on successful download', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedToastSuccess).toHaveBeenCalledWith('Download iniciado com sucesso!');
    });

    it('shows info toast when already_exists is true', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse({ already_exists: true }));
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedToastInfo).toHaveBeenCalledWith('Torrent já estava na fila de downloads');
      expect(mockedToastSuccess).not.toHaveBeenCalled();
    });
  });

  describe('handleDownload - error', () => {
    it('shows error toast on API failure', async () => {
      mockedCreateDownload.mockRejectedValueOnce(new Error('Network error'));
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedToastError).toHaveBeenCalledWith('Erro ao iniciar download.');
    });
  });

  describe('downloadingTorrents state management', () => {
    it('adds torrent key to set during download', async () => {
      let resolvePromise: (value: AxiosResponse) => void;
      const pendingPromise = new Promise<AxiosResponse>((resolve) => { resolvePromise = resolve; });
      mockedCreateDownload.mockReturnValueOnce(pendingPromise);

      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      let downloadPromise: Promise<void>;
      act(() => {
        downloadPromise = result.current.handleDownload(torrent);
      });

      expect(result.current.downloadingTorrents.has('Test TorrentTestIndexer')).toBe(true);

      await act(async () => {
        resolvePromise!(mockResponse());
        await downloadPromise;
      });

      expect(result.current.downloadingTorrents.has('Test TorrentTestIndexer')).toBe(false);
    });

    it('removes torrent key from set after successful download', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(result.current.downloadingTorrents.size).toBe(0);
    });

    it('removes torrent key from set after failed download', async () => {
      mockedCreateDownload.mockRejectedValueOnce(new Error('fail'));
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(result.current.downloadingTorrents.size).toBe(0);
    });

    it('prevents duplicate downloads for same torrent', async () => {
      let resolvePromise: (value: AxiosResponse) => void;
      const pendingPromise = new Promise<AxiosResponse>((resolve) => { resolvePromise = resolve; });
      mockedCreateDownload.mockReturnValueOnce(pendingPromise);

      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      let firstDownload: Promise<void>;
      act(() => {
        firstDownload = result.current.handleDownload(torrent);
      });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledTimes(1);

      await act(async () => {
        resolvePromise!(mockResponse());
        await firstDownload;
      });
    });
  });

  describe('payload construction', () => {
    it('includes season and episode for TV series', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload({
        ...defaultParams,
        effectiveMediaType: 'series',
        selectedSeason: 2,
        selectedEpisode: 5,
      }), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith(
        expect.objectContaining({
          media_type: 'series',
          season: 2,
          episode: 5,
        })
      );
    });

    it('omits episode when selectedEpisode is temporada-inteira', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload({
        ...defaultParams,
        effectiveMediaType: 'series',
        selectedSeason: 1,
        selectedEpisode: 'temporada-inteira',
      }), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith(
        expect.objectContaining({
          season: 1,
          episode: undefined,
        })
      );
    });

    it('uses empty string for title when detail has no display_title', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent();
      const { result } = renderHook(() => useDownload({
        ...defaultParams,
        detail: undefined,
      }), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith(
        expect.objectContaining({ title: '' })
      );
    });

    it('passes undefined for magnet_link when torrent has no magnet_url', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent({ magnet_url: undefined });
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith(
        expect.objectContaining({ magnet_link: undefined })
      );
    });

    it('defaults quality to 1080p when torrent has no quality', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent({ quality: undefined });
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith(
        expect.objectContaining({ quality: '1080p' })
      );
    });

    it('defaults language_preference to legendado when torrent has no language', async () => {
      mockedCreateDownload.mockResolvedValueOnce(mockResponse());
      const torrent = makeTorrent({ language: undefined });
      const { result } = renderHook(() => useDownload(defaultParams), { wrapper });

      await act(async () => {
        await result.current.handleDownload(torrent);
      });

      expect(mockedCreateDownload).toHaveBeenCalledWith(
        expect.objectContaining({ language_preference: 'legendado' })
      );
    });
  });
});
