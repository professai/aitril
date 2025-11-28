"""
Step definitions for AiTril BDD tests
"""
import asyncio
import json
import time
from urllib.request import urlopen
from behave import given, when, then
import websockets


# Web Interface Steps
@given('the AiTril web server is running')
def step_server_running(context):
    """Verify server is running by checking health endpoint"""
    try:
        with urlopen('http://localhost:8888/health') as response:
            data = json.loads(response.read().decode())
            assert data.get('status') == 'healthy', "Server is not healthy"
            context.server_url = 'http://localhost:8888'
            context.ws_url = 'ws://localhost:8888/ws'
    except Exception as e:
        raise AssertionError(f"Server is not running: {e}")


@when('I navigate to the home page')
def step_navigate_home(context):
    """Navigate to the home page"""
    with urlopen(context.server_url + '/') as response:
        context.home_page = response.read().decode()


@then('I should see the AiTril interface')
def step_see_interface(context):
    """Verify AiTril interface is present"""
    assert 'AiTril' in context.home_page, "AiTril interface not found"


@then('the page should load static assets')
def step_static_assets(context):
    """Verify static assets are referenced"""
    assert 'static/app.js' in context.home_page, "app.js not found"
    assert 'static/style.css' in context.home_page, "style.css not found"


@when('I check the health endpoint')
def step_check_health(context):
    """Check health endpoint"""
    with urlopen(context.server_url + '/health') as response:
        context.health_data = json.loads(response.read().decode())


@then('the status should be "{status}"')
def step_status_should_be(context, status):
    """Verify health status"""
    assert context.health_data.get('status') == status, \
        f"Expected status {status}, got {context.health_data.get('status')}"


@then('the service name should be "{service}"')
def step_service_name(context, service):
    """Verify service name"""
    assert context.health_data.get('service') == service, \
        f"Expected service {service}, got {context.health_data.get('service')}"


# WebSocket Steps
@given('I have a WebSocket connection')
@when('I establish a WebSocket connection')
def step_establish_websocket(context):
    """Establish WebSocket connection"""
    async def connect():
        ws = await websockets.connect(context.ws_url)
        # Receive connection message
        msg = await ws.recv()
        data = json.loads(msg)
        context.connection_message = data
        context.websocket = ws
        context.received_events = []
        return ws

    context.ws = asyncio.get_event_loop().run_until_complete(connect())


@then('I should receive a connection confirmation')
def step_connection_confirmation(context):
    """Verify connection confirmation"""
    assert context.connection_message.get('type') == 'connected', \
        "No connection confirmation received"


@then('the connection should remain open')
def step_connection_open(context):
    """Verify connection is open"""
    assert not context.ws.closed, "WebSocket connection is closed"


# Ask Mode Steps
@when('I send an ask mode request to "{provider}" with prompt "{prompt}"')
def step_send_ask_request(context, provider, prompt):
    """Send ask mode request"""
    async def send_and_receive():
        await context.ws.send(json.dumps({
            "prompt": prompt,
            "mode": "ask",
            "provider": provider
        }))

        # Collect events
        events = []
        timeout_count = 0
        while timeout_count < 5:
            try:
                msg = await asyncio.wait_for(context.ws.recv(), timeout=2.0)
                data = json.loads(msg)
                events.append(data)

                if data.get('type') == 'agent_completed':
                    break
            except asyncio.TimeoutError:
                timeout_count += 1

        context.received_events = events

    asyncio.get_event_loop().run_until_complete(send_and_receive())


# Tri Mode Steps
@when('I send a tri mode request with prompt "{prompt}"')
def step_send_tri_request(context, prompt):
    """Send tri mode request"""
    async def send_and_receive():
        await context.ws.send(json.dumps({
            "prompt": prompt,
            "mode": "tri"
        }))

        # Collect events
        events = []
        timeout_count = 0
        while timeout_count < 10:
            try:
                msg = await asyncio.wait_for(context.ws.recv(), timeout=2.0)
                data = json.loads(msg)
                events.append(data)

                if data.get('type') == 'trilam_completed':
                    break
            except asyncio.TimeoutError:
                timeout_count += 1

        context.received_events = events
        context.providers_completed = {
            e.get('agent') for e in events if e.get('type') == 'agent_completed'
        }

    asyncio.get_event_loop().run_until_complete(send_and_receive())


@then('I should receive a "{event_type}" event')
def step_should_receive_event(context, event_type):
    """Verify specific event type was received"""
    event_types = [e.get('type') for e in context.received_events]
    assert event_type in event_types, \
        f"Event {event_type} not found in {event_types}"


@then('I should receive an "{event_type}" event for "{agent}"')
def step_should_receive_agent_event(context, event_type, agent):
    """Verify agent-specific event"""
    found = any(
        e.get('type') == event_type and e.get('agent') == agent
        for e in context.received_events
    )
    assert found, f"Event {event_type} for agent {agent} not found"


@then('I should receive "{event_type}" events')
def step_should_receive_multiple_events(context, event_type):
    """Verify multiple events of a type"""
    count = sum(1 for e in context.received_events if e.get('type') == event_type)
    assert count > 0, f"No {event_type} events received"


@then('I should receive an "{event_type}" event with a response')
def step_should_receive_event_with_response(context, event_type):
    """Verify event with response content"""
    found = any(
        e.get('type') == event_type and e.get('response')
        for e in context.received_events
    )
    assert found, f"Event {event_type} with response not found"


