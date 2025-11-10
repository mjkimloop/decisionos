-- Gate-F RLS scaffold (PostgreSQL)
-- Enable RLS on decisions and audit_ledger tables and scope to app.current_tenant

ALTER TABLE IF EXISTS decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_ledger ENABLE ROW LEVEL SECURITY;

-- Create policies (assumes org_id column on decisions; audit_ledger annotated via payload JSONB with org_id)
DROP POLICY IF EXISTS decisions_tenant_policy ON decisions;
CREATE POLICY decisions_tenant_policy ON decisions USING (
  current_setting('app.current_tenant', true) IS NULL OR org_id = current_setting('app.current_tenant')
);

DROP POLICY IF EXISTS audit_tenant_policy ON audit_ledger;
CREATE POLICY audit_tenant_policy ON audit_ledger USING (
  current_setting('app.current_tenant', true) IS NULL OR (payload ->> 'org_id') = current_setting('app.current_tenant')
);

-- Optional: helper role and setting hook could be added in migrations/env
