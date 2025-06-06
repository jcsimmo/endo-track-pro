STEP2_VERSION_CHECK: Executing build_csa_replacement_chains - version with explicit save debugs - 6/1/2025 PM

Loading data from: clinic_output/oasis/oasis_step1_data.json

Processing data for customer group: Group (3565249000001061039,3565249000009055755)

Found 29 sales orders and 31 sales returns in the JSON file.


--- Filtering all processing for SKUs: P313N00, P417N00 ---

Info: Using shipment_date '2025-04-23' as fallback for SO SO-00462 PKG PKG-00609

Info: Using shipment_date '2025-04-10' as fallback for SO SO-00445 PKG PKG-00596

Info: Using shipment_date '2025-04-08' as fallback for SO SO-00443 PKG PKG-00595

Info: Using shipment_date '2024-07-18' as fallback for SO SO-00295 PKG PKG-00440

Info: Using shipment_date '2024-02-16' as fallback for SO SO-00192 PKG PKG-00327

Info: Using shipment_date '2023-11-12' as fallback for SO SO-00131 PKG PKG-00235

Info: Using shipment_date '2023-08-12' as fallback for SO SO-00098 PKG PKG-00191

Info: Using shipment_date '2023-06-19' as fallback for SO SO-00075 PKG PKG-00159

Info: Using shipment_date '2023-06-07' as fallback for SO SO-00071 PKG PKG-00154

Info: Using shipment_date '2023-06-06' as fallback for SO SO-00068 PKG PKG-00149

Info: Using shipment_date '2023-05-17' as fallback for SO SO-00062 PKG PKG-00136

Info: Using shipment_date '2023-05-17' as fallback for SO SO-00062 PKG PKG-00137

Info: Using shipment_date '2023-05-17' as fallback for SO SO-00062 PKG PKG-00138

Info: Using shipment_date '2023-04-30' as fallback for SO SO-00058 PKG PKG-00130

Info: Using shipment_date '2023-04-06' as fallback for SO SO-00049 PKG PKG-00102

Info: Using shipment_date '2023-03-22' as fallback for SO SO-00042 PKG PKG-00093

Info: Using shipment_date '2023-03-22' as fallback for SO SO-00042 PKG PKG-00094

Info: Using shipment_date '2023-03-22' as fallback for SO SO-00042 PKG PKG-00095

Info: Using shipment_date '2023-03-22' as fallback for SO SO-00042 PKG PKG-00096

Info: Using shipment_date '2023-03-22' as fallback for SO SO-00042 PKG PKG-00097

Info: Using shipment_date '2023-04-10' as fallback for SO SO-00042 PKG PKG-00115

Info: Using shipment_date '2025-04-25' as fallback for SO SO-00463 PKG PKG-00610

Extracted 77 shipment events for SKUs P313N00, P417N00.

Initialized scopeMap with 71 unique shipped serials.

Extracted 50 RMA events potentially related to SKUs P313N00, P417N00 (out of 52 total serials found in receipts).

Identified 4 relevant CSA cohorts for SKUs P313N00, P417N00.


--- Building Optimal Replacement Chains using Bipartite Matching ---

Valid returns: 13, Valid replacement candidates: 71

Building 71x71 cost matrix...

Applying Hungarian algorithm for optimal matching...

