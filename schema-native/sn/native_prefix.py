"""Model-free legal-prefix proof using the exact bundled library and request grammar."""
import hashlib
import json
from pathlib import Path
import subprocess
from . import paths, provenance
from .native_audit import verified_build


def check_prefix(schema, text, *, grammar):
    if not grammar.startswith('%llguidance {}\nstart: %json '):
        raise ValueError('Only the pinned llguidance request transport is allowed')
    root=Path(paths.ROOT)
    helper=root/'.tools/native-llg-audit'
    library=root/'.tools/llama.cpp/build-metal/llguidance/source/target/release/libllguidance.a'
    build=verified_build(helper,library)
    recorded=json.loads((root/'analysis/e0-compatibility/native-clean.json').read_text())
    if build['library_sha256']!=recorded['library_sha256']:
        raise ValueError('Prefix matcher is not the recorded bundled engine')
    response=subprocess.run([str(helper)],input=json.dumps({'schema':schema,'grammar':grammar,'samples':[text]})+'\n',
                            text=True,capture_output=True,check=True,timeout=60)
    result=json.loads(response.stdout)
    if not result.get('compile_ok') or len(result.get('legal_prefix',[]))!=1:
        raise ValueError('Native prefix verification failed: '+str(result.get('error')))
    return {'legal_prefix':bool(result['legal_prefix'][0]),'accepting':bool(result['accepts'][0]),
            'grammar_sha256':hashlib.sha256(grammar.encode()).hexdigest(),
            'text_sha256':hashlib.sha256(text.encode()).hexdigest(),**build}
