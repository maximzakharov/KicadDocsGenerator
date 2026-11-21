#!/usr/bin/env bash
#
# Development installer for KicadDocsGenerator.
#
# Symlinks (default) or copies the plugin package into the KiCad
# "scripting/plugins" folders found on this machine, so the plugin loads
# straight from this repository checkout - no release zip or PCM needed.
# With a symlink every `git pull` / code edit is picked up on the next
# KiCad restart.
#
# Usage:
#   ./install-local.sh                  install into all detected KiCad versions
#   ./install-local.sh --version 9.0    install only into KiCad 9.0
#   ./install-local.sh --copy           copy files instead of symlinking
#   ./install-local.sh --uninstall      remove the development install
#   ./install-local.sh --list           show detected KiCad versions and status
#   ./install-local.sh --deps           print Python dependency instructions
#   ./install-local.sh --help
#
# Notes:
#   - On Windows run from Git Bash with --copy (symlinks need dev mode).
#   - Restart KiCad (pcbnew) after installing or changing plugin code:
#     ActionPlugins are registered at startup.
#   - This script never touches PCM-installed packages (thirdparty folders).

set -euo pipefail

TARGET_NAME="KicadDocsGenerator"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/plugins"
MARKER=".devinstall"

MODE="install"      # install | uninstall | list | deps
LINK_MODE="symlink" # symlink | copy
ONLY_VERSION=""
FORCE=0

usage() { sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }

while [ $# -gt 0 ]; do
    case "$1" in
        --version)  ONLY_VERSION="${2:?--version needs a value, e.g. 9.0}"; shift 2 ;;
        --copy)     LINK_MODE="copy"; shift ;;
        --uninstall) MODE="uninstall"; shift ;;
        --list)     MODE="list"; shift ;;
        --deps)     MODE="deps"; shift ;;
        --force)    FORCE=1; shift ;;
        -h|--help)  usage ;;
        *)          echo "Unknown option: $1" >&2; usage >&2 ;;
    esac
done

if [ ! -f "$PLUGIN_SRC/__init__.py" ]; then
    echo "ERROR: $PLUGIN_SRC/__init__.py not found - run from the repo root." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# KiCad detection
# ---------------------------------------------------------------------------

kicad_base_dir() {
    case "$(uname -s)" in
        Darwin)
            echo "$HOME/Documents/KiCad"
            ;;
        Linux)
            echo "${XDG_DATA_HOME:-$HOME/.local/share}/kicad"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            # Git Bash on Windows
            cygpath -u "${APPDATA:-}" 2>/dev/null | sed 's|$|/kicad|'
            ;;
        *)
            echo ""
            ;;
    esac
}

# Prints one "<version> <scripting plugins dir>" pair per detected KiCad.
detect_kicads() {
    local base version plugins_dir
    base="$(kicad_base_dir)"
    [ -z "$base" ] && return 0
    [ -d "$base" ] || return 0

    for version in "$base"/*/; do
        version="$(basename "$version")"
        case "$version" in
            [0-9]*.[0-9]*) ;;    # looks like 7.0, 8.99, 10.0 ...
            *) continue ;;
        esac
        if [ -n "$ONLY_VERSION" ] && [ "$version" != "$ONLY_VERSION" ]; then
            continue
        fi
        plugins_dir="$base/$version/scripting/plugins"
        if [ -d "$base/$version/scripting" ] || [ -d "$plugins_dir" ]; then
            echo "$version $plugins_dir"
        fi
    done
}

# ---------------------------------------------------------------------------
# Install / uninstall
# ---------------------------------------------------------------------------

# Status of an installed target: symlink | copy | foreign | none
target_status() {
    local target="$1"
    if [ -L "$target" ]; then
        echo "symlink"
    elif [ -d "$target" ] && [ -e "$target/$MARKER" ]; then
        echo "copy"
    elif [ -e "$target" ]; then
        echo "foreign"
    else
        echo "none"
    fi
}

remove_existing() {
    local target="$1" status="$2" version="$3"
    case "$status" in
        symlink|copy)
            rm -rf "$target"
            ;;
        foreign)
            if [ "$FORCE" -eq 1 ]; then
                echo "  --force: replacing foreign $target"
                rm -rf "$target"
            else
                echo "  SKIP $version: $target exists and was not installed by" \
                     "this script (use --force to replace)" >&2
                return 1
            fi
            ;;
    esac
}

install_one() {
    local version="$1" plugins_dir="$2"
    local target="$plugins_dir/$TARGET_NAME"
    mkdir -p "$plugins_dir"

    remove_existing "$target" "$(target_status "$target")" "$version" || return 0

    if [ "$LINK_MODE" = "symlink" ]; then
        ln -s "$PLUGIN_SRC" "$target"
        echo "  $version: symlink $target -> $PLUGIN_SRC"
    else
        cp -R "$PLUGIN_SRC" "$target"
        find "$target" -type d -name __pycache__ -prune -exec rm -rf {} +
        touch "$target/$MARKER"
        echo "  $version: copied to $target"
    fi
}

uninstall_one() {
    local version="$1" plugins_dir="$2"
    local target="$plugins_dir/$TARGET_NAME"
    case "$(target_status "$target")" in
        symlink|copy)
            rm -rf "$target"
            echo "  $version: removed $target"
            ;;
        foreign)
            echo "  SKIP $version: $target was not installed by this script" >&2
            ;;
        none)
            echo "  $version: not installed"
            ;;
    esac
}

list_one() {
    local version="$1" plugins_dir="$2"
    local target="$plugins_dir/$TARGET_NAME"
    echo "  $version  ($(target_status "$target"))  $plugins_dir"
}

print_deps_help() {
    cat <<'EOF'
Python dependencies for the plugin (installed into the Python that KiCad
uses - see README "Problem with Ubuntu"):

    pip install pandas openpyxl xlsxwriter pymupdf

Linux + PyMuPDF segfault workaround:

    sudo apt install python3-fitz

KiCad on macOS/Windows bundles its own Python. If the modules are not
picked up, install them with the same interpreter KiCad uses, or check
~/.KicadDocsGenerator/logs for import errors.
EOF
}

# ---------------------------------------------------------------------------

case "$MODE" in
    deps) print_deps_help; exit 0 ;;
esac

DETECTED="$(detect_kicads)"
if [ -z "$DETECTED" ]; then
    echo "No KiCad installations detected."
    [ -n "$ONLY_VERSION" ] && echo "Requested version: $ONLY_VERSION"
    exit 1
fi

case "$MODE" in
    list)
        echo "Detected KiCad installations (status: symlink/copy/foreign/none):"
        echo "$DETECTED" | while read -r version dir; do list_one "$version" "$dir"; done
        ;;
    install)
        echo "Installing $TARGET_NAME ($LINK_MODE mode) into:"
        echo "$DETECTED" | while read -r version dir; do install_one "$version" "$dir"; done
        echo "Done. Restart KiCad to load the plugin."
        if [ "$LINK_MODE" = "copy" ]; then
            echo "Remember: --copy needs a re-run after every code change."
        fi
        ;;
    uninstall)
        echo "Removing $TARGET_NAME from:"
        echo "$DETECTED" | while read -r version dir; do uninstall_one "$version" "$dir"; done
        ;;
esac
