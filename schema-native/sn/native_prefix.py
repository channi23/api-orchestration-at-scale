"""Model-free legal-prefix proof using the exact bundled library and request grammar."""
import hashlib
import json
from pathlib import Path
import subprocess
from . import paths
from .native_audit import verified_build
from .router import strict_loads
from .e0b_resources import ResourceStop


class PrefixCheckUnavailable(ResourceStop):
    """No prefix verdict: preserve the response and resume only after offline verification."""


def _audit(schema, samples, grammar):
    try:
        if not grammar.startswith('%llguidance {}\nstart: %json '):
            raise ValueError('Only the pinned llguidance request transport is allowed')
        root=Path(paths.ROOT)
        helper=root/'.tools/native-llg-audit'
        library=root/'.tools/llama.cpp/build-metal/llguidance/source/target/release/libllguidance.a'
        build=verified_build(helper,library)
        recorded=json.loads((root/'analysis/e0-compatibility/native-clean.json').read_text())
        if build['library_sha256']!=recorded['library_sha256']:
            raise ValueError('Prefix matcher is not the recorded bundled engine')
        response=subprocess.run([str(helper)],input=json.dumps({'schema':schema,'grammar':grammar,'samples':samples})+'\n',
                                text=True,capture_output=True,check=True,timeout=60)
        result=strict_loads(response.stdout)
        if not isinstance(result,dict) or result.get('compile_ok') is not True:
            raise ValueError('Native prefix grammar compilation failed')
        for name in ('legal_prefix','accepts'):
            values=result.get(name)
            if not isinstance(values,list) or len(values)!=len(samples) or any(type(v) is not bool for v in values):
                raise ValueError('Malformed native prefix verdict: '+name)
        return result,build
    except Exception as exc:
        raise PrefixCheckUnavailable(type(exc).__name__+': '+str(exc)) from exc


def check_prefix(schema, text, *, grammar):
    result,build=_audit(schema,[text],grammar)
    return {'legal_prefix':result['legal_prefix'][0],'accepting':result['accepts'][0],
            'grammar_sha256':hashlib.sha256(grammar.encode()).hexdigest(),
            'text_sha256':hashlib.sha256(text.encode()).hexdigest(),**build}


def verify_prefix(schema,text,*,grammar,prefix_checker=None):
    """Also validate injected checker results; unavailable never means illegal."""
    try:
        proof=(prefix_checker or check_prefix)(schema,text,grammar=grammar)
        if not isinstance(proof,dict) or type(proof.get('legal_prefix')) is not bool:
            raise ValueError('Malformed prefix checker output')
        return proof
    except PrefixCheckUnavailable: raise
    except Exception as exc:
        raise PrefixCheckUnavailable(type(exc).__name__+': '+str(exc)) from exc


def self_test():
    """One helper invocation, three fixed probes; no tokenizer, weights or server."""
    schema={'type':'object','properties':{'n':{'const':7}},'required':['n'],'additionalProperties':False}
    grammar='%llguidance {}\nstart: %json '+json.dumps(schema)
    result,build=_audit(schema,['{"n":7}','{"n":','{"n":8}'],grammar)
    if result['legal_prefix']!=[True,True,False] or result['accepts']!=[True,False,False]:
        raise PrefixCheckUnavailable('Native helper self-test verdicts differ from fixed probes')
    return dict(passed=True,probes=3,helper_invocations=1,**build)
