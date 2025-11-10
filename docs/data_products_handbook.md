# Data Products Handbook

## Overview
This handbook provides comprehensive guidance for data product owners in the DecisionOS platform, covering the complete product lifecycle from conception to retirement, including SLA management, versioning, and rollback policies.

## What is a Data Product?

### Definition
A **Data Product** is a self-contained, reusable data asset that:
- Solves a specific business problem
- Has a defined owner and consumers
- Provides guaranteed service levels (SLA)
- Is versioned and governed
- Includes documentation and support
- Has clear access controls and interfaces

### Data Product vs Dataset
| Aspect | Data Product | Dataset |
|--------|--------------|---------|
| **Ownership** | Dedicated product owner | Data engineer/analyst |
| **SLA** | Formally defined and monitored | Best effort |
| **Documentation** | Comprehensive, consumer-focused | Technical, often minimal |
| **Interface** | Stable API/contract | Direct table access |
| **Versioning** | Semantic versioning, backward compatibility | Ad-hoc or none |
| **Support** | Defined support process | Informal |
| **Discovery** | Published in catalog with metadata | May or may not be cataloged |

## Product Owner Responsibilities

### Core Responsibilities
1. **Product Vision & Strategy**
   - Define product purpose and value proposition
   - Identify target consumers and use cases
   - Maintain product roadmap

2. **Quality Management**
   - Define and monitor data quality metrics
   - Ensure SLA compliance
   - Address quality issues promptly

3. **Consumer Support**
   - Respond to consumer questions and issues
   - Gather feedback and feature requests
   - Communicate changes and updates

4. **Lifecycle Management**
   - Plan and execute version releases
   - Manage deprecation and retirement
   - Coordinate with dependent teams

5. **Documentation**
   - Maintain comprehensive product documentation
   - Provide usage examples and tutorials
   - Document schema changes and migrations

6. **Governance & Compliance**
   - Ensure data privacy and security
   - Manage access controls
   - Maintain audit trails

## Product Lifecycle

### 1. Concept Phase

#### Activities
- Identify business need and opportunity
- Validate with potential consumers
- Define initial requirements
- Assess feasibility and resources

#### Deliverables
- Product proposal document
- Business case and ROI estimate
- Initial consumer interviews
- Resource requirements

#### Decision Gate
- Approval from Data Governance Council
- Resource allocation confirmed
- Product owner assigned

### 2. Development Phase

#### Activities
- Design data model and transformations
- Implement data pipelines
- Build quality checks and monitoring
- Create documentation
- Develop access interfaces (APIs, views)

#### Deliverables
- Data pipeline code
- Data quality framework
- Technical documentation
- Consumer documentation
- Test results

#### Best Practices
```yaml
development_standards:
  code_quality:
    - version_control: git
    - code_review: required
    - testing_coverage: ">80%"
    - documentation: inline_and_external

  data_quality:
    - completeness_checks: required
    - accuracy_validation: required
    - consistency_rules: defined
    - timeliness_monitoring: enabled

  security:
    - pii_identification: automated
    - access_controls: role_based
    - encryption: at_rest_and_transit
    - audit_logging: enabled
```

#### Decision Gate
- Quality metrics meet targets
- Documentation complete
- Security review passed
- Consumer acceptance testing complete

### 3. Launch Phase

#### Pre-Launch Checklist
- [ ] SLA defined and documented
- [ ] Monitoring and alerts configured
- [ ] Documentation published to catalog
- [ ] Consumer onboarding materials ready
- [ ] Support process defined
- [ ] Rollback plan documented
- [ ] Stakeholder communication sent
- [ ] Training materials available (if needed)

#### Launch Activities
1. **Soft Launch** (Optional)
   - Limited release to pilot consumers
   - Gather feedback and iterate
   - Duration: 2-4 weeks

2. **General Availability**
   - Announce to all potential consumers
   - Enable self-service access
   - Activate SLA monitoring

#### Communication Template
```markdown
Subject: [New Data Product] {Product Name} Now Available

Dear Data Community,

We are pleased to announce the availability of {Product Name}, a new data product designed to {primary value proposition}.

**What it is:**
{Brief description}

**Who should use it:**
{Target consumers and use cases}

**How to access:**
{Access instructions and authentication}

**SLA:**
{Availability, freshness, and quality commitments}

**Documentation:**
{Links to catalog entry, user guide, API docs}

**Support:**
{How to get help}

For questions, contact {owner_email} or {slack_channel}.
```

### 4. Operation Phase

