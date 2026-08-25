-- Supabase security baseline for Calcula tu Huella.
--
-- Product contract: browser clients never talk directly to Supabase Data API.
-- The application uses its own FastAPI session/auth layer and direct PostgreSQL
-- access via SQLAlchemy. Therefore anon/authenticated must not receive database
-- object privileges in public. service_role and postgres remain untouched.
--
-- This script is provider-specific and intentionally does NOT advance Alembic.

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL PRIVILEGES ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL PRIVILEGES ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM anon, authenticated;

-- Intentionally not changed here:
-- * service_role privileges;
-- * schema USAGE;
-- * supabase_admin default ACLs (postgres is not a member of that internal role);
-- * RLS policies, because Data API is not an application transport contract.
