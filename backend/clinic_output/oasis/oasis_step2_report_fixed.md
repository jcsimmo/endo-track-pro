STEP2_VERSION_CHECK: Executing build_csa_replacement_chains - version with explicit save debugs - 6/1/2025 PM

Loading data from: backend/clinic_output/oasis/oasis_step1_data.json

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

Initialized shipmentInstanceMap with 77 unique shipment instances.

Extracted 50 RMA events potentially related to SKUs P313N00, P417N00 (out of 52 total serials found in receipts).

Updated shipmentInstanceMap with RMA information for 50 RMA events.

Debug: Serial 390.2549 assigned to original cohort SO-00445

Debug: Serial 390.2565 assigned to original cohort SO-00445

Debug: Serial 380.2919 assigned to original cohort SO-00316

Debug: Serial 380.3322 assigned to original cohort SO-00316

Debug: Serial 380.3323 assigned to original cohort SO-00316

Debug: Serial 380.3350 assigned to original cohort SO-00316

Debug: Serial 380.3372 assigned to original cohort SO-00316

Debug: Serial 380.0592 assigned to original cohort SO-00062

Debug: Serial 380.0594 assigned to original cohort SO-00062

Debug: Serial 380.0596 assigned to original cohort SO-00062

Debug: Serial 380.0878 assigned to original cohort SO-00062

Debug: Serial 380.0885 assigned to original cohort SO-00062

Debug: Serial 380.0889 assigned to original cohort SO-00062

Debug: Serial 380.0891 assigned to original cohort SO-00062

Debug: Serial 380.0892 assigned to original cohort SO-00062

Debug: Serial 380.0927 assigned to original cohort SO-00062

Debug: Serial 380.0930 assigned to original cohort SO-00062

Debug: Serial 370.2315 assigned to original cohort SO-00042

Debug: Serial 370.2374 assigned to original cohort SO-00042

Debug: Serial 370.2378 assigned to original cohort SO-00042

Debug: Serial 370.2391 assigned to original cohort SO-00042

Debug: Serial 380.0273 assigned to original cohort SO-00042

Debug: Serial 380.0275 assigned to original cohort SO-00042

Debug: Serial 380.0277 assigned to original cohort SO-00042

Debug: Serial 380.0278 assigned to original cohort SO-00042

Debug: Serial 380.0282 assigned to original cohort SO-00042

Debug: Serial 380.2241 assigned to original cohort SO-00042

Identified 4 relevant CSA cohorts for SKUs P313N00, P417N00.

CSA Order IDs: ['SO-00042', 'SO-00062', 'SO-00316', 'SO-00445']


--- Building Optimal Replacement Chains using Enhanced Logic ---

Found 13 RMA'd cohort instances to process as validated chain starters

Built 13 validated replacement chains using enhanced logic

Calculated current_validated_in_field_count for 4 cohorts.


============================== Validated CSA Replacement Chains (P313N00, P417N00) =========================

Recalculated correct current_validated_in_field_count for 4 cohorts using actual chain data.


--- Detailed Chains by Cohort ---


Cohort: SO-00042 | CSA Length: 2 year | Start: 2023-03-22 (Earliest ship/delivery date) | End: 2025-03-22 | Warn: 2025-01-21 | Initial Slots: 10 | Validated In-Field: 10 | Available Slots (Pre-Orphan): 0/10 | Max Repl. Events Left: 37/40


  --- P313N00 Chains ---

    Chain: 370.2315 | Final Status: In Field

    Chain: 370.2374 | Final Status: In Field

    Chain: 370.2378 | Final Status: In Field

    Chain: 370.2391 | Final Status: In Field

    Chain: 380.0273 | Final Status: In Field

    Chain: 380.0275 -> 380.0565 -> 380.1000 | Final Status: In Field

      - Returned 380.0275 on 2023-04-13, replaced by 380.0565 shipped on 2023-04-30

      - Returned 380.0565 on 2023-11-12, replaced by 380.1000 shipped on 2023-11-12

    Chain: 380.0277 | Final Status: In Field

    Chain: 380.0278 | Final Status: In Field

    Chain: 380.0282 | Final Status: In Field

    Chain: 380.2241 -> 380.0592 | Final Status: In Field

      - Returned 380.2241 on 2023-05-01, replaced by 380.0592 shipped on 2023-05-17


