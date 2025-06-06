# Detailed Plan for Modifying `STEP2.py`

This document outlines the planned modifications for the `STEP2.py` script, focusing on enhancing the logic for building and associating endoscope replacement chains.

**Last Updated:** 2025-06-03

## I. SKU Consistency:
*   **Action:** Ensure all chain-building and association logic strictly adheres to matching SKUs. The script's current design around a single `TARGET_ENDOSCOPE_SKU` inherently handles this for a single run. No specific code change is anticipated here unless the goal is to process multiple target SKUs simultaneously and ensure chains don't cross those distinct target SKUs.

## II. Modifications to `build_speculative_orphan_chains` (in `STEP2.py`):
    1.  **Remove `cand_key[1] not in csa_order_ids` Restriction:**
        *   **Location:** Inside the loop checking `potential_replacements`.
        *   **Action:** Remove the condition `and cand_key[1] not in csa_order_ids` when evaluating a candidate orphan replacement.
    2.  **Explicit Link Search (New - Highest Priority):**
        *   **Context:** When an orphan `current_instance_key` is returned (has an `rma_dt`), this search occurs *before* falling back to date-based search.
        *   **Action:**
            *   Get the serial number of `current_instance_key` (`returned_orphan_sn`).
            *   Get the RMA number associated with the return of `current_instance_key` if available from `rma_events` (`returned_orphan_rma_num`).
            *   Iterate through `potential_replacements` (`cand_key`). For each `cand_key`:
                *   Fetch the Sales Order (SO) details for `cand_key`'s SO number (`cand_so_num = cand_key[1]`) from the main `sales_orders` list.
                *   Check the `terms`, `notes`, and `reference_number` fields of the fetched SO.
                *   Use regex to search these fields for `returned_orphan_sn` or `returned_orphan_rma_num`.
                *   If a match is found:
                    *   This `cand_key` becomes the `best_replacement_key`.
                    *   Proceed to link it, bypassing the date-window search for this specific handoff.
    3.  **Adjust Replacement Date Window Logic (Fallback):**
        *   **Context:** If no explicit link is found in step II.2.
        *   **Action:**
            *   Define `lower_bound_date` and `upper_bound_date` relative to the `rma_dt` of the returned orphan.
            *   `upper_bound_date = rma_dt + timedelta(days=SPECULATIVE_REPLACEMENT_WINDOW_DAYS)` (default 30 days).
            *   If `current_instance_key == start_instance_key` (first link in a new speculative chain):
                `lower_bound_date = rma_dt + timedelta(days=1)` (replacement must be strictly after RMA).
            *   Else (subsequent link in an ongoing speculative chain):
                `lower_bound_date = rma_dt - timedelta(days=7)` (replacement can be up to 7 days before RMA).
            *   The date check for a candidate replacement becomes: `lower_bound_date <= cand_ship_dt <= upper_bound_date`.

## III. Modifications to Validated Chain Replacement Logic (Step 5 in `run_analysis_and_print_report`):
    1.  **Explicit Link Search (New - Highest Priority):**
        *   **Context:** When a `returned_instance_key` (from a validated CSA chain) is processed, this search occurs *before* falling back to date-based search for a replacement.
        *   **Action:**
            *   Get the serial number of `returned_instance_key` (`returned_validated_sn`).
            *   Get the RMA number associated with its return (`returned_validated_rma_num`).
            *   Iterate through `available_instance_keys` (`cand_key`). For each `cand_key`:
                *   Fetch the SO details for `cand_key`'s SO number (`cand_so_num = cand_key[1]`).
                *   Check `terms`, `notes`, and `reference_number` of `cand_so_num` for `returned_validated_sn` or `returned_validated_rma_num`.
                *   If a match is found AND other existing conditions for a valid replacement are met (e.g., different instance, not already used, `inField` status, not a CSA-initiating SO):
                    *   This `cand_key` becomes the `replacement_instance_key`.
                    *   Proceed to link it, bypassing the date-window search for this replacement.
    2.  **Date-Based Replacement Search (Fallback):**
        *   **Context:** If no explicit link is found in step III.1.
        *   **Action:** The existing logic for finding the earliest available shipment instance (from `available_instance_keys`) shipped on or after the RMA date remains the fallback. This includes the check that the replacement's SO is not in `csa_order_ids`.
    3.  **Replacement Slot Consumption:**
        *   **Location:** In the `else` block when `replacement_instance_key` is *not* found during validated chain processing.
        *   **Action:** Remove or comment out the line `cohort['remainingReplacements'] -= 1`. A replacement slot should only be consumed if a replacement is actually made.

## IV. Helper Function for Parsing SO Text Fields:
*   **Action:** Create a new helper function, e.g., `find_rma_or_serial_in_so_text(so_object, target_sn, target_rma_num)`.
    *   **Inputs:** Sales Order object, target serial number string, target RMA number string.
    *   **Logic:**
        *   Access `so_object.get('terms', '')`.
        *   Access `so_object.get('notes', '')`.
        *   Access `so_object.get('reference_number', '')`.
        *   Concatenate or check these fields individually.
        *   Use regular expressions to search for `target_sn` and `target_rma_num`. Patterns should be flexible (e.g., `SN\s*380.3372`, `380.3372`, `RMA-\s*00305`, `RMA\s*00305`).
    *   **Output:** Return `True` if a link is found, `False` otherwise.
*   **Integration:** This helper function will be called from within `build_speculative_orphan_chains` (II.2) and the validated chain processing logic (III.1).

## V. Visualizing Link Prioritization (Conceptual):

```mermaid
graph TD
    subgraph Chain Link Attempt
        A[Identify Returned Scope (RS)] --> B{Call find_rma_or_serial_in_so_text for Potential Replacements (PR) against RS_Serial or RS_RMA};
        B -- Explicit Link Found in SO Text --> C[Link PR to RS];
        B -- No Explicit Link in SO Text --> D{Fallback to Date-Window Search Logic};
        D -- Replacement Found via Date Criteria --> C;
        D -- No Replacement Found via Date --> E[End Link Attempt for RS];
        C --> F[Update Chain Details];
    end
```

This plan aims to make the chain-linking logic more robust by prioritizing explicit information found in sales order texts, while retaining date-based heuristics as a fallback, and refining the rules for replacement slot consumption.