Found 13 optimal replacement assignments

  Assigned: 380.0275 (returned 2023-04-13) → 380.0565 (shipped 2023-04-30)

  Assigned: 380.2241 (returned 2023-05-01) → 380.0927 (shipped 2023-05-17)

  Assigned: 380.0594 (returned 2023-08-24) → 380.1005 (shipped 2023-11-12)

  Assigned: 380.0930 (returned 2023-11-12) → 380.1037 (shipped 2023-11-12)

  Assigned: 380.0885 (returned 2024-01-25) → 380.2899 (shipped 2024-02-16)

  Assigned: 380.0878 (returned 2024-01-25) → 380.2884 (shipped 2024-02-16)

  Assigned: 380.0889 (returned 2024-01-25) → 380.3349 (shipped 2024-02-16)

  Assigned: 380.0927 (returned 2024-03-14) → 380.3358 (shipped 2024-04-01)

  Assigned: 380.0891 (returned 2024-05-10) → 380.1887 (shipped 2024-05-20)

  Assigned: 380.0596 (returned 2024-06-17) → 380.2617 (shipped 2024-06-20)

  Assigned: 380.2919 (returned 2024-10-16) → 380.0577 (shipped 2024-11-11)

  Assigned: 380.3350 (returned 2024-12-10) → 380.1903 (shipped 2024-12-16)

  Assigned: 380.3372 (returned 2025-04-03) → 390.2565 (shipped 2025-04-10)

Bipartite matching complete. Used 13 replacement scopes.


============================== Validated CSA Replacement Chains (P313N00, P417N00) =========================


--- Detailed Chains by Cohort ---


Cohort: SO-00042 | CSA Length: 2 year | Start: 2023-03-22 (Earliest ship/delivery date) | End: 2025-03-22 | Warn: 2025-01-21 | Replacements Left: 37/40


  --- P313N00 Chains ---

    Chain: 370.2315 | Final Status: In Field

    Chain: 370.2374 | Final Status: In Field

    Chain: 370.2378 | Final Status: In Field

    Chain: 370.2391 | Final Status: In Field

    Chain: 380.0273 | Final Status: In Field

    Chain: 380.0275 -> 380.0565 | Final Status: In Field

      - Returned 380.0275 on 2023-04-13, replaced by 380.0565 shipped on 2023-04-30

    Chain: 380.0277 | Final Status: In Field

    Chain: 380.0278 | Final Status: In Field

    Chain: 380.0282 | Final Status: In Field

    Chain: 380.2241 -> 380.0927 -> 380.3358 | Final Status: In Field

      - Returned 380.2241 on 2023-05-01, replaced by 380.0927 shipped on 2023-05-17

      - Returned 380.0927 on 2024-03-14, replaced by 380.3358 shipped on 2024-04-01


Cohort: SO-00062 | CSA Length: 2 year | Start: 2023-05-17 (Earliest ship/delivery date) | End: 2025-05-17 | Warn: 2025-03-18 | Replacements Left: 33/40


  --- P313N00 Chains ---

    Chain: 380.0592 | Final Status: In Field

    Chain: 380.0594 -> 380.1005 | Final Status: In Field

      - Returned 380.0594 on 2023-08-24, replaced by 380.1005 shipped on 2023-11-12

    Chain: 380.0596 -> 380.2617 | Final Status: In Field

      - Returned 380.0596 on 2024-06-17, replaced by 380.2617 shipped on 2024-06-20

    Chain: 380.0878 -> 380.2884 | Final Status: In Field

      - Returned 380.0878 on 2024-01-25, replaced by 380.2884 shipped on 2024-02-16

    Chain: 380.0885 -> 380.2899 | Final Status: In Field

      - Returned 380.0885 on 2024-01-25, replaced by 380.2899 shipped on 2024-02-16

    Chain: 380.0889 -> 380.3349 | Final Status: In Field

      - Returned 380.0889 on 2024-01-25, replaced by 380.3349 shipped on 2024-02-16

    Chain: 380.0891 -> 380.1887 | Final Status: In Field

      - Returned 380.0891 on 2024-05-10, replaced by 380.1887 shipped on 2024-05-20

    Chain: 380.0892 | Final Status: In Field

    Chain: 380.0927 -> 380.3358 | Final Status: In Field

      - Returned 380.0927 on 2024-03-14, replaced by 380.3358 shipped on 2024-04-01

    Chain: 380.0930 -> 380.1037 | Final Status: In Field

      - Returned 380.0930 on 2023-11-12, replaced by 380.1037 shipped on 2023-11-12


