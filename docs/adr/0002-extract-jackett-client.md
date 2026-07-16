# ADR 0002: Extrair JackettClient de QBittorrentService

## Status

Aceito

## Contexto

O `QBittorrentService` continha 132 linhas de lógica da API do Jackett:

- `_get_fresh_jackett_link` (105 linhas) — busca no Jackett por link fresco quando o original expira. Constrói URL do Jackett, monta query params, parseia resultados, faz matching por nome (3 estratégias: exact, word, substring).
- `_download_torrent_via_jackett` (27 linhas) — baixa .torrent via Jackett proxy download.

Paralelamente, o `JackettScraper` também constrói URLs do Jackett, usa a mesma API key, e parseia os mesmos `Results[]` da API.

Dois módulos com conhecimento duplicado sobre a API do Jackett, violando locality — o conhecimento de como falar com o Jackett está espalhado em vez de concentrado em um único módulo.

## Decisão

Criar um adapter `JackettClient` em `backend/app/clients/jackett_client.py` que encapsula todo o conhecimento da API do Jackett:

**Métodos públicos:**

1. `search(query, category)` → retorna `list[dict]` (os `Results[]` brutos do Jackett)
2. `download_torrent_file(tracker_id, path, filename)` → retorna `bytes` (o .torrent)
3. `find_fresh_link(torrent_name)` → retorna `dict | None` (com `link` e `tracker_id`)

**Localização:**

Criar diretório `backend/app/clients/` para adapters de APIs externas. Isso separa adapters (conhecimento de APIs externas) de services (lógica de domínio).

**Construção e injeção:**

- `JackettClient(db=db)` — lê `jackett_url`, `jackett_api_key`, `jackett_timeout` via `get_config()` no `__init__`, cria seu próprio `httpx.AsyncClient`.
- `QBittorrentService(db=None, jackett_client=None)` — injeção via construtor com default. Se `jackett_client` não for fornecido, cria um `JackettClient(db=db)`.
- `JackettScraper(db=None, jackett_client=None)` — mesma abordagem. Para de gerenciar `httpx.AsyncClient` diretamente e usa `JackettClient.search()`.

**Parsing e scoring:**

O `JackettClient.search()` retorna `list[dict]` brutos. O `JackettScraper` recebe esses dicts e faz:
- Parsing para `TorrentResult`
- Extração de quality/language/release_group do título
- Cálculo de score
- Formatação de size

Isso é conhecimento de domínio do scraper (como interpretar resultados de busca), não do adapter (como falar com a API do Jackett).

O `JackettClient.find_fresh_link()` absorve toda a lógica de matching (exact → word → substring) que hoje está espalhada em 3 loops dentro do `QBittorrentService`. O consumidor só recebe o link pronto.

## Consequências

### Positivas

- **Locality:** conhecimento de Jackett concentra em um único módulo (`JackettClient`)
- **Leverage:** dois adapters (`QBittorrentService` e `JackettScraper`) justificam o seam
- **Testabilidade:** testes podem injetar um `JackettClient` mock sem precisar mockar `httpx` internamente
- **Interface shrinks:** consumidores não sabem que existe `/api/v2.0/indexers/all/results`
- **Delete duplicated code:** 132 linhas de Jackett saem de `QBittorrentService`, parsing duplicado sai de `JackettScraper`

### Negativas

- Novo diretório `clients/` adiciona uma camada de indireção
- Injeção com default mantém o padrão atual de criar instâncias por requisição (não resolve o problema de caching de autenticação do qBittorrent)

### Riscos

- Se o `JackettClient` crescer muito (ex: suportar múltiplos indexers com APIs diferentes), pode precisar ser refatorado em uma interface/Protocol. Mas isso é YAGNI por enquanto — só temos um Jackett.

## Alternativas Consideradas

**Alternativa 1: Interface/Protocol para JackettClient**

Criar `JackettProtocol` (ABC) e implementar `JackettClient` como concretização.

Rejeitada: só temos um Jackett na prática. Interface sem múltiplos implementadores é YAGNI. O seam existe porque dois módulos consomem o mesmo adapter, não porque precisamos de polimorfismo.

**Alternativa 2: Manter JackettClient em `services/`**

Criar `backend/app/services/jackett_client.py` em vez de novo diretório.

Rejeitada: mistura adapters de APIs externas com services de domínio. O diretório `clients/` deixa claro que esses módulos encapsulam conhecimento de APIs externas.

**Alternativa 3: Tornar JackettClient um singleton global**

Criar uma instância global de `JackettClient` e reutilizar em todos os consumers.

Rejeitada: introduz estado global e dificulta testes. Injeção com default é suficiente — cada consumer cria seu próprio `JackettClient` se não for fornecido.

**Alternativa 4: Mover parsing e scoring para JackettClient**

Fazer `JackettClient.search()` retornar `list[TorrentResult]` em vez de `list[dict]`.

Rejeitada: parsing e scoring são conhecimento de domínio do scraper (como interpretar resultados), não do adapter (como falar com a API). O adapter deve retornar dados brutos; o consumidor decide como interpretá-los.

## Implementação

Arquivos a criar/modificar:

- `backend/app/clients/__init__.py` (novo)
- `backend/app/clients/jackett_client.py` (novo)
- `backend/app/services/qbittorrent_service.py` — remover `_get_fresh_jackett_link` e `_download_torrent_via_jackett`, receber `jackett_client` via injeção
- `backend/app/scrapers/jackett_scraper.py` — receber `jackett_client` via injeção, usar `jackett_client.search()` em vez de construir URLs diretamente
- `backend/tests/test_jackett_client.py` (novo) — testes do adapter
- `backend/tests/test_qbittorrent_service.py` — atualizar para injetar `JackettClient` mock
