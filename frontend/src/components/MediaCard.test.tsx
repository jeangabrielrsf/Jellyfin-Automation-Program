import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MediaCard } from './MediaCard';
import type { TMDBSearchResult } from '@/types';

const mockMovie: TMDBSearchResult = {
  id: 1,
  title: 'Test Movie',
  name: undefined,
  overview: 'This is a test movie overview that should appear in list view',
  poster_path: '/test-poster.jpg',
  backdrop_path: null,
  release_date: '2023-01-15',
  first_air_date: undefined,
  vote_average: 8.5,
  media_type: 'movie',
  genre_ids: [28, 12],
};

const mockSeries: TMDBSearchResult = {
  id: 2,
  title: undefined,
  name: 'Test Series',
  overview: 'This is a test series overview',
  poster_path: '/test-poster.jpg',
  backdrop_path: null,
  release_date: undefined,
  first_air_date: '2022-05-20',
  vote_average: 7.8,
  media_type: 'tv',
  genre_ids: [18],
};

const mockNoPoster: TMDBSearchResult = {
  id: 3,
  title: 'No Poster Movie',
  overview: 'Movie without poster',
  poster_path: null,
  backdrop_path: null,
  release_date: '2024-01-01',
  vote_average: 6.0,
  media_type: 'movie',
  genre_ids: [],
};

describe('MediaCard', () => {
  const mockOnClick = vi.fn();

  it('renders movie title and year in grid view', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="grid" />);
    
    expect(screen.getByText('Test Movie')).toBeInTheDocument();
    expect(screen.getByText('2023')).toBeInTheDocument();
    expect(screen.getByText('8.5')).toBeInTheDocument();
  });

  it('renders series name and year in grid view', () => {
    render(<MediaCard media={mockSeries} onClick={mockOnClick} variant="grid" />);
    
    expect(screen.getByText('Test Series')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
  });

  it('renders type badge for movie', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="grid" />);
    
    expect(screen.getByText('Filme')).toBeInTheDocument();
  });

  it('renders type badge for series', () => {
    render(<MediaCard media={mockSeries} onClick={mockOnClick} variant="grid" />);
    
    expect(screen.getByText('Série')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="grid" />);
    
    const card = screen.getByText('Test Movie').closest('[class*="cursor-pointer"]');
    if (card) {
      fireEvent.click(card);
    }
    
    expect(mockOnClick).toHaveBeenCalledWith(mockMovie);
  });

  it('renders placeholder when no poster in grid view', () => {
    render(<MediaCard media={mockNoPoster} onClick={mockOnClick} variant="grid" />);
    
    expect(screen.getByText('Sem imagem')).toBeInTheDocument();
  });

  it('renders horizontal layout in list view', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="list" />);
    
    expect(screen.getByText('Test Movie')).toBeInTheDocument();
    expect(screen.getByText('2023')).toBeInTheDocument();
    expect(screen.getByText('8.5')).toBeInTheDocument();
  });

  it('renders overview in list view', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="list" />);
    
    expect(screen.getByText(/This is a test movie overview/)).toBeInTheDocument();
  });

  it('renders genre chips in list view', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="list" />);
    
    expect(screen.getByText('Ação')).toBeInTheDocument();
    expect(screen.getByText('Aventura')).toBeInTheDocument();
  });

  it('renders poster image in list view', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} variant="list" />);
    
    const img = screen.getByAltText('Test Movie');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://image.tmdb.org/t/p/w200/test-poster.jpg');
  });

  it('defaults to grid view when variant not specified', () => {
    render(<MediaCard media={mockMovie} onClick={mockOnClick} />);
    
    expect(screen.getByText('Test Movie')).toBeInTheDocument();
  });
});
