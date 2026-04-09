#!/bin/bash
source /home/daniel/gas-automation/backend/venv/bin/activate || true
if ! command -v alembic &> /dev/null; then
  echo "Alembic not found in PATH"
  # Let's see what is inside the virtual environments
  ls -la /home/daniel/.virtualenvs/ || true
  ls -la /home/daniel/.local/share/virtualenvs/ || true
else
  alembic revision --autogenerate -m "add_customer_context_fields"
  alembic upgrade head
fi
