from __future__ import annotations
from cannula import utils


def test_gql():
    schema = utils.gql("type Foo { id: Int }")
    assert schema.to_dict() == {
        "definitions": [
            {
                "description": None,
                "directives": [],
                "fields": [
                    {
                        "arguments": [],
                        "description": None,
                        "directives": [],
                        "kind": "field_definition",
                        "name": {"kind": "name", "value": "id"},
                        "type": {
                            "kind": "named_type",
                            "name": {"kind": "name", "value": "Int"},
                        },
                    }
                ],
                "interfaces": [],
                "kind": "object_type_definition",
                "name": {"kind": "name", "value": "Foo"},
            }
        ],
        "kind": "document",
    }
