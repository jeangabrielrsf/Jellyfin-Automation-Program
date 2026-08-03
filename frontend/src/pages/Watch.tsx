import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2, PlayCircle } from 'lucide-react';
import Hls from 'hls.js';
import { downloadAPI } from '@/services/api';
import type { Download, PlaybackFile, PlaybackResponse } from '@/types';

const detailPathFor = (type: Download['type'], tmdbId: number) =>
  `/detail/${type === 'movie' ? 'movie' : 'tv'}/${tmdbId}`;

function playbackErrorMessage(error: unknown): string {
  const status = (error as { response?: { status?: number } })?.response?.status;
  if (status === 503) {
    return 'Muitos streams ativos no momento. Espere um pouco e tente novamente.';
  }
  if (status === 404) {
    return 'Arquivo não encontrado no disco. O download pode ter sido limpo.';
  }
  return 'Não foi possível carregar este conteúdo.';
}

function WatchPage() {
  const { downloadId } = useParams<{ downloadId: string }>();
  const navigate = useNavigate();
  const id = Number(downloadId);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const { data: playbackData, isLoading, error } = useQuery({
    queryKey: ['playback', id],
    queryFn: () => downloadAPI.getPlayback(id),
    enabled: !!id,
  });

  const { data: downloadData, error: downloadError } = useQuery({
    queryKey: ['download', id],
    queryFn: () => downloadAPI.getDownload(id),
    enabled: !!id,
  });

  const playback: PlaybackResponse | undefined = playbackData?.data;
  const files: PlaybackFile[] = playback?.files ?? [];
  const download = downloadData?.data;

  const activeFile = files[Math.min(activeIndex, files.length - 1)];

  const errorMessage = useMemo(() => {
    if (error) return playbackErrorMessage(error);
    if (downloadError) return playbackErrorMessage(downloadError);
    return null;
  }, [error, downloadError]);

  const subtitleUrl = useMemo(() => {
    const url = playback?.subtitle_url;
    if (!url) return undefined;
    const episode = activeFile?.episode;
    if (episode == null || !/episode=\d+/.test(url)) return url;
    return url.replace(/episode=\d+/, `episode=${episode}`);
  }, [playback?.subtitle_url, activeFile?.episode]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !activeFile) return;

    const attachHls = () => {
      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(activeFile.url);
      hls.attachMedia(video);
    };

    if (activeFile.mode === 'transcode' && Hls.isSupported()) {
      attachHls();
    } else {
      video.src = activeFile.url;
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      video.removeAttribute('src');
      video.load();
    };
  }, [activeFile]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]" data-testid="watch-loading">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (errorMessage || files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 text-center" data-testid="watch-error">
        <p className="text-muted-foreground">{errorMessage ?? 'Nenhum arquivo de vídeo encontrado para este download.'}</p>
        <button
          type="button"
          onClick={() => navigate(download ? detailPathFor(download.type, download.tmdb_id) : '/downloads')}
          className="inline-flex items-center gap-2 text-sm text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </button>
      </div>
    );
  }

  const backPath = download ? detailPathFor(download.type, download.tmdb_id) : '/downloads';

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between gap-4 mb-4">
        <button
          type="button"
          onClick={() => navigate(backPath)}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </button>
        <h1 className="text-lg font-semibold truncate">
          {download?.title ?? 'Reproduzindo'}
          {activeFile?.episode != null && <span className="text-muted-foreground"> · Episódio {activeFile.episode}</span>}
        </h1>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1 min-w-0">
          <video
            ref={videoRef}
            data-testid="watch-video"
            controls
            autoPlay
            className="w-full aspect-video bg-black rounded-lg"
          >
            {subtitleUrl && (
              <track key={subtitleUrl} kind="subtitles" src={subtitleUrl} srcLang="pt" label="Legendas" default />
            )}
          </video>
        </div>

        {files.length > 1 && (
          <aside className="lg:w-72 shrink-0 lg:max-h-[70vh] lg:overflow-y-auto border rounded-lg p-3" data-testid="watch-sidebar">
            <h2 className="text-sm font-semibold mb-3">Episódios</h2>
            <ul className="flex lg:flex-col gap-2 lg:gap-1">
              {files.map((file, index) => (
                <li key={file.url}>
                  <button
                    type="button"
                    onClick={() => setActiveIndex(index)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left transition-colors ${
                      index === activeIndex
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    }`}
                  >
                    <PlayCircle className="h-4 w-4 shrink-0" />
                    <span className="truncate">
                      {file.episode != null ? `Episódio ${file.episode}` : file.title}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>
    </div>
  );
}

export default WatchPage;
