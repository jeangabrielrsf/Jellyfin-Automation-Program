import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import type { Download } from '@/types';

interface CancelConfirmationDialogProps {
  isOpen?: boolean;
  download: Download;
  onCancel: (id: number, deleteFiles: boolean) => void;
  onClose?: () => void;
}

export const CancelConfirmationDialog: React.FC<CancelConfirmationDialogProps> = ({
  isOpen: controlledIsOpen,
  download,
  onCancel,
  onClose,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [deleteFiles, setDeleteFiles] = useState(false);

  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;

  const isActive = download.status === 'pending' || download.status === 'downloading';

  useEffect(() => {
    if (!isOpen) {
      setDeleteFiles(false);
    }
  }, [isOpen]);

  const handleOpenChange = (open: boolean) => {
    if (!isControlled) {
      setInternalIsOpen(open);
    }
    if (!open && onClose) {
      onClose();
    }
  };

  const handleCancel = () => {
    onCancel(download.id, deleteFiles);
    setDeleteFiles(false);
    if (!isControlled) {
      setInternalIsOpen(false);
    }
  };

  const handleBack = () => {
    setDeleteFiles(false);
    if (!isControlled) {
      setInternalIsOpen(false);
    }
    if (onClose) {
      onClose();
    }
  };

  const title = isActive ? 'Cancelar download' : 'Limpar da lista';
  const message = isActive
    ? `Tem certeza que deseja cancelar o download de ${download.title}?`
    : `Tem certeza que deseja limpar ${download.title} da lista?`;
  const checkboxLabel = isActive
    ? 'Deletar arquivos parciais do disco'
    : 'Deletar arquivos baixados do disco';
  const buttonLabel = isActive ? 'Cancelar download' : 'Limpar da lista';

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="glass rounded-2xl p-6 max-w-md w-full space-y-4 border-none">
        <DialogHeader>
          <DialogTitle className="font-display text-xl font-bold text-foreground">
            {title}
          </DialogTitle>
        </DialogHeader>
        <p className="text-muted-foreground text-sm">
          {message}
        </p>
        <label className="flex items-center gap-2 cursor-pointer select-none p-3 rounded-lg bg-muted/50 border border-border/30">
          <input
            type="checkbox"
            checked={deleteFiles}
            onChange={(e) => setDeleteFiles(e.target.checked)}
            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
          />
          <span className="text-sm text-foreground">{checkboxLabel}</span>
        </label>
        <DialogFooter>
          <Button variant="outline" onClick={handleBack}>
            Voltar
          </Button>
          <Button variant="destructive" onClick={handleCancel}>
            {buttonLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
