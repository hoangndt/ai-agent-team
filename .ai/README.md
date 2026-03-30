python .ai/bin/ai_run.py init TICKET-1 "Implement Intel CPU enrichment" --domain backend
python .ai/bin/ai_run.py next TICKET-1 --run-auto

python .ai/bin/ai_run.py epic-init TEST-EPIC-1 "Test epic requirement"
python .ai/bin/ai_run.py epic-next TEST-EPIC-1 --run-auto
