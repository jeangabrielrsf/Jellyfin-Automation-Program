# ADR 0008: Streaming de playback direto com transcode on-demand

## Status

Aceito

## Contexto

O usuário quer assistir conteúdos concluídos diretamente no site. Os arquivos de mídia ficam no filesystem local (`MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`) e o Jellyfin roda externamente (na máquina Windows host). Duas arquiteturas possíveis:

- **Stream direto via FastAPI:** o backend serve o arquivo do disco com `FileResponse` (suporte nativo a Range/206 do Starlette). Simples e desacoplado do Jellyfin, mas browsers só tocam H.264/MP4/WebM nativamente — a maioria dos torrents é MKV/H.265, que não reproduz sem transcodificação.
- **Proxy do Jellyfin:** o backend repassa o stream do Jellyfin, que já tem transcodificação via ffmpeg. Toca tudo, mas acopla a feature ao Jellyfin (credenciais, sessão, API própria, dependência do serviço estar de pé).

## Decisão

**Stream direto via FastAPI, com transcodificação on-demand via ffmpeg no container do backend** para codecs não suportados pelo browser:

1. **Stream direto** — `FileResponse` com Range/206 nativo do Starlette.
2. **Transcode on-demand** — ffmpeg no container Docker do backend; disparado apenas quando o arquivo não toca nativo.
3. **Formato HLS** (`m3u8` + segmentos) — servido ao player hls.js no frontend.
4. **Detecção smart** — ffprobe + cache (key = path+mtime) para decidir direto vs transcode.
5. **Sessão de streaming** — processo ffmpeg + diretório temporário de segmentos; touch-on-request com timeout de 60s idle e sweeper lazy em background.
6. **Limite de 3 sessões simultâneas** — semáforo, retornando 503 sob pressão.
7. **Resolução de arquivo por `download_id`** — heurística: filme → maior arquivo excluindo samples; série → casa `season`/`episode` com padrão `SxxExx`; pack de temporada → lista enumerada de episódios (sessão keyed por `download_id + episode`).

## Consequências

### Positivas

- **Desacoplamento do Jellyfin:** assistir não depende do Jellyfin estar de pé nem de credenciais.
- **Controle total do pipeline:** decisões de codec/sessão/limite ficam no nosso domínio, seguindo o padrão de config do projeto.
- **Um player só:** hls.js serve tanto os arquivos diretos H.264 quanto o transcode HLS — code path único no frontend.

### Negativas

- **CPU do backend:** transcodificar 1080p com libx264 pesa; o limite de 3 sessões e o kill por timeout mitigam, mas o container precisa de recursos.
- **Ffprobe no request path:** adiciona ~100-300ms na primeira detecção; mitigado por cache.
- **Sem transcodificação para o que o Jellyfin faria por nós** (subs embutidos, codecs exóticos) — aceito em troca da simplicidade.

### Riscos

- Processos ffmpeg órfãos e disco cheio de segmentos se a limpeza falhar — mitigado por sweeper + timeout.
- Dois players/abas do mesmo download compartilham sessão (touch compartilhado) — comportamento aceito para v1.

## Alternativas Consideradas

**Alternativa 1: Proxy do Jellyfin**

Rejeitada: acoplamento com serviço externo, credenciais e API própria; falha se o Jellyfin estiver fora. Não seria "assistir direto do site", seria "assistir via Jellyfin com nossa UI".

**Alternativa 2: MP4 progressivo (pipe) em vez de HLS**

Rejeitada: seeking ruim — pular adiante exige esperar o ffmpeg alcançar a posição. HLS dá seeking por segmentos e o mesmo player serve direto e transcode.

**Alternativa 3: Transcodificação preguiçosa (converter na conclusão do download)**

Rejeitada: converte tudo que baixar, mesmo o que nunca for assistido; perde qualidade da capa; enche disco.

**Alternativa 4: Sem limite de sessões simultâneas**

Rejeitada: N abas abertas saturam a CPU do container. Limite de 3 com 503 é proteção barata.

## Implementação

- `backend/app/services/stream_service.py` (novo) — decisão direct-vs-transcode, cache de ffprobe, gestão de sessões, heurística de resolução de arquivo
- `backend/app/routers/stream.py` (novo) — `GET /api/downloads/{id}/playback`, `GET /api/stream/{download_id}/playlist.m3u8`, segmentos, legenda WebVTT
- `backend/Dockerfile` — adicionar `ffmpeg`
- `frontend/src/pages/Watch.tsx` (novo) — player hls.js tela cheia com sidebar de episódios, rota `/watch/:downloadId`
- `frontend/src/pages/Detail.tsx` — botão "Assistir"
- `backend/tests/` — unit tests com mock (heurística, decisão, ciclo de vida); integração ffmpeg marcada `@pytest.mark.integration`
