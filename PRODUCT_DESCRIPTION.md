# FinChat Analytics Product Description

## Product Overview

FinChat Analytics is an AI-powered customer retention analytics platform for banks, fintech companies, and financial service teams. It helps business users understand customer behavior, predict churn, estimate customer lifetime value, identify promotion opportunities, and explain the drivers behind customer risk and value.

The product combines:

- A dashboard for monitoring customer health, churn risk, lifetime value, and customer segments.
- A natural language analytics assistant that answers business questions using customer data, machine learning models, and SQL-backed metrics.
- Offline machine learning pipelines for feature engineering, model training, and model registry.
- Online inference services for churn, survival analysis, CLV, uplift modeling, and causal discovery.

## Target Users

FinChat Analytics is designed for:

- Retail banks that need earlier churn warning signals.
- Fintech startups that want customer value and retention analytics.
- CRM and growth teams that need prioritized customer outreach lists.
- Marketing teams that want better promotion targeting.
- Data and analytics teams that need reusable customer behavior models.

## What The Product Does

FinChat Analytics helps answer these business questions:

1. Which customers are most likely to churn?
2. When are risky customers likely to churn?
3. Which customers have the highest future value?
4. Which customers should receive retention offers or promotions?
5. Which customer segments are growing, declining, or becoming inactive?
6. What factors are driving churn, value, and campaign response?

The product turns raw customer and transaction data into actionable outputs: risk scores, customer segments, value rankings, campaign target lists, charts, and plain-language explanations.

## Core Features

### 1. Customer Behavior Dashboard

The dashboard gives a portfolio-level view of customer health and activity.

It shows:

- Total customers.
- Active customers.
- Churned customers.
- Churn rate.
- Average customer tenure.
- Segment distribution.
- Transaction volume.
- Transaction value.
- Recent activity trends.
- Customer activity by city, segment, channel, and promotion status.

### 2. Churn Prediction

The churn module predicts the probability that each customer will leave or become inactive.

It shows:

- Churn probability per customer.
- High-risk, medium-risk, and low-risk customer groups.
- Top customers to contact for retention.
- Churn rate by segment, age group, city, and tenure group.
- Model performance metrics such as AUC-ROC, PR-AUC, and Brier Score.
- Feature explanations for why a customer is considered risky.

### 3. Survival Analysis

Survival analysis estimates when customers are likely to churn, not only whether they will churn.

It shows:

- Estimated time to churn in days.
- Customer-level survival curves.
- Segment-level survival curves.
- Median time to churn by segment or cohort.
- Hazard ratios showing which features increase or reduce churn timing risk.

### 4. Customer Lifetime Value

The CLV module estimates how much value a customer is expected to generate in the future.

It shows:

- Predicted 12-month customer lifetime value.
- High-value customer rankings.
- Average CLV by segment.
- High-value customers who are also at risk of churn.
- CLV distribution across the customer base.

The planned modeling approach includes BG/NBD and Gamma-Gamma models.

### 5. RFM Segmentation

RFM segmentation groups customers based on recency, frequency, and monetary value.

It shows:

- RFM score per customer.
- RFM segment label.
- Segment size.
- Segment value contribution.
- Segment-level churn rate.
- Segment-level CLV.
- Customer lists by segment.

Example segments:

- Champions.
- Loyal customers.
- Potential loyalists.
- At-risk customers.
- Lost customers.

### 6. Uplift Modeling

Uplift modeling estimates which customers are most likely to change behavior because of a promotion or retention campaign.

It shows:

- Uplift score per customer.
- Recommended campaign target list.
- Customers likely to respond to promotions.
- Customers who should not receive costly offers.
- Promotion performance by promotion type.
- Treated vs. untreated customer outcome comparison.

### 7. Causal Discovery

Causal discovery helps identify likely direct drivers of churn, value, or campaign response.

It shows:

- Causal relationship graph.
- Ranked direct drivers of churn.
- Feature relationship directions.
- Strongest causal links.
- Business interpretation of likely root causes.

The planned approach includes DirectLiNGAM or similar causal discovery methods.

### 8. Natural Language Analytics Assistant

The assistant lets users ask questions in plain language and receive analytics-backed answers.

Example questions:

- "Which customers have the highest churn risk?"
- "Show high-value customers who have not transacted recently."
- "Which segment has the highest churn rate?"
- "What is the predicted CLV for customer CUST000123?"
- "Which customers should receive a cashback promotion?"
- "What factors are driving churn?"

It returns:

- Plain-language answer.
- Supporting metrics.
- Customer table when needed.
- Suggested or rendered charts.
- Follow-up analysis prompts.

## Customer-Facing Views

### Executive Overview

Shows the current state of the customer portfolio.

Key elements:

- KPI cards.
- Churn rate trend.
- Total transaction value.
- Active vs. churned customer count.
- Segment distribution.
- High-risk customer count.
- Average CLV.

### Customer Explorer

Shows customer-level data for filtering, ranking, and action planning.

Columns may include:

| Field | Description |
|---|---|
| Customer ID | Unique customer identifier. |
| Segment | Initial or RFM customer segment. |
| City | Customer location. |
| Age | Customer age. |
| Tenure months | Relationship length. |
| Recency | Days since latest activity. |
| Frequency | Transaction count or active transaction days. |
| Monetary value | Total customer transaction value. |
| Churn probability | Predicted churn risk. |
| Time to churn | Estimated churn timing. |
| CLV 12m | Predicted 12-month value. |
| Uplift score | Promotion targeting score. |
| Recommended action | Suggested next business action. |

### Segment Analytics

Shows how customer value and risk are distributed across groups.

It helps users compare:

- Mass, Premium, and VIP customers.
- RFM segments.
- City cohorts.
- Tenure cohorts.
- Promotion vs. non-promotion groups.
- High-risk vs. low-risk customers.

