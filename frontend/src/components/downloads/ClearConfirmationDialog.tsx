import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { downloadAPI } from '@/services/api';
import type { Download } from '@/types';

interface ClearConfirmationDialogProps {
  clearableCount: number;
  onClear: (downloads: { id: number; delete_files: boolean }[]) => void;
  children?: React.ReactNode;
}

export const ClearConfirmationDialog: React.FC<ClearConfirmationDialogProps> = ({
  clearableCount,
  onClear,
  children,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [deleteFilesMap, setDeleteFilesMap] = useState<Record<number, boolean>>({});

  const { data: clearableDownloads } = useQuery({
    queryKey: ['clearable-downloads'],
    queryFn: () => downloadAPI.getClearableDownloads(),
    enabled: isOpen,
  });

  useEffect(() => {
    if (!isOpen) {
      setDeleteFilesMap({});
    }
  }, [isOpen]);

  const downloads: Download[] = clearableDownloads?.data || [];

  const handleToggleAll = (checked: boolean) => {
    const newMap: Record<number, boolean> = {};
    downloads.forEach(d => {
      newMap[d.id] = checked;
    });
    setDeleteFilesMap(newMap);
  };

  const handleToggleOne = (id: number, checked: boolean) => {
    setDeleteFilesMap(prev => ({ ...prev, [id]: checked }));
  };

  const allChecked = downloads.length > 0 && downloads.every(d => deleteFilesMap[d.id]);
  const someChecked = downloads.some(d => deleteFilesMap[d.id]);

  const handleClear = () => {
    const items = downloads.map(d => ({
      id: d.id,
      delete_files: deleteFilesMap[d.id] || false,
    }));
    onClear(items);
    setDeleteFilesMap({});
    setIsOpen(false);
  };

  const handleCancel = () => {
    setDeleteFilesMap({});
    setIsOpen(false);
  };

  const pluralSuffix = clearableCount !== 1 ? 's' : '';

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {children && <DialogTrigger asChild>{children}</DialogTrigger>}
      <DialogContent className="glass rounded-2xl p-6 max-w-lg w-full space-y-4 border-none max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="font-display text-xl font-bold text-foreground">
            Limpar downloads
          </DialogTitle>
        </DialogHeader>
        <p className="text-muted-foreground text-sm">
          {clearableCount} download{pluralSuffix} pronto{pluralSuffix} para limpar.
          Marque os arquivos que deseja deletar do disco.
        </p>

        {downloads.length > 1 && (
          <label className="flex items-center gap-2 cursor-pointer select-none p-3 rounded-lg bg-primary/10 border border-primary/30">
            <input
              type="checkbox"
              checked={allChecked}
              onChange={(e) => handleToggleAll(e.target.checked)}
              className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
            />
            <span className="text-sm font-medium text-foreground">
              {allChecked ? 'Desmarcar todos' : 'Selecionar todos'}
            </span>
          </label>
        )}

        <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
          {downloads.map(download => (
            <label
              key={download.id}
              className="flex items-center gap-3 cursor-pointer select-none p-3 rounded-lg bg-muted/50 border border-border/30 hover:bg-muted/70 transition-colors"
            >
              <input
                type="checkbox"
                checked={deleteFilesMap[download.id] || false}
                onChange={(e) => handleToggleOne(download.id, e.target.checked)}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary flex-shrink-0"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {download.title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {download.status === 'completed' && 'Concluído'}
                  {download.status === 'failed' && 'Falhou'}
                  {download.status === 'cancelled' && 'Cancelado'}
                  {download.status === 'organized' && 'Organizado'}
                  {download.season && download.episode
                    ? ` • T${download.season}E${download.episode}`
                    : download.season
                    ? ` • T${download.season}`
                    : ''}
                </p>
              </div>
            </label>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={handleClear}>
            Limpar {someChecked ? 'e deletar' : ''} {clearableCount} download{pluralSuffix}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
