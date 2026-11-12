# Recall Trail

The demo traces a recalled part to its current kit and loan using fictional inventory records. The verified environment is Windows x64 with Python 3.12 and Relate 1.0.0.

In PowerShell, run these commands from the extracted folder:

```powershell
python -m pip install "https://github.com/relatedb/relate/releases/download/v1.0.0/relate_db-1.0.0-cp39-abi3-win_amd64.whl"
python -B recall.py ".\recall-demo.rl" --init-demo --batch LOT-7
```

The lookup returns part `P-104`, its route through `HEAD-2` to `KIT-02`, and active loan `LOAN-9`. Run the same lookup without `--init-demo` to reopen the database.

## Ask a recall question

In LM Studio, download Qwen3.5-4B GGUF (Q4_K_M). With the LM Studio CLI (`lms`) available in PowerShell, run:

```powershell
lms load qwen3.5-4b --identifier recall-trail-test --gpu off --context-length 4096 --ttl 600 -y
lms server start --bind 127.0.0.1 --port 5167
python -B agent_recall.py ".\recall-demo.rl" "LOT-8 is unrelated. What kit currently contains the part from recalled LOT-7, and which loan is active?" --model recall-trail-test --port 5167
```

The result should show `LOT-7` and the same route and loan. The `matches` field comes from the read-only Relate lookup. The model check indicates whether the model returned that exact tool result. After the demo, stop its server with `lms server stop` and unload its model with `lms unload recall-trail-test`.
