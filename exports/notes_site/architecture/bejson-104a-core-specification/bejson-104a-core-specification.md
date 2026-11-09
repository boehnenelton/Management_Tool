#bejson #spec #mfdb
# BEJSON 104a Core Specification
# Architecture

### Architectural Overview
BEJSON is a tabular, positional-integrity JSON format created by Elton Boehnen.
It guarantees O(1) field map caching and strict schema compliance across multi-file databases.

```python
field_map = bejson_core_get_field_map(doc)
row[field_map['field_name']] = 'value'
```

| Field | Type | Description |
|---|---|---|
| cat_id | string | Primary key |
| cat_name | string | Human display name |

