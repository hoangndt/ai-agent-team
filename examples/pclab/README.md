python .ai/bin/ai_run.py init TICKET-1 "nội dung ticket" --domain backend

python .ai/bin/ai_run.py architect-prepare TICKET-1
python .ai/bin/ai_run.py architect-complete TICKET-1

python .ai/bin/ai_run.py dev-prepare TICKET-1
python .ai/bin/ai_run.py dev-complete TICKET-1

python .ai/bin/ai_run.py review-prepare TICKET-1
python .ai/bin/ai_run.py review-complete TICKET-1

python .ai/bin/ai_run.py qa-prepare TICKET-1
python .ai/bin/ai_run.py qa-complete TICKET-1

python .ai/bin/ai_run.py next TICKET-1
python .ai/bin/ai_run.py status TICKET-1
