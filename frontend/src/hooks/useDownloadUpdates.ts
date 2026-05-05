import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from './useWebSocket';

export function DownloadUpdates(): null {
  const { lastMessage } = useWebSocket();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type !== 'download_update') return;

    const updatedDownload = lastMessage.data;

    queryClient.setQueryData(['downloads'], (old: unknown) => {
      const list = (old as any)?.data;
      if (!Array.isArray(list)) return old;

      const index = list.findIndex((d: any) => d.id === updatedDownload.id);
      if (index >= 0) {
        const next = [...list];
        next[index] = updatedDownload;
        return { ...(old as any), data: next };
      }
      return { ...(old as any), data: [updatedDownload, ...list] };
    });
  }, [lastMessage, queryClient]);

  return null;
}
