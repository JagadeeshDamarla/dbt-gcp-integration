{{ config(materialized='view') }}

-- cte in view      
select 1 as col1
union all
select 2 a col1
union all
select 3 as col1