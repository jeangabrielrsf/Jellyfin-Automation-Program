# CONTEXT.md — Glossário do Domínio

## Descoberta Passiva

Modo de navegação onde o sistema apresenta conteúdo curado sem exigir que o usuário faça buscas ativas. A página "Explorar" implementa este modo — mostra um banner de destaque e fileiras curadas (tendências, recém adicionados, em alta, animes da temporada, clássicos imperdíveis) que mudam com frequência. Sem filtros — a própria curadoria é o filtro.

## Busca Orientada

Modo de navegação onde o usuário sabe mais ou menos o que quer e usa ferramentas para refinar a busca. A página "Buscar" implementa este modo com duas abas: "Texto" (busca por nome) e "Filtros" (6 filtros: tipo, gênero, provider, ano, nota, ordenação). Os dois modos são separados porque o TMDB não permite combinar busca por texto com filtros de descoberta na mesma chamada.

## Banner de Destaque

Elemento visual no topo da página Explorar que mostra o conteúdo #1 em tendência, com rotação entre os top 5 (um por dia). Exibe backdrop em tela cheia, título, ano, nota, gêneros, sinopse curta, provider de streaming, duração, e botão "Ver detalhes". Mostra filmes e séries misturados, sem distinção.

## Fileiras Curadas

Linhas horizontais de conteúdo na página Explorar, cada uma com propósito claro e mudança frequente. As 5 fileiras (em ordem de relevância temporal): Tendências da semana, Recém adicionados (streamings), Em alta no streaming, Animes da temporada, Clássicos imperdiveis. Cada fileira tem scroll horizontal com setas (← →) e mostra ~6-8 cards no desktop, ~3-4 no mobile.

## Modos de Busca

As duas abas da página Buscar: "Texto" (campo de busca + resultados) e "Filtros" (6 filtros em grid 2x3 + botão "Aplicar filtros" + resultados). Quando o usuário digita texto, usa o endpoint `/search/multi` do TMDB (sem filtros). Quando usa filtros, usa `/discover/movie` ou `/discover/tv` (sem texto). Os filtros mantêm estado durante a sessão.

## Busca de Torrents

Fluxo de encontrar torrents para uma mídia específica (filme, série ou anime) via Jackett. O usuário seleciona uma mídia no TMDB, escolhe temporada/episódio (se aplicável), e o sistema busca torrents nos indexers configurados.

## Filtros Server-side

Preferências que afetam a busca ao Jackett e o scoring dos resultados. Definem o que o sistema prioriza ao buscar.

- **Quality**: Qualidade preferida (1080p, 720p, 2160p, 480p). Afeta o scoring — torrents com a qualidade preferida recebem mais pontos.
- **Language**: Idioma preferido (Legendado, Dublado, Dual Áudio). Afeta o scoring — torrents com o idioma preferido recebem mais pontos.

## Filtros Client-side

Refinamentos aplicados sobre os resultados já carregados, sem nova requisição ao Jackett. Permitem ao usuário filtrar e ordenar a lista de torrents retornados.

- **Quality chips**: Multi-select de qualidades. Vem pré-selecionado com base na preferência server-side, mas o usuário pode ajustar.
- **Language chips**: Multi-select de idiomas. Vem pré-selecionado com base na preferência server-side, mas o usuário pode ajustar.
- **Seeds mínimos**: Número mínimo de seeders para exibir um torrent.
- **Freeleech**: Toggle para mostrar apenas torrents freeleech (DownloadVolumeFactor = 0).
- **Ordenação**: Critério de ordenação da lista (Score, Seeds, Data de publicação, Tamanho).
- **Busca no título**: Filtro de texto que filtra torrents cujo título contém o termo buscado.

## Seletor de Título

Dropdown que permite escolher qual título TMDB usar na busca de torrents. O TMDB retorna múltiplos títulos (original, inglês, português, alternativos), e diferentes trackers usam nomes diferentes.

Exemplo para anime:
- 進撃の巨人 (Original japonês)
- Attack on Titan (Inglês internacional)
- Shingeki no Kyojin (Romanização)

