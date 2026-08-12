# Supabase security baseline · Calcula tu Huella

## Decision

Calcula tu Huella does not use Supabase Data API, `supabase-js`, PostgREST or Supabase Auth as an application transport. The browser talks only to FastAPI; FastAPI talks to PostgreSQL through SQLAlchemy.

For that architecture, `anon` and `authenticated` have no business accessing objects in `public`. The provider-specific baseline therefore closes their table/sequence/function grants instead of inventing RLS policies for a transport the product does not use.

`service_role`, the direct PostgreSQL role and schema `USAGE` are intentionally left untouched.

## Applied state · 2026-08-12

Project ref: `thiteaferyakhsoxnbzq` (existing Calcula tu Huella database).

Before hardening, `anon` and `authenticated` had full effective privileges on sensitive tables including `app_users`, `organizations`, `inventories`, `commercial_leads` and the work-item tables. Supabase Security Advisor reported RLS disabled across `public`.

Applied provider migration:

`close_public_data_api_grants_for_direct_postgres_app`

Canonical SQL is stored at `ops/supabase/close_data_api_grants.sql`.

Post-condition checked with PostgreSQL `has_table_privilege` / `has_sequence_privilege`:

- `anon`: no SELECT/INSERT on sampled sensitive tables; no work-item sequence usage;
- `authenticated`: same;
- `postgres`: access retained;
- `service_role`: access retained.

Default privileges owned by `postgres` now grant tables, sequences and functions only to `postgres` and `service_role`, preventing future Alembic objects created by our direct database role from being automatically published to Data API.

## Database integrity after migration reconciliation + security baseline

Alembic revision: `20260812_0040`.

Verified stable row counts:

- organizations: 6
- app_users: 5
- inventories: 7
- activity_data: 290
- commercial_leads: 1
- methodology_source_documents: 18
- work_items / events / links / dependencies: 0 (new tables)

Historical capacities remain:

- `app_users.password_hash`: VARCHAR(255)
- `methodology_source_documents.status`: VARCHAR(160)

## Important distinction: grants vs RLS

Supabase Security Advisor can continue to flag `rls_disabled_in_public` because that lint checks whether RLS is enabled, not whether `anon/authenticated` have effective object privileges. That warning must not be interpreted as permission to enable RLS across the entire ORM without a separate authorization design.

If the product ever adopts Supabase Data API, PostgREST, GraphQL or Supabase Auth for application data, this baseline must be replaced by an explicit grant + RLS policy model and tested per role before exposure.

## Hosting gate

A public FastAPI host may be connected to Pages only after:

1. the host is persistent and independently reachable;
2. its `DATABASE_URL` is injected as a secret, never committed;
3. `/api/health`, `/diagnostico`, `/login`, `/legal/privacidad` and `POST /contacto` pass end-to-end;
4. `site/config.js` is changed from an empty `appBaseUrl` only after that verification.
