import { useState, useMemo, useEffect } from 'react';
import { TorrentResult } from '@/types';

const PAGE_SIZE = 20;

export function useTorrentFilters(torrents: TorrentResult[]) {
  const [preferredQuality, setPreferredQuality] = useState('1080p');
  const [customSearchEnabled, setCustomSearchEnabled] = useState(false);
  const [customQuery, setCustomQuery] = useState('');
  const [selectedTitle, setSelectedTitle] = useState<string>('');

  const [selectedQualities, setSelectedQualities] = useState<string[]>(['1080p']);
  const [minSeeds, setMinSeeds] = useState(0);
  const [freeleechOnly, setFreeleechOnly] = useState(false);
  const [sortBy, setSortBy] = useState<'score' | 'seeds' | 'date' | 'size'>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [titleFilter, setTitleFilter] = useState('');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [advancedOptionsOpen, setAdvancedOptionsOpen] = useState(false);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [selectedQualities, minSeeds, freeleechOnly, titleFilter, sortBy, sortOrder]);

  useEffect(() => {
    setSelectedQualities([preferredQuality]);
  }, [preferredQuality]);

  const filteredAndSortedTorrents = useMemo(() => {
    if (!torrents) return [];

    const filtered = torrents.filter((torrent) => {
      if (selectedQualities.length > 0 && torrent.quality && !selectedQualities.includes(torrent.quality)) {
        return false;
      }
      if (torrent.seeds < minSeeds) {
        return false;
      }
      if (freeleechOnly && torrent.download_volume_factor !== 0) {
        return false;
      }
      if (titleFilter && !torrent.title.toLowerCase().includes(titleFilter.toLowerCase())) {
        return false;
      }
      return true;
    });

    filtered.sort((a, b) => {
      let aVal: number, bVal: number;

      switch (sortBy) {
        case 'seeds':
          aVal = a.seeds;
          bVal = b.seeds;
          break;
        case 'date':
          aVal = a.publish_date ? new Date(a.publish_date).getTime() : 0;
          bVal = b.publish_date ? new Date(b.publish_date).getTime() : 0;
          break;
        case 'size':
          aVal = parseFloat(a.size) || 0;
          bVal = parseFloat(b.size) || 0;
          break;
        case 'score':
        default:
          aVal = a.score;
          bVal = b.score;
          break;
      }

      return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
    });

    return filtered;
  }, [torrents, selectedQualities, minSeeds, freeleechOnly, titleFilter, sortBy, sortOrder]);

  const visibleTorrents = useMemo(() => {
    return filteredAndSortedTorrents.slice(0, visibleCount);
  }, [filteredAndSortedTorrents, visibleCount]);

  const hasMoreTorrents = visibleCount < filteredAndSortedTorrents.length;

  return {
    preferredQuality,
    setPreferredQuality,
    customSearchEnabled,
    setCustomSearchEnabled,
    customQuery,
    setCustomQuery,
    selectedTitle,
    setSelectedTitle,
    selectedQualities,
    setSelectedQualities,
    minSeeds,
    setMinSeeds,
    freeleechOnly,
    setFreeleechOnly,
    sortBy,
    setSortBy,
    sortOrder,
    setSortOrder,
    titleFilter,
    setTitleFilter,
    visibleCount,
    setVisibleCount,
    advancedOptionsOpen,
    setAdvancedOptionsOpen,
    filteredTorrents: filteredAndSortedTorrents,
    visibleTorrents,
    hasMoreTorrents,
    PAGE_SIZE,
  };
}
