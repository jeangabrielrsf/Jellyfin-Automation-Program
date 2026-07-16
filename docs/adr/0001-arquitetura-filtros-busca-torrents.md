# ADR 0001: Arquitetura de Filtros da Busca de Torrents

## Status

Aceito

## Contexto

A busca de torrents retornava resultados "sujos" — torrents com qualidade ou idioma errado apareciam no topo da lista, forçando o usuário a ativar a "Busca Customizada" e digitar manualmente termos como "1080p" ou "S01E05" para filtrar. Para animes e donghuas, o problema era pior: o título original (japonês/chinês) não batia com os nomes usados nos trackers (inglês), exigindo digitação manual constante.

Além disso, a UI não expunha os filtros `quality` e `language` que já existiam no backend — eles eram hardcodados como "1080p" e "legendado" na chamada da API.

## Decisão

Implementar uma arquitetura de filtros em duas camadas:

**Filtros Server-side** (no topo da aba "Torrents"):
- Quality e Language expostos como controles de UI (não mais hardcodados)
- Funcionam como **preferências de scoring** — afetam o ranking dos resultados, mas não filtram rigidamente
- O backend continua retornando todos os resultados, mas prioriza os que batem com as preferências

**Filtros Client-side** (toolbar que aparece após resultados carregarem):
- Quality chips e Language chips **pré-selecionados** com base nas preferências server-side, mas ajustáveis pelo usuário
- Seeds mínimos, toggle Freeleech, ordenação (Score/Seeds/Data/Tamanho), busca por texto no título
- Aplicados instantaneamente sobre os resultados já carregados, sem nova requisição

**Seletor de Título** (substitui a Busca Customizada como controle principal):
- Dropdown com os títulos TMDB disponíveis (original, inglês, português, alternativos)
- Resolve 90% dos casos de anime/donghua sem digitação manual
- A Busca Customizada é movida para "Opções avançadas" (accordion) como fallback para casos específicos (buscar "REPACK", "PROPER", nome de grupo)

**Paginação Híbrida**:
- Mostra 20 resultados iniciais (os de maior score)
- Botão "Carregar mais" para exibir mais 20
- Mantém a noção do total de resultados sem sobrecarregar a UI

**Novos campos do Jackett capturados**:
- `PublishDate` — ordenação por data
- `Grabs` — indicador de confiabilidade (downloads completados)
- `DownloadVolumeFactor` — badge "Freeleech" + filtro
- `Files` — distingue pack de temporada de episódio avulso

## Consequências

### Positivas
- Resultados mais limpos sem necessidade de digitação manual na maioria dos casos
- Flexibilidade para ajustar filtros após a busca (não precisa refazer a busca ao Jackett)
- UX mais clara: separação entre "configurar busca" (server-side) e "refinar resultados" (client-side)
- Seletor de título resolve o problema de anime/donghua de forma elegante
- Paginação híbrida equilibra performance e usabilidade

### Negativas
- Dois conjuntos de filtros (server-side e client-side) pode confundir usuários iniciantes — mitigado pela pré-seleção dos chips client-side com base nas preferências server-side
- Capturar 4 novos campos do Jackett aumenta ligeiramente o payload da resposta — impacto negligível
- Seletor de título depende do TMDB retornar múltiplos títulos — se o TMDB não tiver o título inglês, o usuário ainda precisa usar a Busca Customizada

### Riscos
- Se o TMDB não retornar títulos alternativos suficientes, o Seletor de Título não resolve todos os casos de anime/donghua — mitigado pela Busca Customizada em "Opções avançadas"

## Alternativas Consideradas

**Alternativa 1: Filtros server-side como filtro duro**
- Backend filtraria rigidamente por quality/language, retornando apenas os que batem
- Rejeitada: reduz flexibilidade — se o usuário quisesse ver outras qualidades, precisaria refazer a busca

**Alternativa 2: Tudo em um único conjunto de filtros**
- Server-side e client-side misturados numa barra só
- Rejeitada: difícil deixar claro quais filtros exigem nova busca vs quais são instantâneos

**Alternativa 3: Manter Busca Customizada como controle principal**
- Não implementar Seletor de Título, apenas melhorar a Busca Customizada
- Rejeitada: exige digitação manual constante para anime/donghua, UX inferior

**Alternativa 4: Paginação tradicional (Anterior/Próxima)**
- 20 resultados por página com botões de navegação
- Rejeitada: perde a noção do total de resultados, mais cliques para ver mais

**Alternativa 5: Infinite scroll**
- Carregar mais ao rolar para baixo
- Rejeitada: perde a noção de "quantos resultados existem", difícil de implementar com React Query
