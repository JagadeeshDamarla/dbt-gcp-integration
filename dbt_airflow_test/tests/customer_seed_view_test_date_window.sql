-- Fails if any row has an invalid date window.
select
  customer_id,
  from_date,
  to_date
from {{ ref('customer_seed_view_test') }}
where from_date > to_date
