"""
Command-line interface for AiTril.

Provides commands for initializing configuration, querying single providers,
and running tri-lam parallel queries.
"""

import argparse
import asyncio
import sys

from . import __version__
from .config import ensure_config, init_wizard, load_config
from .orchestrator import AiTril


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
    # Ensure we have at least 2 providers configured (tri-lam rule)
    config = ensure_config(min_providers=2)

    # Create orchestrator
    aitril = AiTril(config)

    # Map friendly names to internal names
    provider_map = {
        "gpt": "openai",
        "claude": "anthropic",
        "gemini": "gemini",
    }

    provider_name = provider_map.get(args.provider.lower(), args.provider.lower())

    # Run async query
    try:
        response = asyncio.run(aitril.ask_single(provider_name, args.prompt))
        print(f"\n{'=' * 60}")
        print(f"{aitril.provider_display_name(provider_name)}")
        print('=' * 60)
        print(response)
        print()
    except ValueError as e:
        print(f"\nError: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}\n")
        sys.exit(1)


def cmd_tri(args):
    """
    Handle 'aitril tri' command.

    Query all enabled providers in parallel and display results.
    """
    # Ensure we have at least 2 providers configured (tri-lam rule)
    config = ensure_config(min_providers=2)

    # Create orchestrator
    aitril = AiTril(config)

    # Run async tri query
    try:
        results = asyncio.run(aitril.ask_tri(args.prompt))

        print("\n" + "=" * 60)
        print("🧬 TRI-LAM RESULTS")
        print("=" * 60)

        for provider_name, response in results.items():
            print(f"\n{'─' * 60}")
            print(f"  {aitril.provider_display_name(provider_name)}")
            print('─' * 60)
            print(response)
            print()

        print("=" * 60 + "\n")

    except ValueError as e:
        print(f"\nError: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}\n")
        sys.exit(1)


def main():
    """Main entry point for the AiTril CLI."""
    parser = argparse.ArgumentParser(
        prog="aitril",
        description="AiTril - Multi-LLM orchestration CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aitril init                                    Initialize configuration
  aitril ask --provider gpt "Hello, world!"     Query a single provider
  aitril tri "Compare your strengths"            Query all providers in parallel

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
    parser_tri.set_defaults(func=cmd_tri)

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
