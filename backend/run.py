import os
import sys

# Constrain thread pools to save virtual memory in low-RAM environments (Render 512MB)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"--> Starting ResumeRanker on {host}:{port}...", flush=True)
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")
