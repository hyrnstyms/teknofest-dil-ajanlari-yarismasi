from backend.app.rag.qdrant_store import QdrantStore, LEGAL_COLLECTION
store = QdrantStore()
res, _ = store.client.scroll(
    collection_name=LEGAL_COLLECTION,
    limit=1000,
    with_payload=True,
    with_vectors=False
)
empty_count = 0
sources = {}
for p in res:
    if not p.payload: continue
    t = p.payload.get('text', '').strip()
    src = p.payload.get('source', 'unknown')
    if src not in sources:
        sources[src] = {'total': 0, 'empty': 0}
    sources[src]['total'] += 1
    if not t:
        empty_count += 1
        sources[src]['empty'] += 1

print(f'Total chunks: {len(res)}')
print(f'Empty chunks: {empty_count}')
print('Breakdown by source:')
for k, v in sources.items():
    print(f'  {k}: {v["empty"]}/{v["total"]} empty')
