import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';
import * as api from '@/services/api';
import type { TMDBDetail, Download } from '@/types';
import DetailPage from './Detail';

vi.mock('@/services/api', () => ({
  searchAPI: {
    getMovieDetail: vi.fn(),
    getTVDetail: vi.fn(),
    getMovieAlternativeTitles: vi.fn(),
    getTVAlternativeTitles: vi.fn(),
    searchTorrents: vi.fn(),
  },
  downloadAPI: {
    listDownloads: vi.fn(),
  },
  listsAPI: {
    getStatus: vi.fn(),
  },
  recommendationsAPI: {
    get: vi.fn(),
  },
}));

function mockResponse<T>(data: T): AxiosResponse<T> {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as AxiosResponse['config'] };
}

const movieDetail: TMDBDetail = {
  id: 100,
  title: 'Test Movie',
  original_title: 'Test Movie',
  overview: 'A test movie overview',
  poster_path: '/poster.jpg',
  backdrop_path: '/backdrop.jpg',
  release_date: '2023-01-15',
  vote_average: 8.0,
  genres: [{ id: 28, name: 'Action' }],
  display_title: 'Test Movie',
  year: 2023,
};

const download = (status: string, id = 1): Download => ({
  id,
  tmdb_id: 100,
  title: 'Test Movie',
  type: 'movie',
  quality: '1080p',
  language_preference: 'Legendado',
  status,
  progress: 100,
  created_at: '2026-01-01T00:00:00Z',
});

const createQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderDetail = () => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/detail/movie/100']}>
        <Routes>
          <Route path="/detail/:mediaType/:id" element={<DetailPage />} />
          <Route path="/watch/:downloadId" element={<div>Watch page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('DetailPage watch button', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.searchAPI.getMovieDetail).mockResolvedValue(mockResponse(movieDetail));
    vi.mocked(api.searchAPI.getMovieAlternativeTitles).mockResolvedValue(mockResponse([]));
    vi.mocked(api.searchAPI.searchTorrents).mockResolvedValue(mockResponse([]));
    vi.mocked(api.listsAPI.getStatus).mockResolvedValue(mockResponse({ watched: false, watchlist: false }));
    vi.mocked(api.recommendationsAPI.get).mockResolvedValue(mockResponse([]));
  });

  it('shows an Assistir button navigating to /watch/:downloadId when a download is COMPLETED', async () => {
    vi.mocked(api.downloadAPI.listDownloads).mockResolvedValue(mockResponse([download('completed')]));

    renderDetail();

    const link = await screen.findByRole('link', { name: /assistir/i });
    expect(link).toHaveAttribute('href', '/watch/1');
    expect(api.downloadAPI.listDownloads).toHaveBeenCalledWith({ tmdb_id: 100 });
  });

  it('shows an Assistir button when a download is ORGANIZED', async () => {
    vi.mocked(api.downloadAPI.listDownloads).mockResolvedValue(mockResponse([download('organized')]));

    renderDetail();

    expect(await screen.findByRole('link', { name: /assistir/i })).toBeInTheDocument();
  });

  it('does not show an Assistir button when downloads are still active', async () => {
    vi.mocked(api.downloadAPI.listDownloads).mockResolvedValue(
      mockResponse([download('downloading'), download('pending', 2)])
    );

    renderDetail();

    await screen.findByText('Test Movie');
    expect(screen.queryByRole('link', { name: /assistir/i })).not.toBeInTheDocument();
  });

  it('does not show an Assistir button when downloads failed or were cancelled', async () => {
    vi.mocked(api.downloadAPI.listDownloads).mockResolvedValue(
      mockResponse([download('failed', 1), download('cancelled', 2), download('cleared', 3)])
    );

    renderDetail();

    await screen.findByText('Test Movie');
    expect(screen.queryByRole('link', { name: /assistir/i })).not.toBeInTheDocument();
  });

  it('does not show an Assistir button when there are no downloads', async () => {
    vi.mocked(api.downloadAPI.listDownloads).mockResolvedValue(mockResponse([]));

    renderDetail();

    await screen.findByText('Test Movie');
    expect(screen.queryByRole('link', { name: /assistir/i })).not.toBeInTheDocument();
  });
});
