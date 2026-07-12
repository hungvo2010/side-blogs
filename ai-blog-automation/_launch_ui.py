"""Launch Streamlit in a fully detached session (survives parent shell exit)."""

import os
import subprocess

project = os.path.dirname(os.path.abspath(__file__))
subprocess.Popen(
    [
        os.path.join(project, ".venv/bin/streamlit"),
        "run",
        "streamlit_app/app.py",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ],
    stdout=open("/tmp/blog_streamlit.log", "w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,  # OS-level setsid — works on macOS
    cwd=project,
)
print("streamlit launched (detached session) -> http://localhost:8501")
