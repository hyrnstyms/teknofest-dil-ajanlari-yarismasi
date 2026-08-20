.venv\Scripts\python scripts\index_qdrant.py --mode all --batch-size 32
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
.venv\Scripts\python scripts\evaluation\run_all.py
