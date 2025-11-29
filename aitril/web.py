"""
FastAPI web server for AiTril with WebSocket support.

Provides a Claude-style web interface with real-time agent visualization.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .config import load_config, load_config_from_env
from .orchestrator import AiTril
from .coordinator import CoordinationStrategy
from .settings import Settings

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    import logging
    logger = logging.getLogger("uvicorn")

    # Try to load from project root directory
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        logger.info(f"✓ Loaded environment variables from {env_file}")
        # Verify API keys loaded
        api_keys = {
            "OPENAI": "SET" if os.environ.get("OPENAI_API_KEY") else "NOT SET",
            "ANTHROPIC": "SET" if os.environ.get("ANTHROPIC_API_KEY") else "NOT SET",
            "GOOGLE": "SET" if os.environ.get("GOOGLE_API_KEY") else "NOT SET"
        }
        logger.info(f"API Keys status: {api_keys}")
    else:
        logger.warning(f".env file not found at {env_file}")
except ImportError:
    pass  # dotenv not installed, skip


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

# Global settings manager
settings_manager = Settings()

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
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🧬</text></svg>">
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div id="app"></div>
        <script src="/static/settings.js"></script>
        <script src="/static/app.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/favicon.ico")
async def get_favicon():
    """Serve favicon as SVG emoji."""
    from fastapi.responses import Response
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🧬</text></svg>"""
    return Response(content=svg_content, media_type="image/svg+xml")


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

            # Handle deployment selection messages
            if data.get("type") == "deployment_selected":
                target = data.get("target")
                await handle_deployment(websocket, target)
                continue

            # Handle regular chat messages
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

            # Get initial planner setting
            general_settings = settings_manager.get_general_settings()
            initial_planner = general_settings.get("initial_planner", "none")

            # Execute based on mode
            if mode == "ask" and provider:
                await handle_ask(websocket, aitril, prompt, provider)
            elif mode == "tri":
                await handle_tri(websocket, aitril, prompt, initial_planner)
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


async def handle_tri(websocket: WebSocket, aitril: AiTril, prompt: str, initial_planner: str = "none"):
    """Handle tri-lam mode with parallel agent visualization or planner-first mode."""
    providers = aitril.get_enabled_providers()

    # Send tri-lam started event
    await manager.send_event(websocket, {
        "type": "trilam_started",
        "providers": providers,
        "planner": initial_planner,
        "timestamp": datetime.now().isoformat()
    })

    # If using planner-first mode, use non-streaming orchestrator
    if initial_planner != "none" and initial_planner in providers:
        # Send planner started event
        await manager.send_event(websocket, {
            "type": "agent_started",
            "agent": initial_planner,
            "role": "planner",
            "timestamp": datetime.now().isoformat()
        })

        # Get responses using planner-first logic
        responses = await aitril.ask_tri(prompt, initial_planner=initial_planner)

        # Send planner response first
        if initial_planner in responses:
            await manager.send_event(websocket, {
                "type": "agent_completed",
                "agent": initial_planner,
                "role": "planner",
                "response": responses[initial_planner],
                "timestamp": datetime.now().isoformat()
            })

        # Send other responses
        for provider, response in responses.items():
            if provider != initial_planner:
                await manager.send_event(websocket, {
                    "type": "agent_started",
                    "agent": provider,
                    "role": "builder",
                    "timestamp": datetime.now().isoformat()
                })
                await manager.send_event(websocket, {
                    "type": "agent_completed",
                    "agent": provider,
                    "role": "builder",
                    "response": response,
                    "timestamp": datetime.now().isoformat()
                })
    else:
        # Use parallel streaming mode (original behavior)
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


