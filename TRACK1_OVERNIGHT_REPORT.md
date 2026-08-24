# Track 1 Overnight Report

## Scope and safety

- Branch verified before work: `track1-rag-model`.
- No push, checkout, merge, rebase, reset, force operation, corpus deletion, or evaluation-gold edit was performed.
- Pre-existing worktree state was preserved: deleted `data/regulations/_ocr_temp_page_0.png` and untracked/generated `data/processed/documents.jsonl` were not touched or staged.
- Existing legacy `data/processed/chunks.jsonl` was not overwritten. Candidate chunks were generated at `C:\tmp\track1_candidate_chunks.jsonl`.

## Starting state

- Qdrant was reachable but had no collections/points.
- Tracked `chunks.jsonl`: 6,350 rows, legacy schema.
- Generated `documents.jsonl`: 21 regulations. `resmi_yazisma_yonetmeligi.pdf` had 0 extracted characters and `resmigazete.pdf` had only 183; neither was silently treated as a complete corpus source.
- `rag_test_seti.jsonl`: 5 targeted 3071 questions. Gold/evaluation files were treated as read-only.
- Canonical QA: 290 raw, 266 active, 24 inactive, 258 active corpus-supported, 8 active unsupported.

## Changes

1. Added `--output` to `scripts/chunk_documents.py`, allowing candidate generation without overwriting the tracked corpus.
2. Added `--chunks-file` and `--device {cpu,cuda}` to `scripts/index_qdrant.py`. CPU remains the production-safe default; CUDA is an explicit one-off indexing choice.
3. Made embedding/Qdrant dimension mismatch fail closed instead of being caught and reported as a skipped connection check.
4. Fixed evaluator source canonicalization by deriving law-name-to-law-number aliases from the corpus. This prevents valid results such as `Türk Borçlar Kanunu` / `6098` from being scored as misses.
5. Added the FastAPI upload runtime dependency `python-multipart` to `requirements.txt`.

## Corpus and index audit

| Item | Result |
|---|---:|
| Candidate chunks | 7,634 |
| Legal domain | 7,575 |
| Official-writing guide | 59 |
| Document knowledge | 0 |
| Qdrant legal points | 7,634 |
| Vector configuration | BGE-M3, 1,024 dimensions, cosine |
| Index behavior | deterministic UUID + existing-ID skip; no delete/recreate |

The 59 official-writing chunks come from `resmiyazısmakılavuzu.pdf`, not from the incomplete management-regulation scans. The candidate schema was validated for required IDs, text, metadata, and `rag_eligible=true` before indexing.

## Benchmarks

Broad and targeted sets are reported separately conceptually: all five targeted 3071 questions are corpus-unsupported, so the 258-record retrieval denominator below is the broad canonical QA set only.

| Run | Hit@1 | Hit@3 | Hit@5 | MRR | Evaluable | Runtime failures |
|---|---:|---:|---:|---:|---:|---:|
| Raw evaluator before alias fix (invalid canonicalization) | 8.53% | 10.08% | 10.47% | 9.38% | 258 | 0 |
| Corrected BGE-M3/Qdrant baseline | 41.09% | 55.81% | 59.69% | 48.55% | 258 | 0 |

Coverage across the evaluator input was 258/271 (95.20%): 8 broad active questions and 5 targeted questions were corpus-missing. The corrected run completed in about 90 seconds end-to-end after model load; per-query p50/p95 were not instrumented, so they are intentionally not claimed.

The apparent gain is an evaluator correctness fix, not a retrieval-model improvement. Remaining examples include genuine neighboring-article misses (for example 5271/259 -> 260 and 6098/19 -> 20), which establishes evidence for a later single-variable neighboring-context experiment.

## Indexing experiment log

- CPU batch 8/32 was too slow (roughly 10-15 points/minute in early measurements).
- CUDA batch 8 gave a large throughput improvement without OOM. The one-hour command boundary preserved all completed upserts.
- Idempotent resume with CUDA batch 16 completed the remaining points. Final count is exactly 7,634.
- CPU remains the default because production is expected to reserve the 4 GB GPU for Qwen; CUDA must be selected explicitly for offline indexing.

## Tests

- Targeted retrieval/evaluation tests before changes: 10 passed.
- Evaluation tests after alias fix: 8 passed.
- Full backend suite initially blocked at collection by missing `python-multipart`; dependency was added and installed without upgrading unrelated packages.
- Final full backend suite: **113 passed, 2 skipped**, 3 non-failing warnings, 180.20 seconds.

## Final configuration

- Embedding: `BAAI/bge-m3`, normalized dense embeddings, dimension 1,024.
- Vector store: Qdrant `legal_knowledge_v2`, cosine, 7,634 points.
- Chunking candidate: pre-chunked legal rows plus article/paragraph chunks, separately validated; tracked legacy file preserved.
- Reranker: none (no clean before/after experiment completed).
- LLM: existing Qwen2.5 3B baseline unchanged; 7B was not attempted because retrieval/corpus blockers remain and no answer-quality benchmark was ready.

## BLOCKERS and known issues

- **BLOCKER — official regulation provenance:** a current, authoritative full digital text for the 10 June 2020 / 31151 regulation was identified by title/date, but no reliably ingestible official digital artifact was obtained during the run. The local regulation PDF has zero text and the Resmî Gazete PDF layer is only 183 characters. Neither incomplete source was indexed. Full PaddleOCR V6 or a verified official digital download remains necessary.
- **BLOCKER — targeted coverage:** all five current targeted questions concern law 3071, which is absent from `statute_chunks.csv`; evaluation gold was correctly left unchanged.
- Document collection remains empty for this candidate because all 21 generated inputs are regulations, not real document examples.
- Evaluator still reports aggregate metric fields; because targeted coverage is zero, the current numeric denominator is broad-only in practice. Explicit per-suite metric fields and latency percentiles remain useful follow-up work.

## Morning follow-up (maximum 3)

1. Verify and ingest the authoritative 2020 official-writing regulation (or approve a provenance-preserving PaddleOCR V6 run), then add 3071 corpus content from an authoritative source without modifying evaluation gold.
2. Add explicit per-suite/p50/p95 evaluator reporting and run one neighboring-article augmentation experiment against this frozen baseline.
3. Review the commit and Qdrant state, then push manually if accepted.