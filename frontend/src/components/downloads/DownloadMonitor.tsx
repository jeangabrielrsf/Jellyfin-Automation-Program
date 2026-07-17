import React, { useState } from "react";
import { Trash2, Download } from "lucide-react";
import type { Download as DownloadType } from "@/types";
import { Button } from "@/components/ui/button";
import { ClearConfirmationDialog } from "./ClearConfirmationDialog";
import { CancelConfirmationDialog } from "./CancelConfirmationDialog";
import { DownloadDetailDialog } from "./DownloadDetailDialog";
import { DownloadList } from "./DownloadList";

interface DownloadMonitorProps {
    downloads: DownloadType[];
    onPause: (id: number) => void;
    onResume: (id: number) => void;
    onCancel: (id: number, deleteFiles: boolean) => void;
    onClear: (downloads: { id: number; delete_files: boolean }[]) => void;
}

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
    downloads,
    onPause,
    onResume,
    onCancel,
    onClear,
}) => {
    const [selectedDownload, setSelectedDownload] =
        useState<DownloadType | null>(null);
    const [downloadToCancel, setDownloadToCancel] =
        useState<DownloadType | null>(null);

    const clearableCount = downloads.filter(
        (d) => d.status !== "pending" && d.status !== "downloading" && d.status !== "cleared",
    ).length;

    if (downloads.length === 0) {
        return (
            <div className="text-center py-16 text-muted-foreground">
                <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mx-auto mb-6">
                    <Download className="w-10 h-10 text-muted-foreground/40" />
                </div>
                <p className="text-xl font-display font-bold mb-2">
                    Nenhum download ativo
                </p>
                <p className="text-sm">
                    Vá para a página de busca para adicionar downloads
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {clearableCount > 0 && (
                <div className="flex justify-end">
                    <ClearConfirmationDialog
                        clearableCount={clearableCount}
                        onClear={onClear}
                    >
                        <Button
                            variant="outline"
                            size="sm"
                            className="text-muted-foreground hover:text-red-400 hover:border-red-400/30"
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Limpar todos ({clearableCount})
                        </Button>
                    </ClearConfirmationDialog>
                </div>
            )}

            <DownloadList
                downloads={downloads}
                onSelectDownload={setSelectedDownload}
                onRequestCancel={setDownloadToCancel}
                onPause={onPause}
                onResume={onResume}
            />

            {downloadToCancel && (
                <CancelConfirmationDialog
                    isOpen={!!downloadToCancel}
                    download={downloadToCancel}
                    onCancel={onCancel}
                    onClose={() => setDownloadToCancel(null)}
                />
            )}

            <DownloadDetailDialog
                download={selectedDownload}
                onClose={() => setSelectedDownload(null)}
            />
        </div>
    );
};