#### Ongoing Activities
- Monitor SLA compliance
- Respond to consumer support requests
- Review usage patterns and feedback
- Plan enhancements and optimizations
- Maintain documentation

#### Health Metrics Dashboard
```yaml
product_health_metrics:
  availability:
    - uptime_percentage
    - incident_count
    - mean_time_to_recovery

  performance:
    - data_freshness
    - query_latency_p95
    - pipeline_execution_time

  quality:
    - quality_score
    - data_quality_incidents
    - schema_validation_failures

  adoption:
    - active_consumer_count
    - daily_query_volume
    - unique_users_per_week

  satisfaction:
    - net_promoter_score
    - support_ticket_volume
    - feedback_rating
```

#### Monthly Review Template
```markdown
# {Product Name} Monthly Review - {Month Year}

## Executive Summary
{1-2 sentence summary of product health}

## SLA Compliance
- Availability: {actual}% (Target: {target}%)
- Freshness: {actual} (Target: {target})
- Quality: {actual}% (Target: {target}%)

## Usage Statistics
- Active Consumers: {count}
- Total Queries: {count}
- Growth vs Last Month: {percentage}

## Issues & Incidents
- P1 Incidents: {count}
- P2 Incidents: {count}
- Average Resolution Time: {hours}

## Consumer Feedback
{Summary of key feedback themes}

## Upcoming Changes
{Planned enhancements or changes}

## Action Items
- [ ] {Action item 1}
- [ ] {Action item 2}
```

### 5. Evolution Phase

#### Version Planning
Use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible API/schema changes)
- **MINOR**: Backward-compatible new features
- **PATCH**: Backward-compatible bug fixes

#### Change Types and Versioning
| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Add optional column | MINOR | 1.2.0 → 1.3.0 |
| Remove column | MAJOR | 1.3.0 → 2.0.0 |
| Rename column | MAJOR | 1.3.0 → 2.0.0 |
| Change data type | MAJOR | 1.3.0 → 2.0.0 |
| Change calculation logic | MAJOR | 1.3.0 → 2.0.0 |
| Add new table/endpoint | MINOR | 1.3.0 → 1.4.0 |
| Fix data quality bug | PATCH | 1.3.0 → 1.3.1 |
| Performance improvement | PATCH | 1.3.1 → 1.3.2 |

#### Breaking Change Process
1. **Announcement** (T-90 days)
   - Notify all consumers of planned change
   - Provide migration guide
   - Offer office hours for questions

2. **Parallel Run** (T-60 to T-0 days)
   - Deploy new version alongside old
   - Consumers can test and migrate
   - Monitor adoption rate

3. **Deprecation** (T-0)
   - Old version marked deprecated
   - Warning messages for users
   - Support for migration continues

4. **Retirement** (T+90 days)
   - Old version disabled
   - Final migration support
   - Post-mortem and lessons learned

#### Migration Communication Template
```markdown
Subject: [Breaking Change] {Product Name} v{X}.0 Coming {Date}

Dear {Product Name} Users,

We will be releasing v{X}.0 of {Product Name} on {Date}, which includes breaking changes.

**What's Changing:**
{Detailed list of breaking changes}

**Why:**
{Business justification}

**Impact:**
{Who is affected and how}

**Migration Guide:**
{Step-by-step instructions or link}

**Timeline:**
- {Date-90d}: This announcement
- {Date-60d}: v{X}.0 available for testing in parallel
- {Date}: v{X}.0 becomes default version
- {Date+90d}: v{X-1}.0 retired

**Support:**
- Migration guide: {link}
- Office hours: {dates/times}
- Slack channel: {channel}
- Contact: {owner_email}

Please plan your migration accordingly. We're here to help!
```

### 6. Retirement Phase

#### Retirement Criteria
- Low/no usage (<5 queries per week for 3 months)
- Superseded by better alternative
- Source system decommissioned
- Business need no longer exists
- Unsustainable maintenance burden

#### Retirement Process
1. **Assessment** (T-180 days)
   - Review usage and dependencies
   - Identify active consumers
   - Evaluate alternatives

2. **Decision** (T-150 days)
   - Seek Data Governance approval
   - Create retirement plan
   - Identify replacement product (if any)

3. **Announcement** (T-120 days)
   - Notify all consumers
   - Provide migration path
   - Offer support for transition

4. **Read-Only Mode** (T-60 days)
   - Stop pipeline updates
   - Maintain access for historical queries
   - Display retirement warnings

5. **Archival** (T-0)
   - Disable access
   - Archive data according to retention policy
   - Update catalog status to "Retired"

6. **Decommission** (T+30 days)
   - Delete infrastructure
   - Archive documentation
   - Conduct retrospective

