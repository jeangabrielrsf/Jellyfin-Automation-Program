import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SearchResults } from './SearchResults';
import type { TMDBSearchResult } from '@/types';

const mockResults: TMDBSearchResult[] = Array.from({ length: 25 }, (_, i) => ({
  id: i + 1,
  title: `Movie ${i + 1}`,
  overview: `Overview for movie ${i + 1}`,
  poster_path: `/poster${i + 1}.jpg`,
  backdrop_path: null,
  release_date: '2023-01-15',
  vote_average: 7.5,
  media_type: 'movie',
  genre_ids: [28],
}));

describe('SearchResults', () => {
  const mockOnClick = vi.fn();

  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('renders results count', () => {
    render(<SearchResults results={mockResults} onMediaClick={mockOnClick} />);
    
    expect(screen.getByText('25 encontrados')).toBeInTheDocument();
  });

  it('renders grid view by default', () => {
    render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    
    const gridButton = screen.getByLabelText('Visualização em grade');
    expect(gridButton).toHaveAttribute('data-active', 'true');
  });

  it('toggles to list view when list button clicked', () => {
    render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    
    const listButton = screen.getByLabelText('Visualização em lista');
    fireEvent.click(listButton);
    
    expect(listButton).toHaveAttribute('data-active', 'true');
  });

  it('shows only first 20 results initially', () => {
    render(<SearchResults results={mockResults} onMediaClick={mockOnClick} />);
    
    expect(screen.getByText('Movie 1')).toBeInTheDocument();
    expect(screen.getByText('Movie 20')).toBeInTheDocument();
    expect(screen.queryByText('Movie 21')).not.toBeInTheDocument();
  });

  it('shows "Load more" button when there are more results', () => {
    render(<SearchResults results={mockResults} onMediaClick={mockOnClick} />);
    
    expect(screen.getByText('Carregar mais')).toBeInTheDocument();
  });

  it('loads more results when "Load more" clicked', () => {
    render(<SearchResults results={mockResults} onMediaClick={mockOnClick} />);
    
    const loadMoreButton = screen.getByText('Carregar mais');
    fireEvent.click(loadMoreButton);
    
    expect(screen.getByText('Movie 21')).toBeInTheDocument();
    expect(screen.getByText('Movie 25')).toBeInTheDocument();
  });

  it('hides "Load more" button after all results loaded', () => {
    render(<SearchResults results={mockResults.slice(0, 15)} onMediaClick={mockOnClick} />);
    
    expect(screen.queryByText('Carregar mais')).not.toBeInTheDocument();
  });

  it('persists view mode in session storage', () => {
    const { unmount } = render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    
    const listButton = screen.getByLabelText('Visualização em lista');
    fireEvent.click(listButton);
    
    unmount();
    
    render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    const listButtonAfter = screen.getByLabelText('Visualização em lista');
    expect(listButtonAfter).toHaveAttribute('data-active', 'true');
  });

  it('calls onMediaClick when a result is clicked', () => {
    render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    
    const firstResult = screen.getByText('Movie 1');
    fireEvent.click(firstResult);
    
    expect(mockOnClick).toHaveBeenCalledWith(mockResults[0]);
  });

  it('renders grid layout with correct columns', () => {
    render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    
    const grid = screen.getByTestId('results-grid');
    expect(grid).toBeInTheDocument();
  });

  it('renders list layout when in list mode', () => {
    render(<SearchResults results={mockResults.slice(0, 5)} onMediaClick={mockOnClick} />);
    
    const listButton = screen.getByLabelText('Visualização em lista');
    fireEvent.click(listButton);
    
    const list = screen.getByTestId('results-list');
    expect(list).toBeInTheDocument();
  });
});
