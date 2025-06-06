# Cohort Assignment Analysis - Serial Numbers in Multiple Cohorts

## The Real Issue: Cross-Cohort Serial Number Usage

### What I Found in the Oasis Report:

**Serial Number 390.2565 appears in TWO different cohorts:**

1. **Cohort SO-00316** (Line 201-203):
   ```
   Chain: 380.3372 -> 390.2565 | Final Status: In Field
   - Returned 380.3372 on 2025-04-03, replaced by 390.2565 shipped on 2025-04-10
   ```

2. **Cohort SO-00445** (Line 225):
   ```
   Chain: 390.2565 | Final Status: In Field
   ```

**Serial Number 380.0600 appears in TWO different cohorts:**

1. **Cohort SO-00062** (Line 251):
   ```
   SRO: 380.0600 (shipped 2023-06-19, returned 2023-06-28) assigned to cohort SO-00062
   ```

2. **Cohort SO-00316** (Line 273):
   ```
   SRO: 380.0600 (shipped 2025-01-07, returned 2025-02-12) assigned to cohort SO-00316
   ```

**Serial Number 380.0596 appears in TWO different cohorts:**

1. **Cohort SO-00062** (Lines 127-133):
   ```
   Chain: 380.0596 -> 380.2640 -> 380.5001 -> 381.0005 | Final Status: In Field
   - Returned 380.0596 on 2024-06-17, replaced by 380.2640 shipped on 2024-06-20
   ```

2. **Also in Cohort SO-00062** (Lines 171-181):
   ```
   Chain: 380.0927 -> 380.2896 -> 380.0596 -> 380.2640 -> 380.5001 -> 381.0005
   - Returned 380.2896 on 2025-04-08, replaced by 380.0596 shipped on 2025-04-08
   ```

## Why This Happens: Cohort Assignment Logic Issues

### Root Cause Analysis:

1. **Replacement Chain Logic**: When a serial is returned and replaced, it can end up in a different cohort's replacement chain
2. **SRO Assignment**: Standalone Returned Orphans (SROs) get assigned to cohorts based on ship dates, not original cohort membership
3. **Cross-Cohort Replacement**: A serial originally from Cohort A can be used to replace a return in Cohort B

### The Business Problem:

**CSA (Customer Service Agreement) cohorts should be isolated** - serials should stay within their original cohort for warranty/service tracking purposes.

## Technical Analysis

### Current Cohort Assignment Logic:
```
1. Determine initial cohort based on first shipment
2. When serial is returned, process as replacement candidate
3. When replacement needed, use ANY available refurbished serial
4. Assign replacement to cohort that needs it (may be different from original)
```

### The Issue:
- Serial 390.2565 starts in SO-00445 cohort
- Gets used as replacement for SO-00316 cohort  
- Now appears in both cohorts
- Breaks cohort isolation principle

## Proposed Solution

### Enhanced Cohort Assignment Rules:

1. **Cohort Isolation**: Serials should only be used for replacements within their original cohort
2. **Cross-Cohort Restriction**: Prevent using Serial from Cohort A to replace item in Cohort B
3. **Orphan Pool**: Create separate pool for truly unassigned serials that can be used anywhere

### Implementation Plan:

```python
def assign_replacement_serial(returned_serial, cohort_needing_replacement):
    # Step 1: Try to find replacement from same cohort
    same_cohort_candidates = get_available_serials_from_cohort(cohort_needing_replacement)
    
    if same_cohort_candidates:
        return select_best_replacement(same_cohort_candidates)
    
    # Step 2: Try orphan pool (never assigned to any cohort)
    orphan_candidates = get_orphan_serials()
    
    if orphan_candidates:
        return select_best_replacement(orphan_candidates)
    
    # Step 3: Only if critical shortage, allow cross-cohort with explicit flag
    if allow_cross_cohort_emergency:
        return select_cross_cohort_replacement(returned_serial, cohort_needing_replacement)
    
    return None  # No replacement available
```

### Cohort Tracking Enhancement:

```python
class SerialCohortTracker:
    def __init__(self):
        self.serial_cohort_map = {}  # serial -> original_cohort
        self.cohort_serials = {}     # cohort -> [serials]
    
    def assign_serial_to_cohort(self, serial, cohort):
        if serial in self.serial_cohort_map:
            raise CohortViolationError(f"Serial {serial} already belongs to cohort {self.serial_cohort_map[serial]}")
        
        self.serial_cohort_map[serial] = cohort
        if cohort not in self.cohort_serials:
            self.cohort_serials[cohort] = []
        self.cohort_serials[cohort].append(serial)
    
    def validate_replacement(self, replacement_serial, target_cohort):
        if replacement_serial in self.serial_cohort_map:
            original_cohort = self.serial_cohort_map[replacement_serial]
            if original_cohort != target_cohort:
                return {
                    'valid': False,
                    'reason': f'Cross-cohort violation: Serial {replacement_serial} belongs to {original_cohort}, cannot replace in {target_cohort}'
                }
        
        return {'valid': True}
```

## Expected Impact

### Before Fix:
- Serial 390.2565 in both SO-00316 and SO-00445 cohorts
- Serial 380.0600 in both SO-00062 and SO-00316 cohorts  
- Cohort integrity compromised
- Warranty/service tracking confusion

### After Fix:
- Each serial belongs to exactly one cohort
- Clear ownership and responsibility
- Proper CSA contract tracking
- No cross-contamination between customer agreements

## Next Steps

1. **Analyze all clinics** for similar cross-cohort serial usage
2. **Implement cohort isolation logic** in STEP2 processing
3. **Create migration strategy** for existing cross-cohort assignments
4. **Add validation rules** to prevent future violations

This addresses the core question: **Serial numbers appear in multiple cohorts because the current replacement logic doesn't enforce cohort isolation - serials can be moved between customer service agreements when they should stay within their original contract boundaries.**