import React from 'react';
import { Link } from 'react-router-dom';
import { Play } from 'lucide-react';
import { findWatchableDownload } from '@/lib/watchableDownload';
import type { Download } from '@/types';

interface WatchNowButtonProps {
  downloads?: Download[];
}

export const WatchNowButton: React.FC<WatchNowButtonProps> = ({ downloads = [] }) => {
  const watchable = findWatchableDownload(downloads);
  if (!watchable) return null;

  return (
    <Link
      to={`/watch/${watchable.id}`}
      className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm font-semibold"
    >
      <Play className="w-4 h-4 fill-current" />
      Assistir
    </Link>
  );
};
