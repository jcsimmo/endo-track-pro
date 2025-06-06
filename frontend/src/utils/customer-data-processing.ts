import brain from "brain"; // Assuming 'brain' is globally accessible or correctly configured for utils

// Interfaces from CustomerDetails.tsx (lines 13-79)
// It's important these are consistent with what transformStep2DataToCustomerPageData expects and returns.

export interface ChainInfo {
  chain: string[];
  finalStatus: string;
  handoffs: string[];
  sku?: string;
  displaySku: string;
  isOrphan?: boolean;
  assignmentReason?: string;
  detailedScopes?: ScopeDetail[];
}

export interface ScopeDetail {
  serial: string;
  salesOrder?: string;
  salesOrderDate?: string;
  packageNumber?: string;
  shipmentNumber?: string;
  shipmentDate?: string;
  deliveryStatus?: string;
  trackingNumber?: string;
  trackingUrl?: string;
  carrier?: string;
  productName?: string;
  rmaDate?: string;
  rmaNumber?: string;
  status: string;
  itemSku?: string;          // New: To be populated from serialStep1DetailsMap.itemSku
  itemCustomerName?: string; // New: To be populated from serialStep1DetailsMap.soCustomerName
}

// Interface for the data extracted from Step 1 JSON for each serial
export interface Step1DetailInfo {
  itemName?: string;
  itemSku?: string;
  salesOrderNumber?: string;
  soCustomerName?: string;
  salesOrderDate?: string;
  packageNumber?: string;
  shipmentDate?: string;
  // Add other fields from Step 1 if needed later
}

export interface OrphanInfo {
  serial: string;
  sku: string;
  status: string;
  assignmentReason?: string;
  initialShipDate?: string;
  chain?: string[];
  handoffs?: string[];
}

export interface CohortDisplayData {
  orderId: string;
  csaLength: string;
  startDate: string;
  endDate: string;
  warningDate: string;
  inFieldScopeCount: number;
  sku: string; // The primary SKU this cohort data is grouped under (used to form cohortKey)
  allChains: ChainInfo[]; // All chains (validated & assigned orphans)
  totalCSASlots: number;
  // Fields needed by ClinicListItem for cohort display
  status: 'active' | 'expired' | 'warning';
  isExpired: boolean;
  activeSerialNumbers: string[];
  skuBreakdown: { [sku: string]: number }; // For display like "X x SKU, Y x SKU"
}

export interface CustomerPageData {
  customerName: string;
  totalScopesUnderCSA: number; // Sum of inFieldScopeCount from *assigned* chains (validated & assigned orphans)
  cohorts: CohortDisplayData[];
  orphanedScopesGlobal: OrphanInfo[];
  // For direct use in ClinicListItem, these are the final display values
  calculatedTotalActiveGreen: number; // Scopes in field from ACTIVE CSAs
  calculatedTotalExpiredRed: number;  // Scopes in field from EXPIRED CSAs
  inFieldGlobalOrphansCount: number; // Count of global orphans that are in-field
  calculatedTotalInPossession: number; // All scopes in customer possession (active CSA, expired CSA, all global orphans)
}

// Function to fetch customer data using the new Step2 analysis API endpoint
// (Originally from CustomerDetails.tsx lines 103-125)
export const fetchDetailedCustomerData = async (customerName: string): Promise<CustomerPageData | null> => {
  console.log(`🔍 DEBUG: fetchDetailedCustomerData for customer: ${customerName}...`);
  try {
    // 1. Fetch Step 2 Analysis Data
    const step2Response = await brain.get_step2_analysis(customerName);
    if (!step2Response.ok) {
      throw new Error(`Failed to fetch Step2 analysis: ${step2Response.status} ${step2Response.statusText}`);
    }
    const step2Data = await step2Response.json();
    console.log(`✅ DEBUG: Successfully fetched Step2 analysis for ${customerName}`);
    // Backend is now expected to provide serialStep1DetailsMap within step2Data
    // No frontend fetching of Step 1 files.

    // Transform the Step2 data into CustomerPageData format
    return transformStep2DataToCustomerPageData(step2Data, customerName);

  } catch (error) {
    console.error('❌ DEBUG: Error in fetchDetailedCustomerData:', error);
    throw error; // Re-throw to be caught by the caller
  }
};

