# Customer Page Implementation Plan
## Bipartite Matching Chain Optimization & Frontend Integration

### Overview
This plan implements a comprehensive solution for building optimal replacement chains using bipartite graph matching and creating a customer details page that displays accurate scope tracking information.

## Phase 1: Mathematical Chain Optimization Algorithm

### 1.1 Problem Statement
Current STEP2.py uses greedy chronological processing that fails to:
- Build optimal replacement chains (380.2900 → 390.0207 missing)
- Balance chain lengths when multiple returns/shipments occur simultaneously
- Handle anticipatory replacements (shipment before return)
- Properly match SKUs due to field name bugs

### 1.2 Bipartite Graph Solution
```
Return Events (Set A) ←→ Shipment Events (Set B)

Cost Function:
cost(return_i, shipment_j) = α × time_gap + β × chain_imbalance + γ × sku_penalty + δ × cohort_preference

Where:
- time_gap = abs(ship_date - return_date) + penalty_if_negative
- chain_imbalance = variance_increase_in_chain_lengths
- sku_penalty = 0 if same SKU, ∞ if different
- cohort_preference = 0 if orphan shipment, 5 if cohort member
```

### 1.3 Algorithm Components
1. **Event Collection**: Gather all returns and shipments by SKU
2. **Cost Matrix**: Calculate pairwise costs for all valid pairings
3. **Hungarian Algorithm**: Find minimum cost perfect matching
4. **Chain Construction**: Build replacement chains from optimal pairings
5. **Orphan Handling**: Process unmatched serials

## Phase 2: STEP2.py Implementation

### 2.1 Dependencies
- Add `scipy` for `linear_sum_assignment` (Hungarian algorithm)
- Add `numpy` for variance calculations

### 2.2 New Data Structures
```python
class ReplacementEvent:
    def __init__(self, serial, date, sku, event_type, cohort=None):
        self.serial = serial
        self.date = date
        self.sku = sku
        self.event_type = event_type  # 'return' or 'shipment'
        self.cohort = cohort

class OptimalChain:
    def __init__(self, starting_serial):
        self.serials = [starting_serial]
        self.handoffs = []
        self.final_status = "inField"
        self.cohort = None
```

### 2.3 Processing Flow
1. Extract all shipment and return events
2. Group events by SKU (P313N00, P417N00)
3. For each SKU group:
   - Build cost matrix for all return→shipment pairings
   - Run Hungarian algorithm for optimal matching
   - Construct chains from matched pairs
4. Handle orphaned serials (unmatched events)
5. Generate output in existing format

### 2.4 Expected Vegas Output Validation
```
Cohort: SO-00199 | P313N00
Confirmed Chains:
- 380.0893 | Final Status: In Field
- 380.1017 | Final Status: In Field  
- 380.2900 → 390.0207 | Final Status: In Field
- 380.3355 | Final Status: In Field
- 380.2881 → 380.1005 | Final Status: Returned (No Replacement Found)
- 380.2904 → 380.1897 | Final Status: Returned (No Replacement Found)

Orphaned Scopes: 6 (390.0211, 390.0214, 390.0219, 390.0220, 390.0221, 390.0222)
```

## Phase 3: Customer Page Data Integration

### 3.1 Data Processing Pipeline
```
Step 1 Data → Step 2 Optimized Analysis → Customer Aggregation → Frontend API → Customer Page
```

### 3.2 Customer Statistics Calculation
Based on optimized chains:
- **Customer Name**: From Step 1 contact data
- **Total Scopes under CSA**: Count from Step 1 CSA line items
- **Confirmed Scopes in Field**: Count chains ending "inField" or "returned_replaced"
- **Returned w/o Replacement**: Count chains ending "returned_no_replacement_found"
- **Orphaned Scopes**: Count from speculative_orphan_analysis by status

### 3.3 Data Structure for Frontend
```typescript
interface CustomerData {
  customerName: string;
  totalScopesUnderCSA: number;
  cohorts: Array<{
    orderId: string;
    csaLength: string;
    startDate: string;
    endDate: string;
    warningDate: string;
    scopesInCohort: number;
    confirmedScopes: ChainInfo[];
    returnedScopes: ChainInfo[];
    orphanedScopes: OrphanInfo[];
  }>;
}

interface ChainInfo {
  chain: string[];
  finalStatus: string;
  handoffs: string[];
}
```

