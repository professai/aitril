"""
Step definitions for AiTril CLI BDD tests
"""
import subprocess
import os
from behave import given, when, then


@given('I have AiTril CLI installed')
def step_cli_installed(context):
    """Verify AiTril CLI is installed"""
    result = subprocess.run(
        ['aitril', '--version'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"AiTril CLI not installed: {result.stderr}"


@given('API keys are configured in environment')
def step_api_keys_configured(context):
    """Verify required API keys are set"""
    required_keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY']
    missing_keys = [key for key in required_keys if not os.environ.get(key)]

    if missing_keys:
        raise AssertionError(f"Missing API keys: {', '.join(missing_keys)}")


@when('I run "{command}"')
def step_run_command(context, command):
    """Run a CLI command and capture output"""
    # Split command into parts, preserving quoted strings
    import shlex
    parts = shlex.split(command)

    # Determine timeout based on command
    # tri and build modes need more time for multiple API calls
    timeout = 180 if any(cmd in parts for cmd in ['tri', 'build']) else 60

    result = subprocess.run(
        parts,
        capture_output=True,
        text=True,
        timeout=timeout
    )

    context.command_output = result.stdout
    context.command_error = result.stderr
    context.exit_code = result.returncode


@then('the output should contain "{text}"')
def step_output_contains(context, text):
    """Verify output contains expected text"""
    # Handle "X" or "Y" pattern
    if '" or "' in text:
        options = [opt.strip() for opt in text.split('" or "')]
        combined_output = context.command_output + context.command_error
        found = any(opt in combined_output for opt in options)
        assert found, \
            f"Expected one of {options} not found in output:\n{combined_output}"
    else:
        combined_output = context.command_output + context.command_error
        assert text in combined_output, \
            f"Expected '{text}' not found in output:\n{combined_output}"


@then('the exit code should be {code:d}')
def step_exit_code_should_be(context, code):
    """Verify exit code matches expected value"""
    assert context.exit_code == code, \
        f"Expected exit code {code}, got {context.exit_code}\nOutput: {context.command_output}\nError: {context.command_error}"


@then('the exit code should not be {code:d}')
def step_exit_code_should_not_be(context, code):
    """Verify exit code does not match value"""
    assert context.exit_code != code, \
        f"Exit code should not be {code}, but got {context.exit_code}"


@then('the output should contain a numeric answer')
def step_output_contains_numeric(context):
    """Verify output contains a number"""
    import re
    combined_output = context.command_output + context.command_error
    assert re.search(r'\d+', combined_output), \
        f"No numeric answer found in output:\n{combined_output}"


@then('I should see responses from {count:d} providers')
def step_see_provider_responses(context, count):
    """Verify responses from multiple providers"""
    combined_output = context.command_output + context.command_error

    # Count provider mentions
    providers = ['OpenAI', 'GPT', 'Anthropic', 'Claude', 'Gemini', 'Google']
    found_providers = set()

    for provider in providers:
        if provider.lower() in combined_output.lower():
            # Map similar provider names
            if provider in ['OpenAI', 'GPT']:
                found_providers.add('openai')
            elif provider in ['Anthropic', 'Claude']:
                found_providers.add('anthropic')
            elif provider in ['Gemini', 'Google']:
                found_providers.add('gemini')

    assert len(found_providers) >= count, \
        f"Expected {count} providers, found {len(found_providers)}: {found_providers}"
