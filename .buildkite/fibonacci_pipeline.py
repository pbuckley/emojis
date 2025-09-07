#!/usr/bin/env python3
"""
Dynamic Buildkite pipeline generator using Fibonacci sequence.

This script creates a pipeline where each step generates the next Fibonacci number
of child steps, creating a recursive tree structure. Think of it like a mathematical
nautilus shell - each iteration follows the same pattern but at increasing scale.

References:
- Buildkite Pipeline YAML: https://buildkite.com/docs/pipelines/defining-steps
- Buildkite Dynamic Pipelines: https://buildkite.com/docs/pipelines/dynamic-pipelines
- Python functools.lru_cache: https://docs.python.org/3/library/functools.html#functools.lru_cache
"""

import argparse
import json
import os
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import yaml


@lru_cache(maxsize=128)
def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number with memoization.

    Uses LRU cache decorator to avoid recalculating values, similar to how
    a sysadmin might cache DNS lookups to avoid repeated queries.

    Args:
        n: Position in Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number

    Reference:
        https://docs.python.org/3/library/functools.html#functools.lru_cache
    """
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def load_emoji_options(markdown_file: str = "README.md") -> List[str]:
    """
    Load emoji options from Buildkite emoji markdown format.

    Parses the Buildkite emoji table format to extract emoji aliases.
    Like parsing a routing table - we need to extract the key identifiers!

    Expected format:
    | <img src="..." alt="nats"/> | `:nats:`, `:nats-io:` |

    Args:
        markdown_file: Path to Buildkite emoji markdown file

    Returns:
        List of emoji alias strings (with colons)
    """
    import re

    emoji_file = Path(markdown_file)
    default_emojis = [":buildkite:", ":rocket:", ":fire:", ":zap:", ":gem:", ":star:", ":sparkles:", ":rainbow:", ":art:", ":tada:"]
    if not emoji_file.exists():
        print(f"Using default Buildkite emoji set since file {markdown_file} does not exist")
        return default_emojis

    emojis = []
    emoji_pattern = re.compile(r'<img[^>]*>\s*\|\s*`:([^`]+):`')

    with emoji_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            match = emoji_pattern.search(line)
            if match:
                alias = match.group(1)  # First (and only) capture group
                emojis.append(f":{alias}:")


    # If we couldn't parse any emojis, provide defaults
    if not emojis:
        return default_emojis

    return emojis


def generate_emoji_label(count: int, emoji_options: List[str]) -> str:
    """
    Generate a label with random emojis repeated 'count' times.

    Like generating a visual representation of load - more emojis = more work!

    Args:
        count: Number of emojis to include in label
        emoji_options: List of available emojis to choose from

    Returns:
        String with repeated random emoji
    """
    if count == 0:
        return "🌱"  # Seed emoji for base case

    # Choose a random emoji for this sequence
    chosen_emoji = random.choice(emoji_options)
    return chosen_emoji * min(count, 10)  # Cap at 10 to keep labels readable


def create_pipeline_step(
    fib_position: int,
    current_fib_value: int,
    emoji_options: List[str],
    max_depth: int = 10
) -> Dict:
    """
    Create a single Buildkite pipeline step.

    Each step is like a process that spawns child processes - it runs the same
    script but with different parameters to create the next level of the tree.

    Args:
        fib_position: Current position in Fibonacci sequence
        current_fib_value: The Fibonacci value at current position
        emoji_options: Available emojis for labels
        max_depth: Maximum recursion depth to prevent infinite pipelines

    Returns:
        Dictionary representing a Buildkite step

    Reference:
        https://buildkite.com/docs/pipelines/command-step
    """
    emoji_label = generate_emoji_label(current_fib_value, emoji_options)

    step = {
        "label": f"{emoji_label} Fib({fib_position}) = {current_fib_value}",
        "command": f"python3 .buildkite/fibonacci_pipeline.py --position {str(fib_position + 1).strip()} --max-depth {str(max_depth).strip()}",
        "key": f"fib-{fib_position}",
        "env": {
            "FIBONACCI_POSITION": str(fib_position),
            "FIBONACCI_VALUE": str(current_fib_value)
        }
    }

    # Add dependency on previous Fibonacci step (except for the first step)
    if fib_position > 1:
        step["depends_on"] = f"fib-{fib_position - 1}"

    # Add retry logic for demo resilience
    step["retry"] = {
        "automatic": [
            {"exit_status": "*", "limit": 2}
        ]
    }

    return step


def generate_dynamic_pipeline(
    starting_position: int = 1,
    max_depth: int = 10,
    emoji_file: str = "README.md"
) -> Dict:
    """
    Generate the complete dynamic pipeline configuration.

    This creates a visual Fibonacci sequence where each Fib(N) becomes a group
    containing N sub-steps. Like building a pyramid where each level has more
    blocks than the last, following the mathematical beauty of Fibonacci.

    Args:
        starting_position: Starting position in Fibonacci sequence
        max_depth: Maximum number of Fibonacci groups to generate
        emoji_file: Path to emoji options file

    Returns:
        Complete pipeline configuration dictionary

    Reference:
        https://buildkite.com/docs/pipelines/defining-steps
        https://buildkite.com/docs/pipelines/group-step
    """
    emoji_options = load_emoji_options(emoji_file)
    steps = []

    # Generate Fibonacci groups, limiting the number of groups (not position)
    groups_generated = 0
    current_position = starting_position

    while groups_generated < max_depth and current_position <= 20:  # Cap position at 20
        current_fib_value = fibonacci(current_position)

        # Skip if Fibonacci value gets too large (avoid overwhelming the UI)
        if current_fib_value > 20:
            break

        group_step = create_pipeline_step(
            current_position,
            current_fib_value,
            emoji_options,
            max_depth
        )
        steps.append(group_step)

        groups_generated += 1
        current_position += 1

    # If no groups were generated, add a completion message
    if not steps:
        steps = [{
            "label": "🏁 Fibonacci sequence parameters too large",
            "command": f"echo 'Starting position {starting_position} would create Fibonacci value {fibonacci(starting_position)} steps'",
            "key": "too-large"
        }]

    pipeline = {
        "env": {
            "FIBONACCI_PIPELINE": "true",
            "PIPELINE_DEPTH": str(starting_position),
            "GROUPS_GENERATED": str(len(steps))
        },
        "steps": steps
    }

    return pipeline


def upload_pipeline(pipeline_config: Dict) -> None:
    """
    Upload the pipeline configuration to Buildkite.

    Like submitting a job to a batch scheduler - we're telling the system
    what work needs to be done and how to do it.

    Args:
        pipeline_config: Complete pipeline configuration

    Reference:
        https://buildkite.com/docs/agent/v3/cli-pipeline
    """
    try:
        # Convert to YAML for Buildkite
        yaml_output = yaml.dump(pipeline_config, default_flow_style=False)

        # In a real Buildkite environment, this would be piped to buildkite-agent
        if os.getenv('BUILDKITE'):
            # Running in actual Buildkite environment
            import subprocess
            process = subprocess.Popen(['buildkite-agent', 'pipeline', 'upload'],
                                     stdin=subprocess.PIPE, text=True)
            process.communicate(input=yaml_output)
        else:
            # Development/demo mode - just print the pipeline
            print("# Generated Buildkite Pipeline YAML")
            print("# " + "=" * 50)
            print(yaml_output)

    except Exception as e:
        print(f"Error uploading pipeline: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main entry point for the Fibonacci pipeline generator.

    Acts like a daemon that can either generate new work or execute existing work
    based on command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate dynamic Buildkite pipeline using Fibonacci sequence",
        epilog="Example: python3 fibonacci_pipeline.py --position 3 --max-depth 8"
    )

    parser.add_argument(
        "--position",
        type=int,
        default=1,
        help="Starting position in Fibonacci sequence (default: 1)"
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="Maximum recursion depth to prevent infinite pipelines (default: 10)"
    )

    parser.add_argument(
        "--emoji-file",
        default="README.md",
        help="Markdown file containing emoji options (default: README.md)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print pipeline YAML without uploading"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.position < 0:
        print("Error: Position must be non-negative", file=sys.stderr)
        sys.exit(1)

    if args.max_depth < 1:
        print("Error: Max depth must be at least 1", file=sys.stderr)
        sys.exit(1)

    # Generate and upload/display pipeline
    pipeline_config = generate_dynamic_pipeline(
        starting_position=args.position,
        max_depth=args.max_depth,
        emoji_file=args.emoji_file
    )

    if args.dry_run or not os.getenv('BUILDKITE'):
        # Print pipeline for inspection
        yaml_output = yaml.dump(pipeline_config, default_flow_style=False)
        print(yaml_output)
    else:
        upload_pipeline(pipeline_config)

    print(f"Generated pipeline with {len(pipeline_config['steps'])} steps "
          f"for Fibonacci position {args.position}", file=sys.stderr)


if __name__ == "__main__":
    main()
