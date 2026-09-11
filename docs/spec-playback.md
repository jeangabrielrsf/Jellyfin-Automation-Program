# Spec — Playback no Site (Streaming Direto com Transcode On-Demand)

## Problem Statement

O usuário quer assistir aos conteúdos que baixou (filmes, séries e animes organizados pelo `OrganizerService`) diretamente no site, sem precisar abrir o Jellyfin. Hoje o site gerencia buscas, downloads e organização, mas não reproduz nada: o usuário precisa sair da aplicação para assistir. Além disso, a maioria dos torrents vem em MKV/HEVC, que browsers não reproduzem nativamente — um player ingênuo tocaria apenas uma fração da biblioteca.

## Solution

Uma página dedicada de player (`/watch/:downloadId`) que reproduz qualquer conteúdo concluído. O backend serve o vídeo diretamente do filesystem local via FastAPI (`FileResponse` com Range/206). Quando o arquivo não é suportado pelo browser (detecção via ffprobe com cache), o backend transcodifica on-demand com ffmpeg (rodando no container Docker do backend) e serve o resultado como HLS (`m3u8` + segmentos) para o hls.js no frontend. Sessões de transcode têm ciclo de vida controlado (touch-on-request, timeout de 60s, sweeper lazy) e limite de 3 simultâneas (503 sob pressão). O botão "Assistir" aparece na página Detail; para packs de temporada, o player mostra sidebar de episódios. Legendas `.srt` sidecar são servidas como WebVTT.

## User Stories

1. Como usuário, quero clicar em "Assistir" na página Detail de um conteúdo concluído, para reproduzi-lo no site sem sair da aplicação.
2. Como usuário, quero que o player comece o playback o mais rápido possível, para não esperar buffering longo ao iniciar.
3. Como usuário assistindo um MP4/H.264, quero que o browser toque o arquivo direto (sem transcodificação), para economizar CPU do servidor e ter menor latência.
4. Como usuário assistindo um MKV/HEVC, quero que o site transcodifique on-demand e reproduza mesmo assim, para assistir qualquer torrent independente do codec.
5. Como usuário assistindo um filme, quero poder dar seek (pular para frente/trás) livremente, para navegar pelo conteúdo com precisão.
6. Como usuário assistindo uma série, quero ver a lista de episódios disponíveis no player, para escolher qual assistir.
7. Como usuário assistindo um pack de temporada, quero clicar em um episódio e ele tocar imediatamente (matando a sessão anterior), para trocar de episódio sem travar.
8. Como usuário, quero que a legenda `.srt` ao lado do vídeo apareça no player, para assistir conteúdo legendado.
9. Como usuário, quero pausar, ajustar volume, entrar em fullscreen e usar os controles nativos do browser no mobile, para ter experiência padrão de vídeo.
10. Como usuário abrindo o mesmo conteúdo em duas abas, quero que ambas reproduzam (compartilhando sessão), sem erro.
11. Como usuário assistindo quando o limite de 3 transcodes está cheio, quero uma mensagem clara ("muitos streams ativos, tente mais tarde"), para entender por que não iniciou.
12. Como usuário que fecha o player abruptamente (aba fechada, browser suspenso), quero que os recursos do servidor sejam liberados sozinhos, para não acumular processos órfãos.
13. Como usuário, quero que o player indique erro claro quando o arquivo não existe mais no disco, para saber que o download foi limpo.
14. Como usuário assistindo série, quero que o título da mídia e o episódio atual apareçam no player, para saber o que estou assistindo.
15. Como usuário, quero voltar do player para a página Detail facilmente, para retomar a navegação.

## Implementation Decisions

Baseado em ADR-0008 (streaming direto com transcode on-demand) e nas decisões de playback registradas no CONTEXT.md:

