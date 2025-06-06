/**
 * Utility functions for processing clinic data into dashboard summary format
 */

export interface ClinicSummary {
  clinicName: string;
  endoscopesUnderCSA: number;
  cohortCount: number;
  cohorts: CohortSummary[];
  // New fields for enhanced dashboard display
  totalActiveScopesGreen: number;
  totalExpiredScopesRed: number;
  totalInFieldScopes: number;
  // activeSerialNumbers: string[]; // Removed: More appropriate at CohortSummary level
}

export interface CohortSummary {
  orderId: string;
  startDate: string;
  endDate: string;
  skuBreakdown: { [sku: string]: number };
  status: 'active' | 'expired' | 'warning';
  csaLength: string;
  // New fields for enhanced display
  inFieldScopeCount: number;
  activeSerialNumbers: string[];
  isExpired: boolean;
}

/**
 * Extract CSA quantity from Step 1 data
 */
export const extractCSAQuantity = (step1Data: any): number => {
  let totalCSAQuantity = 0;
  
  if (!step1Data) {
    console.log('extractCSAQuantity: No step1Data provided');
    return totalCSAQuantity;
  }
  
  const salesOrders = step1Data.salesorders || [];
  console.log(`extractCSAQuantity: Processing ${salesOrders.length} sales orders`);
  
  for (const order of salesOrders) {
    const lineItems = order.line_items || [];
    console.log(`extractCSAQuantity: Order has ${lineItems.length} line items`);
    
    for (const item of lineItems) {
      // Look for CSA line items (HiFCSA-1yr, HiFCSA-2yr, etc.)
      const sku = item.sku || '';
      if (sku.includes('CSA') && (sku.includes('1yr') || sku.includes('2yr'))) {
        const quantity = parseFloat(item.quantity) || 0;
        totalCSAQuantity += quantity;
        console.log(`Found CSA line item: ${sku} with quantity ${quantity}, running total: ${totalCSAQuantity}`);
      }
    }
  }
  
  console.log(`Final CSA quantity extracted from Step 1: ${totalCSAQuantity}`);
  return totalCSAQuantity;
};

/**
 * Calculate SKU breakdown from Step 2 chains_by_sku data
 */
export const calculateSKUBreakdown = (chainsData: any): { [sku: string]: number } => {
  const skuBreakdown: { [sku: string]: number } = {};
  
  if (!chainsData.chains_by_sku) {
    console.log('No chains_by_sku data found');
    return skuBreakdown;
  }
  
  // Count chains for each SKU
  for (const [sku, chains] of Object.entries(chainsData.chains_by_sku)) {
    if (Array.isArray(chains)) {
      skuBreakdown[sku] = chains.length;
      console.log(`SKU ${sku}: ${chains.length} chains`);
    }
  }
  
  console.log('Final SKU breakdown:', skuBreakdown);
  return skuBreakdown;
};

/**
 * Determine cohort status based on end date
 */
export const determineCohortStatus = (endDate: string): 'active' | 'expired' | 'warning' => {
  const today = new Date();
  const expiry = new Date(endDate);
  const daysUntilExpiration = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  
  if (daysUntilExpiration < 0) {
    return 'expired';
  } else if (daysUntilExpiration <= 60) {
    return 'warning';
  } else {
    return 'active';
  }
};

/**
 * Format SKU breakdown for display (e.g., "6 x P313N00, 6 x P417N00")
 */
export const formatSKUBreakdown = (skuBreakdown: { [sku: string]: number }): string => {
  return Object.entries(skuBreakdown)
    .map(([sku, count]) => `${count} x ${sku}`)
    .join(', ');
};

/**
 * Format date for display (MM/DD/YY format)
 */
export const formatDisplayDate = (dateString: string): string => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const month = (date.getMonth() + 1).toString();
  const day = date.getDate().toString();
  const year = date.getFullYear().toString().slice(-2);
  
  return `${month}/${day}/${year}`;
};

/**
 * Process clinic data into summary format for dashboard
 */
export const processClinicDataToSummary = (clinicName: string, clinicData: any): ClinicSummary | null => {
  if (!clinicData) {
    console.warn(`processClinicDataToSummary: No clinicData for ${clinicName}`);
    return null;
  }
 
  // Log the keys of the received clinicData to check for step1_data presence
  if (clinicName === 'Vegas_Breathe_Free' || clinicName === 'Oasis') { // Added Oasis for debugging
    console.log(`processClinicDataToSummary: [${clinicName}] Received clinicData keys: ${Object.keys(clinicData).join(', ')}`);
    // Log the entire clinicData object for Oasis if it's not too large, to see its structure
    if (clinicName === 'Oasis') {
      console.log(`processClinicDataToSummary: [Oasis] Full clinicData:`, JSON.stringify(clinicData, null, 2));
    }
  }
  
  // First check if we have the raw step1/step2 data structure
  if (clinicData.csa_replacement_chains) {
    console.log(`processClinicDataToSummary: [${clinicName}] Has csa_replacement_chains. Using processNewFormatData.`);
    return processNewFormatData(clinicName, clinicData);
  }
  
  // Fallback for existing processed cohort format
  if (clinicData.cohorts) {
    console.log(`processClinicDataToSummary: [${clinicName}] Does NOT have csa_replacement_chains, but has cohorts. Using processExistingCohortFormat.`);
    return processExistingCohortFormat(clinicName, clinicData);
  }
  
  console.warn(`processClinicDataToSummary: [${clinicName}] No csa_replacement_chains AND no cohorts. No suitable processing path found. Data:`, JSON.parse(JSON.stringify(clinicData)));
  return null;
};

