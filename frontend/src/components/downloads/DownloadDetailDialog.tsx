import React from "react";
import {
    Download,
    AlertCircle,
    Folder,
    HardDrive,
    ArrowUpDown,
    Users,
    Gauge,
    Calendar,
    Hash,
    Globe,
    Tv,
} from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";
import type { Download as DownloadType } from "@/types";

interface DownloadDetailDialogProps {
    download: DownloadType | null;
    onClose: () => void;
}

export const DownloadDetailDialog: React.FC<DownloadDetailDialogProps> = ({
    download,
    onClose,
}) => {
    if (!download) {
        return null;
    }

    return (
        <Dialog
            open={!!download}
            onOpenChange={(open) => {
                if (!open) onClose();
            }}
        >
            <DialogContent className="glass rounded-2xl p-6 max-w-2xl w-full space-y-6 border-none max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="font-display text-xl font-bold text-foreground">
                        Detalhes do Download
                    </DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        Informações completas do torrent
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 text-sm">
                    <div>
                        <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                            <HardDrive className="w-3.5 h-3.5" />
                            Nome do arquivo
                        </span>
                        <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                            {download.torrent_name || "—"}
                        </p>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <Gauge className="w-3.5 h-3.5" />
                                Status
                            </span>
                            <p className="font-semibold text-foreground capitalize">
                                {download.status}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <ArrowUpDown className="w-3.5 h-3.5" />
                                Qualidade
                            </span>
                            <p className="font-semibold text-foreground">
                                {download.quality}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <Globe className="w-3.5 h-3.5" />
                                Idioma
                            </span>
                            <p className="font-semibold text-foreground capitalize">
                                {download.language_preference}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <HardDrive className="w-3.5 h-3.5" />
                                Tamanho
                            </span>
                            <p className="font-semibold text-foreground">
                                {download.size || "—"}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <Users className="w-3.5 h-3.5" />
                                Seeds / Peers
                            </span>
                            <p className="font-semibold text-foreground">
                                {download.seeds ?? "—"} /{" "}
                                {download.peers ?? "—"}
                            </p>
                        </div>
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <Hash className="w-3.5 h-3.5" />
                                Hash
                            </span>
                            <p className="font-mono text-foreground text-xs break-all">
                                {download.torrent_hash || "—"}
                            </p>
                        </div>
                    </div>

                    {download.status === "downloading" && (
                        <div className="space-y-2">
                            <span className="text-muted-foreground flex items-center gap-1.5">
                                <Gauge className="w-3.5 h-3.5" />
                                Progresso
                            </span>
                            <div className="flex items-center justify-between text-sm">
                                <span className="font-mono font-semibold text-primary">
                                    {Math.round(download.progress * 100)}%
                                </span>
                                <div className="flex items-center gap-4 text-muted-foreground text-xs font-mono">
                                    {download.speed && (
                                        <span>{download.speed}</span>
                                    )}
                                    {download.eta && (
                                        <span>ETA: {download.eta}</span>
                                    )}
                                </div>
                            </div>
                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-primary to-orange-300"
                                    style={{
                                        width: `${Math.round(download.progress * 100)}%`,
                                    }}
                                />
                            </div>
                        </div>
                    )}

                    <div className="space-y-3">
                        {download.source_folder && (
                            <div>
                                <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                    <Folder className="w-3.5 h-3.5" />
                                    Diretório de salvamento
                                </span>
                                <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                                    {download.source_folder}
                                </p>
                            </div>
                        )}
                        {download.destination_folder && (
                            <div>
                                <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                    <Folder className="w-3.5 h-3.5" />
                                    Diretório de destino
                                </span>
                                <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                                    {download.destination_folder}
                                </p>
                            </div>
                        )}
                    </div>

                    {(download.season || download.episode) && (
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                                <Tv className="w-3.5 h-3.5" />
                                <span>
                                    Temporada {download.season ?? "—"}
                                    {download.episode !== undefined &&
                                        ` • Episódio ${download.episode}`}
                                </span>
                            </div>
                        </div>
                    )}

                    {download.magnet_link && (
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <Download className="w-3.5 h-3.5" />
                                Link / Magnet
                            </span>
                            <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-3">
                                {download.magnet_link}
                            </p>
                        </div>
                    )}

                    {download.indexer_used && (
                        <div>
                            <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                                <Globe className="w-3.5 h-3.5" />
                                Indexer
                            </span>
                            <p className="font-semibold text-foreground">
                                {download.indexer_used}
                            </p>
                        </div>
                    )}

                    {download.error_message && (
                        <div className="rounded-xl bg-red-400/10 border border-red-400/20 p-4">
                            <div className="flex items-center gap-2 mb-2">
                                <AlertCircle className="w-4 h-4 text-red-400" />
                                <span className="font-semibold text-red-400">
                                    Erro
                                </span>
                            </div>
                            <p className="text-red-300 text-sm whitespace-pre-wrap">
                                {download.error_message}
                            </p>
                        </div>
                    )}

                    <div>
                        <span className="text-muted-foreground flex items-center gap-1.5 mb-1">
                            <Calendar className="w-3.5 h-3.5" />
                            Criado em
                        </span>
                        <p className="text-foreground">
                            {new Date(download.created_at).toLocaleString(
                                "pt-BR",
                            )}
                        </p>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
};
