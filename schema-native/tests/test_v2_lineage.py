import pytest

from sn import v2_lineage as lineage


def test_groups_project_paths_across_github_complexities():
    index = {
        "js_12.json": "http://github.com/Example/Project/blob/master/one.json?raw=true",
        "js_13.json": "https://github.com/example/project/blob/main/two.json",
    }
    a = lineage.origin("Github_easy/o12", index)
    b = lineage.origin("Github_medium/o13", index)
    assert a[:2] == b[:2] == ("github:example/project", "indexed_repository")
    assert a[2] != b[2]
    assert lineage.origin("Github_easy/o15", index)[0] is None
    assert lineage.origin("Snowplow/sp_12_Normalized", index) == (
        "collection:Snowplow", "collection_only", None
    )


def test_changed_source_index_fails_closed(tmp_path):
    path = tmp_path / "repos_fullpath.csv"
    path.write_text("js_12.json https://github.com/example/project/blob/main/one.json\n")
    with pytest.raises(ValueError, match="pinned corpus snapshot"):
        lineage.load_index(path)


def test_family_and_exact_schema_connect_transitively_without_splitting_pair():
    families = {"T1": ["pool:calendar"], "T2": ["pool:calendar", "glaive:meeting"],
                "X1": ["glaive:meeting"]}
    hashes = {"T1": ["a"], "T2": ["b"], "X1": ["c"],
              "legacy:fixture": ["c"], "seed:K1": ["d", "e"], "unrelated": ["f"]}
    result = lineage.components(families, hashes)
    assert result == lineage.components(families, dict(reversed(list(hashes.items()))))
    cluster = next(value for value in result.values() if "X1" in value["members"])
    assert cluster["members"] == ["T1", "T2", "X1", "legacy:fixture"]
    assert {link["reason"] for link in cluster["links"]} == {"canonical", "family"}
    assert any(group["members"] == ["seed:K1"] for group in result.values())
    assert any(group["members"] == ["unrelated"] for group in result.values())
