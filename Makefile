# Loads GITHUB_TOKEN etc. from .env (gitignored). Never commit tokens.
-include .env

REPO := https://$(GITHUB_TOKEN)@github.com/Jayden1905/agent_eval_framework.git

.PHONY: help install push pull sync status log clean \
        dev dev-mocks dev-frontend smoke-a2a smoke-eval

help:
	@echo "Git:"
	@echo "  make push          push HEAD to origin/main"
	@echo "  make pull          pull --rebase from origin/main"
	@echo "  make sync          pull then push"
	@echo "  make status        git status"
	@echo "  make log           last 10 commits"
	@echo ""
	@echo "Setup:"
	@echo "  make install       pip install -r requirements.txt"
	@echo "  make clean         wipe __pycache__ + .pytest_cache"
	@echo ""
	@echo "Dev:"
	@echo "  make dev           uvicorn backend on :8000 (real — anthropic+daytona+deepeval required)"
	@echo "  make dev-mocks     uvicorn backend on :8000 (mocks — dep-free, no LLM calls)"
	@echo "  make dev-frontend  cd frontend && npm run dev"
	@echo "  make smoke-a2a     hit the accurate agent's card + one message"
	@echo "  make smoke-eval    full end-to-end eval (discover -> eval -> poll -> scorecard)"

# ---- git ------------------------------------------------------------
_check-token:
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
		echo "Error: GITHUB_TOKEN not set. Add it to .env"; \
		exit 1; \
	fi

push: _check-token
	@git push $(REPO) HEAD:main

pull: _check-token
	@git pull --rebase $(REPO) main

sync: pull push

status:
	@git status

log:
	@git log --oneline -10

# ---- setup ----------------------------------------------------------
install:
	pip install -r requirements.txt

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .venv/lib/python*/site-packages/__pycache__ 2>/dev/null || true

# ---- dev ------------------------------------------------------------
# dev.sh spawns cloudflared, exports TUNNEL_URL, then execs uvicorn with the
# certifi CA bundle (Python 3.13 from python.org ships without CA roots, so
# Daytona SDK HTTPS calls fail with SSLCertVerificationError otherwise).
# Backend rewrites localhost agent_urls -> $TUNNEL_URL so FE-driven evals
# work end-to-end without a separate tunnel process.
dev:
	@bash scripts/dev.sh

dev-mocks:
	USE_MOCKS=1 uvicorn backend.server:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

smoke-a2a:
	@echo "==> agent card"
	@curl -s http://localhost:8000/agents/accurate/.well-known/agent-card.json | head -c 400
	@echo ""
	@echo "==> message/send"
	@curl -s -X POST http://localhost:8000/agents/accurate/a2a/jsonrpc/ \
		-H "content-type: application/json" \
		-d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"ROLE_USER","message_id":"x","parts":[{"text":"What year did Singapore gain independence?"}]}}}'
	@echo ""

smoke-eval:
	@.venv/bin/python scripts/smoke_eval.py
