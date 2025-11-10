# Search Relevance Tuning Guide

## Overview
This guide provides comprehensive instructions for tuning search relevance in the DecisionOS data catalog, including ranking strategies, boosting techniques, evaluation methodologies, and test set generation.

## Search Architecture

### Search Components
1. **Query Parser**: Analyzes user search intent
2. **Retrieval Engine**: Fetches candidate results
3. **Ranking Model**: Scores and orders results
4. **Boosting Rules**: Applies business logic to adjust scores
5. **Result Formatter**: Prepares final output

### Searchable Fields
The following fields are indexed for search:

**Primary Fields** (High Weight):
- Asset name
- Asset title
- Business description

**Secondary Fields** (Medium Weight):
- Technical description
- Column names
- Column descriptions
- Owner information

**Tertiary Fields** (Low Weight):
- Tags
- Comments
- Lineage metadata
- Usage statistics

## Ranking Strategies

### Base Ranking Algorithm

#### TF-IDF Scoring
Default scoring based on term frequency-inverse document frequency:
```
score = tf * idf * field_boost
```

**Configuration**:
```yaml
scoring:
  algorithm: tfidf
  fields:
    asset_name:
      boost: 5.0
      analyzer: standard
    business_description:
      boost: 3.0
      analyzer: english
    technical_description:
      boost: 2.0
      analyzer: english
    column_names:
      boost: 2.5
      analyzer: standard
    tags:
      boost: 1.5
      analyzer: keyword
```

#### BM25 Scoring (Recommended)
Improved probabilistic ranking:
```
BM25(q,d) = Σ IDF(qi) * (f(qi,d) * (k1 + 1)) / (f(qi,d) + k1 * (1 - b + b * |d| / avgdl))
```

**Configuration**:
```yaml
scoring:
  algorithm: bm25
  parameters:
    k1: 1.2  # Term saturation parameter
    b: 0.75  # Length normalization parameter
  fields:
    asset_name:
      boost: 5.0
    business_description:
      boost: 3.0
    column_names:
      boost: 2.5
    tags:
      boost: 1.5
```

### Semantic Ranking (Advanced)

For semantic search using embeddings:

```yaml
scoring:
  algorithm: vector_similarity
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  similarity_metric: cosine
  hybrid_mode:
    enabled: true
    lexical_weight: 0.3
    semantic_weight: 0.7
```

## Boosting Strategies

### Query-Independent Boosting

Boost documents based on inherent properties:

#### Usage-Based Boosting
```yaml
boosting:
  usage_score:
    enabled: true
    weight: 0.2
    calculation: log(1 + query_count_30d)
    max_boost: 2.0
```

#### Quality-Based Boosting
```yaml
boosting:
  quality_score:
    enabled: true
    weight: 0.15
    factors:
      documentation_completeness: 0.4
      schema_documentation: 0.3
      column_description_ratio: 0.3
    max_boost: 1.5
```

#### Freshness Boosting
```yaml
boosting:
  freshness:
    enabled: true
    weight: 0.1
    decay_function: exponential
    scale: 30d  # Half-life of 30 days
    offset: 7d
    decay_rate: 0.5
```

#### Tier-Based Boosting
```yaml
boosting:
  tier_boost:
    products: 2.0    # Tier 4
    analytics: 1.5   # Tier 3
    conformed: 1.2   # Tier 2
    cleaned: 1.0     # Tier 1
    raw: 0.8         # Tier 0
```

### Query-Dependent Boosting

Adjust scores based on query context:

#### Exact Match Boosting
```yaml
boosting:
  exact_match:
    asset_name: 3.0
    column_name: 2.0
    tag: 1.5
```

#### Prefix Match Boosting
```yaml
boosting:
  prefix_match:
    enabled: true
    boost: 1.5
    min_prefix_length: 3
```

#### Domain Match Boosting
```yaml
boosting:
  domain_context:
    enabled: true
    user_domain_boost: 1.3
    team_domain_boost: 1.2
```

