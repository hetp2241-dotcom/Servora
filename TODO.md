# TODO

## Nearby providers map JSON serialization fix
- [x] Update `customer_dashboard` view to serialize `nearby_providers_json` as strict JSON.
- [x] Render the serialized JSON into `data-providers` so JS `JSON.parse(...)` succeeds.

- [x] Keep map/marker/clustering/popup logic unchanged.
- [ ] Run Django checks/tests (or minimal sanity run) to confirm no template/render errors.