#### Retirement Communication Template
```markdown
Subject: [Retirement Notice] {Product Name} to be Retired on {Date}

Dear {Product Name} Users,

We will be retiring {Product Name} on {Date} due to {reason}.

**Why:**
{Detailed justification}

**Alternative:**
{Replacement product or solution}

**Timeline:**
- {Date-120d}: This announcement
- {Date-60d}: Pipeline stops, read-only access continues
- {Date}: Product fully retired, access disabled
- {Date+retention}: Data permanently deleted

**What You Need to Do:**
{Action items for consumers}

**Migration Support:**
{Available resources and contacts}

For questions, please contact {owner_email}.
```

## Service Level Agreements (SLAs)

### SLA Components

#### 1. Availability SLA
**Definition**: Percentage of time the data product is accessible

**Standard Tiers**:
- **Platinum**: 99.9% uptime (≤ 43 minutes downtime/month)
- **Gold**: 99.5% uptime (≤ 3.6 hours downtime/month)
- **Silver**: 99% uptime (≤ 7.2 hours downtime/month)
- **Bronze**: 95% uptime (≤ 36 hours downtime/month)

**Measurement**:
```sql
SELECT
    DATE_TRUNC('month', check_time) AS month,
    product_id,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) AS successful_checks,
    (SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END)::FLOAT / COUNT(*)) * 100 AS availability_percent
FROM product_health_checks
WHERE check_time >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY 1, 2;
```

#### 2. Freshness SLA
**Definition**: Maximum age of data in the product

**Standard Tiers**:
- **Real-time**: < 5 minutes
- **Near real-time**: < 15 minutes
- **Hourly**: Data updated every hour
- **Daily**: Data updated every day by {time}
- **Weekly**: Data updated every {day} by {time}

**Measurement**:
```sql
SELECT
    product_id,
    MAX(last_updated_at) AS most_recent_update,
    CURRENT_TIMESTAMP - MAX(last_updated_at) AS data_age,
    CASE
        WHEN CURRENT_TIMESTAMP - MAX(last_updated_at) <= freshness_sla_interval
        THEN 'Compliant'
        ELSE 'Breach'
    END AS sla_status
FROM product_metadata
GROUP BY product_id;
```

#### 3. Quality SLA
**Definition**: Minimum acceptable data quality score

**Quality Dimensions**:
```yaml
quality_metrics:
  completeness:
    weight: 0.3
    calculation: (non_null_rows / total_rows) * 100
    threshold: ">95%"

  accuracy:
    weight: 0.3
    calculation: (valid_rows / total_rows) * 100
    threshold: ">98%"

  consistency:
    weight: 0.2
    calculation: (consistent_rows / total_rows) * 100
    threshold: ">99%"

  timeliness:
    weight: 0.2
    calculation: freshness_compliance_rate
    threshold: ">99%"

overall_quality_score:
  formula: weighted_average(quality_metrics)
  minimum_acceptable: 95
```

**Standard Tiers**:
- **Platinum**: Quality Score ≥ 99%
- **Gold**: Quality Score ≥ 97%
- **Silver**: Quality Score ≥ 95%
- **Bronze**: Quality Score ≥ 90%

#### 4. Performance SLA
**Definition**: Maximum query response time

**Standard Tiers**:
- **Platinum**: p95 < 1 second
- **Gold**: p95 < 3 seconds
- **Silver**: p95 < 10 seconds
- **Bronze**: p95 < 30 seconds

#### 5. Support SLA
**Definition**: Response time for support requests

**Standard Tiers**:
| Priority | First Response | Resolution Target |
|----------|----------------|-------------------|
| P1 - Critical | 1 hour | 4 hours |
| P2 - High | 4 hours | 1 business day |
| P3 - Medium | 1 business day | 3 business days |
| P4 - Low | 3 business days | Best effort |

### SLA Documentation Template

