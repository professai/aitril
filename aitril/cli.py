"""
Command-line interface for AiTril.

Provides commands for initializing configuration, querying single providers,
running tri-lam parallel queries, and managing cache/sessions.
"""

import argparse
import asyncio
import json
import sys
import time

from . import __version__
from .config import ensure_config, init_wizard, load_config
from .orchestrator import AiTril
from .cache import SessionCache
from .coordinator import CoordinationStrategy
from .display import display


def cmd_init(args):
    """
    Handle 'aitril init' command.

    Runs the interactive configuration wizard.
    """
    config = init_wizard()
    if config is None:
        sys.exit(1)


def cmd_ask(args):
    """
    Handle 'aitril ask' command.

    Query a single provider with a prompt.
    """
    start_time = time.time()

    # Ensure we have at least 2 providers configured (tri-lam rule)
    config = ensure_config(min_providers=2)

    # Create orchestrator with session support
    use_cache = not args.no_cache if hasattr(args, 'no_cache') else True
    session_name = args.session if hasattr(args, 'session') else None
    aitril = AiTril(config, session_name=session_name, use_cache=use_cache)

    # Show cache info if using cache
    if use_cache and aitril.cache:
        history_count = len(aitril.cache.get_history())
        display.show_cache_info(aitril.cache.session_name, history_count)

    # Map friendly names to internal names
    provider_map = {
        "gpt": "openai",
        "claude": "anthropic",
        "gemini": "gemini",
    }

    provider_name = provider_map.get(args.provider.lower(), args.provider.lower())

    # Run async query with streaming (if enabled)
    try:
        if args.stream:
            # Streaming mode
            async def stream_response():
                display.section_header(aitril.provider_display_name(provider_name))
                display.provider_thinking(aitril.provider_display_name(provider_name))

                response_text = ""
                print()  # New line after thinking indicator
                async for chunk in aitril.ask_single_stream(provider_name, args.prompt):
                    print(chunk, end='', flush=True)
                    response_text += chunk
                print("\n")

                # Save to cache if enabled
                if use_cache and aitril.cache:
                    aitril.cache.add_to_history(args.prompt, {provider_name: response_text})

            asyncio.run(stream_response())
        else:
            # Non-streaming mode
            display.task_start(f"Querying {aitril.provider_display_name(provider_name)}")
            response = asyncio.run(aitril.ask_single(provider_name, args.prompt))
            display.task_complete()

            display.section_header(aitril.provider_display_name(provider_name))
            print(response)
            print()

            # Save to cache if enabled
            if use_cache and aitril.cache:
                aitril.cache.add_to_history(args.prompt, {provider_name: response})

        # Show stats
        elapsed = time.time() - start_time
        display.show_stats(elapsed)

    except ValueError as e:
        display.task_error(error_msg=str(e))
        sys.exit(1)
    except Exception as e:
        display.task_error(error_msg=str(e))
        sys.exit(1)


def cmd_tri(args):
    """
    Handle 'aitril tri' command.

    Query all enabled providers in parallel and display results.
    """
    start_time = time.time()

    # Ensure we have at least 2 providers configured (tri-lam rule)
    config = ensure_config(min_providers=2)

    # Create orchestrator with session support
    use_cache = not args.no_cache if hasattr(args, 'no_cache') else True
    session_name = args.session if hasattr(args, 'session') else None
    aitril = AiTril(config, session_name=session_name, use_cache=use_cache)

    # Show cache info if using cache
    if use_cache and aitril.cache:
        history_count = len(aitril.cache.get_history())
        display.show_cache_info(aitril.cache.session_name, history_count)

    # Determine coordination strategy
    strategy = args.coordinate if hasattr(args, 'coordinate') else CoordinationStrategy.PARALLEL

    # Run async tri query
    try:
        display.task_start(f"Querying all providers ({strategy} mode)")
        results = asyncio.run(aitril.ask_tri(args.prompt, strategy=strategy))
        display.task_complete()

        # Display results based on strategy
        if strategy == CoordinationStrategy.CONSENSUS:
            _display_consensus_results(results, aitril)
        elif strategy == CoordinationStrategy.DEBATE:
            _display_debate_results(results, aitril)
        else:
            _display_standard_results(results, aitril)

        # Show stats
        elapsed = time.time() - start_time
        display.show_stats(elapsed, provider_stats=results)

    except ValueError as e:
        display.task_error(error_msg=str(e))
        sys.exit(1)
    except Exception as e:
        display.task_error(error_msg=str(e))
        sys.exit(1)


def _display_standard_results(results: dict, aitril: AiTril) -> None:
    """Display standard tri-lam results."""
    display.section_header("🧬 TRI-LAM RESULTS")

    for provider_name, response in results.items():
        display.subsection_header(aitril.provider_display_name(provider_name))
        print(response)
        print()

    display.divider("=")


def _display_consensus_results(results: dict, aitril: AiTril) -> None:
    """Display consensus results."""
    display.section_header("🧬 TRI-LAM CONSENSUS MODE")

    # Individual responses
    display.subsection_header("Individual Responses")
    for provider_name, response in results.get("individual_responses", {}).items():
        print(f"\n{aitril.provider_display_name(provider_name)}:")
        print(response)

    # Consensus
    display.subsection_header("Synthesized Consensus")
    print(results.get("consensus", "No consensus generated"))

    display.divider("=")


def _display_debate_results(results: dict, aitril: AiTril) -> None:
    """Display debate results."""
    display.section_header("🧬 TRI-LAM DEBATE MODE")

    for round_data in results.get("rounds", []):
        display.subsection_header(f"Round {round_data['round']}")
        for provider_name, response in round_data["responses"].items():
            print(f"\n{aitril.provider_display_name(provider_name)}:")
            print(response)
        print()

    display.divider("=")


