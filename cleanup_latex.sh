#!/bin/bash

# =========================================================
# cleanup_latex.sh
#
# Recursively remove common LaTeX build artifacts from
# the current directory and all subdirectories.
#
# Usage:
#   ./cleanup_latex.sh
# =========================================================

echo "Cleaning LaTeX build artifacts..."
echo

find . \( \
    -name "*.aux" -o \
    -name "*.log" -o \
    -name "*.out" -o \
    -name "*.toc" -o \
    -name "*.synctex.gz" -o \
    -name "*.fdb_latexmk" -o \
    -name "*.fls" -o \
    -name "*.bbl" -o \
    -name "*.bcf" -o \
    -name "*.blg" -o \
    -name "*.run.xml" -o \
    -name "*.nav" -o \
    -name "*.snm" \
\) -type f -print -delete

echo
echo "Cleanup complete."
