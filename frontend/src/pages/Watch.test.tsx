import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';
import type { PlaybackResponse, Download } from '@/types';
import * as api from '@/services/api';
import WatchPage from './Watch';

vi.mock('@/services/api', () => ({
  downloadAPI: {
    getDownload: vi.fn(),
    getPlayback: vi.fn(),
  },
}));

const mockHlsInstances: Array<{
  loadSource: ReturnType<typeof vi.fn>;
  attachMedia: ReturnType<typeof vi.fn>;
  destroy: ReturnType<typeof vi.fn>;
}> = [];

vi.mock('hls.js', () => {
  const mockHls = vi.fn(() => {
    const instance = {
      loadSource: vi.fn(),
      attachMedia: vi.fn(),
      destroy: vi.fn(),
    };
    mockHlsInstances.push(instance);
    return instance;
  });
  (mockHls as unknown as { isSupported: ReturnType<typeof vi.fn> }).isSupported = vi.fn(() => true);
  return { default: mockHls };
});

function mockResponse<T>(data: T): AxiosResponse<T> {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as AxiosResponse['config'] };
}

function mockRejected(status: number, detail: string) {
  return {
    response: { status, data: { detail } },
  };
}

const movieDownload: Download = {
  id: 1,
  tmdb_id: 100,
  title: 'Test Movie',
  type: 'movie',
  quality: '1080p',
  language_preference: 'Legendado',
  status: 'ORGANIZED',
  progress: 100,
  created_at: '2026-01-01T00:00:00Z',
};

const seriesDownload: Download = {
  ...movieDownload,
  id: 2,
  tmdb_id: 200,
  title: 'Test Series',
  type: 'series',
  season: 1,
};

const createQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderWatch = (downloadId: number | string) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/watch/${downloadId}`]}>
        <Routes>
          <Route path="/watch/:downloadId" element={<WatchPage />} />
          <Route path="/detail/:mediaType/:id" element={<div>Detail page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const getVideo = () => screen.getByTestId('watch-video') as HTMLVideoElement;

describe('WatchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHlsInstances.length = 0;
  });

  describe('direct mode', () => {
    it('renders the video player and fetches playback via API', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);

      expect(await screen.findByTestId('watch-video')).toBeInTheDocument();
      expect(api.downloadAPI.getPlayback).toHaveBeenCalledWith(1);
    });

    it('serves the direct file via the video src without instantiating hls.js', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);
      const video = await screen.findByTestId('watch-video') as HTMLVideoElement;

      await vi.waitFor(() => {
        expect(video.getAttribute('src')).toBe('/api/stream/1/playlist.m3u8');
      });
      expect(mockHlsInstances).toHaveLength(0);
    });

    it('shows the media title', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);

      expect(await screen.findByText('Test Movie')).toBeInTheDocument();
    });
  });

  describe('transcode mode', () => {
    it('instantiates hls.js with the playlist url and attaches it to the video', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'transcode',
          files: [{ episode: null, title: 'Test Movie', mode: 'transcode', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);
      const video = await screen.findByTestId('watch-video') as HTMLVideoElement;

      await vi.waitFor(() => {
        expect(mockHlsInstances).toHaveLength(1);
      });

      const hls = mockHlsInstances[0];
      expect(hls.loadSource).toHaveBeenCalledWith('/api/stream/1/playlist.m3u8');
      expect(hls.attachMedia).toHaveBeenCalledWith(video);
    });

    it('destroys the hls instance on unmount', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'transcode',
          files: [{ episode: null, title: 'Test Movie', mode: 'transcode', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      const { unmount } = renderWatch(1);

      await vi.waitFor(() => {
        expect(mockHlsInstances).toHaveLength(1);
      });

      unmount();

      expect(mockHlsInstances[0].destroy).toHaveBeenCalledTimes(1);
    });

    it('switching to another file destroys the previous hls instance and loads the new url', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(seriesDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'transcode',
          files: [
            { episode: 1, title: 'Episódio 1', mode: 'transcode', url: '/api/stream/2/playlist.m3u8?episode=1' },
            { episode: 2, title: 'Episódio 2', mode: 'transcode', url: '/api/stream/2/playlist.m3u8?episode=2' },
          ],
        })
      );

      renderWatch(2);

      await vi.waitFor(() => {
        expect(mockHlsInstances).toHaveLength(1);
      });

      fireEvent.click(screen.getByRole('button', { name: /episódio 2/i }));

      await vi.waitFor(() => {
        expect(mockHlsInstances).toHaveLength(2);
      });

      expect(mockHlsInstances[0].destroy).toHaveBeenCalledTimes(1);
      expect(mockHlsInstances[1].loadSource).toHaveBeenCalledWith('/api/stream/2/playlist.m3u8?episode=2');
    });
  });

  describe('episode sidebar', () => {
    it('shows the episode sidebar when there is more than one file', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(seriesDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [
            { episode: 1, title: 'Episódio 1', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=1' },
            { episode: 2, title: 'Episódio 2', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=2' },
          ],
        })
      );

      renderWatch(2);

      expect(await screen.findByRole('button', { name: /episódio 1/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /episódio 2/i })).toBeInTheDocument();
    });

    it('hides the sidebar for a single file', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);

      await screen.findByTestId('watch-video');

      expect(screen.queryByRole('button', { name: /episódio 1/i })).not.toBeInTheDocument();
    });

    it('switches the direct stream when clicking an episode', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(seriesDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [
            { episode: 1, title: 'Episódio 1', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=1' },
            { episode: 2, title: 'Episódio 2', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=2' },
          ],
        })
      );

      renderWatch(2);

      await vi.waitFor(() => {
        expect(getVideo().getAttribute('src')).toBe('/api/stream/2/playlist.m3u8?episode=1');
      });

      fireEvent.click(screen.getByRole('button', { name: /episódio 2/i }));

      await vi.waitFor(() => {
        expect(getVideo().getAttribute('src')).toBe('/api/stream/2/playlist.m3u8?episode=2');
      });
    });
  });

  describe('subtitles', () => {
    it('attaches the subtitle track when subtitle_url is present', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
          subtitle_url: '/api/stream/1/subtitle.vtt',
        })
      );

      renderWatch(1);

      const video = await screen.findByTestId('watch-video') as HTMLVideoElement;
      const track = video.querySelector('track');
      expect(track).not.toBeNull();
      expect(track?.getAttribute('src')).toBe('/api/stream/1/subtitle.vtt');
    });

    it('does not attach a track without subtitle_url', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);

      const video = await screen.findByTestId('watch-video') as HTMLVideoElement;
      expect(video.querySelector('track')).toBeNull();
    });

    it('swaps the subtitle track src for the active episode in a pack', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(seriesDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [
            { episode: 1, title: 'Episódio 1', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=1' },
            { episode: 2, title: 'Episódio 2', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=2' },
          ],
          subtitle_url: '/api/stream/2/subtitle.vtt?episode=1',
        })
      );

      renderWatch(2);

      await vi.waitFor(() => {
        expect(getVideo().querySelector('track')?.getAttribute('src')).toBe('/api/stream/2/subtitle.vtt?episode=1');
      });

      fireEvent.click(screen.getByRole('button', { name: /episódio 2/i }));

      await vi.waitFor(() => {
        expect(getVideo().querySelector('track')?.getAttribute('src')).toBe('/api/stream/2/subtitle.vtt?episode=2');
      });
    });
  });

  describe('error states', () => {
    it('shows a clear message on 503 (stream limit reached)', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockRejectedValue(mockRejected(503, 'limite de streams atingido'));

      renderWatch(1);

      expect(await screen.findByText(/muitos streams ativos no momento/i)).toBeInTheDocument();
    });

    it('shows a clear message on 404 (file missing / download cleared)', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockRejectedValue(mockRejected(404, 'arquivo não encontrado'));

      renderWatch(1);

      expect(await screen.findByText(/arquivo não encontrado no disco/i)).toBeInTheDocument();
    });

    it('shows the 404 message when the download itself was cleared', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockRejectedValue(mockRejected(404, 'Download not found'));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);

      expect(await screen.findByText(/arquivo não encontrado no disco/i)).toBeInTheDocument();
    });

    it('still offers a way back when the download cannot be loaded', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockRejectedValue(mockRejected(404, 'Download not found'));
      vi.mocked(api.downloadAPI.getPlayback).mockRejectedValue(mockRejected(503, 'limite'));

      renderWatch(1);

      await screen.findByTestId('watch-error');

      expect(screen.getByRole('button', { name: /voltar/i })).toBeInTheDocument();
    });

    it('shows a generic message for other errors', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockRejectedValue(new Error('network down'));

      renderWatch(1);

      expect(await screen.findByText(/não foi possível carregar este conteúdo/i)).toBeInTheDocument();
    });
  });

  describe('back navigation', () => {
    it('links back to the Detail page using the download type and tmdb id', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(movieDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: null, title: 'Test Movie', mode: 'direct', url: '/api/stream/1/playlist.m3u8' }],
        })
      );

      renderWatch(1);
      await screen.findByTestId('watch-video');

      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));

      expect(screen.getByText('Detail page')).toBeInTheDocument();
    });

    it('maps series downloads to the tv detail route', async () => {
      vi.mocked(api.downloadAPI.getDownload).mockResolvedValue(mockResponse(seriesDownload));
      vi.mocked(api.downloadAPI.getPlayback).mockResolvedValue(
        mockResponse<PlaybackResponse>({
          mode: 'direct',
          files: [{ episode: 1, title: 'Episódio 1', mode: 'direct', url: '/api/stream/2/playlist.m3u8?episode=1' }],
        })
      );

      renderWatch(2);
      await screen.findByTestId('watch-video');

      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));

      expect(screen.getByText('Detail page')).toBeInTheDocument();
    });
  });
});