```yaml
product: customer_segmentation_v2
owner: customer_analytics_team

sla:
  availability:
    target: 99.5%
    tier: gold
    measurement_interval: monthly
    exclusions:
      - planned_maintenance_windows
      - upstream_data_source_outages

  freshness:
    target: daily_by_8am_utc
    tier: daily
    measurement: max_data_timestamp
    alert_threshold: 2_hours_late

  quality:
    overall_target: 97%
    tier: gold
    dimensions:
      completeness:
        target: 98%
        critical_columns:
          - customer_id
          - segment_name
          - segment_score
      accuracy:
        target: 99%
        validation_rules:
          - segment_score_range_0_to_100
          - valid_segment_names
      consistency:
        target: 99%
        checks:
          - segment_totals_match_customer_count
          - no_duplicate_customers

  performance:
    target: p95_3_seconds
    tier: gold
    measurement: query_latency_seconds
    test_queries:
      - "SELECT * FROM customer_segments WHERE segment = 'high_value'"

  support:
    p1_response: 1_hour
    p1_resolution: 4_hours
    p2_response: 4_hours
    p2_resolution: 1_business_day
    contact: customer-analytics@company.com
    escalation: data-platform-lead@company.com

exceptions:
  - Upstream source system outages (carry-forward last good data)
  - Planned maintenance (notified 7 days in advance)
  - Force majeure events
```

### SLA Monitoring and Alerting

```yaml
monitoring:
  availability:
    check_frequency: 5_minutes
    alert_on_failure: true
    alert_channels:
      - pagerduty
      - slack_channel: #data-products-alerts

  freshness:
    check_frequency: 1_hour
    alert_conditions:
      warning: data_age > (sla_target * 0.8)
      critical: data_age > sla_target
    alert_channels:
      - slack_channel: #data-products-alerts
      - email: product_owner

  quality:
    check_frequency: after_each_pipeline_run
    alert_conditions:
      warning: quality_score < (target * 0.95)
      critical: quality_score < target
    alert_channels:
      - slack_channel: #data-quality
      - email: product_owner

  performance:
    check_frequency: continuous
    sample_rate: 10%
    alert_conditions:
      warning: p95_latency > (target * 1.2)
      critical: p95_latency > (target * 1.5)
```

### SLA Breach Response

#### Incident Response Process
1. **Detection**: Automated alert triggers
2. **Assessment**: Owner evaluates severity
3. **Communication**: Notify affected consumers
4. **Mitigation**: Implement fix or workaround
5. **Resolution**: Service restored to SLA
6. **Post-Mortem**: Root cause analysis

#### Incident Communication Template
```markdown
Subject: [Incident] {Product Name} SLA Breach - {SLA Type}

**Status:** {Investigating | Identified | Monitoring | Resolved}

**Summary:**
{Product Name} is experiencing {issue description}.

**Impact:**
- Affected SLA: {SLA type}
- Target: {SLA target}
- Current: {current value}
- Consumer Impact: {description}

**Timeline:**
- {Time}: Issue detected
- {Time}: Root cause identified
- {Time}: Fix deployed
- {Time}: Service restored (if resolved)

**Next Steps:**
{What we're doing to resolve}

**Workaround:**
{If available}

We will update this thread every {frequency} until resolved.
```

## Versioning Policy

### Version Lifecycle

#### Version States
1. **Alpha**: Internal testing, unstable, no SLA
2. **Beta**: External testing, limited consumers, reduced SLA
3. **General Availability (GA)**: Production-ready, full SLA
4. **Deprecated**: Marked for retirement, full SLA maintained
5. **Retired**: No longer available

### Version Support Policy

```yaml
version_support:
  current_major_version:
    support_level: full_support
    sla: full_sla
    duration: until_next_major_version + 1_year

  previous_major_version:
    support_level: security_fixes_only
    sla: reduced_sla
    duration: 1_year_after_deprecation

  older_versions:
    support_level: none
    duration: 0
```

### Backward Compatibility Guidelines

#### Safe Changes (No Version Bump Required)
- Add new optional columns at end of schema
- Add new optional parameters to APIs
- Add new endpoints/tables
- Improve performance
- Fix bugs without changing behavior
- Add additional indexes

#### Compatible Changes (Minor Version)
- Add new required columns with defaults
- Add new tables/views
- Expand enum values
- Relax validation rules
- Add new metrics or calculations (additive)

#### Breaking Changes (Major Version)
- Remove columns or tables
- Rename columns or tables
- Change data types
- Change calculation logic
- Restrict validation rules
- Change sort order or grouping
- Modify primary keys

### Rollback Policy

#### Rollback Scenarios
1. **Data Quality Issue**: Quality score below threshold
2. **Performance Degradation**: Latency exceeds SLA
3. **Consumer-Blocking Bug**: Critical functionality broken
4. **Incorrect Logic**: Calculations producing wrong results

#### Rollback Decision Matrix
| Severity | Impact | Decision |
|----------|--------|----------|
| P1 | > 50% consumers affected | Immediate rollback |
| P1 | < 50% consumers affected | Hotfix if possible, else rollback |
| P2 | > 75% consumers affected | Rollback |
| P2 | < 75% consumers affected | Hotfix in 24 hours |
| P3 | Any | Hotfix in next release |