Cohort: SO-00062 | CSA Length: 2 year | Start: 2023-05-17 (Earliest ship/delivery date) | End: 2025-05-17 | Warn: 2025-03-18 | Initial Slots: 10 | Validated In-Field: 8 | Available Slots (Pre-Orphan): 2/10 | Max Repl. Events Left: 22/40


  --- P313N00 Chains ---

    Chain: 380.0592 | Final Status: In Field

    Chain: 380.0596 -> 380.2640 -> 380.5001 -> 381.0005 | Final Status: In Field

      - Returned 380.0596 on 2024-06-17, replaced by 380.2640 shipped on 2024-06-20

      - Returned 380.2640 on 2024-12-10, replaced by 380.5001 shipped on 2024-12-16

      - Returned 380.5001 on 2025-02-12, replaced by 381.0005 shipped on 2025-02-14

    Chain: 380.0878 -> 380.2890 -> 380.2617 -> 380.3376 | Final Status: In Field

      - Returned 380.0878 on 2024-01-25, replaced by 380.2890 shipped on 2024-02-16

      - Returned 380.2890 on 2024-06-17, replaced by 380.2617 shipped on 2024-06-20

      - Returned 380.2617 on 2024-08-27, replaced by 380.3376 shipped on 2024-08-30

    Chain: 380.0885 -> 380.2884 -> 380.0879 | Final Status: In Field

      - Returned 380.0885 on 2024-01-25, replaced by 380.2884 shipped on 2024-02-16

      - Returned 380.2884 on 2024-10-16, replaced by 380.0879 shipped on 2024-11-11

    Chain: 380.0889 -> 380.3349 -> 380.2635 -> 380.1903 -> 381.0003 | Final Status: In Field

      - Returned 380.0889 on 2024-01-25, replaced by 380.3349 shipped on 2024-02-16

      - Returned 380.3349 on 2024-06-17, replaced by 380.2635 shipped on 2024-06-20

      - Returned 380.2635 on 2024-12-10, replaced by 380.1903 shipped on 2024-12-16

      - Returned 380.1903 on 2025-02-12, replaced by 381.0003 shipped on 2025-02-14

    Chain: 380.0891 -> 380.0936 -> 380.2639 -> 380.0568 -> 381.0004 | Final Status: In Field

      - Returned 380.0891 on 2024-05-10, replaced by 380.0936 shipped on 2024-05-20

      - Returned 380.0936 on 2024-06-17, replaced by 380.2639 shipped on 2024-06-20

      - Returned 380.2639 on 2024-12-30, replaced by 380.0568 shipped on 2025-01-07

      - Returned 380.0568 on 2025-02-12, replaced by 381.0004 shipped on 2025-02-14

    Chain: 380.0892 | Final Status: In Field

    Chain: 380.0927 -> 380.2896 -> 380.0596 -> 380.2640 -> 380.5001 -> 381.0005 | Final Status: In Field

      - Returned 380.0927 on 2024-03-14, replaced by 380.2896 shipped on 2024-04-01

      - Returned 380.2896 on 2025-04-08, replaced by 380.0596 shipped on 2025-04-08

      - Returned 380.0596 on 2024-06-17, replaced by 380.2640 shipped on 2024-06-20

      - Returned 380.2640 on 2024-12-10, replaced by 380.5001 shipped on 2024-12-16

      - Returned 380.5001 on 2025-02-12, replaced by 381.0005 shipped on 2025-02-14

    Chain: 380.0594 | Final Status: Returned (No Replacement Shipment Found)

      (Final serial 380.0594 returned on None)

    Chain: 380.0930 | Final Status: Returned (No Replacement Shipment Found)

      (Final serial 380.0930 returned on None)