def cmd_cache(args):
    """
    Handle 'aitril cache' command.

    Manage cache and sessions.
    """
    cache = SessionCache()

    if args.cache_command == "show":
        # Show cache summary
        summary = cache.get_cache_summary()

        display.section_header("AiTril Cache Summary")

        display.key_value("Cache file", summary["cache_file"])
        display.key_value("Current session", summary["current_session"])
        display.key_value("Total sessions", summary["total_sessions"])

        if summary["global_preferences"]:
            print("\nGlobal Preferences:")
            for key, value in summary["global_preferences"].items():
                display.key_value(f"  {key}", value)

        if summary["session_names"]:
            print("\nSessions:")
            display.bullet_list(summary["session_names"])

        print("\nCurrent Session:")
        display.key_value("  History items", summary["current_session_data"]["history_count"])

        if summary["current_session_data"]["preferences"]:
            print("  Preferences:")
            for key, value in summary["current_session_data"]["preferences"].items():
                display.key_value(f"    {key}", value)

        if summary["current_session_data"]["context_keys"]:
            print("  Context keys:")
            display.bullet_list(summary["current_session_data"]["context_keys"], indent=4)

        display.divider("=")

    elif args.cache_command == "clear":
        if args.session:
            # Clear specific session
            cache.clear_session(args.session)
        else:
            # Clear all cache
            confirm = input("Are you sure you want to clear all cache data? [y/N]: ").strip().lower()
            if confirm in ["y", "yes"]:
                cache.clear_all()
            else:
                print("Cache clear cancelled.")

    elif args.cache_command == "list":
        # List all sessions
        sessions = cache.list_sessions()

        display.section_header("AiTril Sessions")

        if sessions:
            display.bullet_list(sessions)
        else:
            print("  No sessions found")

        display.divider("=")

    elif args.cache_command == "history":
        # Show session history
        session_name = args.session if args.session else cache.session_name
        history = cache.get_history()

        display.section_header(f"Session History: {session_name}")

        if history:
            for idx, entry in enumerate(history, 1):
                print(f"\n[{idx}] {entry['timestamp']}")
                print(f"Prompt: {entry['prompt']}")
                print("Responses:")
                for provider, response in entry.get('responses', {}).items():
                    # Truncate long responses
                    truncated = response[:200] + "..." if len(response) > 200 else response
                    print(f"  - {provider}: {truncated}")
        else:
            print("  No history found")

        display.divider("=")


def main():
    """Main entry point for the AiTril CLI."""
    parser = argparse.ArgumentParser(
        prog="aitril",
        description="AiTril - Multi-LLM orchestration CLI tool with agent coordination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  aitril init                                    Initialize configuration
  aitril ask --provider gpt "Hello, world!"     Query a single provider
  aitril tri "Compare your strengths"            Query all providers in parallel

  # Agent coordination modes
  aitril tri --coordinate sequential "Solve this problem step by step"
  aitril tri --coordinate consensus "What is the best approach?"
  aitril tri --coordinate debate "Debate the pros and cons"

  # Session management
  aitril ask --session "my-project" -p gpt "Help with this code"
  aitril tri --session "build-20240101" "Design a new feature"
  aitril ask --no-cache -p claude "Quick question"

  # Cache management
  aitril cache show                              Show cache summary
  aitril cache list                              List all sessions
  aitril cache history                           Show current session history
  aitril cache clear --session "old-session"     Clear specific session
  aitril cache clear                             Clear all cache (with confirmation)

For more information, visit: https://github.com/professai/aitril
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    parser_init = subparsers.add_parser(
        "init",
        help="Initialize AiTril configuration"
    )
    parser_init.set_defaults(func=cmd_init)

    # ask command
    parser_ask = subparsers.add_parser(
        "ask",
        help="Query a single LLM provider"
    )
    parser_ask.add_argument(
        "--provider",
        "-p",
        required=True,
        choices=["gpt", "claude", "gemini"],
        help="Provider to query"
    )
    parser_ask.add_argument(
        "prompt",
        help="Prompt to send to the provider"
    )
    parser_ask.add_argument(
        "--stream",
        action="store_true",
        default=True,
        help="Stream response in real-time (default: True)"
    )
    parser_ask.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Disable streaming, wait for complete response"
    )
    parser_ask.add_argument(
        "--session",
        "-s",
        type=str,
        help="Session name for caching (auto-generated if not specified)"
    )
    parser_ask.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching for this query"
    )
    parser_ask.set_defaults(func=cmd_ask)

    # tri command
    parser_tri = subparsers.add_parser(
        "tri",
        help="Query all enabled providers in parallel (tri-lam mode)"
    )
    parser_tri.add_argument(
        "prompt",
        help="Prompt to send to all providers"
    )
    parser_tri.add_argument(
        "--coordinate",
        "-c",
        choices=["parallel", "sequential", "consensus", "debate", "specialist"],
        default="parallel",
        help="Coordination strategy for multi-agent collaboration"
    )
    parser_tri.add_argument(
        "--session",
        "-s",
        type=str,
        help="Session name for caching (auto-generated if not specified)"
    )
    parser_tri.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching for this query"
    )
    parser_tri.set_defaults(func=cmd_tri)

    # cache command
    parser_cache = subparsers.add_parser(
        "cache",
        help="Manage cache and sessions"
    )
    parser_cache.add_argument(
        "cache_command",
        choices=["show", "clear", "list", "history"],
        help="Cache operation to perform"
    )
    parser_cache.add_argument(
        "--session",
        "-s",
        type=str,
        help="Specific session to operate on"
    )
    parser_cache.set_defaults(func=cmd_cache)

    # Parse arguments
    args = parser.parse_args()

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
