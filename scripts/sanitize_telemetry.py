#!/usr/bin/env python3
"""Small CLI wrapper for the PARA KB telemetry sanitizer."""

import argparse
from para_kb_telemetry import run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--cwd")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    forwarded: list[str] = []
    if args.config:
        forwarded.extend(["--config", args.config])
    if args.cwd:
        forwarded.extend(["--cwd", args.cwd])
    forwarded.extend(["sanitize", args.input, args.output])
    return run(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