### Function Score Query Example

Elasticsearch/OpenSearch function score implementation:

```json
{
  "query": {
    "function_score": {
      "query": {
        "multi_match": {
          "query": "customer orders",
          "fields": [
            "asset_name^5",
            "business_description^3",
            "column_names^2.5"
          ]
        }
      },
      "functions": [
        {
          "filter": { "match": { "tier": "products" }},
          "weight": 2.0
        },
        {
          "field_value_factor": {
            "field": "query_count_30d",
            "modifier": "log1p",
            "factor": 0.1,
            "missing": 1
          }
        },
        {
          "gauss": {
            "updated_at": {
              "scale": "30d",
              "offset": "7d",
              "decay": 0.5
            }
          }
        }
      ],
      "score_mode": "sum",
      "boost_mode": "multiply"
    }
  }
}
```

## Query Processing

### Query Expansion

#### Synonym Expansion
```yaml
synonyms:
  - "customer, client, consumer, user"
  - "order, purchase, transaction, sale"
  - "product, item, sku, article"
  - "revenue, sales, income"
  - "daily, day, per day"
```

#### Stemming and Lemmatization
```yaml
analyzers:
  english_analyzer:
    tokenizer: standard
    filters:
      - lowercase
      - stop_words_english
      - snowball_stemmer
```

### Filtering and Faceting

Pre-filter results before ranking:

```yaml
filters:
  default:
    - exclude_deprecated: true
    - exclude_archived: true

facets:
  - domain
  - tier
  - sensitivity
  - owner
  - source_system
  - update_frequency
```

## Evaluation Methodology

### Key Metrics

#### Precision at K (P@K)
Measures relevance of top K results:
```
P@K = (Relevant items in top K) / K
```

**Target**: P@10 ≥ 0.8

#### Mean Reciprocal Rank (MRR)
Measures rank of first relevant result:
```
MRR = (1/|Q|) * Σ(1/rank_i)
```

**Target**: MRR ≥ 0.85

#### Normalized Discounted Cumulative Gain (NDCG)
Weighted metric accounting for position:
```
NDCG@K = DCG@K / IDCG@K
DCG@K = Σ (2^rel_i - 1) / log2(i + 1)
```

**Target**: NDCG@10 ≥ 0.85

#### Mean Average Precision (MAP)
Average precision across all queries:
```
MAP = (1/|Q|) * Σ AP(q)
```

**Target**: MAP ≥ 0.80

### Evaluation Process

