STEP2_VERSION_CHECK: Executing build_csa_replacement_chains - version with explicit save debugs - 6/1/2025 PM

Loading data from: clinic_output/vegas_breathe_free/vegas_breathe_free_step1_data.json

Processing data for customer group: Group (3565249000004892001)

Found 3 sales orders and 6 sales returns in the JSON file.


--- Filtering all processing for SKUs: P313N00, P417N00 ---

Info: Using shipment_date '2024-02-16' as fallback for SO SO-00199 PKG PKG-00332

Info: Using shipment_date '2024-02-16' as fallback for SO SO-00199 PKG PKG-00333

Extracted 27 shipment events for SKUs P313N00, P417N00.

Initialized scopeMap with 27 unique shipped serials.

Extracted 10 RMA events potentially related to SKUs P313N00, P417N00 (out of 15 total serials found in receipts).

Identified 1 relevant CSA cohorts for SKUs P313N00, P417N00.


--- Building Optimal Replacement Chains using Bipartite Matching ---

Valid returns: 7, Valid replacement candidates: 27

Building 27x27 cost matrix...

Applying Hungarian algorithm for optimal matching...

Found 7 optimal replacement assignments

  Assigned: 380.2900 (returned 2024-06-25) → 390.0220 (shipped 2024-07-01)

  Assigned: 380.0095 (returned 2024-06-25) → 380.6956 (shipped 2024-07-01)

  Assigned: 380.2904 (returned 2024-12-30) → 380.1897 (shipped 2025-01-08)

  Assigned: 380.2881 (returned 2024-12-30) → 380.1005 (shipped 2025-01-08)

  Assigned: 380.0287 (returned 2024-12-30) → 380.0203 (shipped 2025-01-08)

  Assigned: 380.0945 (returned 2024-12-30) → 380.7015 (shipped 2025-01-08)

  Assigned: 380.0284 (returned 2024-12-30) → 380.7197 (shipped 2025-01-08)

Bipartite matching complete. Used 7 replacement scopes.


============================== Validated CSA Replacement Chains (P313N00, P417N00) =========================


--- Detailed Chains by Cohort ---


Cohort: SO-00199 | CSA Length: 1 year | Start: 2024-02-16 (Earliest ship/delivery date) | End: 2025-02-16 | Warn: 2024-12-18 | Replacements Left: 41/48


  --- P313N00 Chains ---

    Chain: 380.0893 | Final Status: In Field

    Chain: 380.1017 | Final Status: In Field

    Chain: 380.2881 -> 380.1005 | Final Status: In Field

      - Returned 380.2881 on 2024-12-30, replaced by 380.1005 shipped on 2025-01-08

    Chain: 380.2900 -> 390.0220 | Final Status: In Field

      - Returned 380.2900 on 2024-06-25, replaced by 390.0220 shipped on 2024-07-01

    Chain: 380.2904 -> 380.1897 | Final Status: In Field

      - Returned 380.2904 on 2024-12-30, replaced by 380.1897 shipped on 2025-01-08

    Chain: 380.3355 | Final Status: In Field


  --- P417N00 Chains ---

    Chain: 380.0095 -> 380.6956 | Final Status: In Field

      - Returned 380.0095 on 2024-06-25, replaced by 380.6956 shipped on 2024-07-01

    Chain: 380.0284 -> 380.7197 | Final Status: In Field

      - Returned 380.0284 on 2024-12-30, replaced by 380.7197 shipped on 2025-01-08

    Chain: 380.0287 -> 380.0203 | Final Status: In Field

      - Returned 380.0287 on 2024-12-30, replaced by 380.0203 shipped on 2025-01-08

    Chain: 380.0460 | Final Status: In Field

    Chain: 380.0462 | Final Status: In Field

    Chain: 380.0945 -> 380.7015 | Final Status: In Field

      - Returned 380.0945 on 2024-12-30, replaced by 380.7015 shipped on 2025-01-08


=========================== End of Validated CSA Chains ===========================


Identified 8 potential orphan serials (never assigned to a cohort).


============================ Speculative Orphan Analysis (P313N00, P417N00) ============================

(Attempting to link 8 orphans using a 30-day replacement window and associating based on initial ship date)


--- Orphan Chains/Units Assigned to Cohort: SO-00199 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 390.0207 | Final Status: In Field

      (Starts with: 390.0207, Initially Shipped: 2024-07-01)

      (Assignment Reason: Initial ship date 2024-07-01 is on or after cohort SO-00199 start date 2024-02-16.)

    Chain/Unit: 390.0211 | Final Status: In Field

      (Starts with: 390.0211, Initially Shipped: 2024-07-01)

      (Assignment Reason: Initial ship date 2024-07-01 is on or after cohort SO-00199 start date 2024-02-16.)

    Chain/Unit: 390.0214 | Final Status: In Field

      (Starts with: 390.0214, Initially Shipped: 2024-07-01)

      (Assignment Reason: Initial ship date 2024-07-01 is on or after cohort SO-00199 start date 2024-02-16.)

    Chain/Unit: 390.0219 | Final Status: In Field

      (Starts with: 390.0219, Initially Shipped: 2024-07-01)

      (Assignment Reason: Initial ship date 2024-07-01 is on or after cohort SO-00199 start date 2024-02-16.)

    Chain/Unit: 390.0221 | Final Status: In Field

      (Starts with: 390.0221, Initially Shipped: 2024-07-01)

      (Assignment Reason: Initial ship date 2024-07-01 is on or after cohort SO-00199 start date 2024-02-16.)

    Chain/Unit: 390.0222 | Final Status: In Field

      (Starts with: 390.0222, Initially Shipped: 2024-07-01)

      (Assignment Reason: Initial ship date 2024-07-01 is on or after cohort SO-00199 start date 2024-02-16.)


  --- P417N00 Orphan Chains ---

    Chain/Unit: 380.6838 | Final Status: In Field

      (Starts with: 380.6838, Initially Shipped: 2025-01-08)

      (Assignment Reason: Initial ship date 2025-01-08 is on or after cohort SO-00199 start date 2024-02-16.)

    Chain/Unit: 390.1986 | Final Status: In Field

      (Starts with: 390.1986, Initially Shipped: 2025-01-08)

      (Assignment Reason: Initial ship date 2025-01-08 is on or after cohort SO-00199 start date 2024-02-16.)


============================ End of Speculative Orphan Analysis =============================


====================== P313N00, P417N00 Status Summary ======================

Total shipped (unique serials): 27

Total returned (unique serials): 7

Serials involved in validated CSA chains: 19

Serials identified as Orphans (never in a cohort): 8

Suspected currently in field (shipped - returned): 20

  -> Serials: 380.0203, 380.0460, 380.0462, 380.0893, 380.1005, 380.1017, 380.1897, 380.3355, 380.6838, 380.6956, 380.7015, 380.7197, 390.0207, 390.0211, 390.0214, 390.0219, 390.0220, 390.0221, 390.0222, 390.1986

=============================================================================

STEP2 DEBUG: Attempting to write JSON to: clinic_output/vegas_breathe_free/vegas_breathe_free_step2_analysis.json

STEP2 DEBUG: 'csa_replacement_chains' has 1 items before saving.


Structured output successfully saved to clinic_output/vegas_breathe_free/vegas_breathe_free_step2_analysis.json

STEP2 DEBUG: Successfully wrote JSON to: clinic_output/vegas_breathe_free/vegas_breathe_free_step2_analysis.json

