import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { listsAPI } from '@/services/api';
import type { ListItem } from '@/types';

const WatchlistCard: React.FC<{ item: ListItem }> = ({ item }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => listsAPI.remove('watchlist', item.media_type, item.tmdb_id),
    onSuccess: () => {
      toast.success('Removido da watchlist');
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
    onError: (e) => {
      toast.error(e instanceof Error ? e.message : 'Falha ao remover');
    },
  });

  const detailPath = `/detail/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`;

  return (
    <div className="rounded-xl overflow-hidden border border-border/30 bg-background/50 hover:border-primary/30 transition-colors">
      <button
        type="button"
        onClick={() => navigate(detailPath)}
        className="block w-full text-left"
      >
        {item.poster_path ? (
          <img
            src={`https://image.tmdb.org/t/p/w300${item.poster_path}`}
            alt={item.title}
            className="w-full aspect-[2/3] object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full aspect-[2/3] bg-muted flex items-center justify-center text-muted-foreground text-sm">
            Sem imagem
          </div>
        )}
        <div className="p-3 space-y-1">
          <p className="text-sm font-medium text-foreground line-clamp-2">{item.title}</p>
          <p className="text-xs text-muted-foreground">{item.year || '—'}</p>
        </div>
      </button>
      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent disabled:opacity-50 transition-colors"
        >
          {remove.isPending ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Trash2 className="w-3 h-3" />
          )}
          Remover
        </button>
      </div>
    </div>
  );
};

const WatchlistPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => listsAPI.listWatchlist().then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Bookmark className="w-7 h-7 text-primary" />
        <h1 className="font-display text-3xl font-bold">Watchlist</h1>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="aspect-[2/3] rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-20 space-y-3">
          <Bookmark className="w-12 h-12 mx-auto text-muted-foreground" />
          <p className="text-muted-foreground">Sua watchlist está vazia.</p>
          <div className="flex items-center justify-center gap-3 text-sm">
            <Link to="/discover" className="text-primary hover:underline">
              Explorar títulos
            </Link>
            <span className="text-muted-foreground">•</span>
            <Link to="/search" className="text-primary hover:underline">
              Buscar
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {data.map((item) => (
            <WatchlistCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
};

export default WatchlistPage;
