"""Pinned CodeGraphContext launcher with isolated local state; no PATH edits."""
import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'state'
STATE.mkdir(exist_ok=True)
os.environ['USERPROFILE'] = str(STATE)
os.environ['CGC_IGNORE_PROJECT_ENV'] = '1'
os.environ['CGC_RUNTIME_DB_TYPE'] = 'kuzudb'
os.environ.setdefault('CGC_RUNTIME_DB_PATH', str(STATE / 'graphs' / 'default.kuzu'))
os.environ['CGC_EMBEDDED_BUFFER_POOL_MB'] = '256'
os.environ['ENABLE_AUTO_WATCH'] = 'false'
os.environ['ENABLE_VECTOR_RESOLVE'] = 'false'
os.environ['SCIP_INDEXER'] = 'false'
os.environ['ENABLE_INHERIT_RESOLVE'] = 'false'
os.environ['SKIP_EXTERNAL_RESOLUTION'] = 'true'
os.environ['REDACT_SECRETS'] = 'true'
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['PYTHONUTF8'] = '1'
os.environ['TREE_SITTER_LANGUAGE_PACK_CACHE_DIR'] = str(STATE / 'parser-cache')
runpy.run_module('codegraphcontext', run_name='__main__')


