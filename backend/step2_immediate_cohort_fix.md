# STEP2 Immediate Cohort Isolation Fix

## Executive Summary

**Problem**: Serial numbers appear in multiple CSA cohorts due to cross-cohort assignments during SRO (Standalone Returned Orphan) processing and orphan association.

**Solution**: Implement cohort isolation by tracking original cohort membership and prioritizing same-cohort assignments.

## Implementation Plan

### Phase 1: Add Cohort Tracking Infrastructure

**Location**: Insert after line 1282 in STEP2.py (after `serial_to_cohort_map = {}`)

```python
# COHORT ISOLATION FIX: Track original cohort membership
original_cohort_membership = {}  # serial -> original_cohort_id
cross_cohort_violations = []     # Track violations for reporting
cohort_isolation_stats = {       # Statistics for reporting
    'sro_same_cohort_assignments': 0,
    'sro_cross_cohort_assignments': 0,
    'orphan_same_cohort_assignments': 0,
    'orphan_cross_cohort_blocked': 0
}
```

### Phase 2: Track Original Cohort Membership

**Location**: Modify lines 1425-1435 in STEP2.py

```python
# --- IMPORTANT: Update scopeMap and build serial_to_cohort_map ---
for sn in cohort_data['csaScopes']:
    if sn in scopeMap:
        # COHORT ISOLATION FIX: Track original cohort membership
        if sn not in original_cohort_membership:
            original_cohort_membership[sn] = so_number
            print(f"Debug: Serial {sn} assigned to original cohort {so_number}")
        elif original_cohort_membership[sn] != so_number:
            # Detect conflicting initial assignments
            cross_cohort_violations.append({
                'serial': sn,
                'original_cohort': original_cohort_membership[sn],
                'conflicting_cohort': so_number,
                'violation_type': 'initial_assignment_conflict',
                'timestamp': datetime.now().isoformat()
            })
            print(f"Warning: Serial {sn} conflicting cohort assignments: {original_cohort_membership[sn]} vs {so_number}")
        
        # Check if already assigned - log warning, keep first assignment
        if scopeMap[sn]['cohort'] is not None and scopeMap[sn]['cohort'] != so_number:
             print(f"Warning: Serial {sn} reassigned from cohort {scopeMap[sn]['cohort']} to {so_number}. Check data.", file=sys.stderr)
        scopeMap[sn]['cohort'] = so_number # Assign cohort ID
        serial_to_cohort_map[sn] = cohort_data # Map original serial to its cohort
    else:
         # This should not happen if scopeMap initialization was complete
         print(f"Error: Serial {sn} from cohort {so_number} not found in initialized scopeMap!", file=sys.stderr)
```

### Phase 3: Fix SRO Assignment with Cohort Isolation

**Location**: Replace the entire SRO processing block (lines 1708-1792)

