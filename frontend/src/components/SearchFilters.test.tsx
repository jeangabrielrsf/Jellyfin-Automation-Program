import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';
import { SearchFilters } from './SearchFilters';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  searchAPI: {
    discoverMedia: vi.fn(),
  },
  discoverAPI: {
    getGenres: vi.fn(),
    getProviders: vi.fn(),
  },
}));

function mockResponse<T>(data: T): AxiosResponse<T> {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as AxiosResponse['config'] };
}

const mockGenres = [
  { id: 28, name: 'Action' },
  { id: 12, name: 'Adventure' },
];

const mockProviders = [
  { id: 8, name: 'Netflix', logo_path: '/netflix.png' },
];

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

describe('SearchFilters', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
    vi.mocked(api.discoverAPI.getGenres).mockResolvedValue(mockResponse(mockGenres));
    vi.mocked(api.discoverAPI.getProviders).mockResolvedValue(mockResponse(mockProviders));
  });

  it('renders filter section with title', () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    expect(screen.getByText('Filtros')).toBeInTheDocument();
  });

  it('renders apply and clear buttons', () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    expect(screen.getByRole('button', { name: /aplicar filtros/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /limpar filtros/i })).toBeInTheDocument();
  });

  it('renders media type select with options', () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const select = screen.getByRole('combobox', { name: /tipo de midia/i });
    expect(select).toBeInTheDocument();
    expect(screen.getByText('Todos')).toBeInTheDocument();
    expect(screen.getByText('Filme')).toBeInTheDocument();
    expect(screen.getByText('Serie')).toBeInTheDocument();
    expect(screen.getByText('Anime')).toBeInTheDocument();
  });

  it('renders year range inputs', () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    expect(screen.getByPlaceholderText('De')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ate')).toBeInTheDocument();
  });

  it('renders sort by select with options', () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const select = screen.getByRole('combobox', { name: /ordenacao/i });
    expect(select).toBeInTheDocument();
    expect(screen.getByText('Popularidade')).toBeInTheDocument();
    expect(screen.getByText('Nota')).toBeInTheDocument();
    expect(screen.getByText('Votos')).toBeInTheDocument();
    expect(screen.getByText('Lancamento')).toBeInTheDocument();
    expect(screen.getByText('Titulo')).toBeInTheDocument();
  });

  it('validates year range (from must be <= to)', () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const yearFromInput = screen.getByPlaceholderText('De');
    const yearToInput = screen.getByPlaceholderText('Ate');
    
    fireEvent.change(yearFromInput, { target: { value: '2020' } });
    fireEvent.change(yearToInput, { target: { value: '2010' } });
    
    const applyButton = screen.getByRole('button', { name: /aplicar filtros/i });
    expect(applyButton).toBeDisabled();
  });

  it('calls discoverMedia when apply button is clicked', async () => {
    vi.mocked(api.searchAPI.discoverMedia).mockResolvedValue(
      mockResponse({ page: 1, results: mockResults, total_pages: 1, total_results: 1 })
    );
    
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const applyButton = screen.getByRole('button', { name: /aplicar filtros/i });
    fireEvent.click(applyButton);
    
    await waitFor(() => {
      expect(api.searchAPI.discoverMedia).toHaveBeenCalled();
    });
  });

  it('shows results after successful search', async () => {
    vi.mocked(api.searchAPI.discoverMedia).mockResolvedValue(
      mockResponse({ page: 1, results: mockResults, total_pages: 1, total_results: 1 })
    );
    
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const applyButton = screen.getByRole('button', { name: /aplicar filtros/i });
    fireEvent.click(applyButton);
    
    await waitFor(() => {
      expect(screen.getByText('Test Movie')).toBeInTheDocument();
    });
  });

  it('shows empty state when no results found', async () => {
    vi.mocked(api.searchAPI.discoverMedia).mockResolvedValue(
      mockResponse({ page: 1, results: [], total_pages: 0, total_results: 0 })
    );
    
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const applyButton = screen.getByRole('button', { name: /aplicar filtros/i });
    fireEvent.click(applyButton);
    
    await waitFor(() => {
      expect(screen.getByText(/nenhum resultado encontrado/i)).toBeInTheDocument();
    });
  });

  it('clears filters when clear button is clicked', async () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const yearFromInput = screen.getByPlaceholderText('De') as HTMLInputElement;
    fireEvent.change(yearFromInput, { target: { value: '2020' } });
    
    const clearButton = screen.getByRole('button', { name: /limpar filtros/i });
    fireEvent.click(clearButton);
    
    await waitFor(() => {
      expect(yearFromInput.value).toBe('');
    });
  });

  it('persists filter state in sessionStorage', async () => {
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    const mediaTypeSelect = screen.getByRole('combobox', { name: /tipo de midia/i });
    fireEvent.change(mediaTypeSelect, { target: { value: 'movie' } });
    
    await waitFor(() => {
      const saved = sessionStorage.getItem('search_filters_state');
      expect(saved).toBeTruthy();
      const parsed = JSON.parse(saved!);
      expect(parsed.mediaType).toBe('movie');
    });
  });

  it('restores filter state from sessionStorage on mount', async () => {
    sessionStorage.setItem('search_filters_state', JSON.stringify({
      mediaType: 'series',
      genreIds: [28],
      providerIds: [],
      yearFrom: '2020',
      yearTo: '2023',
      minRating: '7.0',
      sortBy: 'vote_average.desc',
    }));
    
    renderWithProviders(<SearchFilters onMediaClick={() => {}} />);
    
    await waitFor(() => {
      const mediaTypeSelect = screen.getByRole('combobox', { name: /tipo de midia/i }) as HTMLSelectElement;
      expect(mediaTypeSelect.value).toBe('series');
    });
  });
});
