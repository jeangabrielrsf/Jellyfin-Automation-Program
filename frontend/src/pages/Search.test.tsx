import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';
import SearchPage from './Search';
import * as api from '@/services/api';
import type { TMDBSearchResponse } from '@/types';

vi.mock('@/services/api', () => ({
  searchAPI: {
    searchMedia: vi.fn(),
  },
}));

function mockResponse(data: TMDBSearchResponse): AxiosResponse<TMDBSearchResponse> {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as AxiosResponse['config'] };
}

const mockResults = [
  {
    id: 1,
    title: 'Test Movie',
    overview: 'Test overview',
    poster_path: '/poster.jpg',
    backdrop_path: null,
    release_date: '2023-01-15',
    vote_average: 8.0,
    media_type: 'movie',
    genre_ids: [28],
  },
];

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

describe('SearchPage', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('renders page title', () => {
    renderWithProviders(<SearchPage />);
    
    expect(screen.getByText('Buscar Conteúdo')).toBeInTheDocument();
  });

  it('renders tabs with Texto and Filtros', () => {
    renderWithProviders(<SearchPage />);
    
    expect(screen.getByRole('tab', { name: /texto/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /filtros/i })).toBeInTheDocument();
  });

  it('has Texto tab active by default', () => {
    renderWithProviders(<SearchPage />);
    
    const textoTab = screen.getByRole('tab', { name: /texto/i });
    expect(textoTab).toHaveAttribute('data-state', 'active');
  });

  it('renders search bar', () => {
    renderWithProviders(<SearchPage />);
    
    expect(screen.getByPlaceholderText(/buscar filmes/i)).toBeInTheDocument();
  });

  it('shows empty state when no search performed', () => {
    renderWithProviders(<SearchPage />);
    
    expect(screen.getByText(/comece digitando/i)).toBeInTheDocument();
  });

  it('shows empty state with suggestions when no results found', async () => {
    vi.mocked(api.searchAPI.searchMedia).mockResolvedValue(
      mockResponse({ page: 1, results: [], total_pages: 0, total_results: 0 })
    );
    
    renderWithProviders(<SearchPage />);
    
    const searchInput = screen.getByPlaceholderText(/buscar filmes/i);
    const searchButton = screen.getByRole('button', { name: /buscar/i });
    
    fireEvent.change(searchInput, { target: { value: 'nonexistent movie xyz' } });
    fireEvent.click(searchButton);
    
    await waitFor(() => {
      expect(screen.getByText(/nenhum resultado encontrado/i)).toBeInTheDocument();
    });
  });

  it('shows search results when query is submitted', async () => {
    vi.mocked(api.searchAPI.searchMedia).mockResolvedValue(
      mockResponse({ page: 1, results: mockResults, total_pages: 1, total_results: 1 })
    );
    
    renderWithProviders(<SearchPage />);
    
    const searchInput = screen.getByPlaceholderText(/buscar filmes/i);
    const searchButton = screen.getByRole('button', { name: /buscar/i });
    
    fireEvent.change(searchInput, { target: { value: 'test movie' } });
    fireEvent.click(searchButton);
    
    await waitFor(() => {
      expect(screen.getByText('Test Movie')).toBeInTheDocument();
    });
  });

  it('has Filtros tab available', () => {
    renderWithProviders(<SearchPage />);
    
    const filtrosTab = screen.getByRole('tab', { name: /filtros/i });
    expect(filtrosTab).toBeInTheDocument();
  });

  it('shows placeholder content in Filtros tab', () => {
    renderWithProviders(<SearchPage />);
    
    const filtrosTab = screen.getByRole('tab', { name: /filtros/i });
    expect(filtrosTab).toBeInTheDocument();
    expect(filtrosTab).toHaveAttribute('data-state', 'inactive');
  });

  it('restores search state from session storage', async () => {
    sessionStorage.setItem('search_state', JSON.stringify({ query: 'saved query', scrollY: 0 }));
    vi.mocked(api.searchAPI.searchMedia).mockResolvedValue(
      mockResponse({ page: 1, results: mockResults, total_pages: 1, total_results: 1 })
    );
    
    renderWithProviders(<SearchPage />);
    
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText(/buscar filmes/i) as HTMLInputElement;
      expect(searchInput.value).toBe('saved query');
    });
  });
});