O seletor resolve casos onde o título original não bate com os nomes usados nos trackers.

## Busca Customizada

Texto livre que sobrescreve a query de busca ao Jackett. Usado para casos específicos onde o usuário precisa de controle total (buscar "REPACK", "PROPER", nome de grupo específico, etc).

Movida para "Opções avançadas" (accordion) para não poluir a UI principal. A maioria dos usuários usa o Seletor de Título + Filtros Server-side.

## Paginação Híbrida

Estratégia de paginação que mostra 20 resultados iniciais (os de maior score) e um botão "Carregar mais" para exibir mais 20. Mantém a noção do total de resultados sem sobrecarregar a UI.

## Novos Campos do Jackett

Campos retornados pela API do Jackett que serão capturados e usados na UI:

- **PublishDate**: Data de publicação do torrent. Usado para ordenação por data e filtro "recentes".
- **Grabs**: Número de downloads completados. Indicador de confiabilidade — torrents com muitos grabs são mais confiáveis.
- **DownloadVolumeFactor**: Fator de volume de download. `0.0` = freeleech (não conta download no ratio). Útil para usuários de trackers privados.
- **Files**: Número de arquivos no torrent. Distingue pack de temporada (dezenas de arquivos) de episódio avulso (1-3 arquivos).

## Playback

Assistir a um conteúdo concluído diretamente no site, sem depender do Jellyfin. O backend serve o vídeo do filesystem local (opção A — stream direto via FastAPI), com transcodificação on-demand via ffmpeg no container do backend quando o browser não suporta o codec (MKV/HEVC).

## Sessão de Streaming

Instância ativa de playback: um processo ffmpeg + diretório temporário de segmentos HLS no container. Convivência entre `download_id` da mídia e o arquivo-alvo resolvido por heurística (filme: maior arquivo excluindo samples; série: casa `season`/`episode` com padrão `SxxExx`). Ciclo de vida: touch-on-request (playlist ou segmento atualiza `last_access`, matando o processo após ~60s idle) com sweeper lazy em background.

**Episódios:** sessão é keyed por `download_id + episode` — um pack de temporada vira múltiplos episódios enumerados (`GET /api/downloads/{id}/playback` retorna lista `files`). Tocar um episódio novo mata a sessão anterior do mesmo download (libera semáforo imediato).

## Decisões de Playback

1. **Stream direto** (não via Jellyfin) — `FileResponse` com suporte a Range/206 nativo do Starlette.
2. **Transcode on-demand** com ffmpeg no comando Docker do backend para codecs não suportados pelo browser.
3. **Formato HLS** (`m3u8` + segmentos) servido ao player hls.js no frontend.
4. **Detecção smart** com ffprobe + cache (key = path+mtime) para decidir direto vs transcode.
5. **Limite de 3 sessões simultâneas** via semáforo, retornando 503 sob pressão.
6. **Legendas v1**: apenas `.srt` sidecar servido como WebVTT. **Pendência**: suporte completo a legendas embutidas (multitrilha, idiomas, forced) — deve ser implementado como feature futura por mudar o mapeamento de trilhas do ffmpeg.
7. **Contrato de API**: `GET /api/downloads/{id}/playback` → `{ mode, files: [{ episode, title, url }], subtitle_url? }`; stream via `/api/stream/{download_id}/playlist.m3u8?episode=N` (sessão lazy no primeiro request, reusa nos seguintes).
8. **UI**: rota dedicada `/watch/:downloadId` com sidebar de episódios (estilo Netflix); botão "Assistir" apenas na página Detail.
9. **Sem resume** na v1; sem auth extra (consistente com o resto do app); mobile com controls nativos do `<video>`.
10. **Testes**: unit tests da heurística/decisão/ciclo de vida com mocks; integração ffmpeg real marcada `@pytest.mark.integration` (pulada por default). ffmpeg instalado no WSL2 (dev) e no Dockerfile do backend (prod).
