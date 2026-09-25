#!/usr/bin/env bash

require_teleopit_conda() {
  if [[ "${CONDA_DEFAULT_ENV:-}" != "teleopit" || -z "${CONDA_PREFIX:-}" ]]; then
    cat >&2 <<'EOF'
The Conda environment "teleopit" must be active.
Run:
  source /home/unitree/miniforge3/bin/activate teleopit
EOF
    return 2
  fi

  TELEOPIT_PYTHON="$(command -v python || true)"
  if [[ -z "$TELEOPIT_PYTHON" || ! -x "$TELEOPIT_PYTHON" ]]; then
    echo "Python is not available in the active teleopit environment." >&2
    return 2
  fi

  local python_prefix python_version
  python_prefix="$("$TELEOPIT_PYTHON" -c 'import os, sys; print(os.path.realpath(sys.prefix))')"
  if [[ "$python_prefix" != "$(realpath "$CONDA_PREFIX")" ]]; then
    echo "The python command does not belong to the active teleopit environment: $TELEOPIT_PYTHON" >&2
    return 2
  fi

  python_version="$("$TELEOPIT_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$python_version" != "3.10" && "$python_version" != "3.11" ]]; then
    echo "The teleopit environment must use Python 3.10 or 3.11; found $python_version." >&2
    return 2
  fi

  export TELEOPIT_PYTHON
}
