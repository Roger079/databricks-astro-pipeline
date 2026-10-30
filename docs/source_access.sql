-- Para ejecutar por el propietario de la tabla o un administrador autorizado.
-- No se ha ejecutado ni se han cambiado permisos desde este proyecto.
-- Permisos mínimos para que ASTRO lea la fuente original; no concede escritura.
GRANT USE CATALOG ON CATALOG workspace TO `a01381456@tec.mx`;
GRANT USE SCHEMA ON SCHEMA workspace.default TO `a01381456@tec.mx`;
GRANT SELECT ON TABLE workspace.default.tb_daily_tld_01_01_2026_m TO `a01381456@tec.mx`;
