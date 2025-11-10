# Naming Convention Guide

## Overview
This document establishes standardized naming conventions for data assets, tables, columns, and other artifacts in the DecisionOS data platform.

## General Principles

1. **Clarity**: Names should be self-explanatory and unambiguous
2. **Consistency**: Follow the same patterns across all assets
3. **Brevity**: Keep names concise while maintaining clarity
4. **Avoid Abbreviations**: Use full words unless abbreviation is industry-standard
5. **No Reserved Keywords**: Avoid SQL/database reserved words
6. **Case Sensitivity**: Use lowercase with underscores (snake_case)

## Database and Schema Naming

### Pattern
```
{tier}_{domain}_{purpose}
```

### Examples
- `raw_customer_salesforce`
- `cleaned_sales_transactions`
- `conformed_customer_master`
- `analytics_marketing_campaigns`
- `products_customer_segments`

### Guidelines
- Start with tier prefix: `raw`, `cleaned`, `conformed`, `analytics`, `products`
- Include domain: `customer`, `product`, `sales`, `marketing`, `operations`, `finance`
- Add specific purpose or source system name
- Maximum 63 characters

## Table Naming

### Pattern
```
{entity}_{type}_{qualifier}
```

### Entity Names
- Use plural for fact tables: `orders`, `transactions`, `events`
- Use singular for dimension tables: `customer`, `product`, `date`
- Use descriptive names for aggregates: `daily_sales`, `monthly_revenue`

### Type Suffixes
- `_fact`: Fact tables (optional, implied by plural)
- `_dim`: Dimension tables (optional, implied by singular)
- `_bridge`: Bridge tables for many-to-many relationships
- `_snapshot`: Point-in-time snapshots
- `_scd`: Slowly Changing Dimension tables
- `_agg`: Aggregated/rolled-up data
- `_tmp`: Temporary tables
- `_stg`: Staging tables

### Examples
- `customers_dim`
- `orders_fact`
- `customer_product_bridge`
- `inventory_snapshot`
- `product_scd`
- `daily_sales_agg`
- `customer_import_stg`

### Guidelines
- Maximum 63 characters
- Avoid prefixing with tier (tier is in schema name)
- Include time grain for aggregates: `daily_`, `weekly_`, `monthly_`
- Use consistent entity names across schemas

## Column Naming

### Pattern
```
{entity}_{attribute}_{modifier}
```

### Primary Keys
```
{entity}_id
```
Examples: `customer_id`, `order_id`, `product_id`

### Foreign Keys
```
{referenced_entity}_id
```
Examples: `customer_id`, `product_id`, `account_id`

### Attribute Naming
- Use descriptive full words: `first_name`, `email_address`, `order_total`
- Avoid cryptic abbreviations: Use `quantity` not `qty`, `amount` not `amt`
- Standard abbreviations allowed: `id`, `url`, `ip`, `iso`

### Boolean Columns
Prefix with `is_`, `has_`, or `can_`:
- `is_active`
- `has_subscription`
- `can_purchase`

### Date/Timestamp Columns
Suffix with type indicator:
- `_date`: Date only (no time component)
  - `order_date`, `birth_date`, `effective_date`
- `_timestamp` or `_at`: Date and time
  - `created_at`, `updated_at`, `processed_timestamp`
- `_datetime`: Explicit date and time (alternative to _timestamp)

### Amount/Quantity Columns
Be explicit about currency and units:
- `{item}_amount`: Monetary amount
  - `order_amount`, `discount_amount`
- `{item}_quantity`: Count or quantity
  - `order_quantity`, `item_count`
- `{item}_percent` or `{item}_rate`: Percentages/rates
  - `discount_percent`, `conversion_rate`

### Derived/Calculated Columns
Indicate calculation in name:
- `total_{item}`: Sum aggregation
  - `total_revenue`, `total_orders`
- `avg_{item}`: Average
  - `avg_order_value`, `avg_rating`
- `{item}_rank`: Ranking
  - `sales_rank`, `customer_rank`
- `{item}_score`: Calculated score
  - `credit_score`, `propensity_score`

### Examples
```sql
-- Good
customer_id
first_name
last_name
email_address
created_at
is_active
total_order_count
lifetime_value_amount

-- Avoid
cust_id
fname
lname
email
created
active
orders
ltv
```

## View Naming

### Pattern
```
{prefix}_{entity}_{description}
```

### Prefixes
- `v_`: Standard view
- `mv_`: Materialized view
- `rpt_`: Reporting view
- `api_`: API exposure view

