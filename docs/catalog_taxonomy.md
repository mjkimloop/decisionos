# Catalog Taxonomy Guide

## Overview
This document defines the taxonomy structure for organizing data assets in the DecisionOS data catalog, including domain classification, tier levels, and sensitivity classifications.

## Domain Classification

### Primary Domains
Data assets are organized into the following primary domains:

1. **Customer Domain**
   - Customer profiles and attributes
   - Customer behavior and interactions
   - Customer segmentation data

2. **Product Domain**
   - Product catalog and specifications
   - Product pricing and inventory
   - Product performance metrics

3. **Sales Domain**
   - Sales transactions and orders
   - Sales performance metrics
   - Sales pipeline data

4. **Marketing Domain**
   - Campaign data and performance
   - Marketing attribution
   - Lead generation and tracking

5. **Operations Domain**
   - Supply chain data
   - Logistics and fulfillment
   - Operational metrics

6. **Finance Domain**
   - Financial transactions
   - Accounting data
   - Revenue and cost metrics

7. **Analytics Domain**
   - Derived metrics and KPIs
   - Analytical models and features
   - Aggregated insights

## Tier Classification

### Tier 0: Raw Data
- **Description**: Unprocessed source data ingested from operational systems
- **Characteristics**:
  - Direct replicas of source systems
  - Minimal to no transformation
  - Historical archive capability
- **Examples**: Database dumps, API extracts, log files

### Tier 1: Cleaned Data
- **Description**: Standardized and validated data with basic quality checks
- **Characteristics**:
  - Schema standardization
  - Data type validation
  - Deduplication applied
  - Basic quality metrics captured
- **Examples**: Cleaned customer records, validated transaction data

### Tier 2: Conformed Data
- **Description**: Integrated data following enterprise-wide standards
- **Characteristics**:
  - Cross-domain integration
  - Master data applied
  - Business rules implemented
  - Slowly Changing Dimensions (SCD) applied
- **Examples**: Customer 360 view, unified product catalog

### Tier 3: Analytics-Ready Data
- **Description**: Feature-engineered data optimized for analytical use cases
- **Characteristics**:
  - Domain-specific transformations
  - Calculated metrics and features
  - Aggregations and roll-ups
  - Performance-optimized schemas
- **Examples**: Customer segments, sales forecasts, recommendation features

### Tier 4: Data Products
- **Description**: Published, governed data products ready for consumption
- **Characteristics**:
  - Documented APIs and interfaces
  - SLA-backed availability
  - Version controlled
  - Access governance applied
- **Examples**: Customer Segment API, Sales Dashboard Dataset

## Sensitivity Classification

### Public
- **Access Level**: Unrestricted within organization
- **Description**: Non-sensitive data with no privacy or security concerns
- **Examples**: Product catalogs, public marketing content
- **Security Requirements**: Standard authentication

### Internal
- **Access Level**: General employee access
- **Description**: Standard business data not requiring special protection
- **Examples**: Aggregated sales metrics, operational dashboards
- **Security Requirements**: Role-based access control (RBAC)

### Confidential
- **Access Level**: Restricted to specific teams/roles
- **Description**: Sensitive business information requiring protection
- **Examples**: Customer contact information, pricing strategies
- **Security Requirements**:
  - Enhanced RBAC
  - Data masking for non-authorized users
  - Audit logging

### Restricted
- **Access Level**: Highly restricted, approval required
- **Description**: Highly sensitive data with regulatory or compliance requirements
- **Examples**: Payment card information (PCI), personally identifiable information (PII), health records (PHI)
- **Security Requirements**:
  - Strict access controls with approval workflow
  - Encryption at rest and in transit
  - Data masking and tokenization
  - Comprehensive audit trails
  - Compliance monitoring

## Tagging Guidelines

### Required Tags
All data assets must include the following tags:

- `domain`: Primary domain classification
- `tier`: Data tier (0-4)
- `sensitivity`: Sensitivity classification
- `owner`: Data owner (team or individual)
- `source_system`: Origin system or application

### Optional Tags
Additional tags to enhance discoverability and governance:

- `sub_domain`: Secondary domain classification
- `region`: Geographic region (if applicable)
- `update_frequency`: Data refresh frequency (real-time, daily, weekly, monthly)
- `retention_period`: Data retention policy
- `compliance`: Regulatory requirements (GDPR, CCPA, SOX, etc.)
- `quality_tier`: Data quality classification (gold, silver, bronze)
- `cost_center`: Business unit or cost center
- `project`: Associated project or initiative
- `use_case`: Primary use case or application

### Tag Naming Conventions
- Use lowercase with underscores for multi-word tags
- Use consistent controlled vocabularies
- Avoid abbreviations unless widely understood
- Keep tag values concise and meaningful

### Example Tag Set
```yaml
domain: customer
tier: 3
sensitivity: confidential
owner: customer_analytics_team
source_system: salesforce_crm
sub_domain: customer_behavior
region: north_america
update_frequency: daily
retention_period: 7_years
compliance: gdpr,ccpa
quality_tier: gold
use_case: customer_segmentation
```

## Cross-Domain Data Assets

Some data assets span multiple domains. In these cases:
1. Assign the primary domain based on the main business entity
2. Use the `sub_domain` tag to indicate secondary classification
3. Document cross-domain relationships in metadata

## Taxonomy Governance

### Taxonomy Updates
- Taxonomy changes require approval from the Data Governance Council
- New domains or tiers must be documented and communicated
- Quarterly review of taxonomy effectiveness

### Compliance
- All new data assets must be classified within 48 hours of creation
- Existing assets should be audited quarterly for correct classification
- Reclassification requests follow standard change management process

## References
- See [Naming Convention Guide](naming_convention.md) for asset naming standards
- See [Data Products Handbook](data_products_handbook.md) for Tier 4 product guidelines