```python
# --- Phase 3: Handle "Standalone Returned Orphans" (SROs) with Cohort Isolation ---
print("\n--- Handling Standalone Returned Orphans (SROs) with Cohort Isolation ---")
sro_events_for_report = []
sro_processed_instance_keys = set() # Track instances processed as SROs

# Ensure validated_chain_instances is defined, even if no validated chains were built
if 'validated_chain_instances' not in locals():
    validated_chain_instances = set()

for instance_key, instance_data in shipmentInstanceMap.items():
    if (instance_data.get('cohort') is None and
        instance_data.get('rmaDateObj') is not None and
        instance_data.get('currentStatus') == 'returned' and # Ensure it's marked as returned
        instance_key not in validated_chain_instances):

        sro_serial = instance_data.get('serial')
        sro_initial_ship_date_obj = instance_data.get('originalShipmentDateObj')
        sro_rma_date_obj = instance_data.get('rmaDateObj')

        if not sro_initial_ship_date_obj or not sro_rma_date_obj:
            print(f"  Skipping potential SRO {sro_serial} due to missing dates.")
            continue

        # COHORT ISOLATION FIX: Check original cohort membership first
        original_cohort_id = original_cohort_membership.get(sro_serial)
        assigned = False
        
        if original_cohort_id:
            print(f"  SRO {sro_serial}: Checking original cohort {original_cohort_id} first...")
            # Try to assign to original cohort first
            original_cohort = next((c for c in csa_cohorts if c['orderId'] == original_cohort_id), None)
            
            if original_cohort and original_cohort['remainingReplacements'] > 0:
                # PREFERRED: Assign to original cohort
                original_cohort['remainingReplacements'] -= 1
                instance_data['cohort'] = original_cohort['orderId']
                instance_data['currentStatus'] = 'SRO_slot_consumed'
                
                if sro_serial in scopeMap:
                    scopeMap[sro_serial]['cohort'] = original_cohort['orderId']

                sro_events_for_report.append({
                    "serial": sro_serial,
                    "original_ship_date": dt_to_str(sro_initial_ship_date_obj),
                    "rma_date": dt_to_str(sro_rma_date_obj),
                    "assigned_cohort_id": original_cohort['orderId'],
                    "action": "SRO assigned to original cohort.",
                    "cohort_isolation": "respected",
                    "assignment_type": "same_cohort_preferred"
                })
                sro_processed_instance_keys.add(instance_key)
                cohort_isolation_stats['sro_same_cohort_assignments'] += 1
                print(f"  ✓ SRO: {sro_serial} assigned to ORIGINAL cohort {original_cohort['orderId']}. Isolation respected.")
                assigned = True
            else:
                capacity_msg = "no capacity" if original_cohort else "not found"
                print(f"  SRO {sro_serial}: Original cohort {original_cohort_id} {capacity_msg}. Checking alternatives...")
        
        if not assigned:
            # FALLBACK: Find best alternative cohort by date
            best_cohort_for_sro = None
            latest_start_date_for_sro = None

            for cohort_obj in csa_cohorts:
                cohort_start_date_obj = cohort_obj.get('startDateObj')
                if (cohort_start_date_obj and 
                    cohort_start_date_obj <= sro_initial_ship_date_obj and
                    cohort_obj['remainingReplacements'] > 0):
                    
                    if latest_start_date_for_sro is None or cohort_start_date_obj > latest_start_date_for_sro:
                        latest_start_date_for_sro = cohort_start_date_obj
                        best_cohort_for_sro = cohort_obj
            
            if best_cohort_for_sro:
                # CROSS-COHORT ASSIGNMENT - Track as violation
                best_cohort_for_sro['remainingReplacements'] -= 1
                instance_data['cohort'] = best_cohort_for_sro['orderId']
                instance_data['currentStatus'] = 'SRO_slot_consumed'
                
                if sro_serial in scopeMap:
                    scopeMap[sro_serial]['cohort'] = best_cohort_for_sro['orderId']
                
                # Track cross-cohort violation
                violation_reason = 'original_cohort_no_capacity' if original_cohort_id else 'no_original_cohort'
                cross_cohort_violations.append({
                    'serial': sro_serial,
                    'original_cohort': original_cohort_id,
                    'assigned_cohort': best_cohort_for_sro['orderId'],
                    'violation_type': 'sro_cross_cohort_assignment',
                    'reason': violation_reason,
                    'timestamp': datetime.now().isoformat()
                })

                sro_events_for_report.append({
                    "serial": sro_serial,
                    "original_ship_date": dt_to_str(sro_initial_ship_date_obj),
                    "rma_date": dt_to_str(sro_rma_date_obj),
                    "assigned_cohort_id": best_cohort_for_sro['orderId'],
                    "original_cohort_id": original_cohort_id,
                    "action": f"SRO cross-cohort assignment ({violation_reason}).",
                    "cohort_isolation": "violated",
                    "assignment_type": "cross_cohort_fallback"
                })
                sro_processed_instance_keys.add(instance_key)
                cohort_isolation_stats['sro_cross_cohort_assignments'] += 1
                print(f"  ⚠ SRO: {sro_serial} CROSS-COHORT assignment to {best_cohort_for_sro['orderId']} (was {original_cohort_id}). Violation logged.")
            else:
                print(f"  ✗ SRO: {sro_serial} - no suitable cohort with capacity found.")
                sro_events_for_report.append({
                    "serial": sro_serial,
                    "original_ship_date": dt_to_str(sro_initial_ship_date_obj),
                    "rma_date": dt_to_str(sro_rma_date_obj),
                    "action": "SRO identified, but no cohort capacity available.",
                    "cohort_isolation": "n/a",
                    "assignment_type": "unassigned"
                })

print(f"Processed {len(sro_processed_instance_keys)} instances as SROs.")
print(f"Cohort Isolation - Same-cohort SRO assignments: {cohort_isolation_stats['sro_same_cohort_assignments']}")
print(f"Cohort Isolation - Cross-cohort SRO assignments: {cohort_isolation_stats['sro_cross_cohort_assignments']}")
```

### Phase 4: Create Cohort-Aware Orphan Association Function

**Location**: Add new function before line 1852

