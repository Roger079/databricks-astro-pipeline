-- Referencia mínima de lectura de la fuente. No ejecutada automáticamente.
-- Estos permisos ya están incluidos en los grants de proyecto aplicados al equipo;
-- conservar como diagnóstico para nuevas identidades. No cubren esquemas astro_* nuevos.
GRANT USE CATALOG ON CATALOG workspace TO `a01381456@tec.mx`;
GRANT USE SCHEMA ON SCHEMA workspace.default TO `a01381456@tec.mx`;
GRANT SELECT ON TABLE workspace.default.tb_daily_tld_01_01_2026_m TO `a01381456@tec.mx`;
-- 01_ingest concede ALL PRIVILEGES y MANAGE en el destino a team_principals.