### Campaign Targeting

Shows which customers should receive retention campaigns or promotions.

It helps users:

- Select customers with high uplift.
- Prioritize high-CLV customers.
- Avoid wasting promotions on customers unlikely to change behavior.
- Export a campaign target list.
- Compare expected campaign impact by segment.

## Key Metrics

### Customer Metrics

| Metric | Meaning |
|---|---|
| Total customers | Number of customers in the selected scope. |
| Active customers | Customers still considered active. |
| Churned customers | Customers labeled as churned. |
| Churn rate | Churned customers divided by total customers. |
| Average tenure | Average customer relationship length. |
| Segment mix | Distribution across customer segments. |

### Transaction Metrics

| Metric | Meaning |
|---|---|
| Total transaction value | Sum of all transaction amounts. |
| Average transaction value | Mean transaction amount. |
| Transaction frequency | Number of transactions or transaction days. |
| Recency | Days since the latest transaction. |
| Monetary value | Total spend or transaction amount per customer. |
| Active days ratio | Active transaction days divided by total transaction count. |
| 30-day activity | Recent frequency and monetary value. |
| 90-day activity | Medium-term frequency and monetary value. |
| 180-day activity | Longer-term frequency and monetary value. |

### Predictive Metrics

| Metric | Meaning |
|---|---|
| Churn probability | Predicted probability of churn. |
| Time to churn days | Estimated days until churn. |
| CLV 12m | Predicted 12-month customer lifetime value. |
| Uplift score | Estimated incremental promotion effect. |
| RFM score | Combined recency, frequency, and monetary score. |
| Hazard ratio | Survival model measure of churn timing risk. |

### Model Quality Metrics

| Metric | Meaning |
|---|---|
| AUC-ROC | Measures churn model ranking quality. |
| PR-AUC | Measures precision-recall quality for churn detection. |
| Brier Score | Measures probability calibration quality. |
| C-index | Measures survival model ranking quality. |
| Partial AIC | Measures survival model fit for comparison. |

## Charts and Visualizations

### Dashboard Charts

- KPI cards for customers, churn rate, average CLV, and high-risk customers.
- Line chart of transaction value over time.
- Line chart of transaction count over time.
- Bar chart of customer segment distribution.
- Donut chart of active vs. churned customers.
- Bar chart of churn rate by city.
- Bar chart of churn rate by segment.

### Churn Charts

- Churn risk histogram.
- Churn probability by segment.
- Churn rate by tenure group.
- Top churn drivers bar chart.
- ROC curve.
- Precision-recall curve.
- Confusion matrix.
- Customer risk ranking table.

### Survival Charts

- Survival curve for all customers.
- Survival curves by segment.
- Survival curves by promotion status.
- Hazard ratio coefficient plot.
- Median time-to-churn bar chart.

### CLV Charts

- CLV distribution histogram.
- Top customer value leaderboard.
- CLV by segment bar chart.
- CLV vs. churn probability scatter plot.
- High-value at-risk quadrant chart.

### RFM Charts

- RFM segment size bar chart.
- RFM segment value contribution chart.
- Recency-frequency scatter plot.
- Monetary value box plot by segment.
- Segment migration chart when historical snapshots are available.

### Uplift Charts

- Uplift score distribution.
- Promotion response by promotion type.
- Treated vs. untreated outcome comparison.
- Campaign targeting matrix using CLV and uplift.
- Expected incremental value by campaign cohort.

### Causal Discovery Charts

- Causal graph.
- Direct churn driver ranking.
- Feature relationship matrix.
- Edge weight chart for strongest causal links.

## Data Foundation

The product uses three main data groups:

### Customer Data

- Customer ID.
- Tenant ID.
- Full name.
- Age.
- Gender.
- City.
- Signup date.
- Tenure months.
- Initial segment.
- Promotion status.
- Churn label.

### Transaction Data

- Transaction ID.
- Customer ID.
- Transaction date.
- Amount.
- Transaction type.
- Channel.
- Status.
- Category.

### Feature and Prediction Data

- RFM recency.
- RFM frequency.
- RFM monetary value.
- RFM score.
- RFM segment.
- CLV 12m.
- Churn probability.
- Time to churn days.
- Uplift score.
- Last updated timestamp.

## Recommended Business Actions

| Customer Pattern | Recommended Action |
|---|---|
| High churn risk and high CLV | Prioritize for retention outreach. |
| High CLV and low churn risk | Maintain relationship and offer loyalty benefits. |
| Low CLV and high churn risk | Use low-cost automated retention workflow. |
| High uplift score | Include in promotion campaign. |
| Low uplift score | Avoid expensive promotion spend. |
| Recently inactive customer | Trigger reactivation campaign. |
| New customer with low activity | Trigger onboarding support. |

## Current Repository Status

The current project contains:

- Synthetic banking data generation.
- Supabase Postgres table design.
- One-time CSV-to-Supabase mock data seed pipeline.
- Feature engineering for RFM, rolling activity windows, behavioral features, and promotion features.
- Model notebooks for churn classification, survival analysis, CLV, causal inference, and uplift modeling.
- A project plan for FastAPI, Streamlit, LangChain, MLflow, Docker, and AWS deployment.

The next major product steps are:

1. Improve behavioral data generation so churn depends on realistic transaction patterns.
2. Complete the unified training pipeline.
3. Register models in MLflow.
4. Build API inference tools.
5. Build Streamlit dashboard views.
6. Connect the natural language assistant to SQL and model outputs.

## One-Sentence Description

FinChat Analytics helps financial institutions predict churn, estimate customer value, target promotions, explain customer behavior, and turn banking transaction data into clear retention actions.