Cohort: SO-00316 | CSA Length: 1 year | Start: 2024-08-16 (Earliest ship/delivery date) | End: 2025-08-16 | Warn: 2025-06-17 | Initial Slots: 5 | Validated In-Field: 3 | Available Slots (Pre-Orphan): 2/5 | Max Repl. Events Left: 17/20


  --- P313N00 Chains ---

    Chain: 380.3322 | Final Status: In Field

    Chain: 380.3323 | Final Status: In Field

    Chain: 380.3372 -> 390.2565 | Final Status: In Field

      - Returned 380.3372 on 2025-04-03, replaced by 390.2565 shipped on 2025-04-10

    Chain: 380.2919 -> 380.0888 | Final Status: Returned (No Replacement Shipment Found)

      - Returned 380.2919 on 2024-10-16, replaced by 380.0888 shipped on 2024-11-11

      (Final serial 380.0888 returned on None)

    Chain: 380.3350 -> 380.0875 | Final Status: Returned (No Replacement Shipment Found)

      - Returned 380.3350 on 2024-12-10, replaced by 380.0875 shipped on 2024-12-16

      (Final serial 380.0875 returned on None)


Cohort: SO-00445 | CSA Length: 1 year | Start: 2025-04-10 (Earliest ship/delivery date) | End: 2026-04-10 | Warn: 2026-02-09 | Initial Slots: 2 | Validated In-Field: 2 | Available Slots (Pre-Orphan): 0/2 | Max Repl. Events Left: 8/8


  --- P313N00 Chains ---

    Chain: 390.2549 | Final Status: In Field

    Chain: 390.2565 | Final Status: In Field


=========================== End of Validated CSA Chains ===========================


--- Handling Standalone Returned Orphans (SROs) with Cohort Isolation ---

  ⚠ SRO: 380.0582 CROSS-COHORT assignment to SO-00042 (was None). Violation logged.

  ⚠ SRO: 380.0568 CROSS-COHORT assignment to SO-00042 (was None). Violation logged.

  ⚠ SRO: 380.0587 CROSS-COHORT assignment to SO-00042 (was None). Violation logged.

  ⚠ SRO: 380.0586 CROSS-COHORT assignment to SO-00042 (was None). Violation logged.

  ⚠ SRO: 380.0611 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.0888 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.5001 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.0573 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.0882 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.0600 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.1005 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.1037 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.2899 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.3358 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.4045 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.2604 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.0924 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.2643 CROSS-COHORT assignment to SO-00062 (was None). Violation logged.

  ⚠ SRO: 380.3329 CROSS-COHORT assignment to SO-00316 (was None). Violation logged.

  ⚠ SRO: 380.3351 CROSS-COHORT assignment to SO-00316 (was None). Violation logged.

  ⚠ SRO: 380.0600 CROSS-COHORT assignment to SO-00316 (was None). Violation logged.

  ⚠ SRO: 380.0917 CROSS-COHORT assignment to SO-00316 (was None). Violation logged.

Processed 22 instances as SROs.

Cohort Isolation - Same-cohort SRO assignments: 0

Cohort Isolation - Cross-cohort SRO assignments: 22


Identified 23 potential orphan serials (never assigned to a cohort).

Identified 6 remaining orphan instance keys for enhanced chain building (after SRO processing).


Building orphan chains using enhanced logic with explicit SO text field search...

Built 6 orphan chains using enhanced logic.

Associating orphan chains to cohorts with cohort isolation...

  Using cohort isolation logic for orphan association...

    Orphan 380.0577: No original cohort found, checking date-based assignment...

    ✓ Orphan 380.0577: New assignment to cohort SO-00316 (date-based)

    Orphan 380.0587: No original cohort found, checking date-based assignment...

    Orphan 380.0588: No original cohort found, checking date-based assignment...

    ✓ Orphan 380.0588: New assignment to cohort SO-00316 (date-based)

    Orphan 380.0928: No original cohort found, checking date-based assignment...

    ✓ Orphan 380.0928: New assignment to cohort SO-00062 (date-based)

    Orphan 380.1001: No original cohort found, checking date-based assignment...

    ✓ Orphan 380.1001: New assignment to cohort SO-00062 (date-based)

    Orphan 380.1887: No original cohort found, checking date-based assignment...


============================ Speculative Orphan Analysis (P313N00, P417N00) ============================

(Attempting to link 23 orphans using a 30-day replacement window and associating based on initial ship date)


--- Orphan Chains/Units Assigned to Cohort: No Suitable Cohort Found (Capacity) ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0587 | Final Status: Status: inField

      (Starts with: 380.0587, Initially Shipped: 2023-04-30)

      (Assignment Reason: All date-suitable cohorts are at in-field capacity for orphan.)

    Chain/Unit: 380.1887 | Final Status: Status: inField

      (Starts with: 380.1887, Initially Shipped: 2024-05-20)

      (Assignment Reason: All date-suitable cohorts are at in-field capacity for orphan.)