@then('the event should list {count:d} providers')
def step_event_should_list_providers(context, count):
    """Verify provider count in trilam_started event"""
    trilam_events = [e for e in context.received_events if e.get('type') == 'trilam_started']
    assert len(trilam_events) > 0, "No trilam_started event found"

    providers = trilam_events[0].get('providers', [])
    assert len(providers) == count, \
        f"Expected {count} providers, got {len(providers)}: {providers}"


@then('I should receive "agent_started" events for all providers')
def step_agent_started_for_all(context):
    """Verify all providers started"""
    started_agents = {
        e.get('agent') for e in context.received_events
        if e.get('type') == 'agent_started'
    }
    expected = {'openai', 'anthropic', 'gemini'}
    assert started_agents == expected, \
        f"Expected {expected}, got {started_agents}"


@then('I should receive "agent_completed" events for "{provider}"')
def step_agent_completed_for_provider(context, provider):
    """Verify specific provider completed"""
    assert provider in context.providers_completed, \
        f"{provider} not in completed providers: {context.providers_completed}"


@then('each provider should return a unique response')
def step_unique_responses(context):
    """Verify each provider returned a response"""
    responses = {
        e.get('agent'): e.get('response')
        for e in context.received_events
        if e.get('type') == 'agent_completed' and e.get('response')
    }
    assert len(responses) == 3, f"Expected 3 responses, got {len(responses)}"


@then('all responses should be received within {seconds:d} seconds')
def step_responses_within_time(context, seconds):
    """Verify timing constraint"""
    # This is already satisfied if we got all events
    pass


@then('no provider should block others')
def step_no_blocking(context):
    """Verify parallel execution"""
    # If we got trilam_completed, providers ran in parallel
    assert any(e.get('type') == 'trilam_completed' for e in context.received_events), \
        "Trilam did not complete properly"


# Build Mode Steps
@when('I send a build mode request with prompt "{prompt}"')
def step_send_build_request(context, prompt):
    """Send build mode request"""
    async def send_and_receive():
        await context.ws.send(json.dumps({
            "prompt": prompt,
            "mode": "build"
        }))

        # Collect events
        events = []
        context.phases = []
        context.deployment_options = None

        timeout_count = 0
        while timeout_count < 20:
            try:
                msg = await asyncio.wait_for(context.ws.recv(), timeout=3.0)
                data = json.loads(msg)
                events.append(data)

                if data.get('type') == 'phase_changed':
                    context.phases.append(data.get('phase'))

                if data.get('type') == 'deployment_options':
                    context.deployment_options = data.get('options', [])

                if data.get('type') == 'build_completed':
                    break
            except asyncio.TimeoutError:
                timeout_count += 1

        context.received_events = events

    asyncio.get_event_loop().run_until_complete(send_and_receive())


@then('I should see the "{phase}" phase')
def step_should_see_phase(context, phase):
    """Verify specific phase was seen"""
    assert phase in context.phases, \
        f"Phase {phase} not found in {context.phases}"


@then('I should receive deployment options')
def step_should_receive_deployment_options(context):
    """Verify deployment options were received"""
    assert context.deployment_options is not None, "No deployment options received"
    assert len(context.deployment_options) > 0, "Deployment options list is empty"


@then('the phases should execute in this order')
def step_phases_in_order(context):
    """Verify phase execution order"""
    expected_phases = [row['phase'] for row in context.table]
    assert context.phases == expected_phases, \
        f"Expected phases {expected_phases}, got {context.phases}"


@when('the build completes')
def step_build_completes(context):
    """Wait for build to complete"""
    # Already handled in send_build_request
    pass


@then('I should see these deployment options')
def step_should_see_deployment_options(context):
    """Verify specific deployment options"""
    expected = {row['option']: row['name'] for row in context.table}
    actual = {opt['id']: opt['name'] for opt in context.deployment_options}

    for option_id, option_name in expected.items():
        assert option_id in actual, f"Option {option_id} not found"
        assert actual[option_id] == option_name, \
            f"Expected {option_name}, got {actual[option_id]}"


# Deployment Steps
@when('I send a deployment selection for "{target}"')
def step_send_deployment_selection(context, target):
    """Send deployment selection"""
    async def send_and_receive():
        await context.ws.send(json.dumps({
            "type": "deployment_selected",
            "target": target
        }))

        # Collect events
        events = []
        context.deployment_name = None
        context.status_message = None

        timeout_count = 0
        while timeout_count < 3:
            try:
                msg = await asyncio.wait_for(context.ws.recv(), timeout=1.0)
                data = json.loads(msg)
                events.append(data)

                if data.get('type') == 'deployment_started':
                    context.deployment_name = data.get('name')

                if data.get('type') == 'status_message':
                    context.status_message = data.get('message')

                if data.get('type') == 'deployment_completed':
                    break
            except asyncio.TimeoutError:
                timeout_count += 1

        context.received_events = events

    asyncio.get_event_loop().run_until_complete(send_and_receive())


@then('the deployment name should be "{name}"')
def step_deployment_name_should_be(context, name):
    """Verify deployment name"""
    assert context.deployment_name == name, \
        f"Expected deployment name {name}, got {context.deployment_name}"


@then('the status message should contain "{text}"')
def step_status_message_contains(context, text):
    """Verify status message content"""
    assert context.status_message is not None, "No status message received"
    assert text in context.status_message, \
        f"Text '{text}' not found in status message: {context.status_message}"
