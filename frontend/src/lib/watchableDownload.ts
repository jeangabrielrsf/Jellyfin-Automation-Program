import type { Download } from '@/types';

export function findWatchableDownload(downloads: Download[]): Download | null {
  return downloads.find(
    (d) => d.status === 'completed' || d.status === 'organized'
  ) ?? null;
}