Cohort: SO-00316 | CSA Length: 1 year | Start: 2024-08-16 (Earliest ship/delivery date) | End: 2025-08-16 | Warn: 2025-06-17 | Replacements Left: 17/20


  --- P313N00 Chains ---

    Chain: 380.2919 -> 380.0577 | Final Status: In Field

      - Returned 380.2919 on 2024-10-16, replaced by 380.0577 shipped on 2024-11-11

    Chain: 380.3322 | Final Status: In Field

    Chain: 380.3323 | Final Status: In Field

    Chain: 380.3350 -> 380.1903 | Final Status: In Field

      - Returned 380.3350 on 2024-12-10, replaced by 380.1903 shipped on 2024-12-16

    Chain: 380.3372 -> 390.2565 | Final Status: In Field

      - Returned 380.3372 on 2025-04-03, replaced by 390.2565 shipped on 2025-04-10


Cohort: SO-00445 | CSA Length: 1 year | Start: 2025-04-10 (Earliest ship/delivery date) | End: 2026-04-10 | Warn: 2026-02-09 | Replacements Left: 8/8


  --- P313N00 Chains ---

    Chain: 390.2549 | Final Status: In Field

    Chain: 390.2565 | Final Status: In Field


=========================== End of Validated CSA Chains ===========================


Identified 33 potential orphan serials (never assigned to a cohort).


--- Building Optimal Orphan Chains using Bipartite Matching ---

  Found orphan replacement candidate: 380.2643 shipped 2024-06-20

  Found orphan replacement candidate: 380.2604 shipped 2024-05-20

  Found orphan replacement candidate: 381.0003 shipped 2025-02-14

  Found orphan replacement candidate: 380.2635 shipped 2024-06-20

  Found orphan replacement candidate: 380.0888 shipped 2023-06-07

  Found orphan replacement candidate: 380.0587 shipped 2023-04-30

  Found orphan replacement candidate: 380.0573 shipped 2023-06-19

  Found orphan replacement candidate: 380.0879 shipped 2024-11-11

  Found orphan replacement candidate: 380.3351 shipped 2024-08-30

  Found orphan replacement candidate: 380.5001 shipped 2023-06-07

  Found orphan replacement candidate: 380.1001 shipped 2023-11-12

  Found orphan replacement candidate: 380.3329 shipped 2024-08-30

  Found orphan replacement candidate: 380.2639 shipped 2024-06-20

  Found orphan replacement candidate: 380.0928 shipped 2025-04-14

  Found orphan replacement candidate: 380.0936 shipped 2024-05-20

  Found orphan replacement candidate: 380.3376 shipped 2024-08-30

  Found orphan replacement candidate: 381.0005 shipped 2025-02-14

  Found orphan replacement candidate: 380.0611 shipped 2023-06-06

  Found orphan replacement candidate: 380.0917 shipped 2025-01-07

  Found orphan replacement candidate: 380.1000 shipped 2023-11-12

  Found orphan replacement candidate: 380.0875 shipped 2024-12-16

  Found orphan replacement candidate: 381.0004 shipped 2025-02-14

  Found orphan replacement candidate: 380.2890 shipped 2024-02-16

  Found orphan replacement candidate: 380.0588 shipped 2025-04-25

  Found orphan replacement candidate: 380.0582 shipped 2023-04-06

  Found orphan replacement candidate: 380.4045 shipped 2024-04-01

  Found orphan replacement candidate: 380.0586 shipped 2023-04-30

  Found orphan replacement candidate: 380.0568 shipped 2023-04-06

  Found orphan replacement candidate: 380.2896 shipped 2024-04-01

  Found orphan replacement candidate: 380.0600 shipped 2023-06-19

  Found orphan replacement candidate: 380.2640 shipped 2024-06-20

  Found orphan replacement candidate: 380.0924 shipped 2024-05-20

  Found orphan replacement candidate: 380.0882 shipped 2023-06-19

Valid orphan returns: 0, Valid orphan replacement candidates: 33