// Transform Step2 analysis data into CustomerPageData format
export const transformStep2DataToCustomerPageData = (
  step2Data: any, // This object is now expected to contain serialStep1DetailsMap
  customerName: string
): CustomerPageData => {
  // serialStep1DetailsMap is now expected to be part of step2Data
  const serialStep1DetailsMap = new Map<string, Step1DetailInfo>(Object.entries(step2Data.serialStep1DetailsMap || {}));
  console.log(`🔄 DEBUG: transformStep2DataToCustomerPageData for ${customerName}. serialStep1DetailsMap has ${serialStep1DetailsMap.size} entries from step2Data.`);
  if (customerName.toLowerCase().includes('oasis')) { // Log input for specific clinic
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] Input step2Data keys:`, Object.keys(step2Data));
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] step2Data.serialStep1DetailsMap (first 5 if many):`, JSON.stringify(Array.from(serialStep1DetailsMap.entries()).slice(0,5), null, 2));
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] step2Data.speculative_orphan_analysis:`, JSON.stringify(step2Data?.speculative_orphan_analysis, null, 2));
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] step2Data.speculative_orphan_analysis_by_cohort?.["No Suitable Cohort Found (Capacity)"]:`, JSON.stringify(step2Data?.speculative_orphan_analysis_by_cohort?.["No Suitable Cohort Found (Capacity)"], null, 2));
  }
  const actualCustomerName = customerName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  
  const cohortMap = new Map<string, CohortDisplayData>();
  let totalScopesUnderCSAFromAssignedChains = 0;
  const orphanedScopesGlobal: OrphanInfo[] = [];

  // Initialize cohorts from csa_replacement_chains
  if (step2Data?.csa_replacement_chains) {
    for (const cohortChainData of step2Data.csa_replacement_chains) {
      const cohortSummary = cohortChainData.cohort_summary;
      const chainsBySku = cohortChainData.chains_by_sku;
      for (const sku of Object.keys(chainsBySku || {})) {
        const cohortKey = `${cohortSummary.orderId}-${sku}`;
        if (!cohortMap.has(cohortKey)) {
          cohortMap.set(cohortKey, {
            orderId: cohortSummary.orderId,
            csaLength: cohortSummary.csaLength,
            startDate: cohortSummary.startDate,
            endDate: cohortSummary.endDate,
            warningDate: cohortSummary.warningDate,
            inFieldScopeCount: 0, // Will be calculated
            sku: sku,
            allChains: [],
            totalCSASlots: cohortSummary.totalReplacements || 0,
            // Initialize new fields
            status: 'active', // Default, will be updated
            isExpired: false, // Default, will be updated
            activeSerialNumbers: [], // Will be populated
            skuBreakdown: {}, // Will be populated
          });
        }
      }
    }
  }

  // Process validated CSA replacement chains
  if (step2Data?.csa_replacement_chains) {
    for (const cohortChainData of step2Data.csa_replacement_chains) {
      const cohortSummary = cohortChainData.cohort_summary;
      const chainsBySku = cohortChainData.chains_by_sku;
      for (const [sku, chains] of Object.entries(chainsBySku || {})) {
        const cohortKey = `${cohortSummary.orderId}-${sku}`;
        const currentCohort = cohortMap.get(cohortKey);
        if (currentCohort) {
          for (const chainInfo of chains as any[]) {
            const processedChainSerials = chainInfo.chain.map((item: any) => typeof item === 'string' ? item : item.serial || 'N/A');
            const chainFinalStatus = chainInfo.final_status_description || chainInfo.final_status || "Unknown";
            const detailedScopesList: ScopeDetail[] = [];

            for (const serialNum of processedChainSerials) {
              const s1Details = serialStep1DetailsMap.get(serialNum); // Use the passed map
              if (s1Details) {
                detailedScopesList.push({
                  serial: serialNum,
                  productName: s1Details.itemName,
                  itemSku: s1Details.itemSku,
                  salesOrder: s1Details.salesOrderNumber,
                  itemCustomerName: s1Details.soCustomerName,
                  salesOrderDate: s1Details.salesOrderDate,
                  packageNumber: s1Details.packageNumber,
                  shipmentDate: s1Details.shipmentDate,
                  status: chainFinalStatus,
                });
              } else {
                detailedScopesList.push({
                  serial: serialNum,
                  status: chainFinalStatus,
                  productName: "N/A (No Step 1 Data)",
                });
              }
            }

            currentCohort.allChains.push({
              chain: processedChainSerials,
              finalStatus: chainFinalStatus,
              handoffs: chainInfo.handoffs || [],
              displaySku: sku,
              isOrphan: false,
              sku: chainInfo.sku,
              detailedScopes: detailedScopesList,
            });
          }
        }
      }
    }
  }

  // Process assigned orphan chains from speculative_orphan_analysis_by_cohort
  if (step2Data?.speculative_orphan_analysis_by_cohort) {
    for (const [assignedCohortId, skuData] of Object.entries(step2Data.speculative_orphan_analysis_by_cohort as any)) {
      if (assignedCohortId === "No Suitable Cohort Found (Capacity)") continue;
      for (const [sku, orphanChains] of Object.entries(skuData as any)) {
        const cohortKey = `${assignedCohortId}-${sku}`;
        let currentCohort = cohortMap.get(cohortKey);
        if (!currentCohort && step2Data.csa_replacement_chains?.find((c:any) => c.cohort_summary.orderId === assignedCohortId)) {
            const cohortSummary = step2Data.csa_replacement_chains.find((c:any) => c.cohort_summary.orderId === assignedCohortId)?.cohort_summary;
            if (cohortSummary) {
                 cohortMap.set(cohortKey, {
                    orderId: cohortSummary.orderId, csaLength: cohortSummary.csaLength,
                    startDate: cohortSummary.startDate, endDate: cohortSummary.endDate, warningDate: cohortSummary.warningDate,
                    inFieldScopeCount: 0, sku: sku, allChains: [], totalCSASlots: cohortSummary.totalReplacements || 0,
                    status: 'active',
                    isExpired: false,
                    activeSerialNumbers: [],
                    skuBreakdown: {},
                });
                currentCohort = cohortMap.get(cohortKey);
            }
        }
        if (currentCohort) {
          for (const orphanChainData of orphanChains as any[]) {
            let normalizedStatus = orphanChainData.final_status_description || orphanChainData.final_status || "Unknown";
            if (normalizedStatus.toLowerCase().includes('infield') || normalizedStatus.toLowerCase() === 'status: infield') {
              normalizedStatus = "In Field";
            }
            const processedOrphanChainSerials = orphanChainData.chain.map((item: any) => typeof item === 'string' ? item : item.serial || 'N/A');
            const orphanDetailedScopesList: ScopeDetail[] = [];

            for (const serialNum of processedOrphanChainSerials) {
              const s1Details = serialStep1DetailsMap.get(serialNum); // Use the passed map
              if (s1Details) {
                orphanDetailedScopesList.push({
                  serial: serialNum,
                  productName: s1Details.itemName,
                  itemSku: s1Details.itemSku,
                  salesOrder: s1Details.salesOrderNumber,
                  itemCustomerName: s1Details.soCustomerName,
                  salesOrderDate: s1Details.salesOrderDate,
                  packageNumber: s1Details.packageNumber,
                  shipmentDate: s1Details.shipmentDate,
                  status: normalizedStatus,
                });
              } else {
                orphanDetailedScopesList.push({
                  serial: serialNum,
                  status: normalizedStatus,
                  productName: "N/A (No Step 1 Data)",
                });
              }
            }
            
            currentCohort.allChains.push({
              chain: processedOrphanChainSerials,
              finalStatus: normalizedStatus,
              handoffs: orphanChainData.handoffs || [],
              displaySku: sku, isOrphan: true, sku: orphanChainData.sku,
              assignmentReason: orphanChainData.assignment_reason,
              detailedScopes: orphanDetailedScopesList,
            });
          }
        }
      }
    }
  }
  
  // Calculate inFieldScopeCount, activeSerialNumbers, skuBreakdown, status, isExpired for each cohort
  // and sum for totalScopesUnderCSAFromAssignedChains
  cohortMap.forEach(cohort => {
    const activeSerials: string[] = [];
    const skuBreakdownCalc: { [sku: string]: number } = {};
    let countInField = 0;

    cohort.allChains.forEach(c => {
      // SKU breakdown for this specific cohort (grouped by original orderId + displaySku)
      // Uses displaySku from the chain, which should match the cohort's main 'sku' field here.
      skuBreakdownCalc[c.displaySku] = (skuBreakdownCalc[c.displaySku] || 0) + 1;

      if (c.finalStatus.toLowerCase().includes('in field')) {
        countInField++;
        // Assuming the last serial in the chain is the active one if status is "in field"
        if (c.chain.length > 0) {
          activeSerials.push(c.chain[c.chain.length - 1]);
        }
      }
    });
    cohort.inFieldScopeCount = countInField;
    cohort.activeSerialNumbers = activeSerials;
    cohort.skuBreakdown = skuBreakdownCalc; // Populate skuBreakdown

    // Determine status and isExpired (moved from helper to ensure it's set on CohortDisplayData)
    const today = new Date();
    const expiry = new Date(cohort.endDate);
    const daysUntilExpiration = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    
    if (daysUntilExpiration < 0) {
      cohort.status = 'expired';
      cohort.isExpired = true;
    } else if (daysUntilExpiration <= 60) {
      cohort.status = 'warning';
      cohort.isExpired = false;
    } else {
      cohort.status = 'active';
      cohort.isExpired = false;
    }
    
    totalScopesUnderCSAFromAssignedChains += cohort.inFieldScopeCount;
  });

  const cohortsArray = Array.from(cohortMap.values());
  // Sort cohorts by start date, most recent first
  cohortsArray.sort((a, b) => new Date(b.startDate).getTime() - new Date(a.startDate).getTime());

  // Process unassigned orphans from "No Suitable Cohort Found (Capacity)"
  if (step2Data?.speculative_orphan_analysis_by_cohort?.["No Suitable Cohort Found (Capacity)"]) {
    const unassignedData = step2Data.speculative_orphan_analysis_by_cohort["No Suitable Cohort Found (Capacity)"];
    for (const [sku, orphanChains] of Object.entries(unassignedData as any)) {
      for (const orphanChainData of orphanChains as any[]) {
        const firstSerialInChain = orphanChainData.chain?.[0];
        orphanedScopesGlobal.push({
          serial: typeof firstSerialInChain === 'string' ? firstSerialInChain : firstSerialInChain?.serial || 'N/A',
          sku: sku,
          status: orphanChainData.final_status_description || orphanChainData.final_status || "Unknown",
          assignmentReason: orphanChainData.assignment_reason,
          initialShipDate: orphanChainData.starter_serial_ship_date || orphanChainData.initial_ship_date,
          chain: orphanChainData.chain?.map((item: any) => typeof item === 'string' ? item : item.serial || 'N/A'),
          handoffs: orphanChainData.handoffs || []
        });
      }
    }
  }

  // Process truly unassigned orphans from global speculative_orphan_analysis
  if (step2Data?.speculative_orphan_analysis) {
    for (const orphanChainData of step2Data.speculative_orphan_analysis as any[]) {
      if (!orphanChainData.assigned_cohort) {
        const firstSerialInChain = orphanChainData.chain?.[0];
        const orphanSku = orphanChainData.sku || (firstSerialInChain && typeof firstSerialInChain !== 'string' ? firstSerialInChain.sku : 'Unknown SKU');
        orphanedScopesGlobal.push({
          serial: typeof firstSerialInChain === 'string' ? firstSerialInChain : firstSerialInChain?.serial || 'N/A',
          sku: orphanSku,
          status: orphanChainData.final_status_description || orphanChainData.final_status || "Unknown",
          initialShipDate: orphanChainData.starter_serial_ship_date || orphanChainData.initial_ship_date,
          chain: orphanChainData.chain?.map((item: any) => typeof item === 'string' ? item : item.serial || 'N/A'),
          handoffs: orphanChainData.handoffs || []
        });
      }
    }
  }
  
  // Perform final calculations for dashboard display, similar to CustomerDetails.tsx rendering logic
  const activeCohorts = cohortsArray.filter(cohort => !(new Date(cohort.endDate) < new Date()));
  const expiredCohorts = cohortsArray.filter(cohort => new Date(cohort.endDate) < new Date());

  const activeInFieldFromCohorts = activeCohorts.reduce((sum, cohort) => sum + cohort.inFieldScopeCount, 0);
  const expiredInFieldFromCohorts = expiredCohorts.reduce((sum, cohort) => sum + cohort.inFieldScopeCount, 0);

  const inFieldGlobalOrphans = orphanedScopesGlobal.filter(orphan => {
    if (!orphan.status) return false;
    const lowerStatus = orphan.status.toLowerCase().replace(/\s+/g, ''); // Remove all whitespace
    const isInField = lowerStatus.includes('infield'); // Check for 'infield' without spaces
    if (customerName.toLowerCase().includes('oasis')) {
      console.log(`[transformStep2DataToCustomerPageData - ${customerName}] GlobalOrphan Check: serial=${orphan.serial}, status='${orphan.status}', processedLowerStatus='${lowerStatus}', isInField=${isInField}`);
    }
    return isInField;
  }).length;

  if (customerName.toLowerCase().includes('oasis')) {
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] Populated orphanedScopesGlobal:`, JSON.stringify(orphanedScopesGlobal, null, 2));
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] Calculated inFieldGlobalOrphans:`, inFieldGlobalOrphans);
    console.log(`[transformStep2DataToCustomerPageData - ${customerName}] activeInFieldFromCohorts:`, activeInFieldFromCohorts);
  }

  const calculatedTotalActiveGreen = activeInFieldFromCohorts; // Corrected: Only from active cohorts
  const calculatedTotalExpiredRed = expiredInFieldFromCohorts;
  // Total in possession includes active CSA, expired CSA, and all global orphans (regardless of their status for this specific count)
  const calculatedTotalInPossession = activeInFieldFromCohorts + expiredInFieldFromCohorts + orphanedScopesGlobal.length;


  return {
    customerName: actualCustomerName,
    totalScopesUnderCSA: totalScopesUnderCSAFromAssignedChains, // Populate the required field
    cohorts: cohortsArray,
    orphanedScopesGlobal,
    calculatedTotalActiveGreen,
    calculatedTotalExpiredRed,
    inFieldGlobalOrphansCount: inFieldGlobalOrphans, // Pass the count
    calculatedTotalInPossession
  };
};

// No need for a separate isCohortExpired helper if logic is inline and sets cohort.status/isExpired