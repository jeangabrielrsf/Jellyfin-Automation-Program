# CONTEXT.md — Glossário do Domínio

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
