#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path

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


def should_include_file(file_path, include_exts, exclude_exts):
    """
    Decide if a file should be included based on the provided include/exclude lists.

    - `file_path`: Full path to the file.
    - `include_exts`: A set of extensions to include. If non-empty, only these are included.
    - `exclude_exts`: A set of extensions to exclude.

    Returns True if the file should be included, False otherwise.
    """
    ext = Path(file_path).suffix.lower().lstrip(".")

    # If `include_exts` is non-empty, the file extension must appear in that set.
    if include_exts and ext not in include_exts:
        return False

    # If the file extension is in `exclude_exts`, skip it.
    if exclude_exts and ext in exclude_exts:
        return False

    return True


def gather_files(paths, recursive=False, include_exts=None, exclude_exts=None):
    """
    Given a list of paths (files or directories), return a list of files found.
    If 'recursive' is False, only list immediate files in directories.
    The `include_exts` and `exclude_exts` sets specify which extensions to include/exclude.
    """
    all_files = []

    for p in paths:
        path_obj = Path(p).resolve()

        if not path_obj.exists():
            print(f"Warning: {path_obj} does not exist. Skipping.", file=sys.stderr)
            continue

        if path_obj.is_file():
            if should_include_file(str(path_obj), include_exts, exclude_exts):
                all_files.append(str(path_obj))
        else:
            if recursive:
                for root, dirs, files in os.walk(path_obj):
                    for f in files:
                        file_path = str(Path(root) / f)
                        if should_include_file(file_path, include_exts, exclude_exts):
                            all_files.append(file_path)
            else:
                for f in path_obj.iterdir():
                    if f.is_file():
                        file_path = str(f.resolve())
                        if should_include_file(file_path, include_exts, exclude_exts):
                            all_files.append(file_path)

    return sorted(all_files)


def build_directory_tree(file_paths):
    """
    Build a nested dictionary representing the directory structure
    for only the files that will be concatenated. We then return
    this dictionary so we can print a tree of those files.
    """
    root = {}

    for f in file_paths:
        parts = Path(f).parts
        # Navigate down the dict, creating subdicts as needed
        current = root
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        # Add the file itself to a special key "_files"
        current.setdefault("_files", []).append(parts[-1])

    return root


def print_directory_tree(tree, indent="", lines=None):
    """
    Recursively print the directory structure from a nested dictionary
    (as produced by build_directory_tree). 
    """
    if lines is None:
        lines = []

    # Keys that are not "_files" are subdirectories
    subdirs = [k for k in tree.keys() if k != "_files"]
    # Sort them for a consistent ordering
    subdirs.sort()

    # Print subdirectories first
    for d in subdirs:
        lines.append(f"{indent}{d}/")
        print_directory_tree(tree[d], indent + "  ", lines)

    # Now handle files
    if "_files" in tree:
        files = tree["_files"]
        # Sort them for a consistent ordering
        files.sort()
        for f in files:
            lines.append(f"{indent}  {f}")

    return lines


def main():
    args = parse_arguments()

    # Prepare sets of included or excluded extensions (lowercase, no leading ".")
    include_exts = set(e.lower().lstrip(".") for e in args.include) if args.include else None
    exclude_exts = set(e.lower().lstrip(".") for e in args.exclude) if args.exclude else None

    # 1. Gather files from the provided paths
    file_paths = gather_files(
        args.paths,
        recursive=args.recursive,
        include_exts=include_exts,
        exclude_exts=exclude_exts
    )

    # 2. Build a nested structure *only* for the files that are actually going to be concatenated
    directory_tree = build_directory_tree(file_paths)
    tree_lines = print_directory_tree(directory_tree)

    # Open output destination (file or stdout)
    if args.output:
        out_f = open(args.output, "w", encoding="utf-8", errors="replace")
    else:
        out_f = sys.stdout

    try:
        # 3. Write the header
        out_f.write("===== Directory Structure Header =====\n")
        if file_paths:
            for line in tree_lines:
                out_f.write(line + "\n")
        else:
            out_f.write("(No files matched the filters.)\n")
        out_f.write("======================================\n\n")

        # 4. Concatenate each file
        for fpath in file_paths:
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

    # If we were writing to a file, let the user know
    if args.output:
        print(f"All files concatenated into '{args.output}'.")
    else:
        print("All files concatenated to STDOUT.")


if __name__ == "__main__":
    main()
