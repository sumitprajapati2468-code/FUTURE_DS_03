# Marketing Funnel & Conversion Performance Summary

## Executive Overview
This analysis used 3,128 cleaned rows derived from 3,214 raw rows. The dataset covers 6 months, 5 channels, 2 campaigns per channel, and 2 audience segments.

## Data Quality Check
| column        | dtype   |   missing_values |   unique_values |
|:--------------|:--------|-----------------:|----------------:|
| date          | object  |                0 |             175 |
| week_start    | object  |                0 |              26 |
| channel       | object  |               64 |               5 |
| source        | object  |                0 |              20 |
| campaign      | object  |               32 |              10 |
| segment       | object  |                0 |               2 |
| stage         | object  |                0 |              12 |
| stage_order   | int64   |                0 |               6 |
| stage_count   | float64 |               32 |             729 |
| cost          | float64 |               32 |             513 |
| revenue       | float64 |               32 |             498 |
| channel_index | int64   |                0 |               5 |

## Funnel Performance
| stage       |   total_count | stage_to_stage_conversion_rate   | stage_drop_off_rate   |
|:------------|--------------:|:---------------------------------|:----------------------|
| Visitor     |        735470 | 100.0%                           | 0.0%                  |
| Lead        |         94584 | 12.9%                            | 87.1%                 |
| MQL         |         49657 | 52.5%                            | 47.5%                 |
| SQL         |         24735 | 49.8%                            | 50.2%                 |
| Opportunity |         10433 | 42.2%                            | 57.8%                 |
| Customer    |          3046 | 29.2%                            | 70.8%                 |

## Channel Performance
| channel     |   visitors |   leads |   customers | lead_to_customer_conversion_rate   | cac    | roi      |
|:------------|-----------:|--------:|------------:|:-----------------------------------|:-------|:---------|
| Referral    |      86987 |   18370 |        1082 | 5.9%                               | $14    | 12440.8% |
| Email       |     118158 |   20026 |         901 | 4.5%                               | $42    | 3495.0%  |
| Paid Search |     176207 |   24187 |         435 | 1.8%                               | $536   | 180.7%   |
| Organic     |     136111 |   15167 |         396 | 2.6%                               | $190   | 640.8%   |
| Paid Social |     218007 |   16834 |         232 | 1.4%                               | $1,624 | -17.7%   |

## Weekly and Monthly Trends
The weekly trend chart highlights short-term conversion movement. The monthly channel table below shows which channels hold efficiency over time.

| month               | channel   |   leads |   customers |    cost | lead_to_customer_conversion_rate   |
|:--------------------|:----------|--------:|------------:|--------:|:-----------------------------------|
| 2026-07-01 00:00:00 | Referral  |    1692 |         112 | 1469.1  | 6.6%                               |
| 2026-01-01 00:00:00 | Referral  |     861 |          55 |  776.29 | 6.4%                               |
| 2026-04-01 00:00:00 | Referral  |    2734 |         174 | 2383    | 6.4%                               |
| 2026-06-01 00:00:00 | Referral  |    3351 |         202 | 2936.94 | 6.0%                               |
| 2026-02-01 00:00:00 | Referral  |    3247 |         190 | 2561.42 | 5.9%                               |
| 2026-03-01 00:00:00 | Referral  |    3811 |         212 | 3126.62 | 5.6%                               |
| 2026-02-01 00:00:00 | Email     |    3185 |         166 | 6185.29 | 5.2%                               |
| 2026-05-01 00:00:00 | Referral  |    2674 |         137 | 2065.54 | 5.1%                               |

## Key Insights
- The largest funnel leak is between Lead and the previous stage, with a 87.1% drop-off.
- Paid Search generates the most leads, while Referral converts leads to customers at the highest rate (5.9%).
- Referral has the best CAC at $14, while Paid Social is the most expensive at $1624 per customer.
- Weekly conversion peaks around 2026-02-16 at 3.9% and bottoms out around 2026-07-06 at 2.6%.
- Monthly trends show that Referral and Email are the most efficient channels when demand is summarized by month.

## Recommendations
- Prioritize fixing the Lead handoff by tightening qualification rules, improving follow-up speed, and testing stage-specific messaging.
- Reallocate budget away from Paid Social until its CAC moves closer to the portfolio average of $481.
- Scale Referral with more budget or inventory because it has the strongest lead-to-customer efficiency.
- Review week-over-week fluctuations to identify campaign launches, creative fatigue, or sales capacity issues that coincide with conversion dips.
- Create a monthly channel scorecard that balances volume, conversion rate, CAC, and revenue so budget decisions are made on efficiency, not just traffic.

## Charts
![Funnel Chart](charts/funnel.png)
![Channel Performance Chart](charts/channel.png)
![Weekly Trend Chart](charts/trend.png)
![Monthly Trend Chart](charts/channel_trend.png)

## Notes for Stakeholders
The highest-volume channel is not always the most efficient. Use the CAC and conversion columns together when deciding where to scale budget.