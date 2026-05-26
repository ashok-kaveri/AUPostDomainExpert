# AU Post RAG Sync Flow

## Knowledge Stores

| Store | ChromaDB Collection | Source Types |
|---|---|---|
| Domain knowledge | `aupost_knowledge` | pluginhive_docs, pluginhive_seeds, sheets, wiki, app, aupost_api, qa_feedback |
| Code knowledge | `aupost_code_knowledge` | automation (POM + specs), backend, frontend |

## Normal Sync Policy

| Source | Repo / URL | Default Branch | When To Sync |
|---|---|---|---|
| `codebase` (automation) | `/Users/madan/Documents/AU_Post/aupost-test-automation` | Ask QA | After new specs/POMs merged |
| `codebase` (backend) | `/Users/madan/Documents/shopify-australia-post-app` | `master` | After backend PR merged |
| `codebase` (frontend) | `/Users/madan/Documents/shopify-au-post-web-client` | `main` | After frontend PR merged |
| `wiki` | `/Users/madan/Documents/aupost-wiki` | main | After new wiki pages added |
| `pluginhive_docs` | PluginHive official AU Post docs | N/A (web scrape) | When docs page updated |
| `pluginhive_seeds` | PluginHive seed URLs | N/A (web scrape) | When seed knowledge stale |
| `sheets` | Google Sheets (eParcel + MyPost) | N/A (Google API) | After new test cases added to sheets |
| `aupost_api` | Local AU Post API knowledge file | N/A | When AU Post API changes |
| `app` | Live app UI knowledge | N/A | When app UI changes |

## Partial Ingest Behavior

Partial `--sources` runs are ADDITIVE:
```python
# Only clears on full default rebuild (all sources >= _DEFAULT_SOURCES)
if clear is None:
    should_clear = (set(active_sources) >= set(_DEFAULT_SOURCES))
```

Do NOT use `--clear` for normal partial syncs unless QA explicitly wants to reset that source type.

## Full Rebuild Policy

Run full rebuild (`python -m ingest.run_ingest`) only when:
- QA explicitly asks for a full rebuild
- ChromaDB collection is corrupt or missing
- After major app architecture changes affecting all source types

Full rebuild clears `aupost_knowledge` collection before re-adding all sources.

## Recommended QA Prompts

Ask QA before starting:
- For automation sync: "Which branch should I pull? (current: <branch>)"
- For full rebuild: "This will clear all domain knowledge and rebuild from scratch. Confirm?"

## Dirty Repo Check

Run before any `git pull`:
```bash
cd <repo_path>
git status
```
- Clean → safe to pull
- Dirty (uncommitted changes) → stop, report to QA, do not auto-stash

## Source Count Verification

After sync, check chunk counts using the Python REPL pattern (not an import — run as script):
```bash
cd /Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert
PYTHONPATH=. .venv/bin/python -c "
from rag.code_indexer import get_index_stats
stats = get_index_stats()
print(stats)
# Expected: {'frontend': N, 'backend': M, 'total': T}
"
```

For domain knowledge counts, query ChromaDB directly:
```bash
PYTHONPATH=. .venv/bin/python -c "
import chromadb
from config import CHROMA_PERSIST_DIRECTORY, AUPOST_COLLECTION_NAME
client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)
col = client.get_collection(AUPOST_COLLECTION_NAME)
print('Total chunks:', col.count())
"
```

Expected baseline counts (as of last full rebuild):
- `aupost_knowledge`: ~7,400+ chunks total
- `aupost_code_knowledge`: ~7,400+ chunks total (automation ~1,887, backend ~3,956, frontend ~1,594)
