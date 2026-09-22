-- Least-privilege database roles (§6.2 C-08/C-09).
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'c360_app') THEN
        CREATE ROLE c360_app LOGIN PASSWORD 'c360_app';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'c360_loader') THEN
        CREATE ROLE c360_loader LOGIN PASSWORD 'c360_loader';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE c360 TO c360_app, c360_loader;