1. **Stream direto via FastAPI** — `FileResponse` do Starlette, que trata Range/206 nativamente. Sem proxy do Jellyfin.
2. **Transcode on-demand** — ffmpeg no container Docker do backend (e instalado no WSL2 para dev). Disparado apenas quando necessário.
3. **Formato HLS** — ffmpeg gera `m3u8` + segmentos em diretório temporário do container; player é hls.js no frontend (mesmo player serve direct e transcode).
4. **Detecção smart** — ffprobe decide direct vs transcode; resultado cacheado em memória com key = `(path, mtime)`. Ffprobe roda no request path (~100-300ms no primeiro acesso).
5. **Sessão de Streaming** — módulo `StreamService` gerencia sessões: cada sessão = processo ffmpeg + diretório de segmentos, keyed por `(download_id, episode)`. Touch-on-request (playlist ou segmento atualiza `last_access`); timeout de 60s idle; sweeper lazy (verifica ao criar sessão nova + varredura periódica) mata processo e apaga diretório.
6. **Limite de 3 sessões simultâneas** — semáforo; quando cheio, o endpoint responde 503. Trocar de episódio dentro do mesmo download mata a sessão anterior (libera o semáforo imediatamente).
7. **Resolução de arquivo** — `StreamService` resolve o folder a partir do `Download` (source/destination_folder na DB). Filme: maior arquivo de vídeo excluindo nomes com `sample`/`trailer`/`extra`. Série: enumera episódios parseando `SxxExx` dos nomes de arquivo, ordenados; casa com `downloads.season`/`episode` quando o download é episódio avulso.
8. **Contrato de API**:
   - `GET /api/downloads/{id}/playback` → `{ mode: "direct" | "transcode", files: [{ episode, title, url }], subtitle_url?: string }`
   - `GET /api/stream/{download_id}/playlist.m3u8?episode=N` → playlist HLS (cria sessão lazy no primeiro request; direto → FileResponse do arquivo; transcode → playlist do processo ffmpeg)
   - Segmentos HLS servidos do diretório temporário da sessão (URLs relativas à playlist)
   - `GET /api/stream/{download_id}/subtitle.vtt` → `.srt` sidecar convertido para WebVTT
   - Erro padrão: 503 com corpo JSON claro quando semáforo cheio; 404 quando arquivo não existe.
9. **Frontend** — página `Watch` na rota `/watch/:downloadId`: hls.js instanciado no mount (e destruído no unmount), instanciado apenas quando `mode === "transcode"`; sidebar de episódios (estilo Netflix) quando `files.length > 1`; `<track>`/attach de legenda quando `subtitle_url` presente; controles nativos do `<video>` (sem gestures customizadas); botão "Assistir" na página Detail que navega para a rota. Sem resume de playback.
10. **Config** — limite de transcodes e timeout da sessão via `get_config` (padrão do projeto), com defaults 3 e 60s.
11. **Sem auth extra** — player exposto na LAN como o resto do app.

## Testing Decisions

Bom teste: verifica comportamento externo (decisões e contratos), não implementação. Não roda ffmpeg real no suite padrão.

**Seam 1 — `StreamService` (nível serviço, principal):** heurística de resolução (filme com samples/extras, pack com múltiplos episódios, episódio avulso), decisão direct-vs-transcode com ffprobe mockado (incl. cache path+mtime), ciclo de vida de sessão (touch, timeout 60s, kill ao trocar episódio, sweeper) com processo ffmpeg fake e temp dirs reais, semáforo de 3 com 503. Prior art: `backend/tests/test_organizer_service.py` (temp dirs + `get_config` mockado via `patch`).

**Seam 2 — API HTTP (TestClient):** contrato `playback` (modo, files[], subtitle_url presente/ausente), sessão lazy no primeiro request de playlist, 503 sob pressão, 404 arquivo inexistente, legenda WebVTT. Prior art: `backend/tests/test_filesystem_router.py`, `backend/tests/test_routers.py` (fixtures `client`/`db_session` do `conftest.py`).

**Seam 3 — Página Watch (frontend):** render com API mockada (`playback` retornando direct/transcode), sidebar de episódios aparece com N>1, troca de episódio chama a URL certa, hls.js mockado. Prior art: `frontend/src/components/downloads/*.test.tsx` (testing-library + vitest).

**Integração real com ffmpeg:** marcada `@pytest.mark.integration` (pulada por default no `pytest tests/ -v`), para smoke test manual/CI futuro.

## Out of Scope

- Resume de playback (continuar de onde parou) — pendência registrada no CONTEXT.md, feature futura.
- Legendas embutidas em MKV (multitrilha, idiomas, forced) — pendência registrada no CONTEXT.md, feature futura.
- Seletor de episódio na página Detail (a escolha acontece no player).
- Botões "Assistir" na Watchlist/Downloads (apenas Detail na v1).
- Autenticação/controle de acesso ao player.
- Suporte a DASH/WebRTC/low-latency.
- Cleanup imediato de sessão ao desmontar o player (apenas timeout de 60s + kill ao trocar episódio).

## Further Notes

- O `playback` endpoint precisa considerar downloads em estado `ORGANIZED` (e `COMPLETED`), com `destination_folder`/`source_folder` resolvidos.
- Em dev (WSL2): `sudo apt install ffmpeg`; em prod: adicionar ffmpeg ao Dockerfile do backend.
- Packs de temporada com nomes fora do padrão `SxxExx` podem não enumerar — comportamento aceito (episódio cai fora da lista).
- Dois browsers assistindo o mesmo `(download_id, episode)` compartilham a sessão (touch compartilhado) — aceito na v1.
- A conversão `.srt` → WebVTT usa ffmpeg (`-f webvtt`), sem estado próprio.
