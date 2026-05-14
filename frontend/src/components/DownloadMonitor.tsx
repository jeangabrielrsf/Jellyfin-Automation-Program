import React, { useState } from 'react';
import { Pause, Play, Trash2, Download, CheckCircle2, AlertCircle, Clock, Info, Folder, HardDrive, ArrowUpDown, Users, Gauge, Calendar, Hash, Globe, Tv } from 'lucide-react';
import { Download as DownloadType } from '../types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface DownloadMonitorProps {
  downloads: DownloadType[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
  onClear: () => void;
}

const statusConfig: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  downloading: { icon: Download, color: 'text-sky-400', bg: 'bg-sky-400/10', label: 'Baixando' },
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: 'Concluído' },
  failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Falhou' },
  cancelled: { icon: Trash2, color: 'text-muted-foreground', bg: 'bg-muted', label: 'Cancelado' },
  paused: { icon: Pause, color: 'text-amber-400', bg: 'bg-amber-400/10', label: 'Pausado' },
  pending: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Na fila' },
};

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
  onClear,
}) => {
  const [selectedDownload, setSelectedDownload] = useState<DownloadType | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);

  const clearableCount = downloads.filter(
    (d) => d.status !== 'pending' && d.status !== 'downloading'
  ).length;

  if (downloads.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mx-auto mb-6">
          <Download className="w-10 h-10 text-muted-foreground/40" />
        </div>
        <p className="text-xl font-display font-bold mb-2">Nenhum download ativo</p>
        <p className="text-sm">Vá para a página de busca para adicionar downloads</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {clearableCount > 0 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setClearDialogOpen(true)}
            className="text-muted-foreground hover:text-red-400 hover:border-red-400/30"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Limpar todos ({clearableCount})
          </Button>
        </div>
      )}
      {downloads.map((download, index) => {
        const status = statusConfig[download.status] || statusConfig.pending;
        const StatusIcon = status.icon;
        const progress = Math.round(download.progress * 100);

        return (
          <div
            key={download.id}
            onClick={() => setSelectedDownload(download)}
            className="glass rounded-2xl p-5 transition-all duration-300
                     hover:border-primary/20 hover:-translate-y-0.5 cursor-pointer"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-10 h-10 rounded-xl ${status.bg} flex items-center justify-center flex-shrink-0`}>
                  <StatusIcon className={`w-5 h-5 ${status.color}`} />
                </div>
                <div className="min-w-0">
                  <h4 className="font-body font-semibold text-foreground truncate">
                    {download.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md ${status.bg} ${status.color}`}>
                      {status.label}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      {download.quality || '1080p'}
                    </span>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      Clique para detalhes
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0 sm:self-auto self-end">
                {download.status === 'downloading' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onPause(download.id); }}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-amber-400/10 hover:text-amber-400
                             active:scale-95 transition-all duration-200"
                    title="Pausar"
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                )}
                {download.status === 'paused' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onResume(download.id); }}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-emerald-400/10 hover:text-emerald-400
                             active:scale-95 transition-all duration-200"
                    title="Retomar"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); onCancel(download.id); }}
                  className="w-9 h-9 rounded-lg glass flex items-center justify-center
                           hover:bg-red-400/10 hover:text-red-400
                           active:scale-95 transition-all duration-200"
                  title="Cancelar"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Progress */}
            {download.status === 'downloading' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono font-semibold text-primary">{progress}%</span>
                  <div className="flex items-center gap-4 text-muted-foreground text-xs font-mono">
                    {download.speed && <span>{download.speed}</span>}
                    {download.eta && <span>ETA: {download.eta}</span>}
                  </div>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary to-orange-300
                             transition-all duration-500 ease-out relative"
                    style={{ width: `${progress}%` }}
                  >
                    {progress < 100 && (
                      <div className="absolute inset-0 animate-shimmer" />
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Clear confirmation Dialog */}
      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent className="glass rounded-2xl p-6 max-w-md w-full space-y-4 border-none">
          <DialogHeader>
            <DialogTitle className="font-display text-xl font-bold text-foreground">
              Limpar downloads
            </DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground text-sm">
            Isso removerá {clearableCount} download{clearableCount !== 1 ? 's' : ''} concluído{clearableCount !== 1 ? 's' : ''}, falho{clearableCount !== 1 ? 's' : ''} ou cancelado{clearableCount !== 1 ? 's' : ''} do banco de dados.
            Downloads ativos não serão afetados.
          </p>
          <p className="text-muted-foreground text-xs">
            Os arquivos baixados serão mantidos no disco.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setClearDialogOpen(false);
                onClear();
              }}
            >
              Limpar {clearableCount} download{clearableCount !== 1 ? 's' : ''}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={!!selectedDownload} onOpenChange={(open) => !open && setSelectedDownload(null)}>
        <DialogContent className="glass rounded-2xl p-6 max-w-2xl w-full space-y-6 border-none max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display text-xl font-bold text-foreground">
              Detalhes do Download
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Informações completas do torrent
            </DialogDescription>
          </DialogHeader>

          {selectedDownload && (
            <div className="space-y-6 text-sm">
              {/* Torrent Name */}
              <div>
                <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                  <HardDrive className="w-3.5 h-3.5" />
                  Nome do arquivo
                </span>
                <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                  {selectedDownload.torrent_name || '—'}
                </p>
              </div>

              {/* Info Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <Gauge className="w-3.5 h-3.5" />
                    Status
                  </span>
                  <p className="font-semibold text-foreground capitalize">{selectedDownload.status}</p>
                </div>
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <ArrowUpDown className="w-3.5 h-3.5" />
                    Qualidade
                  </span>
                  <p className="font-semibold text-foreground">{selectedDownload.quality}</p>
                </div>
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <Globe className="w-3.5 h-3.5" />
                    Idioma
                  </span>
                  <p className="font-semibold text-foreground capitalize">{selectedDownload.language_preference}</p>
                </div>
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <HardDrive className="w-3.5 h-3.5" />
                    Tamanho
                  </span>
                  <p className="font-semibold text-foreground">{selectedDownload.size || '—'}</p>
                </div>
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <Users className="w-3.5 h-3.5" />
                    Seeds / Peers
                  </span>
                  <p className="font-semibold text-foreground">
                    {selectedDownload.seeds ?? '—'} / {selectedDownload.peers ?? '—'}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <Hash className="w-3.5 h-3.5" />
                    Hash
                  </span>
                  <p className="font-mono text-foreground text-xs break-all">
                    {selectedDownload.torrent_hash || '—'}
                  </p>
                </div>
              </div>

              {/* Progress / Speed */}
              {selectedDownload.status === 'downloading' && (
                <div className="space-y-2">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Gauge className="w-3.5 h-3.5" />
                    Progresso
                  </span>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-mono font-semibold text-primary">
                      {Math.round(selectedDownload.progress * 100)}%
                    </span>
                    <div className="flex items-center gap-4 text-muted-foreground text-xs font-mono">
                      {selectedDownload.speed && <span>{selectedDownload.speed}</span>}
                      {selectedDownload.eta && <span>ETA: {selectedDownload.eta}</span>}
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary to-orange-300"
                      style={{ width: `${Math.round(selectedDownload.progress * 100)}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Paths */}
              <div className="space-y-3">
                {selectedDownload.source_folder && (
                  <div>
                    <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                      <Folder className="w-3.5 h-3.5" />
                      Diretório de salvamento
                    </span>
                    <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                      {selectedDownload.source_folder}
                    </p>
                  </div>
                )}
                {selectedDownload.destination_folder && (
                  <div>
                    <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                      <Folder className="w-3.5 h-3.5" />
                      Diretório de destino
                    </span>
                    <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                      {selectedDownload.destination_folder}
                    </p>
                  </div>
                )}
              </div>

              {/* Season / Episode */}
              {(selectedDownload.season || selectedDownload.episode) && (
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Tv className="w-3.5 h-3.5" />
                    <span>
                      Temporada {selectedDownload.season ?? '—'}
                      {selectedDownload.episode !== undefined && ` • Episódio ${selectedDownload.episode}`}
                    </span>
                  </div>
                </div>
              )}

              {/* Magnet / Link */}
              {selectedDownload.magnet_link && (
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <Download className="w-3.5 h-3.5" />
                    Link / Magnet
                  </span>
                  <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                    {selectedDownload.magnet_link}
                  </p>
                </div>
              )}

              {/* Indexer */}
              {selectedDownload.indexer_used && (
                <div>
                  <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                    <Globe className="w-3.5 h-3.5" />
                    Indexer
                  </span>
                  <p className="font-semibold text-foreground">{selectedDownload.indexer_used}</p>
                </div>
              )}

              {/* Error */}
              {selectedDownload.error_message && (
                <div className="rounded-xl bg-red-400/10 border border-red-400/20 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    <span className="font-semibold text-red-400">Erro</span>
                  </div>
                  <p className="text-red-300 text-sm whitespace-pre-wrap">
                    {selectedDownload.error_message}
                  </p>
                </div>
              )}

              {/* Created at */}
              <div>
                <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                  <Calendar className="w-3.5 h-3.5" />
                  Criado em
                </span>
                <p className="text-foreground">
                  {new Date(selectedDownload.created_at).toLocaleString('pt-BR')}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
