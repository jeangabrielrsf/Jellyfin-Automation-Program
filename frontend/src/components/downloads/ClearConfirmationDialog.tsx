import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface ClearConfirmationDialogProps {
  clearableCount: number;
  onClear: (deleteFiles: boolean) => void;
  children?: React.ReactNode;
}

export const ClearConfirmationDialog: React.FC<ClearConfirmationDialogProps> = ({
  clearableCount,
  onClear,
  children,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [deleteFiles, setDeleteFiles] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setDeleteFiles(false);
    }
  }, [isOpen]);

  const handleClear = () => {
    onClear(deleteFiles);
    setDeleteFiles(false);
    setIsOpen(false);
  };

  const handleCancel = () => {
    setDeleteFiles(false);
    setIsOpen(false);
  };

  const pluralSuffix = clearableCount !== 1 ? 's' : '';

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {children && <DialogTrigger asChild>{children}</DialogTrigger>}
      <DialogContent className="glass rounded-2xl p-6 max-w-md w-full space-y-4 border-none">
        <DialogHeader>
          <DialogTitle className="font-display text-xl font-bold text-foreground">
            Limpar downloads
          </DialogTitle>
        </DialogHeader>
        <p className="text-muted-foreground text-sm">
          Isso removerá {clearableCount} download{pluralSuffix} concluído{pluralSuffix}, falho{pluralSuffix} ou cancelado{pluralSuffix} do banco de dados.
          Downloads ativos não serão afetados.
        </p>
        <label className="flex items-center gap-2 cursor-pointer select-none p-3 rounded-lg bg-muted/50 border border-border/30">
          <input
            type="checkbox"
            checked={deleteFiles}
            onChange={(e) => setDeleteFiles(e.target.checked)}
            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
          />
          <span className="text-sm text-foreground">Deletar arquivos baixados do disco</span>
        </label>
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={handleClear}>
            Limpar {clearableCount} download{pluralSuffix}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