async def stream_provider_response(websocket: WebSocket, aitril: AiTril, provider: str, prompt: str) -> str:
    """Stream response from a single provider with error handling.

    Returns:
        The full response text from the provider.
    """
    # Send agent started event
    await manager.send_event(websocket, {
        "type": "agent_started",
        "agent": provider,
        "timestamp": datetime.now().isoformat()
    })

    try:
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
        return full_response
    except Exception as e:
        # Send error event
        error_message = f"Error from {provider}: {str(e)}"
        await manager.send_event(websocket, {
            "type": "agent_error",
            "agent": provider,
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        })
        # Send a chunk with the error so it appears in the UI
        await manager.send_event(websocket, {
            "type": "agent_chunk",
            "agent": provider,
            "chunk": f"⚠️ {error_message}",
            "timestamp": datetime.now().isoformat()
        })
        # Still mark as completed so UI doesn't hang
        await manager.send_event(websocket, {
            "type": "agent_completed",
            "agent": provider,
            "response": error_message,
            "timestamp": datetime.now().isoformat()
        })
        return error_message


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

    # Phase 1: Planning - Consensus on architecture
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "planning",
        "description": "Building consensus on architecture and approach",
        "timestamp": datetime.now().isoformat()
    })

    planning_prompt = aitril.coordinator._build_planning_prompt(prompt, tech_stack, project_context)

    # Stream planning phase (all agents in parallel) and capture responses
    providers = aitril.get_enabled_providers()
    tasks = []
    for provider in providers:
        task = asyncio.create_task(
            stream_provider_response(websocket, aitril, provider, planning_prompt)
        )
        tasks.append(task)

    # Gather responses from streaming (no duplicate API calls!)
    planning_responses_list = await asyncio.gather(*tasks)
    planning_responses = dict(zip(providers, planning_responses_list))

    # Build consensus
    consensus_prompt = aitril.coordinator._build_consensus_prompt(planning_prompt, planning_responses)
    consensus = await aitril.providers[providers[0]].ask(consensus_prompt)

    # Phase 2: Implementation - Sequential build
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "implementation",
        "description": "Implementing code sequentially",
        "timestamp": datetime.now().isoformat()
    })

    implementation_prompt = aitril.coordinator._build_implementation_prompt(
        prompt, consensus, tech_stack, project_context
    )

    # Stream implementation phase (sequential)
    implementation_responses = {}
    context_history = []

    for provider in providers:
        enriched_prompt = implementation_prompt
        if context_history:
            context_str = "\n\n".join([
                f"[Context from {name}]: {resp[:500]}..." if len(resp) > 500
                else f"[Context from {name}]: {resp}"
                for name, resp in context_history
            ])
            enriched_prompt = (
                f"{implementation_prompt}\n\n"
                f"Previous agent responses for context:\n{context_str}\n\n"
                f"Please provide your implementation, building on the above."
            )

        # Stream this provider's response and capture it (no duplicate API call!)
        response = await stream_provider_response(websocket, aitril, provider, enriched_prompt)
        implementation_responses[provider] = response
        context_history.append((provider, response))

    # Phase 3: Review - Consensus validation
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "review",
        "description": "Reviewing implementation with consensus",
        "timestamp": datetime.now().isoformat()
    })

    review_prompt = aitril.coordinator._build_review_prompt(
        prompt, implementation_responses, tech_stack
    )

    # Stream review phase (all agents in parallel)
    tasks = []
    for provider in providers:
        task = asyncio.create_task(
            stream_provider_response(websocket, aitril, provider, review_prompt)
        )
        tasks.append(task)
    await asyncio.gather(*tasks)

    # Phase 4: Deployment (Optional)
    await manager.send_event(websocket, {
        "type": "phase_changed",
        "phase": "deployment",
        "description": "Deployment options available",
        "timestamp": datetime.now().isoformat()
    })

    # Send deployment options
    await manager.send_event(websocket, {
        "type": "deployment_options",
        "options": [
            {"id": "local", "name": "Local File System", "description": "Save files to local directory"},
            {"id": "docker", "name": "Docker Container", "description": "Build and run as Docker container"},
            {"id": "github", "name": "GitHub Pages", "description": "Deploy to GitHub Pages"},
            {"id": "ec2", "name": "AWS EC2", "description": "Deploy to EC2 instance"},
            {"id": "skip", "name": "Skip Deployment", "description": "Just show the code"}
        ],
        "timestamp": datetime.now().isoformat()
    })

    # Send status message
    await manager.send_event(websocket, {
        "type": "status_message",
        "message": "✅ Build complete! Select a deployment option above, or choose 'Skip Deployment' to finish.",
        "timestamp": datetime.now().isoformat()
    })

    # Send build completed event (deployment is optional)
    await manager.send_event(websocket, {
        "type": "build_completed",
        "results": {
            "task": prompt,
            "planning": planning_responses,
            "implementation": implementation_responses,
            "status": "completed"
        },
        "timestamp": datetime.now().isoformat()
    })


