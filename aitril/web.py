"""
FastAPI web server for AiTril with WebSocket support.

Provides a Claude-style web interface with real-time agent visualization.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .config import load_config, load_config_from_env
from .orchestrator import AiTril
from .coordinator import CoordinationStrategy


class ChatMessage(BaseModel):
    """Chat message from user."""
    prompt: str
    mode: str = "tri"  # "ask", "tri", "sequential", "consensus", "debate", "build"
    provider: Optional[str] = None
    session: Optional[str] = None


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_event(self, websocket: WebSocket, event: Dict[str, Any]):
        """Send event to specific connection."""
        await websocket.send_json(event)

    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast event to all connections."""
        for connection in self.active_connections:
            try:
                await connection.send_json(event)
            except:
                pass


# Global connection manager
manager = ConnectionManager()

# Create FastAPI app
app = FastAPI(title="AiTril Web Interface")

# Mount static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def get_index():
    """Serve the main chat interface."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AiTril - Multi-Agent Orchestration</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div id="app"></div>
        <script src="/static/app.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat and agent updates."""
    await manager.connect(websocket)

    try:
        # Send initial connection event
        await manager.send_event(websocket, {
            "type": "connected",
            "timestamp": datetime.now().isoformat()
        })

        # Load config from file or environment variables
        config = load_config()
        if config is None:
            config = load_config_from_env()

        if config is None:
            await manager.send_event(websocket, {
                "type": "error",
                "message": "No configuration found. Please set API keys in environment variables.",
                "timestamp": datetime.now().isoformat()
            })
            return

        while True:
            # Receive message from client
            data = await websocket.receive_json()
            prompt = data.get("prompt")
            mode = data.get("mode", "tri")
            provider = data.get("provider")
            session = data.get("session")

            # Send acknowledgment
            await manager.send_event(websocket, {
                "type": "message_received",
                "prompt": prompt,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            })

            # Create AiTril instance
            aitril = AiTril(config, session_name=session, use_cache=True)

            # Execute based on mode
            if mode == "ask" and provider:
                await handle_ask(websocket, aitril, prompt, provider)
            elif mode == "tri":
                await handle_tri(websocket, aitril, prompt)
            elif mode in ["sequential", "consensus", "debate"]:
                await handle_coordination(websocket, aitril, prompt, mode)
            elif mode == "build":
                await handle_build(websocket, aitril, prompt)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_ask(websocket: WebSocket, aitril: AiTril, prompt: str, provider: str):
    """Handle single provider query with streaming."""
    # Send agent started event
    await manager.send_event(websocket, {
        "type": "agent_started",
        "agent": provider,
        "timestamp": datetime.now().isoformat()
    })

    # Stream response
    full_response = ""
    async for chunk in aitril.ask_single_stream(provider, prompt):
        full_response += chunk
        await manager.send_event(websocket, {
            "type": "agent_chunk",
            "agent": provider,
            "chunk": chunk,
            "timestamp": datetime.now().isoformat()
        })

    # Send completion event
    await manager.send_event(websocket, {
        "type": "agent_completed",
        "agent": provider,
        "response": full_response,
        "timestamp": datetime.now().isoformat()
    })


async def handle_tri(websocket: WebSocket, aitril: AiTril, prompt: str):
    """Handle tri-lam mode with parallel agent visualization."""
    providers = aitril.get_enabled_providers()

    # Send tri-lam started event
    await manager.send_event(websocket, {
        "type": "trilam_started",
        "providers": providers,
        "timestamp": datetime.now().isoformat()
    })

    # Create tasks for each provider
    tasks = []
    for provider in providers:
        task = asyncio.create_task(
            stream_provider_response(websocket, aitril, provider, prompt)
        )
        tasks.append(task)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)

    # Send completion event
    await manager.send_event(websocket, {
        "type": "trilam_completed",
        "timestamp": datetime.now().isoformat()
    })


async def stream_provider_response(websocket: WebSocket, aitril: AiTril, provider: str, prompt: str):
    """Stream response from a single provider."""
    # Send agent started event
    await manager.send_event(websocket, {
        "type": "agent_started",
        "agent": provider,
        "timestamp": datetime.now().isoformat()
    })

    # Stream response
    full_response = ""
    async for chunk in aitril.ask_single_stream(provider, prompt):
        full_response += chunk
        await manager.send_event(websocket, {
            "type": "agent_chunk",
            "agent": provider,
            "chunk": chunk,
            "timestamp": datetime.now().isoformat()
        })

    # Send completion event
    await manager.send_event(websocket, {
        "type": "agent_completed",
        "agent": provider,
        "response": full_response,
        "timestamp": datetime.now().isoformat()
    })


async def handle_coordination(websocket: WebSocket, aitril: AiTril, prompt: str, mode: str):
    """Handle coordination modes with phase visualization."""
    # Map mode to strategy
    strategy_map = {
        "sequential": CoordinationStrategy.SEQUENTIAL,
        "consensus": CoordinationStrategy.CONSENSUS,
        "debate": CoordinationStrategy.DEBATE
    }
    strategy = strategy_map.get(mode)

    # Send coordination started event
    await manager.send_event(websocket, {
        "type": "coordination_started",
        "mode": mode,
        "timestamp": datetime.now().isoformat()
    })

    # Execute coordination (this will be enhanced with event emission)
    results = await aitril.coordinator.coordinate(prompt, strategy)

    # Send coordination completed event
    await manager.send_event(websocket, {
        "type": "coordination_completed",
        "mode": mode,
        "results": results,
        "timestamp": datetime.now().isoformat()
    })


async def handle_build(websocket: WebSocket, aitril: AiTril, prompt: str):
    """Handle code building with three-phase visualization."""
    # Get tech stack
    tech_stack = aitril.cache.get_tech_stack() if aitril.cache else None
    project_context = aitril.cache.get_project_context() if aitril.cache else None

    # Send build started event
    await manager.send_event(websocket, {
        "type": "build_started",
        "tech_stack": tech_stack,
        "timestamp": datetime.now().isoformat()
    })

    # Phase 1: Planning
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "planning",
        "description": "Building consensus on architecture and approach",
        "timestamp": datetime.now().isoformat()
    })

    # Phase 2: Implementation
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "implementation",
        "description": "Implementing code sequentially",
        "timestamp": datetime.now().isoformat()
    })

    # Phase 3: Review
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "review",
        "description": "Reviewing implementation with consensus",
        "timestamp": datetime.now().isoformat()
    })

    # Execute build (this will be enhanced with event emission)
    results = await aitril.coordinator.coordinate_code_build(
        prompt,
        tech_stack=tech_stack,
        project_context=project_context
    )

    # Send build completed event
    await manager.send_event(websocket, {
        "type": "build_completed",
        "results": results,
        "timestamp": datetime.now().isoformat()
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aitril-web"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