No valid orphan returns or shipments for bipartite matching.

Using fallback greedy approach for orphan chains...


============================ Speculative Orphan Analysis (P313N00, P417N00) ============================

(Attempting to link 33 orphans using a 30-day replacement window and associating based on initial ship date)


--- Orphan Chains/Units Assigned to Cohort: SO-00042 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0568 | Final Status: In Field

      (Starts with: 380.0568, Initially Shipped: 2023-04-06)

      (Assignment Reason: Initial ship date 2023-04-06 is on or after cohort SO-00042 start date 2023-03-22.)

    Chain/Unit: 380.0582 | Final Status: In Field

      (Starts with: 380.0582, Initially Shipped: 2023-04-06)

      (Assignment Reason: Initial ship date 2023-04-06 is on or after cohort SO-00042 start date 2023-03-22.)

    Chain/Unit: 380.0586 | Final Status: In Field

      (Starts with: 380.0586, Initially Shipped: 2023-04-30)

      (Assignment Reason: Initial ship date 2023-04-30 is on or after cohort SO-00042 start date 2023-03-22.)

    Chain/Unit: 380.0587 | Final Status: In Field

      (Starts with: 380.0587, Initially Shipped: 2023-04-30)

      (Assignment Reason: Initial ship date 2023-04-30 is on or after cohort SO-00042 start date 2023-03-22.)