/**
 * Process new Step 1/Step 2 data format
 */
const processNewFormatData = (clinicName: string, data: any): ClinicSummary => {
  console.log(`processNewFormatData: [${clinicName}] Entry. Has step1_data: ${!!data.step1_data}, Has csa_replacement_chains: ${!!(data.csa_replacement_chains && data.csa_replacement_chains.length > 0)}`);
  const cohorts: CohortSummary[] = [];
  let clinicTotalActiveScopesGreen = 0;
  let clinicTotalExpiredScopesRed = 0;
  let clinicTotalInFieldScopes = 0;

  let endoscopesUnderCSA = 0;
  if (data.step1_data) {
    endoscopesUnderCSA = extractCSAQuantity(data.step1_data);
    console.log(`processNewFormatData: [${clinicName}] CSA quantity from Step 1: ${endoscopesUnderCSA}`);
  } else {
    console.warn(`processNewFormatData: [${clinicName}] Missing step1_data. CSA count will be 0.`);
  }
 
  const csaChainsData = data.csa_replacement_chains || [];
  if (clinicName === 'Oasis') {
    console.log(`processNewFormatData: [Oasis] csa_replacement_chains content:`, JSON.stringify(csaChainsData, null, 2));
  }
  if (csaChainsData.length === 0) {
    console.warn(`processNewFormatData: [${clinicName}] Missing or empty csa_replacement_chains. Cohort data will be empty.`);
  }

  for (const chainGroup of csaChainsData) {
    const cohortSummaryData = chainGroup.cohort_summary;
    if (!cohortSummaryData) {
      console.warn(`processNewFormatData: [${clinicName}] A chainGroup is missing its cohort_summary.`);
      continue;
    }

    const skuBreakdown = calculateSKUBreakdown(chainGroup);
    const status = determineCohortStatus(cohortSummaryData.endDate || '');
    const isExpired = status === 'expired';
    
    let cohortInFieldScopeCount = 0;
    const cohortActiveSerialNumbers: string[] = [];
    const chainsBySku = chainGroup.chains_by_sku || {};

    for (const sku in chainsBySku) {
      const chains = chainsBySku[sku] || [];
      for (const chain of chains) {
        if (clinicName === 'Oasis') {
          console.log(`processNewFormatData: [Oasis] Checking chain for SKU ${sku}. Chain final_status: '${chain.final_status}'`);
        }
        if (chain.final_status && chain.final_status.toLowerCase().includes('in field')) {
          cohortInFieldScopeCount++;
          if (clinicName === 'Oasis') {
            console.log(`processNewFormatData: [Oasis] Matched 'in field' for status '${chain.final_status}'. cohortInFieldScopeCount is now ${cohortInFieldScopeCount}`);
          }
          if (chain.final_serial_number) {
            cohortActiveSerialNumbers.push(chain.final_serial_number);
          }
        }
      }
    }

    cohorts.push({
      orderId: cohortSummaryData.orderId || 'N/A',
      startDate: cohortSummaryData.startDate || 'N/A',
      endDate: cohortSummaryData.endDate || 'N/A',
      skuBreakdown,
      status,
      csaLength: cohortSummaryData.csaLength || 'Unknown',
      inFieldScopeCount: cohortInFieldScopeCount,
      activeSerialNumbers: cohortActiveSerialNumbers,
      isExpired: isExpired,
    });

    clinicTotalInFieldScopes += cohortInFieldScopeCount;
    if (!isExpired) {
      clinicTotalActiveScopesGreen += cohortInFieldScopeCount;
    } else {
      clinicTotalExpiredScopesRed += cohortInFieldScopeCount;
    }
  }
  
  const summaryResult: ClinicSummary = {
    clinicName: formatClinicName(clinicName),
    endoscopesUnderCSA,
    cohortCount: cohorts.length,
    cohorts,
    totalActiveScopesGreen: clinicTotalActiveScopesGreen,
    totalExpiredScopesRed: clinicTotalExpiredScopesRed,
    totalInFieldScopes: clinicTotalInFieldScopes,
  };
  console.log(`processNewFormatData: [${clinicName}] Resulting summary:`, JSON.parse(JSON.stringify(summaryResult)));
  return summaryResult;
};

/**
 * Process existing cohort format (fallback)
 */
