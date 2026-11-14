import json
import pytest
from sn.native_audit import verified_build
from sn.provenance import file_sha


def test_static_helper_identity_rejects_stale_library_and_replaced_helper(tmp_path):
    helper = tmp_path / 'audit'
    library = tmp_path / 'lib.a'
    helper.write_bytes(b'helper')
    library.write_bytes(b'library')
    metadata = {'library_sha256': file_sha(library), 'helper_sha256': file_sha(helper)}
    helper.with_suffix('.build.json').write_text(json.dumps(metadata))
    assert verified_build(helper, library) == metadata
    library.write_bytes(b'rebuilt library')
    with pytest.raises(ValueError, match='build mismatch'):
        verified_build(helper, library)
    library.write_bytes(b'library')
    helper.write_bytes(b'replaced helper')
    with pytest.raises(ValueError, match='build mismatch'):
        verified_build(helper, library)
