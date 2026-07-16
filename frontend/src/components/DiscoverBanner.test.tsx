import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DiscoverBanner } from './DiscoverBanner';
import type { TMDBSearchResult } from '@/types';
import { BrowserRouter } from 'react-router-dom';

const mockMedia: TMDBSearchResult = {
  id: 123,
  title: 'Test Movie',
  overview: 'This is a test movie overview with some details.',
  poster_path: '/poster.jpg',
  backdrop_path: '/backdrop.jpg',
  release_date: '2024-01-15',
  vote_average: 8.5,
  media_type: 'movie',
  genre_ids: [28, 12],
  display_title: 'Test Movie',
  year: 2024,
};

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('DiscoverBanner', () => {
  it('renders nothing when media is null', () => {
    const { container } = renderWithRouter(<DiscoverBanner media={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders backdrop image', () => {
    renderWithRouter(<DiscoverBanner media={mockMedia} />);
    const img = screen.getByAltText('Test Movie');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://image.tmdb.org/t/p/original/backdrop.jpg');
  });

  it('renders title', () => {
    renderWithRouter(<DiscoverBanner media={mockMedia} />);
    expect(screen.getByText('Test Movie')).toBeInTheDocument();
  });

  it('renders year', () => {
    renderWithRouter(<DiscoverBanner media={mockMedia} />);
    expect(screen.getByText('2024')).toBeInTheDocument();
  });

  it('renders vote average', () => {
    renderWithRouter(<DiscoverBanner media={mockMedia} />);
    expect(screen.getByText('8.5')).toBeInTheDocument();
  });

  it('renders overview', () => {
    renderWithRouter(<DiscoverBanner media={mockMedia} />);
    expect(screen.getByText('This is a test movie overview with some details.')).toBeInTheDocument();
  });

  it('renders "Ver detalhes" button', () => {
    renderWithRouter(<DiscoverBanner media={mockMedia} />);
    expect(screen.getByRole('button', { name: /ver detalhes/i })).toBeInTheDocument();
  });

  it('renders fallback when backdrop_path is null', () => {
    const mediaWithoutBackdrop = { ...mockMedia, backdrop_path: null };
    renderWithRouter(<DiscoverBanner media={mediaWithoutBackdrop} />);
    const img = screen.queryByAltText('Test Movie');
    expect(img).not.toBeInTheDocument();
  });

  it('uses name for TV shows', () => {
    const tvMedia: TMDBSearchResult = {
      ...mockMedia,
      title: undefined,
      name: 'Test Series',
      media_type: 'tv',
      first_air_date: '2024-03-10',
      display_title: 'Test Series',
    };
    renderWithRouter(<DiscoverBanner media={tvMedia} />);
    expect(screen.getByText('Test Series')).toBeInTheDocument();
  });
});