#### Rollback Process
1. **Decision**: Product owner makes call (15 min SLA)
2. **Notification**: Alert all consumers immediately
3. **Execution**: Automated rollback to previous version
4. **Verification**: Confirm service restored
5. **Analysis**: Root cause investigation
6. **Fix**: Address underlying issue
7. **Re-release**: Deploy fix with additional testing

#### Rollback Automation
```yaml
rollback:
  enabled: true
  trigger_conditions:
    - quality_score < critical_threshold
    - error_rate > 5%
    - data_freshness > (sla * 2)

  automated_rollback:
    max_versions_back: 1
    verification_tests: required
    notification: automatic

  manual_rollback:
    approval_required: false  # Product owner can self-authorize
    command: "rollback_product --product {id} --version {version}"
```

## Best Practices

### Product Design
- Start with clear problem definition and consumer needs
- Design for self-service consumption
- Implement idempotent pipelines
- Build in observability from day one
- Plan for scale from the beginning

### Documentation
- Write for your audience (consumers, not just engineers)
- Include quick start guide and common use cases
- Provide code examples in multiple languages
- Keep FAQ updated based on support questions
- Version documentation alongside code

### Communication
- Over-communicate changes, especially breaking ones
- Maintain regular office hours for complex products
- Build community around popular products
- Celebrate consumer successes and use cases
- Be responsive to feedback

### Quality
- Implement automated quality checks at every stage
- Monitor quality metrics in real-time
- Set up alerts for quality degradation
- Conduct regular data quality audits
- Have rollback plan for quality issues

### Performance
- Optimize for common query patterns
- Implement caching where appropriate
- Monitor and alert on performance degradation
- Load test before major releases
- Provide performance tuning guidance to consumers

## Tools and Resources

### Product Management Tools
```yaml
tools:
  catalog:
    - DataHub
    - Amundsen
    - Alation

  monitoring:
    - Datadog
    - Grafana
    - Monte Carlo

  quality:
    - Great Expectations
    - Soda
    - dbt tests

  documentation:
    - Confluence
    - Notion
    - GitBook

  versioning:
    - Git
    - dbt
    - Semantic versioning tools
```

### Templates and Checklists
- Product proposal template
- SLA definition template
- Launch checklist
- Monthly review template
- Incident response playbook
- Retirement plan template

## Governance and Compliance

### Data Governance Council
- Reviews new product proposals
- Approves major version changes
- Authorizes product retirements
- Resolves inter-product conflicts
- Sets platform-wide standards

### Compliance Requirements
```yaml
compliance_by_sensitivity:
  restricted:
    - data_classification: required
    - encryption_at_rest: required
    - encryption_in_transit: required
    - access_audit_logging: required
    - annual_access_review: required
    - data_masking: default_for_non_owners

  confidential:
    - data_classification: required
    - access_audit_logging: required
    - annual_access_review: required

  internal:
    - data_classification: required
    - access_control: rbac

  public:
    - data_classification: required
```

## Metrics and KPIs

### Product Health Metrics
```yaml
metrics:
  adoption:
    - unique_consumers_monthly
    - total_queries_monthly
    - consumer_growth_rate

  engagement:
    - queries_per_active_consumer
    - days_since_last_use_distribution
    - feature_usage_breakdown

  reliability:
    - sla_compliance_rate
    - mttr_mean_time_to_recovery
    - incident_count_by_severity

  satisfaction:
    - net_promoter_score
    - support_ticket_sentiment
    - consumer_retention_rate

  efficiency:
    - cost_per_query
    - cost_per_consumer
    - infrastructure_utilization
```

### Reporting Cadence
- **Daily**: SLA compliance, incidents
- **Weekly**: Usage trends, quality metrics
- **Monthly**: Comprehensive health report
- **Quarterly**: Product review and roadmap update
- **Annually**: Total cost of ownership, strategic assessment

## Appendix

### Glossary
- **Data Product**: See "What is a Data Product?"
- **SLA**: Service Level Agreement, a commitment to consumers
- **SLO**: Service Level Objective, internal target (often stricter than SLA)
- **SLI**: Service Level Indicator, measurable metric
- **Semantic Versioning**: Version numbering scheme (MAJOR.MINOR.PATCH)
- **Breaking Change**: Change that breaks existing consumer integrations

### Related Documentation
- [Catalog Taxonomy Guide](catalog_taxonomy.md)
- [Naming Convention Guide](naming_convention.md)
- [Search Relevance Tuning Guide](search_relevance.md)

### Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-03 | DecisionOS Team | Initial version |
