# Financial definitions inferred from the two-day extract

## Scope and method

Read-only analysis of all 284,428 rows in
`workspace.default.tb_daily_tld_01_01_2026_m` (2025-12-31 and 2026-01-01).
There are 40,306 candidate tickets across 114 stores, grouped by store, date and
check number. No rows were deduplicated or excluded before profiling.
Amounts were compared as DECIMAL(20,4), allowing a one-cent residual (<= 0.011).

Reproduce the principal profile with
`validation/financial_definition_analysis.sql`. The returned aggregate evidence,
including its Databricks statement ID, is saved in
`docs/evidence/financial-definition-analysis.json`.

## Observed facts

1. Total, Tax and Total Discount are repeated ticket-level fields: none of the
   40,306 ticket groups has conflicting values for those fields.
2. The extract contains two stable store populations with different monetary
   conventions. One has long check numbers (> 10^12) and one has shorter numbers.
   No store has both shapes in these two days. Number shape is a descriptive
   separator for this extract, not proof of a POS vendor or a universal routing rule.
3. Prices must not be interpreted identically across the populations.

| Population | Stores | Tickets | Accounting identity | Reconciled | Exceptions |
|---|---:|---:|---|---:|---:|
| A: long-number tickets | 78 | 28,810 | Total = SUM(Menu Price) - SUM(Item Voided) - Total Discount + Tax | 28,787 (99.92%) | 23 |
| B: short-number tickets | 36 | 11,496 | Total = SUM(Menu Price * Quantity) | 11,480 (99.86%) | 16 |

Combined: 40,267 / 40,306 = 99.90% reconcile. These are accounting matches,
not certification that every matched record is a completed sale. The 39 residual
exceptions must remain visible; zero-total/positive-tax and void-status flags need
separate review even if an arithmetic identity happens to match.

For population A, all 28,431 tickets without item-void amounts reconcile as
Total = SUM(Menu Price) - Total Discount + Tax. All 216,394 source rows in this
population have Quantity = 1. With void adjustment included, 356 of its 379
void-affected tickets also reconcile. The remaining 23 are not forced to fit.

For population B, 13,047 source rows have Quantity = 0. Many are modifiers or
unselected components with a menu price but no purchased units; multiplying by
quantity correctly gives zero. Zero quantity alone is not evidence of corruption.

## Working financial interpretation

The equations strongly support the following interpretation for reconciled tickets:

| Derived metric | Population A | Population B |
|---|---|---|
| Net merchandise amount, excluding tax | Total - Tax | Total - Total Discount |
| Customer total, including tax | Total | Total - Total Discount + Tax |
| Discount amount | Total Discount once per ticket | Total Discount once per ticket |

Population A's Total behaves as a tax-inclusive, post-discount amount.
Population B's Total behaves as a pre-discount, tax-exclusive merchandise amount.
Thus summing the source Total across the two populations mixes definitions.
Retain source_total unchanged and add explicitly named normalized metrics with
the inferred semantic profile and reconciliation status. Do not call source_total
uniform net revenue. The equations do not establish settlement, cash collection,
profit, or accounting recognition; currency is not established by these columns.

### Concrete examples

- Store 5026: item prices sum to 23.76, ticket discount is 2.38 and tax is 1.76.
  The reported Total is 23.14 = 23.76 - 2.38 + 1.76. Its merchandise amount
  excluding tax is 21.38; subtracting the discount again would be incorrect.
- Store 5261: price times quantity sums to 18.53, discount is 3.71 and tax is
  1.22. The reported Total is 18.53. The inferred merchandise amount after
  discount is 14.82, and tax-inclusive customer total is 16.04.

These are evidence-based interpretations of this extract, not externally verified
receipt definitions. Use deterministic profile and reconciliation rules rather
than waiting for documentation that is not available to the team.

## Discounts, voids and repeated rows

- All 647 tickets containing Transaction Type = Discount belong to population B.
  For all 647, SUM(Item Discount) equals the single ticket Total Discount.
  Discount rows therefore represent discounted item records in this extract;
  do not automatically treat them as separate negative payments or bad tickets.
- 194 population-B tickets have Total = Total Discount > 0 and Tax = 0,
  consistent with fully discounted merchandise, not automatically invalid sales.
- Population A has 254 negative-price rows labeled Item Promo on 241 tickets.
  All 241 reconcile with the population-A identity. Those signed promotional
  adjustments must not be rejected merely because Menu Price is negative.
  Another seven negative rows have no menu label and require separate review.
- Population B contains 343 Void rows across 213 tickets. Their Menu Price is
  zero, while Item Voided records the removed amount. A voided item is not
  sufficient evidence that the entire ticket was canceled.
- Order Voided is not sufficient by itself to detect all void events.
- Removing every identical full row would reduce accounting matches from
  40,267 to 24,652: A falls to 13,688 and B to 10,964. This is strong evidence
  that blanket DISTINCT destroys legitimate repeated items. It does not prove
  that no ingestion duplicates exist; use provenance or failed reconciliation
  to investigate candidates.

## Required follow-up in the pipeline

The initial analysis was read-only. These rules are now implemented in main:
versioned store profiles, check-grain input, normalized metrics, record roles and
reconciliation review. Execution evidence is stored separately in normalized-*-verification.json.
The implementation addresses the following requirements:

1. Set the common amount grain to check based on the full-ticket consistency
   result, while separately recording the two monetary semantic profiles.
2. Use a versioned store-profile mapping supported by accounting fit; do not
   silently hardcode number length as a general business rule.
3. Calculate separate normalized merchandise and tax-inclusive metrics and
   preserve raw Total, Tax and Total Discount.
4. Add equation residuals and ticket-status flags. Route unresolved exceptions
   to review rather than inventing corrections.
5. Replace blanket exclusions for zero quantity, Discount labels and negative
   Item Promo adjustments with evidence-based record roles. Void item quantities
   must not inflate sold-unit measures.
6. Keep original occurrences, measure reconciliation before and after any
   suspected ingestion-deduplication rule, and only remove proven duplicates.
7. Test both populations, discounts, free tickets, partial voids, promo lines,
   zero-quantity components and residual exceptions before running the two days.

Business claims must stay within the two-day scope. High arithmetic agreement
supports a defensible analytical contract; it does not remove every ambiguity
about transaction status or the source extraction process.