async def handle_deployment(websocket: WebSocket, target: str):
    """Handle deployment to selected target."""
    deployment_info = {
        "local": {
            "name": "Local File System",
            "description": "Files will be saved to your current directory",
            "action": "save_files"
        },
        "docker": {
            "name": "Docker Container",
            "description": "Building Docker container with your code",
            "action": "build_docker"
        },
        "github": {
            "name": "GitHub Pages",
            "description": "Deploying to GitHub Pages (requires GitHub repo)",
            "action": "deploy_github"
        },
        "ec2": {
            "name": "AWS EC2",
            "description": "Deploying to EC2 instance (requires AWS credentials)",
            "action": "deploy_ec2"
        },
        "skip": {
            "name": "Skip Deployment",
            "description": "Code generation complete - no deployment",
            "action": "skip"
        }
    }

    info = deployment_info.get(target, deployment_info["skip"])

    # Send acknowledgment
    await manager.send_event(websocket, {
        "type": "deployment_started",
        "target": target,
        "name": info["name"],
        "timestamp": datetime.now().isoformat()
    })

    # For now, just send a completion message
    # In the future, this would actually perform the deployment
    if target == "skip":
        await manager.send_event(websocket, {
            "type": "status_message",
            "message": "✅ Build complete! Code is ready to use.",
            "timestamp": datetime.now().isoformat()
        })
    else:
        await manager.send_event(websocket, {
            "type": "status_message",
            "message": f"🚀 Deployment to {info['name']} initiated! (Implementation coming soon)",
            "timestamp": datetime.now().isoformat()
        })

    # Send deployment completed event
    await manager.send_event(websocket, {
        "type": "deployment_completed",
        "target": target,
        "status": "acknowledged",
        "timestamp": datetime.now().isoformat()
    })


# Settings API endpoints
@app.get("/api/settings")
async def get_settings():
    """Get all settings (excluding sensitive data)."""
    return settings_manager.export_settings()


@app.get("/api/settings/providers")
async def get_providers():
    """Get all LLM provider configurations."""
    return settings_manager.get_llm_providers()


@app.get("/api/settings/providers/enabled")
async def get_enabled_providers():
    """Get list of enabled provider IDs."""
    return {"providers": settings_manager.get_enabled_providers()}


@app.put("/api/settings/providers/{provider_id}")
async def update_provider(provider_id: str, config: Dict[str, Any]):
    """Update LLM provider configuration."""
    success = settings_manager.update_provider(provider_id, config)
    if success:
        return {"status": "success", "provider_id": provider_id}
    else:
        return {"status": "error", "message": "Failed to update provider"}


@app.post("/api/settings/providers/custom")
async def add_custom_provider(
    provider_id: str,
    name: str,
    api_key_env: str,
    model: str,
    base_url: str
):
    """Add a custom LLM provider."""
    success = settings_manager.add_custom_provider(
        provider_id, name, api_key_env, model, base_url
    )
    if success:
        return {"status": "success", "provider_id": provider_id}
    else:
        return {"status": "error", "message": "Failed to add custom provider"}


@app.get("/api/settings/deployments")
async def get_deployment_targets():
    """Get all deployment target configurations."""
    return settings_manager.get_deployment_targets()


@app.get("/api/settings/deployments/enabled")
async def get_enabled_deployments():
    """Get list of enabled deployment target IDs."""
    return {"targets": settings_manager.get_enabled_targets()}


@app.put("/api/settings/deployments/{target_id}")
async def update_deployment_target(target_id: str, config: Dict[str, Any]):
    """Update deployment target configuration."""
    success = settings_manager.update_deployment_target(target_id, config)
    if success:
        return {"status": "success", "target_id": target_id}
    else:
        return {"status": "error", "message": "Failed to update deployment target"}


@app.get("/api/settings/general")
async def get_general_settings():
    """Get general application settings."""
    return settings_manager.get_general_settings()


@app.put("/api/settings/general")
async def update_general_settings(config: Dict[str, Any]):
    """Update general application settings."""
    success = settings_manager.update_general_settings(config)
    if success:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Failed to update general settings"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aitril-web"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=37142)
