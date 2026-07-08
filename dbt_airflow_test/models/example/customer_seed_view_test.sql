{{
config(
        materialized = "view",
        schema="PRD_BIWC_MARKETPLACE_SALES_PROV",
        tags=['test_run','view'],
        enabled=True,
        persist_docs={"relation": true, "columns": true},
        query_tag=var("snowflk_query_tag",{'ottoid': '1234', 'team': 'test team'}) | tojson,
        alias="customer_seed_view_test"
)
}}

{% set from_date = var('from_date') %}
{% set to_date = var('to_date') %}

select
    customer_id,
    first_name,
    last_name,
    full_name,
    city,
    state,
    city_state,
    signup_date,
    signup_year,
    account_tier,
    lifetime_value,
    value_segment,
    is_gold_customer,
    cast('{{ from_date }}' as date) as from_date,
    cast('{{ to_date }}' as date) as to_date
from {{ ref('customer_seed_view') }}
where 1 = 1 