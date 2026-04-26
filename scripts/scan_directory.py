#!/usr/bin/env python3
import os


def generate_directory_structure(startpath, output_file):
    """
    Generate a text representation of the directory structure
    starting from the specified path and write it to a file.
    """
    with open(output_file, "w") as f:
        for root, dirs, files in os.walk(startpath):
            # Skip directories that start with a dot (like .git)
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "venv"]

            level = root.replace(startpath, "").count(os.sep)
            indent = " " * 4 * level
            f.write(f"{indent}{os.path.basename(root)}/\n")
            sub_indent = " " * 4 * (level + 1)
            for file in sorted(files):
                if (
                    not file.startswith(".") and file != "scan_directory.py" and file != "Verzeichnisstruktur.txt"
                ):  # Skip hidden files and this script
                    f.write(f"{sub_indent}{file}\n")


if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(current_directory, "Verzeichnisstruktur.txt")

    # Generate structure starting from the current directory
    generate_directory_structure(current_directory, output_file)

    print(f"Directory structure has been written to {output_file}")
