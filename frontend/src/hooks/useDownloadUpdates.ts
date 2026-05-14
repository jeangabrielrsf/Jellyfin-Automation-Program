import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from './useWebSocket';

interface DownloadUpdate {
  id: number;
  [key: string]: unknown;
}

interface DownloadsQueryData {
  data: DownloadUpdate[];
}

export function DownloadUpdates(): null {
  const { lastMessage } = useWebSocket();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type !== 'download_update') return;

    const updatedDownload = lastMessage.data as DownloadUpdate;

    queryClient.setQueryData(['downloads'], (old: unknown) => {
      const list = (old as DownloadsQueryData | undefined)?.data;
      if (!Array.isArray(list)) return old;

      const index = list.findIndex((d) => d.id === updatedDownload.id);
      if (index >= 0) {
        const next = [...list];
        next[index] = updatedDownload;
        return { ...(old as DownloadsQueryData), data: next };
      }
      return { ...(old as DownloadsQueryData), data: [updatedDownload, ...list] };
    });
  }, [lastMessage, queryClient]);

  return null;
}