```python
def associate_orphans_to_cohorts_with_isolation(orphan_chains, scope_map, csa_cohorts, original_cohort_membership, isolation_stats):
    """
    Enhanced orphan association that respects original cohort membership.
    Prevents cross-cohort contamination by prioritizing original cohort assignments.
    """
    print("  Using cohort isolation logic for orphan association...")
    
    orphan_analysis = []
    
    for chain in orphan_chains:
        starter_serial = chain.get('starter_serial', 'N/A')
        final_status = chain.get('final_status', 'Unknown')
        
        # Check original cohort membership first
        original_cohort_id = original_cohort_membership.get(starter_serial)
        assigned_cohort = None
        assignment_reason = ""
        assignment_type = "unassigned"
        
        if original_cohort_id:
            print(f"    Orphan {starter_serial}: Checking original cohort {original_cohort_id}...")
            # Try original cohort first
            original_cohort = next((c for c in csa_cohorts if c['orderId'] == original_cohort_id), None)
            
            if original_cohort:
                total_slots = original_cohort.get('total_CSA_slots', 0)
                validated_count = original_cohort.get('current_validated_in_field_count', 0)
                assigned_orphans = original_cohort.get('current_assigned_in_field_orphans', 0)
                
                if (validated_count + assigned_orphans) < total_slots and final_status == 'inField':
                    assigned_cohort = original_cohort_id
                    assignment_reason = f"Assigned to original cohort {original_cohort_id}. Cohort isolation respected."
                    assignment_type = "same_cohort_preferred"
                    original_cohort['current_assigned_in_field_orphans'] += 1
                    isolation_stats['orphan_same_cohort_assignments'] += 1
                    print(f"    ✓ Orphan {starter_serial}: Assigned to original cohort {original_cohort_id}")
                else:
                    if final_status != 'inField':
                        assigned_cohort = original_cohort_id  # Can still track returned items in original cohort
                        assignment_reason = f"Tracked in original cohort {original_cohort_id} (status: {final_status})."
                        assignment_type = "same_cohort_tracking"
                        isolation_stats['orphan_same_cohort_assignments'] += 1
                    else:
                        assignment_reason = f"Original cohort {original_cohort_id} at capacity ({validated_count + assigned_orphans}/{total_slots}). Preserving isolation - not reassigned."
                        assignment_type = "isolation_preserved"
                        isolation_stats['orphan_cross_cohort_blocked'] += 1
                        print(f"    🛡 Orphan {starter_serial}: Cohort isolation preserved (capacity constraint)")
        
        if not assigned_cohort and not original_cohort_id:
            # Only assign to other cohorts if no original cohort exists (truly orphaned)
            print(f"    Orphan {starter_serial}: No original cohort found, checking date-based assignment...")
            starter_details = scope_map.get(starter_serial, {})
            initial_ship_date_str = starter_details.get('originalShipmentDate', 'N/A')
            
            if initial_ship_date_str != 'N/A' and final_status == 'inField':
                initial_ship_date = parse_date_flexible(initial_ship_date_str)
                
                # Find best cohort by date (latest start <= ship date)
                best_cohort = None
                for cohort in csa_cohorts:
                    cohort_start_obj = cohort.get('startDateObj')
                    if cohort_start_obj and initial_ship_date and cohort_start_obj <= initial_ship_date:
                        total_slots = cohort.get('total_CSA_slots', 0)
                        validated_count = cohort.get('current_validated_in_field_count', 0)
                        assigned_orphans = cohort.get('current_assigned_in_field_orphans', 0)
                        
                        if (validated_count + assigned_orphans) < total_slots:
                            if not best_cohort or cohort_start_obj > best_cohort.get('startDateObj'):
                                best_cohort = cohort
                
                if best_cohort:
                    assigned_cohort = best_cohort['orderId']
                    assignment_reason = f"Initial ship date {initial_ship_date_str} is on or after cohort {assigned_cohort} start date {best_cohort.get('startDate', 'N/A')}. Assigned as in-field, capacity OK."
                    assignment_type = "date_based_new_assignment"
                    best_cohort['current_assigned_in_field_orphans'] += 1
                    print(f"    ✓ Orphan {starter_serial}: New assignment to cohort {assigned_cohort} (date-based)")
                else:
                    assigned_cohort = "No Suitable Cohort Found (Capacity)"
                    assignment_reason = "All date-suitable cohorts are at in-field capacity for orphan."
                    assignment_type = "capacity_constrained"
            else:
                if final_status != 'inField':
                    assigned_cohort = "No Cohort Assignment Required"
                    assignment_reason = f"Orphan status is {final_status}, no cohort assignment needed."
                    assignment_type = "status_based_skip"
                else:
                    assigned_cohort = "No Suitable Cohort Found (Date)"
                    assignment_reason = "No ship date available for cohort assignment."
                    assignment_type = "missing_data"
        
        # Create analysis entry
        chain_copy = chain.copy()
        chain_copy['assigned_cohort'] = assigned_cohort or "Unassigned"
        chain_copy['assignment_reason'] = assignment_reason
        chain_copy['cohort_isolation_status'] = assignment_type
        chain_copy['original_cohort'] = original_cohort_id
        
        orphan_analysis.append(chain_copy)
    
    return orphan_analysis
```

