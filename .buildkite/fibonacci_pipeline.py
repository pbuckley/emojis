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
    <img src="img-buildkite-64/nats.png" width="20" height="20" alt="nats"/> | `:nats:`, `:nats-io:`

    Args:
        markdown_file: Path to Buildkite emoji markdown file

    Returns:
        List of emoji alias strings (with colons)
    """
    import re

    emoji_file = Path(markdown_file)
    default_emojis = [":buildkite:", ":rocket:", ":fire:", ":zap:", ":gem:", ":star:", ":sparkles:", ":rainbow:", ":art:", ":tada:"]

    if not emoji_file.exists():
        print(f"DEBUG: Using default Buildkite emoji set since file {markdown_file} does not exist", file=sys.stderr)
        return default_emojis

    emojis = []
    # Match lines with <img> tag followed by | and capture first :alias:
    # Pattern: <img...> | `:something:`, other stuff
    emojis_pattern = re.compile(r'<img[^>]*>\s*\|\s*`:([^`]+):`')

    with emoji_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            match = emojis_pattern.search(line)
            if match:
                alias = match.group(1)  # First (and only) capture group
                emojis.append(f":{alias}:")

    # If we couldn't parse any emojis, provide defaults
    if not emojis:
        print(f"DEBUG: No emojis parsed from {markdown_file}, using defaults", file=sys.stderr)
        return default_emojis

    print(f"DEBUG: Loaded {len(emojis)} emojis from {markdown_file}", file=sys.stderr)
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
    # For groups, just use the emoji alias directly (no repetition for group title)
    return chosen_emoji


def create_pipeline_step(
    fib_position: int,
    current_fib_value: int,
    emoji_options: List[str],
    max_depth: int = 10
) -> Dict:
    """
    Create a Buildkite group step containing N sub-steps.

    Creates a group with current_fib_value number of echo steps inside,
    each with different emoji patterns. Like organizing a team where each
    member has a unique visual identifier but they all work together.

    Args:
        fib_position: Current position in Fibonacci sequence
        current_fib_value: The Fibonacci value at current position (number of sub-steps)
        emoji_options: Available emojis for labels
        max_depth: Maximum recursion depth to prevent infinite pipelines

    Returns:
        Dictionary representing a Buildkite group step

    Reference:
        https://buildkite.com/docs/pipelines/group-step
    """
    # Create the nested steps within this group
    nested_steps = []

    for i in range(current_fib_value):
        # Choose a different emoji for each sub-step
        emoji_index = i % len(emoji_options)
        chosen_emoji = emoji_options[emoji_index]

        # Create label with emoji repeated (fib_position) times
        emoji_label = chosen_emoji * min(fib_position, 25)  # Increased from 10 to 25 for more visual impact

        sub_step = {
            "label": f"{emoji_label} Step {i + 1}/{current_fib_value}",
            "command": "echo foo",
            "key": f"fib-{fib_position}-sub-{i + 1}",
            "env": {
                "FIBONACCI_POSITION": str(fib_position),
                "FIBONACCI_VALUE": str(current_fib_value),
                "SUB_STEP_INDEX": str(i + 1)
            }
        }

        nested_steps.append(sub_step)

    # Create the main group step
    group_emoji = generate_emoji_label(current_fib_value, emoji_options)

    group_step = {
        "group": f"{group_emoji} Fib({fib_position}) = {current_fib_value}",
        "key": f"fib-{fib_position}",
        "steps": nested_steps
    }

    # Add dependency on previous Fibonacci group (except for the first group)
    if fib_position > 1:
        group_step["depends_on"] = f"fib-{fib_position - 1}"

    return group_step


def generate_dynamic_pipeline(
    starting_position: int = 1,
    max_depth: int = 14,
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

    # Debug output
    print(f"DEBUG: Starting pipeline generation with position={starting_position}, max_depth={max_depth}", file=sys.stderr)

    # Generate Fibonacci groups, limiting the number of groups (not position)
    groups_generated = 0
    current_position = starting_position

    while groups_generated < max_depth and current_position <= 30:  # Position cap to prevent runaway
        current_fib_value = fibonacci(current_position)

        print(f"DEBUG: Checking position {current_position}, Fib({current_position})={current_fib_value}, groups_generated={groups_generated}", file=sys.stderr)

        # Only skip if we're creating truly massive individual groups that would break the UI
        if current_fib_value > 5000:  # Much higher limit - let max_depth be the real control
            print(f"DEBUG: Stopping - Fib({current_position}) = {current_fib_value} would create too many sub-steps", file=sys.stderr)
            break

        group_step = create_pipeline_step(
            current_position,
            current_fib_value,
            emoji_options,
            max_depth
        )
        steps.append(group_step)

        print(f"DEBUG: Added group {groups_generated + 1}: Fib({current_position}) = {current_fib_value}", file=sys.stderr)

        groups_generated += 1
        current_position += 1

    # If no groups were generated, add a completion message
    if not steps:
        steps = [{
            "label": "🏁 Fibonacci sequence parameters too large",
            "command": f"echo 'Starting position {starting_position} would create Fibonacci value {fibonacci(starting_position)} steps'",
            "key": "too-large"
        }]

    print(f"DEBUG: Final result - generated {len(steps)} groups", file=sys.stderr)

    pipeline = {
        "env": {
            "FIBONACCI_PIPELINE": "true",
            "PIPELINE_DEPTH": str(starting_position),
            "GROUPS_GENERATED": str(len(steps))
        },
        "steps": steps
    }

    return pipeline


def chunk_steps_by_count(steps: List[Dict], chunk_size: int = 450) -> List[List[Dict]]:
    """
    Chunk pipeline steps into batches to avoid Buildkite's 500-step limit.

    Like splitting a large dataset into manageable batches for processing -
    we need to stay under the 500-step API limit per upload.

    Args:
        steps: List of pipeline steps to chunk
        chunk_size: Maximum steps per chunk (default: 450 for safety margin)

    Returns:
        List of step chunks, each containing <= chunk_size steps
    """
    chunks = []

    for i in range(0, len(steps), chunk_size):
        chunk = steps[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


def count_total_jobs_in_steps(steps: List[Dict]) -> int:
    """
    Count the total number of jobs (including nested jobs in groups).

    Groups can contain multiple sub-steps, so we need to count them all
    to accurately determine if we're approaching the 500-job limit.

    Args:
        steps: List of pipeline steps

    Returns:
        Total count of individual jobs
    """
    total_jobs = 0

    for step in steps:
        if step.get("group"):
            # Group step - count all nested steps
            nested_steps = step.get("steps", [])
            total_jobs += len(nested_steps)
        else:
            # Regular step - count as 1 job
            total_jobs += 1

    return total_jobs


def chunk_steps_by_jobs(steps: List[Dict], max_jobs_per_chunk: int = 450) -> List[List[Dict]]:
    """
    Chunk pipeline steps by total job count instead of step count.

    This is more accurate for group steps since one group can contain
    hundreds of individual jobs. Like a memory allocator that considers
    actual object sizes rather than just object count.

    Args:
        steps: List of pipeline steps to chunk
        max_jobs_per_chunk: Maximum jobs per chunk (default: 450 for safety)

    Returns:
        List of step chunks, each containing <= max_jobs_per_chunk total jobs
    """
    chunks = []
    current_chunk = []
    current_job_count = 0

    for step in steps:
        # Calculate jobs in this step
        if step.get("group"):
            step_job_count = len(step.get("steps", []))
        else:
            step_job_count = 1

        # If adding this step would exceed limit, start new chunk
        if current_job_count + step_job_count > max_jobs_per_chunk and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_job_count = 0

        current_chunk.append(step)
        current_job_count += step_job_count

    # Add remaining steps to final chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def upload_pipeline(pipeline_config: Dict, chunk_uploads: bool = True, dry_run: bool = False) -> None:
    """
    Upload the pipeline configuration to Buildkite with chunking support.

    Like submitting multiple batch jobs instead of one massive job -
    we split large pipelines into chunks to respect Buildkite's 500-job limit.

    Args:
        pipeline_config: Complete pipeline configuration
        chunk_uploads: Whether to chunk uploads for large pipelines
        dry_run: Whether this is a dry run (affects debug output behavior)

    Reference:
        https://buildkite.com/docs/agent/v3/cli-pipeline
        https://buildkite.com/docs/pipelines/configure/dynamic-pipelines
    """
    try:
        steps = pipeline_config.get("steps", [])
        env_vars = pipeline_config.get("env", {})

        # Count total jobs to determine if chunking is needed
        total_jobs = count_total_jobs_in_steps(steps)
        total_steps = len(steps)

        print(f"DEBUG: Total groups: {total_steps}, Total jobs: {total_jobs}", file=sys.stderr)
        print(f"DEBUG: Chunk uploads enabled: {chunk_uploads}", file=sys.stderr)

        # Determine if we need chunking
        needs_chunking = chunk_uploads and total_jobs > 450
        is_buildkite_env = bool(os.getenv('BUILDKITE'))

        print(f"DEBUG: Needs chunking: {needs_chunking} (jobs > 450 and chunking enabled)", file=sys.stderr)
        print(f"DEBUG: Running in Buildkite: {is_buildkite_env}", file=sys.stderr)

        # Show chunking analysis even in dry-run mode
        if needs_chunking:
            step_chunks = chunk_steps_by_jobs(steps, max_jobs_per_chunk=450)
            print(f"DEBUG: Would chunk into {len(step_chunks)} uploads:", file=sys.stderr)
            for i, chunk in enumerate(step_chunks):
                chunk_jobs = count_total_jobs_in_steps(chunk)
                chunk_groups = len(chunk)
                print(f"DEBUG:   Chunk {i + 1}: {chunk_groups} groups, {chunk_jobs} jobs", file=sys.stderr)
        else:
            print("DEBUG: Single upload - no chunking needed", file=sys.stderr)

        # Handle the actual upload logic
        if dry_run or not is_buildkite_env:
            # Dry run or development mode - just print the pipeline with debug info
            if needs_chunking and not dry_run:
                # Only show the chunking warning if not explicitly in dry-run mode
                print(f"# WARNING: {total_jobs} jobs exceeds Buildkite's 500-job limit!", file=sys.stderr)
                print("# This pipeline would be chunked when uploaded to Buildkite", file=sys.stderr)

            print("# Generated Buildkite Pipeline YAML")
            print("# " + "=" * 50)
            yaml_output = yaml.dump(pipeline_config, default_flow_style=False)
            print(yaml_output)

        elif needs_chunking:
            # Production mode with chunking needed
            print(f"DEBUG: Executing chunked upload - {total_jobs} jobs in {len(step_chunks)} chunks", file=sys.stderr)

            step_chunks = chunk_steps_by_jobs(steps, max_jobs_per_chunk=450)

            # Upload each chunk separately
            for i, chunk in enumerate(step_chunks):
                chunk_config = {
                    "env": env_vars,
                    "steps": chunk
                }

                chunk_yaml = yaml.dump(chunk_config, default_flow_style=False)
                chunk_jobs = count_total_jobs_in_steps(chunk)

                print(f"DEBUG: Uploading chunk {i + 1}/{len(step_chunks)} ({len(chunk)} groups, {chunk_jobs} jobs)", file=sys.stderr)

                # Upload this chunk
                import subprocess
                process = subprocess.Popen(['buildkite-agent', 'pipeline', 'upload'],
                                         stdin=subprocess.PIPE, text=True)
                process.communicate(input=chunk_yaml)

                if process.returncode != 0:
                    print(f"Error uploading chunk {i + 1}: exit code {process.returncode}", file=sys.stderr)
                    sys.exit(1)

            print(f"DEBUG: Successfully uploaded {len(step_chunks)} chunks", file=sys.stderr)

        else:
            # Production mode, single upload
            print(f"DEBUG: Executing single upload - {total_jobs} jobs under limit", file=sys.stderr)
            yaml_output = yaml.dump(pipeline_config, default_flow_style=False)

            import subprocess
            process = subprocess.Popen(['buildkite-agent', 'pipeline', 'upload'],
                                     stdin=subprocess.PIPE, text=True)
            process.communicate(input=yaml_output)

            if process.returncode != 0:
                print(f"Error uploading pipeline: exit code {process.returncode}", file=sys.stderr)
                sys.exit(1)

            print("DEBUG: Successfully uploaded single pipeline", file=sys.stderr)

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
        epilog="Example: python3 .buildkite/fibonacci_pipeline.py --position 3 --max-depth 8"
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
        default=14,
        help="Maximum recursion depth to prevent infinite pipelines (default: 14, recommended max: 16)"
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

    parser.add_argument(
        "--chunk-uploads",
        action="store_true",
        default=True,
        help="Enable chunked uploads for large pipelines (default: True)"
    )

    parser.add_argument(
        "--no-chunk-uploads",
        dest="chunk_uploads",
        action="store_false",
        help="Disable chunked uploads (upload entire pipeline at once)"
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

    # Always call upload_pipeline, passing the dry_run flag
    upload_pipeline(
        pipeline_config,
        chunk_uploads=args.chunk_uploads,
        dry_run=args.dry_run
    )

    total_jobs = count_total_jobs_in_steps(pipeline_config.get("steps", []))
    print(f"Generated pipeline with {len(pipeline_config['steps'])} groups ({total_jobs} total jobs) "
          f"for Fibonacci starting at position {args.position}", file=sys.stderr)


if __name__ == "__main__":
    main()
