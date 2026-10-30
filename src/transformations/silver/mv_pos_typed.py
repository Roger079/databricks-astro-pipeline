"""Preserve source rows and type POS fields; evaluated by Lakeflow."""
import re
from pyspark import pipelines as dp

catalog, schema = [spark.conf.get(k) for k in ("astro.catalog", "astro.schema")]
assert all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x) for x in (catalog, schema))
assert schema.startswith("astro_")
bronze = f"`{catalog}`.`{schema}`.bronze_pos"

@dp.materialized_view(name='silver_pos_typed')
@dp.expect('valid_date', 'business_date IS NOT NULL')
@dp.expect('valid_total', 'total IS NOT NULL')
def typed():
    return spark.sql(f"""
      SELECT try_cast(store_id AS BIGINT) store_id,
        coalesce(cast(try_to_timestamp(trim(cast(`date` AS STRING)), 'M/d/yyyy') AS DATE),
                 try_cast(`date` AS DATE)) business_date,
        nullif(trim(cast(check_number AS STRING)), '') check_number,
        nullif(trim(cast(menu_item AS STRING)), '') menu_item,
        coalesce(nullif(trim(report_group), ''), 'Unknown') report_group,
        coalesce(nullif(trim(tender_type), ''), 'Unknown') tender_type,
        lower(trim(transaction_type)) transaction_type,
        coalesce(nullif(trim(pop), ''), 'Unknown') channel,
        try_cast(total AS DECIMAL(20,4)) total,
        try_cast(tax AS DECIMAL(20,4)) tax,
        try_cast(total_discount AS DECIMAL(20,4)) total_discount,
        try_cast(menu_price AS DECIMAL(20,4)) menu_price,
        try_cast(item_discount AS DECIMAL(20,4)) item_discount,
        try_cast(item_voided AS DECIMAL(20,4)) item_voided,
        try_cast(order_voided AS DECIMAL(20,4)) order_voided,
        try_cast(quantity AS DECIMAL(20,4)) quantity,
        try_to_timestamp(concat('1970-01-01 ', trim(cast(begin_time AS STRING))), 'yyyy-MM-dd HH:mm:ss[.SSSSSS]') begin_time,
        try_to_timestamp(concat('1970-01-01 ', trim(cast(end_time AS STRING))), 'yyyy-MM-dd HH:mm:ss[.SSSSSS]') end_time,
        sha2(to_json(struct(*)), 256) source_row_hash,
        _astro_amount_grain amount_grain, _astro_demo is_demo,
        _astro_loaded_at loaded_at, _astro_source source_table
      FROM {bronze}
    """)
