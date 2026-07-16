# ADR 0004: Deepen Download model with lifecycle behavior

## Status

Aceito

## Contexto

O `Download` model (54 linhas) é um data container anêmico — zero behavior. Toda a lógica do ciclo de vida está espalhada:

- **Hash extraction:** `_extract_hash_from_magnet()` no router `downloads.py` (linhas 36-41)
- **Status transitions:** `download_worker.py` (linhas 95-108) mapeia estado do qBittorrent para `DownloadStatus` e faz transições diretamente
- **Serialização:** `_download_to_dict()` no worker (linhas 256-284) e serialização manual no router (linhas 164-192) — duas cópias da mesma lista de ~24 campos
- **Validação de transições:** nenhuma — qualquer status pode ser setado para qualquer outro

Isso viola locality — o conhecimento do ciclo de vida do download está espalhado em 3 arquivos. Se alguém adicionar um novo status ou mudar uma regra de transição, precisa caçar em múltiplos lugares.

## Decisão

Adicionar quatro métodos ao `Download` model:

### `transition_to(new_status)`

Muda o status com validação de transições válidas. Lança `ValueError` se a transição for inválida.

**Tabela de transições válidas:**

```python
VALID_TRANSITIONS = {
    DownloadStatus.PENDING: {DownloadStatus.DOWNLOADING, DownloadStatus.FAILED, DownloadStatus.CANCELLED},
    DownloadStatus.DOWNLOADING: {DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED},
    DownloadStatus.COMPLETED: {DownloadStatus.ORGANIZED, DownloadStatus.FAILED},  # FAILED se organização falhar
    DownloadStatus.FAILED: {DownloadStatus.PENDING},  # retry
    DownloadStatus.CANCELLED: set(),  # terminal
    DownloadStatus.ORGANIZED: set(),  # terminal
}
```

**Nota:** `COMPLETED → FAILED` é permitido para capturar falhas do `OrganizerService` (ex: disco cheio, permissões, arquivo não encontrado). O `error_message` diferencia falha de download vs falha de organização.

### `extract_hash(magnet_link)` — `@staticmethod`

Extrai hash btih de um magnet link. Move `_extract_hash_from_magnet` do router para o model.

```python
@staticmethod
def extract_hash(magnet_link: str) -> Optional[str]:
    match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})", magnet_link)
    return match.group(1).lower() if match else None
```

**Uso:**
```python
download.torrent_hash = Download.extract_hash(download.magnet_link)
```

### `is_active()`

Retorna `True` se o download está em estado ativo (`PENDING`, `DOWNLOADING`, `COMPLETED`). Útil para queries e lógica de negócio (ex: não cancelar downloads já finalizados).

```python
def is_active(self) -> bool:
    return self.status in {DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.COMPLETED}
```

### `to_dict()`

Serializa o Download para dict. Substitui `_download_to_dict()` no worker e a serialização manual no router.

```python
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "tmdb_id": self.tmdb_id,
        "title": self.title,
        "type": self.type.value if self.type else None,
        # ... todos os campos
    }
```

**Uso:**
```python
# Worker
await self.broadcast_callback({"type": "download_update", "data": download.to_dict()})

# Router
return download.to_dict()
```

## Consequências

### Positivas

- **Locality:** ciclo de vida do download concentra em um módulo
- **Leverage:** uma interface, N call sites (router, worker, testes)
- **Testabilidade:** state machine testável sem DB ou qBittorrent
- **Delete duplicated code:** remove `_download_to_dict` do worker e serialização manual do router
- **Fail-fast:** `transition_to` lança `ValueError` em transições inválidas, força o caller a pensar nas regras

### Negativas

- Model fica mais "gordo" — mas é behavior que já deveria estar ali
- Se alguém adicionar um novo status, precisa atualizar `VALID_TRANSITIONS` — mas isso é explícito e auditável

### Riscos

- Se o `OrganizerService` falhar repetidamente, o download fica em `COMPLETED` → `FAILED` → `PENDING` em loop. Mas isso é um problema de retry logic, não de model.

## Alternativas Consideradas

**Alternativa 1: `transition_to` retorna `bool` em vez de lançar exceção**

Retornar `True` se transição válida, `False` se inválida.

Rejeitada: transições inválidas são bugs de lógica, não condições normais. Fail-fast força o caller a pensar nas regras. Consistente com Python — `dict["key"]` lança `KeyError`, não retorna `None`.

**Alternativa 2: `extract_hash` como método de instância**

`download.extract_hash()` lê `self.magnet_link` e popula `self.torrent_hash`.

Rejeitada: @staticmethod é mais flexível — pode ser usado antes de criar o Download (ex: validar magnet no router). Consistente com o código atual (`_extract_hash_from_magnet` é função livre).

**Alternativa 3: Novo status `ORGANIZATION_FAILED`**

Adicionar status específico para falha de organização.

Rejeitada: adiciona complexidade. `FAILED` já existe, e `error_message` diferencia o motivo. YAGNI.

**Alternativa 4: `to_dict` no router com Pydantic response model**

Criar `DownloadResponse(BaseModel)` e usar `response_model` no FastAPI.

Rejeitada: Pydantic response model é uma camada extra. `to_dict()` é suficiente para os dois casos de uso (WebSocket e HTTP). Se no futuro precisar de validação de saída, pode adicionar Pydantic.

## Implementação

Arquivos a criar/modificar:

- `backend/app/models/download.py` — adicionar `VALID_TRANSITIONS`, `transition_to`, `extract_hash`, `is_active`, `to_dict`
- `backend/app/routers/downloads.py` — remover `_extract_hash_from_magnet`, usar `Download.extract_hash()`, usar `download.to_dict()`
- `backend/app/services/download_worker.py` — remover `_download_to_dict()`, usar `download.to_dict()`, usar `download.transition_to()`
- `backend/tests/test_download_model.py` (novo) — testes da state machine e métodos