--- Orphan Chains/Units Assigned to Cohort: SO-00062 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0928 | Final Status: Status: inField

      (Starts with: 380.0928, Initially Shipped: 2025-04-14)

      (Assignment Reason: Initial ship date 2025-04-14 is on or after cohort SO-00062 start date 2023-05-17. Assigned as in-field, capacity OK.)

    Chain/Unit: 380.1001 | Final Status: Status: inField

      (Starts with: 380.1001, Initially Shipped: 2023-11-12)

      (Assignment Reason: Initial ship date 2023-11-12 is on or after cohort SO-00062 start date 2023-05-17. Assigned as in-field, capacity OK.)


--- Orphan Chains/Units Assigned to Cohort: SO-00316 ---


  --- P313N00 Orphan Chains ---

    Chain/Unit: 380.0577 | Final Status: Status: inField

      (Starts with: 380.0577, Initially Shipped: 2024-11-11)

      (Assignment Reason: Initial ship date 2024-11-11 is on or after cohort SO-00316 start date 2024-08-16. Assigned as in-field, capacity OK.)

    Chain/Unit: 380.0588 | Final Status: Status: inField

      (Starts with: 380.0588, Initially Shipped: 2025-04-25)

      (Assignment Reason: Initial ship date 2025-04-25 is on or after cohort SO-00316 start date 2024-08-16. Assigned as in-field, capacity OK.)


============================ End of Speculative Orphan Analysis =============================


====================== P313N00, P417N00 Status Summary ======================

Total shipped (unique serials): 71

Total returned (unique serials): 24

Serials involved in validated CSA chains: 48

Serials identified as Orphans (never in a cohort): 23

Suspected currently in field (shipped - returned): 47

  -> Serials: 370.2315, 370.2374, 370.2378, 370.2391, 380.0273, 380.0277, 380.0278, 380.0282, 380.0573, 380.0577, 380.0582, 380.0586, 380.0587, 380.0588, 380.0592, 380.0594, 380.0600, 380.0611, 380.0875, 380.0879, 380.0882, 380.0888, 380.0892, 380.0917, 380.0924, 380.0928, 380.0930, 380.1000, 380.1001, 380.1005, 380.1037, 380.1887, 380.2604, 380.2643, 380.2899, 380.3322, 380.3323, 380.3329, 380.3351, 380.3358, 380.3376, 380.4045, 381.0003, 381.0004, 381.0005, 390.2549, 390.2565

=============================================================================


========================= Cohort Isolation Summary =========================

Cross-Cohort Violations Detected: 22

SRO Assignments - Same Cohort: 0

SRO Assignments - Cross Cohort: 22

Orphan Assignments - Same Cohort: 0

Orphan Assignments - Blocked (Isolation): 0


Detailed Cross-Cohort Violations:

  1. Serial 380.0582: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00042

      Reason: no_original_cohort

  2. Serial 380.0568: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00042

      Reason: no_original_cohort

  3. Serial 380.0587: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00042

      Reason: no_original_cohort

  4. Serial 380.0586: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00042

      Reason: no_original_cohort

  5. Serial 380.0611: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00062

      Reason: no_original_cohort

  6. Serial 380.0888: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00062

      Reason: no_original_cohort

  7. Serial 380.5001: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00062

      Reason: no_original_cohort

  8. Serial 380.0573: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00062

      Reason: no_original_cohort

  9. Serial 380.0882: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00062

      Reason: no_original_cohort

  10. Serial 380.0600: sro_cross_cohort_assignment

      Original: None → Assigned: SO-00062

      Reason: no_original_cohort

  ... and 12 more violations

============================================================================

STEP2 DEBUG: Attempting to write JSON to: backend/clinic_output/oasis/oasis_step2_analysis_fixed.json

STEP2 DEBUG: 'csa_replacement_chains' has 4 items before saving.


Structured output successfully saved to backend/clinic_output/oasis/oasis_step2_analysis_fixed.json

STEP2 DEBUG: Successfully wrote JSON to: backend/clinic_output/oasis/oasis_step2_analysis_fixed.json

