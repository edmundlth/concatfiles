#!/usr/bin/env python3

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Concatenate multiple files into one, "
                    "with a directory structure header and file delimiters."
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="+",
        help="One or more files/directories to process."
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file name. If not specified, outputs to STDOUT."
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively traverse directories to find files."
    )
    parser.add_argument(
        "--include",
        metavar="EXT",
        action="append",
        default=None,
        help="Include only files with these extensions (multiple allowed). "
             "Example: --include py --include txt"
    )
    parser.add_argument(
        "--exclude",
        metavar="EXT",
        action="append",
        default=None,
        help="Exclude files with these extensions (multiple allowed). "
             "Example: --exclude ipynb --exclude json"
    )
    return parser.parse_args()


def should_include_file(file_path: Path, include_exts, exclude_exts) -> bool:
    """
    Decide if a file should be included based on the provided include/exclude lists.

    - file_path: Path object pointing to a file.
    - include_exts: A set of extensions to include. If non-empty, only these are included.
    - exclude_exts: A set of extensions to exclude.

    Returns True if the file should be included, False otherwise.
    """
    ext = file_path.suffix.lower().lstrip(".")
    # If `include_exts` is non-empty, only those extensions are allowed.
    if include_exts and ext not in include_exts:
        return False
    # If the file extension is in `exclude_exts`, skip it.
    if exclude_exts and ext in exclude_exts:
        return False
    return True


def gather_files_for_path(
    path: Path, 
    recursive: bool, 
    include_exts, 
    exclude_exts
) -> List[Path]:
    """
    Gather a list of files under a single top-level path (file or directory),
    respecting the recursive flag and include/exclude filters.
    Returns a list of absolute Paths.
    """
    gathered = []

    if not path.exists():
        print(f"Warning: {path} does not exist. Skipping.", file=sys.stderr)
        return gathered

    # If it's a single file, just check if it passes the filters
    if path.is_file():
        if should_include_file(path, include_exts, exclude_exts):
            gathered.append(path.resolve())
        return gathered

    # If it's a directory:
    if recursive:
        for root, dirs, files in os.walk(path):
            for f in files:
                full_path = Path(root) / f
                if should_include_file(full_path, include_exts, exclude_exts):
                    gathered.append(full_path.resolve())
    else:
        for f in path.iterdir():
            if f.is_file():
                if should_include_file(f, include_exts, exclude_exts):
                    gathered.append(f.resolve())

    return gathered


def gather_all_files(
    paths: List[str],
    recursive: bool,
    include_exts,
    exclude_exts
) -> Dict[Path, List[Path]]:
    """
    For each top-level path provided by the user, gather all matching files
    (absolute Paths) and store them in a dictionary keyed by the top-level Path (resolved).

    Example return structure:
    {
      Path('/abs/path/to/dirA'): [Path('/abs/path/to/dirA/file1.txt'), ...],
      Path('/abs/path/to/some_file.py'): [Path('/abs/path/to/some_file.py')]
    }
    """
    results = {}
    for p in paths:
        top_path = Path(p).resolve()
        files = gather_files_for_path(top_path, recursive, include_exts, exclude_exts)
        results[top_path] = sorted(files, key=lambda x: str(x))
    return results


def build_directory_structure_for_files(
    top_path: Path, 
    files: List[Path]
) -> List[str]:
    """
    Given a single top-level path and a list of *absolute* file paths under it,
    build a mini "tree" (list of lines) showing their structure relative to top_path.

    If top_path is a file, we just show that file name (if it was included).
    If top_path is a directory, we show a tree structure from top_path down.
    """
    lines = []

    if top_path.is_file():
        # top_path is already in `files` if it was included
        # Just show the file name, no sub-tree
        if len(files) == 1:  # The top_path itself
            lines.append(str(top_path.name))
        elif len(files) > 1:
            # Very unusual edge case: user passed a file path that somehow matched multiple?
            # Realistically that won't happen, but let's handle gracefully
            lines.extend(str(f.name) for f in files)
        return lines

    # If it's a directory, build a structure
    # Approach: a nested dict from the relative paths
    tree = {}
    for f in files:
        relative = f.relative_to(top_path)  # path from top_path
        parts = relative.parts
        current = tree
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current.setdefault("_files", []).append(parts[-1])

    lines.append(f"{top_path.name}/")  # Start with the directory name
    _print_tree(tree, indent="  ", lines=lines)
    return lines


def _print_tree(node: dict, indent: str, lines: List[str]):
    """
    Recursively print the directory structure from a nested dictionary.
    A node's subdirs are all keys except "_files".
    """
    subdirs = [k for k in node.keys() if k != "_files"]
    subdirs.sort()
    for d in subdirs:
        lines.append(f"{indent}{d}/")
        _print_tree(node[d], indent + "  ", lines)

    if "_files" in node:
        files = node["_files"]
        files.sort()
        for f in files:
            lines.append(f"{indent}{f}")


def main():
    args = parse_arguments()

    # Prepare sets of included or excluded extensions (lowercase, no leading ".")
    include_exts = set(e.lower().lstrip(".") for e in args.include) if args.include else None
    exclude_exts = set(e.lower().lstrip(".") for e in args.exclude) if args.exclude else None

    # 1. Gather files per top-level path
    file_dict = gather_all_files(
        args.paths,
        recursive=args.recursive,
        include_exts=include_exts,
        exclude_exts=exclude_exts
    )

    # Create one combined list of all files for concatenation
    all_files = []
    for file_list in file_dict.values():
        all_files.extend(file_list)
    # Sort them by path just for consistency
    all_files = sorted(all_files, key=lambda x: str(x))

    # 2. Open output destination (file or stdout)
    if args.output:
        out_f = open(args.output, "w", encoding="utf-8", errors="replace")
    else:
        out_f = sys.stdout

    try:
        # 3. Write the header
        out_f.write("===== Directory Structure Header =====\n")
        something_printed = False

        for top_path, files in file_dict.items():
            # Only print a sub-tree if we actually have files
            if not files:
                continue

            something_printed = True
            # Print a small label for each top-level path
            # or skip if it's clearly a single item?
            lines = build_directory_structure_for_files(top_path, files)
            for line in lines:
                out_f.write(line + "\n")
        if not something_printed:
            out_f.write("(No files matched the filters.)\n")

        out_f.write("======================================\n\n")

        # 4. Concatenate each file
        for fpath in all_files:
            out_f.write(f"===== START OF FILE: {fpath} =====\n")
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as in_f:
                    for line in in_f:
                        out_f.write(line)
            except Exception as e:
                out_f.write(f"[Error reading file: {e}]\n")
            out_f.write(f"===== END OF FILE: {fpath} =====\n\n")

    finally:
        if out_f is not sys.stdout:
            out_f.close()

    # If we wrote to a file, let the user know
    if args.output:
        print(f"All files concatenated into '{args.output}'.")
    else:
        print("All files concatenated to STDOUT.")


if __name__ == "__main__":
    main()