### Examples
- `v_customer_360`
- `mv_daily_sales_summary`
- `rpt_executive_dashboard`
- `api_product_catalog`

## Data Product Naming

### Pattern
```
{domain}_{product_name}_{version}
```

### Examples
- `customer_segmentation_v1`
- `sales_forecast_v2`
- `product_recommendations_v1`

### Guidelines
- Use semantic versioning: `v1`, `v2`, `v3`
- Major version changes indicate breaking changes
- Keep product names business-friendly
- Document version changes in product metadata

## File and Dataset Naming

### Pattern
```
{tier}_{domain}_{entity}_{date}_{partition}.{format}
```

### Examples
- `raw_sales_orders_20250103_part001.parquet`
- `cleaned_customer_profiles_20250103.csv`
- `analytics_daily_revenue_20250103.json`

### Guidelines
- Use ISO 8601 date format: `YYYYMMDD`
- Include partition number for split files
- Use consistent file extensions: `.parquet`, `.csv`, `.json`, `.avro`

## ETL/Pipeline Naming

### Pattern
```
{source}_{to}_{target}_{frequency}
```

### Examples
- `salesforce_to_raw_daily`
- `raw_to_cleaned_customer_hourly`
- `analytics_to_products_segments_weekly`

### Guidelines
- Indicate data flow direction with `_to_`
- Include refresh frequency: `realtime`, `hourly`, `daily`, `weekly`, `monthly`
- Use descriptive source and target names

## Metric and KPI Naming

### Pattern
```
{measure}_{aggregation}_{timeframe}_{filter}
```

### Examples
- `revenue_total_daily`
- `customers_count_active_monthly`
- `orders_avg_value_weekly`
- `conversion_rate_new_users_daily`

### Guidelines
- Start with the business measure: `revenue`, `customers`, `orders`
- Include aggregation: `total`, `count`, `avg`, `median`, `sum`
- Specify timeframe: `daily`, `weekly`, `monthly`, `quarterly`, `yearly`
- Add filters if applicable: `active`, `new`, `churned`

## Column Metadata Tags

Use consistent suffixes in column descriptions for automatic tooling:

- `(PII)`: Personally Identifiable Information
- `(PCI)`: Payment Card Industry data
- `(PHI)`: Protected Health Information
- `(SK)`: Surrogate Key
- `(NK)`: Natural Key
- `(SCD2)`: Slowly Changing Dimension Type 2

Example:
```sql
COMMENT ON COLUMN customers.email_address IS 'Customer email address (PII)';
COMMENT ON COLUMN customers.customer_key IS 'Surrogate key for customer dimension (SK)';
```

## Naming Anti-Patterns

### Avoid These Practices

❌ **Hungarian Notation**
```
str_customer_name  -- Don't prefix with data type
int_order_count
```

✅ **Better**
```
customer_name
order_count
```

❌ **Excessive Abbreviation**
```
cust_fst_nm
ord_dt
prod_ctg
```

✅ **Better**
```
customer_first_name
order_date
product_category
```

❌ **Ambiguous Names**
```
data
info
value
temp
```

✅ **Better**
```
customer_data
order_info  -- Or better: specific column names
order_amount
customer_import_staging
```

❌ **Mixed Case or CamelCase**
```
CustomerName
OrderDate
productCategory
```

✅ **Better**
```
customer_name
order_date
product_category
```

## Reserved Word Handling

If you must use a reserved word, use suffix/prefix:
- `user` → `user_account` or `app_user`
- `order` → `customer_order` or `order_record`
- `group` → `user_group` or `customer_group`

## Naming Checklist

Before finalizing any name, verify:
- [ ] Follows snake_case convention
- [ ] Uses full words (no unclear abbreviations)
- [ ] Matches the pattern for its object type
- [ ] Is not a reserved keyword
- [ ] Is unique within its scope
- [ ] Follows domain-specific conventions
- [ ] Is under maximum length (63 characters)
- [ ] Will be understandable to new team members

## Governance

### Review Process
- All naming standards updates require Data Governance Council approval
- New patterns should be documented before implementation
- Legacy naming patterns should be migrated during major refactors

### Tooling
- Use automated linters to enforce naming conventions
- Implement naming validation in CI/CD pipelines
- Maintain a data dictionary with approved terms

## References
- See [Catalog Taxonomy Guide](catalog_taxonomy.md) for classification standards
- See [Data Products Handbook](data_products_handbook.md) for product naming guidelines
