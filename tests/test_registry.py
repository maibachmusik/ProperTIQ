"""Block registry — SC-C2 (no drift) and SC-C4 (metadata completeness)."""

from __future__ import annotations

import propertiq as pq
from propertiq import registry
from propertiq.strategy import Criterion, Filter


def _public_block_classes():
    classes = []
    for name in pq.__all__:
        obj = getattr(pq, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, (Filter, Criterion))
            and obj not in (Filter, Criterion)
        ):
            classes.append(obj)
    return set(classes)


def test_registry_has_no_drift():
    # Every public filter/criterion has exactly one registry entry, and vice-versa.
    registered = {b.cls for b in registry.REGISTRY}
    assert registered == _public_block_classes()


def test_registry_keys_unique():
    keys = registry.all_keys()
    assert len(keys) == len(set(keys))


def test_every_block_has_label_and_description():
    for b in registry.REGISTRY:
        assert b.label.strip(), f"{b.key} missing label"
        assert b.description.strip(), f"{b.key} missing description"
        assert b.kind in ("filter", "criterion")


def test_every_param_has_label_and_help():
    for b in registry.REGISTRY:
        for p in b.params:
            assert p.label.strip(), f"{b.key}.{p.name} missing label"
            assert p.help.strip(), f"{b.key}.{p.name} missing help/tooltip"


def test_param_constructor_names_match_class():
    # Every ParamSpec name must be a real constructor arg on the block class.
    import inspect

    for b in registry.REGISTRY:
        sig = set(inspect.signature(b.cls).parameters)
        for p in b.params:
            assert p.name in sig, f"{b.key}.{p.name} is not a constructor arg of {b.cls.__name__}"


def test_filters_and_criteria_partition():
    assert len(registry.filters()) == 9
    assert len(registry.criteria()) == 5


def test_every_block_has_a_category():
    for b in registry.REGISTRY:
        assert b.category.strip(), f"{b.key} missing category"
    assert "Site & terrain" in registry.categories()
