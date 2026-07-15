import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useTorrentFilters } from './useTorrentFilters';
import { TorrentResult } from '@/types';

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

const sampleTorrents: TorrentResult[] = [
  makeTorrent({ title: 'Movie.2024.1080p', quality: '1080p', language: 'Legendado', seeds: 50, score: 90, size: '2.0 GB' }),
  makeTorrent({ title: 'Movie.2024.720p', quality: '720p', language: 'Dublado', seeds: 30, score: 70, size: '1.0 GB' }),
  makeTorrent({ title: 'Movie.2024.2160p', quality: '2160p', language: 'Dual Áudio', seeds: 5, score: 95, size: '5.0 GB' }),
  makeTorrent({ title: 'Movie.2024.Freeleech', quality: '1080p', language: 'Legendado', seeds: 20, score: 85, size: '1.8 GB', download_volume_factor: 0 }),
  makeTorrent({ title: 'Old.Movie.2020', quality: '1080p', language: 'Legendado', seeds: 2, score: 40, size: '1.2 GB', publish_date: '2020-06-01' }),
];

describe('useTorrentFilters', () => {
  describe('default state', () => {
    it('returns default filter values', () => {
      const { result } = renderHook(() => useTorrentFilters([]));

      expect(result.current.preferredQuality).toBe('1080p');
      expect(result.current.preferredLanguage).toBe('legendado');
      expect(result.current.customSearchEnabled).toBe(false);
      expect(result.current.customQuery).toBe('');
      expect(result.current.selectedTitle).toBe('');
      expect(result.current.selectedQualities).toEqual(['1080p']);
      expect(result.current.selectedLanguages).toEqual(['Legendado']);
      expect(result.current.minSeeds).toBe(0);
      expect(result.current.freeleechOnly).toBe(false);
      expect(result.current.sortBy).toBe('score');
      expect(result.current.sortOrder).toBe('desc');
      expect(result.current.titleFilter).toBe('');
      expect(result.current.visibleCount).toBe(20);
      expect(result.current.advancedOptionsOpen).toBe(false);
    });

    it('returns empty filtered and visible torrents for empty input', () => {
      const { result } = renderHook(() => useTorrentFilters([]));
      expect(result.current.filteredTorrents).toEqual([]);
      expect(result.current.visibleTorrents).toEqual([]);
      expect(result.current.hasMoreTorrents).toBe(false);
    });
  });

  describe('sync effects: preferredQuality → selectedQualities', () => {
    it('syncs preferredQuality to selectedQualities', () => {
      const { result } = renderHook(() => useTorrentFilters([]));

      act(() => {
        result.current.setPreferredQuality('720p');
      });

      expect(result.current.selectedQualities).toEqual(['720p']);
    });
  });

  describe('sync effects: preferredLanguage → selectedLanguages', () => {
    it('syncs preferredLanguage to selectedLanguages with capitalization', () => {
      const { result } = renderHook(() => useTorrentFilters([]));

      act(() => {
        result.current.setPreferredLanguage('dublado');
      });

      expect(result.current.selectedLanguages).toEqual(['Dublado']);
    });

    it('handles "dual áudio" capitalization', () => {
      const { result } = renderHook(() => useTorrentFilters([]));

      act(() => {
        result.current.setPreferredLanguage('dual áudio');
      });

      expect(result.current.selectedLanguages).toEqual(['Dual áudio']);
    });
  });

  describe('sync effects: reset visibleCount on filter change', () => {
    it('resets visibleCount when selectedQualities changes', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setVisibleCount(2);
      });
      expect(result.current.visibleCount).toBe(2);

      act(() => {
        result.current.setSelectedQualities(['720p']);
      });
      expect(result.current.visibleCount).toBe(20);
    });

    it('resets visibleCount when minSeeds changes', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setVisibleCount(2);
      });

      act(() => {
        result.current.setMinSeeds(10);
      });
      expect(result.current.visibleCount).toBe(20);
    });

    it('resets visibleCount when sortBy changes', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setVisibleCount(2);
      });

      act(() => {
        result.current.setSortBy('seeds');
      });
      expect(result.current.visibleCount).toBe(20);
    });
  });

  describe('filtering', () => {
    it('filters by quality', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSelectedQualities(['720p']);
        result.current.setSelectedLanguages([]);
      });

      expect(result.current.filteredTorrents).toHaveLength(1);
      expect(result.current.filteredTorrents[0].quality).toBe('720p');
    });

    it('filters by multiple qualities', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSelectedQualities(['1080p', '720p']);
        result.current.setSelectedLanguages([]);
      });

      expect(result.current.filteredTorrents).toHaveLength(4);
    });

    it('filters by language', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSelectedLanguages(['Dublado']);
        result.current.setSelectedQualities([]);
      });

      expect(result.current.filteredTorrents).toHaveLength(1);
      expect(result.current.filteredTorrents[0].language).toBe('Dublado');
    });

    it('filters by minSeeds', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setMinSeeds(25);
      });

      expect(result.current.filteredTorrents.every(t => t.seeds >= 25)).toBe(true);
    });

    it('filters by freeleech only', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setFreeleechOnly(true);
      });

      expect(result.current.filteredTorrents).toHaveLength(1);
      expect(result.current.filteredTorrents[0].download_volume_factor).toBe(0);
    });

    it('filters by title', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setTitleFilter('old');
      });

      expect(result.current.filteredTorrents).toHaveLength(1);
      expect(result.current.filteredTorrents[0].title).toBe('Old.Movie.2020');
    });

    it('returns all torrents when no filters applied (except defaults)', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      expect(result.current.filteredTorrents).toHaveLength(5);
    });
  });

  describe('sorting', () => {
    it('sorts by score descending by default', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      const scores = result.current.filteredTorrents.map(t => t.score);
      expect(scores).toEqual([95, 90, 85, 70, 40]);
    });

    it('sorts by seeds descending', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSortBy('seeds');
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      const seeds = result.current.filteredTorrents.map(t => t.seeds);
      expect(seeds).toEqual([50, 30, 20, 5, 2]);
    });

    it('sorts by date descending', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSortBy('date');
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      const dates = result.current.filteredTorrents.map(t => t.publish_date);
      expect(dates[0]).toBe('2024-01-15');
      expect(dates[dates.length - 1]).toBe('2020-06-01');
    });

    it('sorts ascending when sortOrder is asc', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSortOrder('asc');
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      const scores = result.current.filteredTorrents.map(t => t.score);
      expect(scores).toEqual([40, 70, 85, 90, 95]);
    });
  });

  describe('pagination', () => {
    it('returns only visibleCount torrents in visibleTorrents', () => {
      const manyTorrents = Array.from({ length: 50 }, (_, i) =>
        makeTorrent({ title: `Torrent ${i}`, score: 100 - i })
      );

      const { result } = renderHook(() => useTorrentFilters(manyTorrents));

      act(() => {
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      expect(result.current.visibleTorrents).toHaveLength(20);
      expect(result.current.hasMoreTorrents).toBe(true);
    });

    it('increases visible count when setVisibleCount is called', () => {
      const manyTorrents = Array.from({ length: 50 }, (_, i) =>
        makeTorrent({ title: `Torrent ${i}`, score: 100 - i })
      );

      const { result } = renderHook(() => useTorrentFilters(manyTorrents));

      act(() => {
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      act(() => {
        result.current.setVisibleCount(prev => prev + 20);
      });

      expect(result.current.visibleTorrents).toHaveLength(40);
      expect(result.current.hasMoreTorrents).toBe(true);
    });

    it('hasMoreTorrents is false when all torrents are visible', () => {
      const { result } = renderHook(() => useTorrentFilters(sampleTorrents));

      act(() => {
        result.current.setSelectedQualities([]);
        result.current.setSelectedLanguages([]);
      });

      expect(result.current.hasMoreTorrents).toBe(false);
    });
  });
});