## Phase 4: Frontend Implementation

### 4.1 Customer Page Components
1. **CustomerSummaryCard**: Display aggregated statistics
2. **CohortDetailCard**: Show cohort-specific information with expandable details
3. **ChainVisualization**: Interactive replacement chain display
4. **ScopeStatusBadge**: Reusable status indicators
5. **OrphanScopeManager**: Handle orphan assignment and visualization

### 4.2 Navigation Updates
- Update [`ClinicListItem.tsx`](frontend/src/components/ClinicListItem.tsx) to navigate to customer page
- Map clinic names to customer names appropriately
- Support URL parameters: `/customer-details?customer=Vegas_Breathe_Free`

### 4.3 Page Layout Structure
```
┌─────────────────────────────────────┐
│ Customer Header                     │
│ - Name: Vegas Breathe Free          │
│ - Total Scopes under CSA: 12        │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Cohort: SO-00199                   │
│ CSA Length: 1 year                 │
│ Start: 2024-02-16 | End: 2025-02-16│
│ Scopes in Cohort: 12 (P313N00)    │
│                                     │
│ [Confirmed: 4] [Returned: 2] [Orphaned: 6] │
│                                     │
│ ▼ Confirmed Scopes (Expandable)    │
│   • 380.0893 | In Field            │
│   • 380.1017 | In Field            │
│   • 380.2900 → 390.0207 | In Field │
│   • 380.3355 | In Field            │
│                                     │
│ ▼ Returned Scopes (Expandable)     │
│   • 380.2881 → 380.1005 | Returned │
│   • 380.2904 → 380.1897 | Returned │
│                                     │
│ ▼ Orphaned Scopes (Expandable)     │
│   • 390.0211 | In Field            │
│   • 390.0214 | In Field            │
│   • ... (4 more)                   │
└─────────────────────────────────────┘
```

## Phase 5: Implementation Steps

### 5.1 Backend Implementation (Priority 1)
1. **Install Dependencies**: Add scipy to requirements
2. **Refactor STEP2.py**: 
   - Implement bipartite matching algorithm
   - Fix SKU field name bugs ('sku' vs 'csaItemSku')
   - Add multi-SKU support
3. **Validate Output**: Ensure Vegas matches expected format
4. **Performance Testing**: Verify sub-second response times

### 5.2 Frontend Implementation (Priority 2)
1. **Data Utilities**: Create customer data aggregation functions
2. **Update CustomerDetails.tsx**: Complete redesign for new data format
3. **Create Components**: Chain visualization and interaction components
4. **Update Navigation**: Dashboard → Customer page flow
5. **Error Handling**: Graceful fallbacks for missing data

### 5.3 Testing & Validation
1. **Unit Tests**: Algorithm correctness with known datasets
2. **Integration Tests**: End-to-end customer page flow
3. **Performance Tests**: Large dataset handling
4. **User Acceptance**: Vegas data produces exact expected output

## Success Criteria

### Technical Metrics
- ✅ Vegas produces exact expected chain output
- ✅ Algorithm handles multiple simultaneous returns/shipments optimally
- ✅ Chain length variance minimized across cohorts
- ✅ Multi-SKU support (P313N00 + P417N00) working correctly
- ✅ Customer page displays comprehensive scope information
- ✅ Performance remains sub-second for typical datasets

### Business Metrics
- ✅ Replacement chains reflect logical business flow
- ✅ Orphan scope assignment is accurate and intuitive
- ✅ Customer page provides actionable insights for CSA management
- ✅ Data integrity maintained across Step 1 → Step 2 → Frontend pipeline

## Risk Mitigation

### Algorithm Complexity
- **Risk**: Hungarian algorithm O(n³) complexity for large datasets
- **Mitigation**: Implement time-based batching, limit matching window

### Data Consistency
- **Risk**: Step 1/Step 2 data format changes breaking frontend
- **Mitigation**: Robust error handling, data validation layers

### Performance
- **Risk**: Large customer datasets causing slow page loads
- **Mitigation**: Pagination, lazy loading, data caching strategies

---

**Next Steps**: Begin implementation with STEP2.py bipartite matching algorithm, validate against Vegas expected output, then proceed to customer page frontend development.