# ADR 0007: Separacao entre Explorar (Descoberta Passiva) e Buscar (Busca Orientada)

## Status

Aceito

## Contexto

A pagina Explorar tinha 13 fileiras hardcoded + 4 filtros cosmeticos que apenas reordenavam resultados ao inves de descobrir conteudo novo. O usuario nao sabia por onde comecar, via conteudo irrelevante (ex: "Nos Cinemas" num app de download), e os filtros nao agregavam valor real.

A pagina Buscar era apenas um campo de texto que fazia busca no TMDB — sem filtros para refinar resultados por genero, provider, ano, nota, etc.

As duas paginas tentavam fazer descoberta e busca ao mesmo tempo, sem fazer nenhum dos dois direito.

## Decisao

Separar claramente as responsabilidades:

**Pagina Explorar = Descoberta Passiva**
- Proposito: "Nao sei o que quero, me mostre coisas legais"
- Sem filtros — a propria curadoria e o filtro
- Layout:
  - Banner de destaque no topo (top 1 trending com rotacao entre top 5, um por dia)
  - 5 fileiras curadas com scroll horizontal e setas:
    1. Tendencias da semana
    2. Recem adicionados (nos streamings, ultimos 30 dias)
    3. Em alta no streaming (populares na Netflix, Disney+, etc)
    4. Animes da temporada
    5. Classicos imperdiveis (top rated de todos os tempos)
  - Carregamento progressivo (todas chamadas em paralelo, cada fileira aparece quando pronta)
  - Banner mostra: backdrop, titulo, ano, nota, generos, sinopse curta, provider, duracao, botao "Ver detalhes"

**Pagina Buscar = Busca Orientada**
- Proposito: "Sei mais ou menos o que quero, me ajude a encontrar"
- Layout com tabs no topo:
  - **Aba Texto**: campo de busca + grid/lista de resultados (toggle de visualizacao)
  - **Aba Filtros**: 6 filtros em grid 2x3 + botao "Aplicar filtros" + resultados
- Filtros disponiveis:
  1. Tipo de midia (single select: Filme/Serie/Anime/Todos)
  2. Genero (multi select)
  3. Provider de streaming (multi select)
  4. Faixa de ano (dois campos: De/Ate)
  5. Nota minima (valor unico)
  6. Ordenacao (Popularidade/Nota/Votos/Lancamento/Titulo)
- Modos separados: texto e filtros nao se misturam (limitacao do TMDB)
- Resultados: grid de cards (padrao) ou lista com informacoes estendidas (toggle)
- Paginacao: botao "Carregar mais" (20 resultados por vez)
- Estado dos filtros persiste durante a sessao
- Empty state: mensagem com sugestoes (remover filtros, buscar outro termo, ver sugestoes populares)

## Consequências

### Positivas
- Cada pagina tem proposito claro e focado
- Explorar oferece curadoria sem sobrecarregar (5 fileiras ao inves de 13)
- Buscar oferece controle granular com filtros que realmente mudam o resultado
- UX mais intuitiva: usuario escolhe o modo que faz sentido para o momento
- Remove conteudo irrelevante (ex: "Nos Cinemas") da pagina Explorar
- Tabs na pagina Buscar deixam claro que texto e filtros sao modos separados

### Negativas
- Dois modos na pagina Buscar podem confundir usuarios que esperam combinar texto + filtros
- Implementacao mais complexa (duas paginas com logicas diferentes)
- Filtros na aba "Filtros" exigem clique em "Aplicar" (menos fluido que atualizacao automatica)

### Riscos
- Limitacao do TMDB: busca por texto (`/search/multi`) nao aceita filtros, e descoberta (`/discover`) nao aceita texto. Mitigado pela separacao clara em tabs.
- Se o usuario quiser combinar texto + filtros, precisa usar a pagina de detalhes apos a busca

## Alternativas Consideradas

**Alternativa 1: Manter Explorar como esta, so remover fileiras irrelevantes**
- Rejeitada: filtros cosmeticos continuam nao agregando valor, pagina continua sem proposito claro

**Alternativa 2: Unificar Explorar e Buscar em uma pagina so**
- Uma pagina com campo de texto + filtros laterais
- Rejeitada: mistura descoberta passiva com busca orientada, resulta em UX confusa

**Alternativa 3: Filtros na pagina Buscar com atualizacao automatica**
- A cada mudanca de filtro, resultados atualizam sozinhos (debounce 300ms)
- Rejeitada: experiencia ruim em mobile (muitas chamadas, tela fica carregando), usuario prefere controle explicito com botao "Aplicar"

**Alternativa 4: Paginacao tradicional (Anterior/Proxima) na pagina Buscar**
- Rejeitada: botao "Carregar mais" e mais simples e ja funciona bem na pagina de torrents

**Alternativa 5: Visualizacao em lista como padrao**
- Lista com informacoes estendidas (poster, titulo, ano, nota, generos, provider, sinopse)
- Rejeitada: grid de cards e mais visual e ocupa menos espaco, lista fica como opcao via toggle
