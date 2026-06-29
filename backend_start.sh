name=backend/start.sh
#!/usr/bin/env bash
set -euo pipefail
# Build frontend (if sources exist) then start backend
if [ -d "../frontend" ]; then
  echo "Building frontend..."
  cd ../frontend
  if [ -f package.json ]; then
    npm ci
    npm run build
  fi
  cd ../backend
fi
echo "Installing backend deps..."
pip install -r requirements.txt
echo "Starting uvicorn..."
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"