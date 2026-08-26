# Session Q first live amend (D-35): the quantity description correction

Environment: the Mac, Shell B, claude-sonnet-5 default, effort high, max_tokens 16384; the intent recorded verbatim in the record.

uv run python -m metricmine.agents propose amend --table "silver_invoice_lines" --intent "Correct the quantity column description: measured against the warehouse, 90 negative-quantity rows are not cancellation lines; all 90 carry unit_price 0 (stock-adjustment lines, zero revenue impact). The description must state both negative cases instead of claiming cancellations only."  
description_change quantity: Measured against the warehouse, 90 negative-quantity rows are not cancellation lines and all 90 carry unit_price 0, so the prior claim that negative quantity occurs only on cancellation lines is false; the description must state both cases.
decisionNegativeQuantityCause: 90 negative-quantity rows measured against the warehouse are non-cancellation lines and all carry unit_price 0, establishing a second, zero-revenue cause of negative quantity distinct from cancellations.
validation: schema ok, groundedness ok, completeness ok, lint ok, staleness ok (attempts: 1)
model claude-sonnet-5 (default); tokens in 10710, out 4317; cost ~$0.0646
draft:  proposals/silver-cleanup-proposer/20260826T153712684636Z_e65bee81/draft.odcs.yaml
record: proposals/silver-cleanup-proposer/20260826T153712684636Z_e65bee81/record.json
--- contracts/silver_invoice_lines.odcs.yaml
+++ proposals/silver-cleanup-proposer/20260826T153712684636Z_e65bee81/draft.odcs.yaml
@@ -2,8 +2,8 @@
 kind: DataContract
 id: silver_invoice_lines
 name: Silver invoice lines
-version: 1.1.0
-status: active
+version: 1.1.1
+status: draft
 domain: retail
 dataProduct: metricmine
 tenant: metricmine
@@ -52,7 +52,7 @@
     required: true
     primaryKey: true
     primaryKeyPosition: 3
-    description: Units on the line, cast DECIMAL(38,9) to INTEGER (integral min, max, and samples at v0001; range -1395 to 5184). Negative only on cancellation lines.
+    description: Units on the line, cast from DECIMAL(38,9) to INTEGER. Negative values occur both on cancellation-invoice lines and on zero-unit-price stock-adjustment lines; consumers must not infer cancellation from negative quantity alone.
   - name: invoiced_at
     logicalType: date
     physicalType: TIMESTAMP
@@ -105,11 +105,21 @@
   schema: silver
 customProperties:
 - property: proposedBy
-  value: human
+  value: silver-cleanup-proposer
+- property: proposerVersion
+  value: 0.1.0
+- property: promptVersion
+  value: 1.0.0
+- property: modelId
+  value: claude-sonnet-5
 - property: profileHash
-  value: sha256:79f801e1d8182ee55a32a0e3323134a27fec839c5a5478edfb8f5683cf5221f0
+  value: sha256:e65bee8117b65958b8c4741b43509ece19a581dd1d6bad9a7e1da9b67b0b5fcd
 - property: proposedAt
-  value: '2026-07-31'
+  value: '2026-08-26'
+- property: proposerStance
+  value: amend
+- property: amendsContract
+  value: silver_invoice_lines@1.1.0#sha256:c7b1c4c0c6fb8d490346ab520871a7dfe5d9220e8a8a064e0d829a19e3c4a2fe
 - property: decisionCancellations
   value: retained-and-flagged
 - property: decisionExactDuplicates
@@ -124,3 +134,5 @@
   value: strict-timestamp-cast
 - property: grain
   value: invoice_id, stock_code, quantity, unit_price (unique after capture-artifact exclusion)
+- property: decisionNegativeQuantityCause
+  value: cancellation-or-zero-price-adjustment
amendment direction: neutral; patch bump to 1.1.1 over 1.1.0 (amends silver_invoice_lines@1.1.0)