### Phase 5: Replace Orphan Association Call

**Location**: Replace line 1852-1855

```python
# --- Step 9: Associate Orphan Chains to Cohorts with Isolation ---
print("Associating orphan chains to cohorts with cohort isolation...")
speculative_orphan_analysis = associate_orphans_to_cohorts_with_isolation(
    speculative_orphan_chains, scopeMap, csa_cohorts, original_cohort_membership, cohort_isolation_stats
)
results_data["speculative_orphan_analysis"] = speculative_orphan_analysis
```

### Phase 6: Add Cohort Isolation Reporting

**Location**: Add after line 1953 (after the status summary)

```python
# --- Cohort Isolation Summary ---
print("\n" + "="*25 + " Cohort Isolation Summary " + "="*25)
print(f"Cross-Cohort Violations Detected: {len(cross_cohort_violations)}")
print(f"SRO Assignments - Same Cohort: {cohort_isolation_stats['sro_same_cohort_assignments']}")
print(f"SRO Assignments - Cross Cohort: {cohort_isolation_stats['sro_cross_cohort_assignments']}")
print(f"Orphan Assignments - Same Cohort: {cohort_isolation_stats['orphan_same_cohort_assignments']}")
print(f"Orphan Assignments - Blocked (Isolation): {cohort_isolation_stats['orphan_cross_cohort_blocked']}")

if cross_cohort_violations:
    print("\nDetailed Cross-Cohort Violations:")
    for i, violation in enumerate(cross_cohort_violations[:10]):  # Show first 10
        print(f"  {i+1}. Serial {violation['serial']}: {violation['violation_type']}")
        print(f"      Original: {violation['original_cohort']} → Assigned: {violation.get('assigned_cohort', 'N/A')}")
        print(f"      Reason: {violation.get('reason', 'N/A')}")
    
    if len(cross_cohort_violations) > 10:
        print(f"  ... and {len(cross_cohort_violations) - 10} more violations")

print("=" * (25 + len(" Cohort Isolation Summary ") + 25))

# Add violation data to results
results_data["cohort_isolation_analysis"] = {
    "statistics": cohort_isolation_stats,
    "violations": cross_cohort_violations,
    "violation_count": len(cross_cohort_violations),
    "isolation_effectiveness": {
        "sro_isolation_rate": cohort_isolation_stats['sro_same_cohort_assignments'] / 
                             (cohort_isolation_stats['sro_same_cohort_assignments'] + cohort_isolation_stats['sro_cross_cohort_assignments']) 
                             if (cohort_isolation_stats['sro_same_cohort_assignments'] + cohort_isolation_stats['sro_cross_cohort_assignments']) > 0 else 1.0,
        "orphan_isolation_rate": cohort_isolation_stats['orphan_same_cohort_assignments'] / 
                                (cohort_isolation_stats['orphan_same_cohort_assignments'] + cohort_isolation_stats['orphan_cross_cohort_blocked']) 
                                if (cohort_isolation_stats['orphan_same_cohort_assignments'] + cohort_isolation_stats['orphan_cross_cohort_blocked']) > 0 else 1.0
    }
}
```

## Expected Results

### Before Fix (Current Oasis Output):
- Serial 390.2565 appears in cohorts SO-00316 AND SO-00445
- Serial 380.0600 appears in cohorts SO-00062 AND SO-00316
- No tracking of cross-cohort violations

### After Fix (Expected Oasis Output):
- Each serial assigned to exactly ONE cohort (preferably original)
- Clear violation reporting for any cross-cohort assignments
- Statistics showing isolation effectiveness
- Detailed reasoning for all assignments

### Key Benefits:
1. **Preserves CSA integrity** - Each customer agreement maintains clear boundaries
2. **Prioritizes original cohort** - Serials stay in their original CSA when possible
3. **Transparent violations** - Any cross-cohort assignments are logged with reasons
4. **Capacity awareness** - Respects cohort slot limits while maintaining isolation
5. **Audit trail** - Clear tracking of all assignment decisions

## Implementation Steps

1. **Backup current STEP2.py**: `cp STEP2.py STEP2_backup.py`
2. **Apply changes incrementally** following the phases above
3. **Test with Oasis data**: Run on existing oasis_step1_data.json
4. **Compare outputs**: Analyze before/after cohort assignments
5. **Validate isolation**: Confirm no cross-cohort contamination

This fix will immediately resolve the cross-cohort serial number issue while maintaining backward compatibility and providing detailed reporting on the isolation effectiveness.