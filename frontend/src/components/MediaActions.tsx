import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Eye, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { listsAPI } from '@/services/api';
import type { ListKind, UserMediaType } from '@/types';

interface MediaActionsProps {
  mediaType: UserMediaType;
  tmdbId: number;
  title: string;
  posterPath: string | null;
  backdropPath: string | null;
  year: number | null;
}

export const MediaActions: React.FC<MediaActionsProps> = ({
  mediaType,
  tmdbId,
  title,
  posterPath,
  backdropPath,
  year,
}) => {
  const queryClient = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ['list-status', mediaType, tmdbId],
    queryFn: () => listsAPI.getStatus(mediaType, tmdbId).then((r) => r.data),
  });

  const toggle = useMutation({
    mutationFn: async (kind: ListKind) => {
      const inList = status?.[kind] ?? false;
      if (inList) {
        await listsAPI.remove(kind, mediaType, tmdbId);
      } else {
        await listsAPI.add(kind, mediaType, tmdbId, {
          title,
          poster_path: posterPath,
          backdrop_path: backdropPath,
          year,
        });
      }
    },
    onSuccess: (_, kind) => {
      toast.success(
        kind === 'watched' ? 'Marcado como visto' : 'Adicionado à watchlist',
      );
      queryClient.invalidateQueries({ queryKey: ['list-status', mediaType, tmdbId] });
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
    onError: (e) => {
      const msg = e instanceof Error ? e.message : 'Falha ao atualizar lista';
      toast.error(msg);
    },
  });

  const pillBase =
    'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50';
  const pillActive = 'bg-primary/20 text-primary hover:bg-primary/30';
  const pillInactive = 'glass border border-border/50 text-muted-foreground hover:text-foreground';

  return (
    <div className="flex items-center gap-2 mt-3 flex-wrap">
      <button
        type="button"
        onClick={() => toggle.mutate('watchlist')}
        disabled={toggle.isPending}
        className={`${pillBase} ${status?.watchlist ? pillActive : pillInactive}`}
      >
        {toggle.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bookmark className="w-4 h-4" />}
        {status?.watchlist ? 'Na watchlist' : 'Watchlist'}
      </button>
      <button
        type="button"
        onClick={() => toggle.mutate('watched')}
        disabled={toggle.isPending}
        className={`${pillBase} ${status?.watched ? pillActive : pillInactive}`}
      >
        {toggle.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
        {status?.watched ? 'Visto' : 'Marcar como visto'}
      </button>
    </div>
  );
};