const processExistingCohortFormat = (clinicName: string, data: any): ClinicSummary => {
  console.log(`processExistingCohortFormat: [${clinicName}] Entry. Has step1_data: ${!!data.step1_data}, Has cohorts: ${!!(data.cohorts && data.cohorts.length > 0)}`);
  const cohorts: CohortSummary[] = [];
  const existingCohorts = data.cohorts || [];
  
  let clinicTotalActiveScopesGreen = 0;
  let clinicTotalExpiredScopesRed = 0;
  let clinicTotalInFieldScopes = 0;

  let endoscopesUnderCSA = 0;
  let csaCountFromStep1Attempted = false;

  if (data.step1_data) {
    console.log(`processExistingCohortFormat: [${clinicName}] Found step1_data. Calling extractCSAQuantity.`);
    endoscopesUnderCSA = extractCSAQuantity(data.step1_data); // extractCSAQuantity has its own detailed logging
    console.log(`processExistingCohortFormat: [${clinicName}] CSA quantity from Step 1 data: ${endoscopesUnderCSA}`);
    csaCountFromStep1Attempted = true;
  } else {
    console.warn(`processExistingCohortFormat: [${clinicName}] No step1_data found.`);
  }
  
  // Fallback to summing totalUnits for CSA count ONLY if Step 1 data was NOT available.
  // This is generally incorrect for CSA count but preserves original fallback behavior if step1_data is truly absent.
  if (!csaCountFromStep1Attempted && existingCohorts.length > 0) {
    console.warn(`processExistingCohortFormat: [${clinicName}] No step1_data was available to calculate CSA quantity. Falling back to summing cohort.totalUnits. This is likely NOT the true CSA count.`);
    let sumFromTotalUnits = 0;
    for (const cohort of existingCohorts) {
      sumFromTotalUnits += cohort.totalUnits || 0;
    }
    // Assign this sum only if we haven't gotten anything from step1_data
    endoscopesUnderCSA = sumFromTotalUnits;
    console.log(`processExistingCohortFormat: [${clinicName}] 'CSA quantity' (derived from sum of totalUnits): ${endoscopesUnderCSA}`);
  }
  
  for (const cohort of existingCohorts) {
    // Extract actual SKU breakdown from serials if available
    const skuBreakdown: { [sku: string]: number } = {};
    
    if (cohort.serials && Array.isArray(cohort.serials)) {
      for (const serial of cohort.serials) {
        if (serial.model) {
          skuBreakdown[serial.model] = (skuBreakdown[serial.model] || 0) + 1;
        }
      }
    } else if (cohort.totalUnits) {
      // Only use "Mixed" as last resort if we have no serial data
      skuBreakdown['Mixed'] = cohort.totalUnits;
    }
    
    const status = determineCohortStatus(cohort.endDate || ''); // Use determineCohortStatus consistently
    const isExpired = status === 'expired';

    let cohortInFieldScopeCount = 0;
    const cohortActiveSerialNumbers: string[] = [];

    if (cohort.serials && Array.isArray(cohort.serials)) {
      for (const serial of cohort.serials) {
        // Assuming serial object has a 'status' field like 'In Field' and 'id' for serial number
        if (serial.status && typeof serial.status === 'string' && serial.status.toLowerCase().includes('in field')) {
          cohortInFieldScopeCount++;
          if (serial.id) {
            cohortActiveSerialNumbers.push(serial.id);
          }
        }
      }
    }
    
    cohorts.push({
      orderId: cohort.id || 'N/A',
      startDate: cohort.startDate || 'N/A',
      endDate: cohort.endDate || 'N/A',
      skuBreakdown,
      status,
      csaLength: cohort.csaLength || 'Unknown', // Use actual csaLength if available
      inFieldScopeCount: cohortInFieldScopeCount,
      activeSerialNumbers: cohortActiveSerialNumbers,
      isExpired: isExpired,
    });

    clinicTotalInFieldScopes += cohortInFieldScopeCount;
    if (!isExpired) {
      clinicTotalActiveScopesGreen += cohortInFieldScopeCount;
    } else {
      clinicTotalExpiredScopesRed += cohortInFieldScopeCount;
    }
  }
  
  const summaryResult: ClinicSummary = {
    clinicName: formatClinicName(clinicName),
    endoscopesUnderCSA,
    cohortCount: cohorts.length,
    cohorts,
    totalActiveScopesGreen: clinicTotalActiveScopesGreen,
    totalExpiredScopesRed: clinicTotalExpiredScopesRed,
    totalInFieldScopes: clinicTotalInFieldScopes,
  };
  console.log(`processExistingCohortFormat: [${clinicName}] Resulting summary:`, JSON.parse(JSON.stringify(summaryResult)));
  return summaryResult;
};

/**
 * Format clinic name for display
 */
export const formatClinicName = (name: string): string => {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Process all clinic data into summary format
 */
export const processAllClinicsToSummary = (allClinicData: Record<string, any>): ClinicSummary[] => {
  const summaries: ClinicSummary[] = [];
  
  for (const [clinicName, clinicData] of Object.entries(allClinicData)) {
    const summary = processClinicDataToSummary(clinicName, clinicData);
    if (summary) {
      summaries.push(summary);
    }
  }
  
  // Sort by clinic name
  summaries.sort((a, b) => a.clinicName.localeCompare(b.clinicName));
  
  return summaries;
};