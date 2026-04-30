"""Logs router."""
from fastapi import APIRouter, Query
from typing import List, Optional
from pathlib import Path

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("/")
def get_logs(
    level: Optional[str] = None,
    lines: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None
):
    """Get recent log entries."""
    log_file = Path("logs/app.log")
    
    if not log_file.exists():
        return {"logs": [], "total": 0}
    
    with open(log_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    if level:
        all_lines = [l for l in all_lines if f" | {level.upper()} |" in l]
    
    if search:
        all_lines = [l for l in all_lines if search.lower() in l.lower()]
    
    logs = all_lines[-lines:]
    
    return {
        "logs": logs,
        "total": len(all_lines),
        "returned": len(logs)
    }