#### 1. Test Set Preparation
See [Test Set Generation](#test-set-generation) section below.

#### 2. Baseline Measurement
```bash
# Run baseline evaluation
python evaluate_search.py \
  --test-set data/search_test_set.json \
  --config config/search_baseline.yaml \
  --output results/baseline_metrics.json
```

#### 3. A/B Testing
```yaml
ab_test:
  variant_a:
    name: baseline
    config: config/search_baseline.yaml
    traffic: 50%

  variant_b:
    name: boosted_products
    config: config/search_tier_boost.yaml
    traffic: 50%

  duration: 7d
  metrics:
    - click_through_rate
    - time_to_first_click
    - result_engagement
    - user_satisfaction_score
```

#### 4. Offline Evaluation
```python
# Example evaluation script
from search_evaluator import SearchEvaluator

evaluator = SearchEvaluator(test_set='search_test_set.json')

results = evaluator.evaluate(
    search_config='config/search_optimized.yaml',
    metrics=['precision@10', 'mrr', 'ndcg@10', 'map']
)

print(f"Precision@10: {results['precision@10']:.3f}")
print(f"MRR: {results['mrr']:.3f}")
print(f"NDCG@10: {results['ndcg@10']:.3f}")
print(f"MAP: {results['map']:.3f}")
```

## Test Set Generation

### Manual Curation Method

#### Step 1: Identify Query Categories
```yaml
query_categories:
  - navigational: "User knows specific asset name"
  - informational: "User exploring domain/topic"
  - transactional: "User needs specific data for task"
```

#### Step 2: Collect Representative Queries

Sample 50-100 queries covering:
- Common search patterns (60%)
- Edge cases (20%)
- Domain-specific terminology (20%)

```json
{
  "query_id": "Q001",
  "query": "customer lifetime value",
  "category": "informational",
  "user_intent": "Find datasets related to CLV metrics",
  "relevant_results": [
    {
      "asset_id": "analytics.customers.clv_segments",
      "relevance": 3,
      "reason": "Primary CLV segmentation table"
    },
    {
      "asset_id": "products.customer_analytics.lifetime_value",
      "relevance": 3,
      "reason": "Production LTV data product"
    },
    {
      "asset_id": "analytics.marketing.customer_value_score",
      "relevance": 2,
      "reason": "Related customer scoring table"
    }
  ]
}
```

#### Step 3: Relevance Labeling

Use 4-point scale:
- **3**: Highly Relevant - Exactly what user needs
- **2**: Relevant - Useful for user's task
- **1**: Partially Relevant - Tangentially related
- **0**: Not Relevant - Does not match intent

#### Step 4: Inter-Rater Reliability

Have 2-3 raters label same queries:
```python
from sklearn.metrics import cohen_kappa_score

# Calculate agreement
kappa = cohen_kappa_score(rater1_labels, rater2_labels)
print(f"Inter-rater agreement (Kappa): {kappa:.3f}")
# Target: Kappa > 0.7
```

### Query Log Mining Method

#### Step 1: Extract Search Logs
```sql
SELECT
    query_text,
    COUNT(*) as query_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(click_position) as avg_click_position,
    COUNT(CASE WHEN clicked = true THEN 1 END) as click_count
FROM search_logs
WHERE query_date >= CURRENT_DATE - INTERVAL '90 days'
    AND query_text IS NOT NULL
    AND LENGTH(query_text) >= 3
GROUP BY query_text
HAVING COUNT(*) >= 5
ORDER BY query_count DESC
LIMIT 1000;
```

#### Step 2: Click-Through Analysis
```python
# Identify successful searches (clicked within top 5)
successful_queries = df[
    (df['click_count'] > 0) &
    (df['avg_click_position'] <= 5)
]

# Identify failed searches (no clicks or low position clicks)
failed_queries = df[
    (df['click_count'] == 0) |
    (df['avg_click_position'] > 10)
]
```

#### Step 3: Implicit Relevance Signals
```yaml
relevance_signals:
  strong_positive:
    - click_position <= 3
    - time_on_asset >= 30s
    - asset_downloaded: true
    - query_refinement: false

  weak_positive:
    - click_position <= 10
    - time_on_asset >= 10s

  negative:
    - immediate_back_button
    - query_refinement: true
    - no_clicks
```

#### Step 4: Generate Test Set
```python
import json

test_set = []

for idx, row in successful_queries.head(100).iterrows():
    query_id = f"Q{idx:03d}"

    # Get clicked assets for this query
    clicked_assets = get_clicked_assets(row['query_text'])

    relevant_results = [
        {
            "asset_id": asset['id'],
            "relevance": calculate_relevance_score(asset),
            "reason": "User clicked and engaged with asset"
        }
        for asset in clicked_assets
    ]

    test_set.append({
        "query_id": query_id,
        "query": row['query_text'],
        "category": classify_query(row['query_text']),
        "relevant_results": relevant_results
    })

with open('search_test_set.json', 'w') as f:
    json.dump(test_set, f, indent=2)
```

### Synthetic Query Generation

For cold-start scenarios:

```python
# Generate queries from asset metadata
def generate_queries_from_assets(assets):
    queries = []

    for asset in assets:
        # Entity name queries
        queries.append({
            "query": asset['name'],
            "expected_result": asset['id'],
            "relevance": 3
        })

        # Business term queries
        for term in extract_key_terms(asset['description']):
            queries.append({
                "query": term,
                "expected_result": asset['id'],
                "relevance": 2
            })

        # Tag-based queries
        for tag in asset['tags']:
            queries.append({
                "query": tag,
                "expected_result": asset['id'],
                "relevance": 2
            })

    return queries
```

### Test Set Maintenance

```yaml
maintenance_schedule:
  review_frequency: quarterly
  update_triggers:
    - new_domain_added
    - major_catalog_changes
    - search_performance_degradation

versioning:
  format: "test_set_v{YYYY}_{Q}{quarter}.json"
  retention: 2_years
  changelog_required: true
```

## Continuous Improvement

### Monitoring Dashboard

Track these metrics in real-time:
```yaml
monitoring:
  search_metrics:
    - queries_per_day
    - avg_results_count
    - zero_results_rate
    - avg_click_position
    - click_through_rate

  performance_metrics:
    - p50_latency
    - p95_latency
    - p99_latency
    - error_rate

  quality_metrics:
    - user_satisfaction_score
    - query_reformulation_rate
    - result_engagement_rate
```

### Feedback Loop

```yaml
feedback_collection:
  explicit_feedback:
    - thumbs_up_down
    - relevance_rating
    - report_issue

  implicit_feedback:
    - click_position
    - dwell_time
    - asset_usage_post_search
    - query_refinement_pattern
```

### Tuning Workflow

1. **Analyze Metrics**: Review weekly search metrics
2. **Identify Issues**: Find queries with poor performance
3. **Hypothesis**: Propose boosting/ranking changes
4. **Test Offline**: Evaluate against test set
5. **A/B Test**: Run controlled experiment
6. **Measure Impact**: Compare metrics vs baseline
7. **Deploy or Rollback**: Make decision based on data
8. **Document**: Record changes and results

## Troubleshooting

### Common Issues

#### Low Precision
**Symptoms**: Many irrelevant results in top 10
**Solutions**:
- Increase field boosts for high-value fields
- Add filters to exclude low-quality assets
- Improve query parsing and stemming
- Add domain-specific synonyms

#### Low Recall
**Symptoms**: Relevant results not appearing
**Solutions**:
- Add synonym expansion
- Reduce stemming aggressiveness
- Lower minimum score threshold
- Index additional fields

#### Position Bias
**Symptoms**: Users only click top results
**Solutions**:
- Diversify top results
- Add recency boost
- Implement result shuffling for testing
- Use position-unbiased metrics

#### Cold Start
**Symptoms**: New assets don't appear
**Solutions**:
- Reduce usage-based boosting weight
- Add content-based boosting
- Manual quality curation for new assets

## Configuration Examples

### Conservative Configuration (High Precision)
```yaml
scoring:
  algorithm: bm25
  k1: 1.2
  b: 0.75

boosting:
  tier_boost:
    products: 3.0
    analytics: 2.0
  usage_weight: 0.3
  quality_weight: 0.3
  exact_match_boost: 5.0

filters:
  min_quality_score: 0.7
  exclude_deprecated: true
```

### Exploratory Configuration (High Recall)
```yaml
scoring:
  algorithm: bm25
  k1: 1.5
  b: 0.5

boosting:
  tier_boost:
    products: 1.5
    analytics: 1.3
  usage_weight: 0.1
  freshness_weight: 0.2
  diversity_factor: 0.3

query_expansion:
  synonyms: true
  fuzzy_matching: true
  min_similarity: 0.7
```

## References
- [Catalog Taxonomy Guide](catalog_taxonomy.md)
- [Naming Convention Guide](naming_convention.md)
- [Elasticsearch Relevance Tuning](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-relevance.html)
- Information Retrieval: Implementing and Evaluating Search Engines (Buttcher et al.)
