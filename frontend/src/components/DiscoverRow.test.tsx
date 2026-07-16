import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AxiosResponse } from 'axios';
import { DiscoverRow } from './DiscoverRow';
import type { SectionInfo, DiscoverParams, TMDBSearchResult, DiscoverSection } from '@/types';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  discoverAPI: {
    getSection: vi.fn(),
  },
}));

function mockResponse(data: DiscoverSection): AxiosResponse<DiscoverSection> {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as AxiosResponse['config'] };
}

const mockResults: TMDBSearchResult[] = [
  {
    id: 1,
    title: 'Movie 1',
    overview: 'Overview 1',
    poster_path: '/poster1.jpg',
    backdrop_path: null,
    vote_average: 8.0,
    media_type: 'movie',
    genre_ids: [28],
  },
  {
    id: 2,
    title: 'Movie 2',
    overview: 'Overview 2',
    poster_path: '/poster2.jpg',
    backdrop_path: null,
    vote_average: 7.5,
    media_type: 'movie',
    genre_ids: [28],
  },
];

const mockSection: SectionInfo = {
  id: 'trending',
  title: 'Tendências da Semana',
  media_type: 'mixed',
};

const mockFilters: DiscoverParams = {};

const createQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('DiscoverRow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders skeleton while loading', () => {
    vi.mocked(api.discoverAPI.getSection).mockResolvedValue(
      mockResponse({ id: 'trending', title: 'Tendências da Semana', media_type: 'mixed', results: [], total_results: 0 })
    );

    renderWithProviders(<DiscoverRow section={mockSection} filters={mockFilters} />);
    expect(screen.getByText('Tendências da Semana')).toBeInTheDocument();
    const shimmerElements = document.querySelectorAll('.animate-shimmer');
    expect(shimmerElements.length).toBeGreaterThan(0);
  });

  it('renders section title', async () => {
    vi.mocked(api.discoverAPI.getSection).mockResolvedValue(
      mockResponse({ id: 'trending', title: 'Tendências da Semana', media_type: 'mixed', results: mockResults, total_results: 2 })
    );

    renderWithProviders(<DiscoverRow section={mockSection} filters={mockFilters} />);
    expect(await screen.findByText('Tendências da Semana')).toBeInTheDocument();
  });

  it('renders scroll arrows', async () => {
    vi.mocked(api.discoverAPI.getSection).mockResolvedValue(
      mockResponse({ id: 'trending', title: 'Tendências da Semana', media_type: 'mixed', results: mockResults, total_results: 2 })
    );

    renderWithProviders(<DiscoverRow section={mockSection} filters={mockFilters} />);
    
    const leftArrow = await screen.findByLabelText('scroll left');
    const rightArrow = await screen.findByLabelText('scroll right');
    expect(leftArrow).toBeInTheDocument();
    expect(rightArrow).toBeInTheDocument();
  });

  it('renders nothing on error', async () => {
    vi.mocked(api.discoverAPI.getSection).mockRejectedValue(new Error('API Error'));

    const { container } = renderWithProviders(<DiscoverRow section={mockSection} filters={mockFilters} />);
    await vi.waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });

  it('renders nothing when results are empty', async () => {
    vi.mocked(api.discoverAPI.getSection).mockResolvedValue(
      mockResponse({ id: 'trending', title: 'Tendências da Semana', media_type: 'mixed', results: [], total_results: 0 })
    );

    const { container } = renderWithProviders(<DiscoverRow section={mockSection} filters={mockFilters} />);
    await vi.waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });
});