--- Orphan Chains/Units Assigned to Cohort: SO-00062 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0573 | Final Status: In Field

      (Starts with: 380.0573, Initially Shipped: 2023-06-19)

      (Assignment Reason: Initial ship date 2023-06-19 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.0600 | Final Status: In Field

      (Starts with: 380.0600, Initially Shipped: 2023-06-19)

      (Assignment Reason: Initial ship date 2023-06-19 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.0611 | Final Status: In Field

      (Starts with: 380.0611, Initially Shipped: 2023-06-06)

      (Assignment Reason: Initial ship date 2023-06-06 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.0882 | Final Status: In Field

      (Starts with: 380.0882, Initially Shipped: 2023-06-19)

      (Assignment Reason: Initial ship date 2023-06-19 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.0888 | Final Status: In Field

      (Starts with: 380.0888, Initially Shipped: 2023-06-07)

      (Assignment Reason: Initial ship date 2023-06-07 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.0924 | Final Status: In Field

      (Starts with: 380.0924, Initially Shipped: 2024-05-20)

      (Assignment Reason: Initial ship date 2024-05-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.0936 | Final Status: In Field

      (Starts with: 380.0936, Initially Shipped: 2024-05-20)

      (Assignment Reason: Initial ship date 2024-05-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.1000 | Final Status: In Field

      (Starts with: 380.1000, Initially Shipped: 2023-11-12)

      (Assignment Reason: Initial ship date 2023-11-12 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.1001 | Final Status: In Field

      (Starts with: 380.1001, Initially Shipped: 2023-11-12)

      (Assignment Reason: Initial ship date 2023-11-12 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2604 | Final Status: In Field

      (Starts with: 380.2604, Initially Shipped: 2024-05-20)

      (Assignment Reason: Initial ship date 2024-05-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2635 | Final Status: In Field

      (Starts with: 380.2635, Initially Shipped: 2024-06-20)

      (Assignment Reason: Initial ship date 2024-06-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2639 | Final Status: In Field

      (Starts with: 380.2639, Initially Shipped: 2024-06-20)

      (Assignment Reason: Initial ship date 2024-06-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2640 | Final Status: In Field

      (Starts with: 380.2640, Initially Shipped: 2024-06-20)

      (Assignment Reason: Initial ship date 2024-06-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2643 | Final Status: In Field

      (Starts with: 380.2643, Initially Shipped: 2024-06-20)

      (Assignment Reason: Initial ship date 2024-06-20 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2890 | Final Status: In Field

      (Starts with: 380.2890, Initially Shipped: 2024-02-16)

      (Assignment Reason: Initial ship date 2024-02-16 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.2896 | Final Status: In Field

      (Starts with: 380.2896, Initially Shipped: 2024-04-01)

      (Assignment Reason: Initial ship date 2024-04-01 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.4045 | Final Status: In Field

      (Starts with: 380.4045, Initially Shipped: 2024-04-01)

      (Assignment Reason: Initial ship date 2024-04-01 is on or after cohort SO-00062 start date 2023-05-17.)

    Chain/Unit: 380.5001 | Final Status: In Field

      (Starts with: 380.5001, Initially Shipped: 2023-06-07)

      (Assignment Reason: Initial ship date 2023-06-07 is on or after cohort SO-00062 start date 2023-05-17.)


--- Orphan Chains/Units Assigned to Cohort: SO-00316 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0875 | Final Status: In Field

      (Starts with: 380.0875, Initially Shipped: 2024-12-16)

      (Assignment Reason: Initial ship date 2024-12-16 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 380.0879 | Final Status: In Field

      (Starts with: 380.0879, Initially Shipped: 2024-11-11)

      (Assignment Reason: Initial ship date 2024-11-11 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 380.0917 | Final Status: In Field

      (Starts with: 380.0917, Initially Shipped: 2025-01-07)

      (Assignment Reason: Initial ship date 2025-01-07 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 380.3329 | Final Status: In Field

      (Starts with: 380.3329, Initially Shipped: 2024-08-30)

      (Assignment Reason: Initial ship date 2024-08-30 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 380.3351 | Final Status: In Field

      (Starts with: 380.3351, Initially Shipped: 2024-08-30)

      (Assignment Reason: Initial ship date 2024-08-30 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 380.3376 | Final Status: In Field

      (Starts with: 380.3376, Initially Shipped: 2024-08-30)

      (Assignment Reason: Initial ship date 2024-08-30 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 381.0003 | Final Status: In Field

      (Starts with: 381.0003, Initially Shipped: 2025-02-14)

      (Assignment Reason: Initial ship date 2025-02-14 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 381.0004 | Final Status: In Field

      (Starts with: 381.0004, Initially Shipped: 2025-02-14)

      (Assignment Reason: Initial ship date 2025-02-14 is on or after cohort SO-00316 start date 2024-08-16.)

    Chain/Unit: 381.0005 | Final Status: In Field

      (Starts with: 381.0005, Initially Shipped: 2025-02-14)

      (Assignment Reason: Initial ship date 2025-02-14 is on or after cohort SO-00316 start date 2024-08-16.)


--- Orphan Chains/Units Assigned to Cohort: SO-00445 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0588 | Final Status: In Field

      (Starts with: 380.0588, Initially Shipped: 2025-04-25)

      (Assignment Reason: Initial ship date 2025-04-25 is on or after cohort SO-00445 start date 2025-04-10.)

    Chain/Unit: 380.0928 | Final Status: In Field

      (Starts with: 380.0928, Initially Shipped: 2025-04-14)

      (Assignment Reason: Initial ship date 2025-04-14 is on or after cohort SO-00445 start date 2025-04-10.)


============================ End of Speculative Orphan Analysis =============================


====================== P313N00, P417N00 Status Summary ======================

Total shipped (unique serials): 71

Total returned (unique serials): 13

Serials involved in validated CSA chains: 38

Serials identified as Orphans (never in a cohort): 33

Suspected currently in field (shipped - returned): 58

  (List too long to display: 58 serials)

=============================================================================

STEP2 DEBUG: Attempting to write JSON to: clinic_output/oasis/oasis_step2_analysis_test.json

STEP2 DEBUG: 'csa_replacement_chains' has 4 items before saving.


Structured output successfully saved to clinic_output/oasis/oasis_step2_analysis_test.json

STEP2 DEBUG: Successfully wrote JSON to: clinic_output/oasis/oasis_step2_analysis_test.json

