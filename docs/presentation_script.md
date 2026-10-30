# Taco Bueno POS Data Pipeline

Speaker notes aligned to the slide numbers in **Taco 2.pdf**. Target delivery: approximately five minutes. Read the spoken text; the short slide labels are navigation cues.

## Slide 1 - Introduction

Our project turns Taco Bueno point-of-sale records into consistent data for pricing and promotion analysis. Before deciding whether an offer works, we need numbers we can trust. This demonstration covers December 31, 2025, and January 1, 2026.

## Slide 2 - Pipeline

Bronze preserves a source snapshot and records its version. Silver standardizes fields, classifies items and adjustments, and reconstructs tickets. Structurally invalid records go to quarantine, while identifiable tickets with financial issues go to review.

Published tickets feed Gold business metrics. The job then validates the outputs before running analysis. The dashboard and Genie make those results available for exploration. This is batch ingestion from an existing source table.

## Slide 3 - Why ticket reconstruction matters

This example shows the same ticket total repeated on two item rows. Adding both would produce 21.60 instead of 10.80. We identify tickets by store, business date, and check number, check that their repeated amounts agree, and count each ticket amount once. Legitimate repeated purchases remain in the data.

We also found different financial definitions across stores: some totals include tax after discounts; others are before discounts and tax. Store-specific rules normalize them into comparable customer and merchandise amounts.

## Slide 4 - What was processed and validated

We processed 284,428 records from 114 stores. Of 40,306 identifiable tickets, 40,257 were published and 49 were held for financial review. The 99.88% figure is publication coverage, not an accuracy score.

For completeness, all source rows were accounted for. For consistency, published amounts reconcile across outputs. Validity checks cover fields and financial rules, while uniqueness checks prevent duplicate published ticket keys. A synthetic invalid-date example demonstrates quarantine, and all 28 automated tests passed.

Financial equations check arithmetic, not independent accuracy against receipts. A rerun reproduced the same business counts and totals.

## Slide 5 - Findings

With those checks in place, we can examine the results and distinguish observations from conclusions that need more evidence.

## Slide 6 - Business overview

Across both dates, normalized customer amount was 615,846.68, including tax. Merchandise amount after discounts and excluding tax was 571,874.16. These are source monetary units; the currency is unconfirmed.

January 1 had 24,240 published tickets versus 16,017 on December 31, an increase of about 51%. However, average ticket value fell from 16.32 to 14.62. More transactions did not mean larger average baskets.

## Slide 7 - What people order

This view compares reported units by category and item. It helps us understand what people order and where to investigate the menu further.

Combo components can appear alongside other items, so these counts are not necessarily standalone products. We report units here, not allocated product revenue or profit.

## Slide 8 - Demand by hour and channel

These charts show when published tickets were recorded and how activity differs across the source channels. They help identify hours and channels worth investigating.

The daily table provides context: both dates represent 114 stores, but transaction volume and average ticket differ. Two holiday dates do not establish typical operating patterns or seasonality.

## Slide 9 - Pricing and discounts

About 6.4% of published tickets have a positive reported ticket discount. Ticket-discount depth is about 1.61%, measured against merchandise amount before that ticket discount and excluding tax.

We compare discounted and non-discounted baskets descriptively. These groups may contain different products or purchase occasions, so their difference is not promotion lift. A reported discount also does not identify a specific campaign.

## Slide 10 - Conclusions and next steps

We demonstrated a repeatable pipeline with reconciled metrics, visible exceptions, and useful descriptive analysis. January 1 had more tickets but a lower average ticket value.

Next, we would investigate the 49 review tickets, validate financial rules across more dates, and identify offers with a defensible comparison baseline. That is the foundation for stronger promotion decisions; these two days alone cannot establish lift or cannibalization.

## Slide 12 - Thank you

Thank you. We can walk through the pipeline, validation evidence, or dashboard questions.

---

## Deck preparation checklist - not spoken

- Slide numbers above refer to the current PDF. Remove placeholder slide 11 and blank slide 13, then renumber if needed.
- On slide 2, draw quarantine and review as branches from Silver; published records continue to Gold.
- Label slide 3's arithmetic as illustrative rather than an extracted receipt.
- Enlarge the dashboard screenshots and remove unconfirmed currency symbols from their formatting. If any remain, explicitly explain the currency limitation.
- Change the closing slide date to October 30, 2026.
- Keep publication coverage distinct from accuracy, source rows distinct from tickets, and item units distinct from product revenue.
