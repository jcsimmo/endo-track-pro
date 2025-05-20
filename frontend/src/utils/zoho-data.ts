import brain from "brain";
import { Cohort } from "./cohort-types";

/**
 * Fetches and processes Zoho data for CSA cohorts
 * @param setIsLoading - Loading state setter function
 * @param setError - Error state setter function 
 * @returns Promise resolving to processed cohort data
 */
export const fetchZohoData = async (
  setIsLoading?: (loading: boolean) => void,
  setError?: (error: string | null) => void
): Promise<Cohort[]> => {
  if (setIsLoading) setIsLoading(true);
  if (setError) setError(null);
  
  try {
    console.log("Starting Zoho data fetch...");
    
    // Step 1: Fetch customer list
    const customersResponse = await brain.list_customers();
    if (!customersResponse.ok) {
      throw new Error(`Failed to fetch customers: ${customersResponse.status} ${customersResponse.statusText}`);
    }
    
    const customersData = await customersResponse.json();
    if (!customersData.customers || customersData.customers.length === 0) {
      throw new Error("No customers found. Please import customer data first.");
    }
    
    // Use the first customer for now
    const customerName = customersData.customers[0].contact_name;
    console.log(`Using customer: ${customerName}`);
    
    // Step 2: Run data extraction
    const extractionResponse = await brain.run_data_extraction({ customer_name: customerName });
    if (!extractionResponse.ok) {
      throw new Error(`Failed to start data extraction: ${extractionResponse.status} ${extractionResponse.statusText}`);
    }
    
    const extractionData = await extractionResponse.json();
    if (!extractionData.task_id) {
      throw new Error("No task ID returned from data extraction");
    }
    
    const taskId = extractionData.task_id;
    console.log("Extraction task started with ID:", taskId);
    
    // Step 3: Poll for task completion
    let taskComplete = false;
    let attempts = 0;
    let jsonKey = null;
    
    while (!taskComplete && attempts < 15) {
      attempts++;
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      
      console.log(`Checking status for task ${taskId}, attempt ${attempts}`);
      
      // Skip API call if taskId is undefined or null
      if (!taskId) {
        console.error("Cannot check task status: Task ID is undefined");
        throw new Error("Task ID is undefined. Cannot check status.");
      }
      
      const statusResponse = await brain.get_task_status({ taskId });
      if (!statusResponse.ok) {
        throw new Error(`Failed to check task status: ${statusResponse.status} ${statusResponse.statusText}`);
      }
      
      const statusData = await statusResponse.json();
      console.log("Status response:", statusData);
      
      if (statusData.status === "completed") {
        taskComplete = true;
        jsonKey = statusData.json_key;
        console.log("Extraction completed. JSON key:", jsonKey);
        if (!jsonKey) {
          console.error("Warning: Task completed but no JSON key was provided");
        }
      } else if (statusData.status === "failed") {
        throw new Error("Data extraction failed: " + (statusData.error || "Unknown error"));
      }
    }
    
    if (!jsonKey) {
      throw new Error("Timed out waiting for data extraction to complete or no JSON key was returned");
    }
    
    console.log("Attempting to download JSON data with key:", jsonKey);
    
    // Step 4: Download the JSON data
    const dataResponse = await brain.download_json({ jsonKey });
    if (!dataResponse.ok) {
      throw new Error(`Failed to download extracted data: ${dataResponse.status} ${dataResponse.statusText}`);
    }
    
    const zohoData = await dataResponse.json();
    
    // Log the data structure for debugging
    console.log("Zoho data structure keys:", Object.keys(zohoData));
    console.log("Has csa_cohorts_final?", !!zohoData.csa_cohorts_final);
    if (zohoData.csa_cohorts_final) {
      console.log("Number of cohorts:", Object.keys(zohoData.csa_cohorts_final).length);
      console.log("Cohort keys:", Object.keys(zohoData.csa_cohorts_final));
    }
    
    // Process the data into our format
    const processedCohorts = processZohoData(zohoData);
    console.log("Processed cohorts:", processedCohorts.length);
    return processedCohorts;
  } catch (err) {
    console.error("Error fetching Zoho data:", err);
    const errorMessage = `${err instanceof Error ? err.message : String(err)}\n\nPlease try again or contact support if this issue persists.`;
    if (setError) setError(errorMessage);
    throw err;
  } finally {
    if (setIsLoading) setIsLoading(false);
  }
};

/**
 * Process Zoho data into our Cohort format
 */
export const processZohoData = (data: any): Cohort[] => {
  console.log("Processing Zoho data:", data);
  
  if (!data) {
    console.error("No data provided to processZohoData");
    return [];
  }
  
  // Check if we have the expected csa_cohorts_final structure
  if (data.csa_cohorts_final) {
    // Process using the expected structure
    return processCSACohorts(data);
  }
  
  // If we don't have csa_cohorts_final, check if we have salesorders and salesreturns
  if (data.salesorders || data.salesreturns) {
    console.log("Using salesorders/salesreturns data structure");
    // Process using the salesorders/salesreturns structure
    return processSalesData(data);
  }
  
  console.error("Unknown data structure. Available keys:", Object.keys(data));
  return [];
};

/**
 * Process data with the expected CSA cohorts structure
 */
const processCSACohorts = (data: any): Cohort[] => {
  if (!data.csa_cohorts_final) {
    return [];
  }
  
  const cohorts: Cohort[] = [];
  
  // Process each cohort in the data
  for (const [cohortId, cohortData] of Object.entries<any>(data.csa_cohorts_final)) {
    const summary = cohortData.summary || {};
    const customerName = data.customer_name || "Unknown Customer";
    
    // Extract start and end dates
    const startDate = summary.startDate || "";
    const endDate = summary.endDate || "";
    
    // Process chains to get serials
    const validatedChains = cohortData.validated_chains || [];
    const orphanChains = cohortData.assigned_orphan_chains_data || [];
    const allChains = [...validatedChains, ...orphanChains];
    
    // Count active units
    const activeUnits = allChains.filter(chain => 
      chain && chain.final_status === 'inField'
    ).length;
    
    // Count total units
    const totalUnits = allChains.length;
    
    // Get replacements info
    const totalReplacements = summary.initialReplacements || 0;
    const usedReplacements = totalReplacements - (summary.remainingReplacements || 0);
    
    // Determine status
    let status: 'active' | 'maxed' | 'expired' = 'active';
    if (summary.remainingReplacements <= 0) {
      status = 'maxed';
    } else if (new Date(endDate) < new Date()) {
      status = 'expired';
    }
    
    // Process serials
    const serials = [];
    
    // Helper to extract shipping instance data
    const getInstanceData = (instanceKey: string) => {
      const instances = data.shipmentInstanceMap || {};
      return instances[instanceKey] || {};
    };
    
    // Process all chains to extract serials
    allChains.forEach(chain => {
      if (!chain || !chain.chain || !Array.isArray(chain.chain)) {
        console.log("Skipping invalid chain:", chain);
        return;
      }
      
      // Get the last (current) instance in the chain
      const finalInstanceKey = chain.chain[chain.chain.length - 1];
      const finalInstance = getInstanceData(finalInstanceKey);
      
      if (finalInstance) {
        const serialNumber = finalInstance.serial;
        const model = finalInstance.model || "Unknown";
        
        console.log("Processing chain with serial:", serialNumber, "model:", model);
        
        // For each previous item in the chain (if exists), those are replacements
        if (chain.chain.length > 1) {
          // Add previous serials (replaced ones)
          for (let i = 0; i < chain.chain.length - 1; i++) {
            const instanceKey = chain.chain[i];
            const instance = getInstanceData(instanceKey);
            if (instance && instance.serial) {
              // Get replacement date from the next item's shipment date
              const nextInstanceKey = chain.chain[i + 1];
              const nextInstance = getInstanceData(nextInstanceKey);
              const replacementDate = nextInstance?.originalShipmentDate || null;
              
              console.log("Adding replaced serial:", instance.serial);
              
              serials.push({
                id: instance.serial,
                model: instance.model || "Unknown",
                status: 'replaced',
                replacementDate
              });
            }
          }
        }
        
        // Add current active serial
        if (serialNumber) {
          console.log("Adding active serial:", serialNumber);
          
          serials.push({
            id: serialNumber,
            model,
            status: chain.final_status === 'inField' ? 'active' : 'retired',
            replacementDate: null
          });
        }
      }
    });
    
    // Log the serials we've collected
    console.log(`Cohort ${cohortId} has ${serials.length} serials:`, serials.map(s => s.id));
    
    // Create the cohort object
    cohorts.push({
      id: cohortId,
      customer: customerName,
      totalUnits,
      activeUnits,
      replacementsUsed: usedReplacements,
      replacementsTotal: totalReplacements,
      startDate,
      endDate,
      status,
      serials
    });
  }
  
  return cohorts;
};

/**
 * Process data with salesorders and salesreturns structure
 */
/**
 * Process data with salesorders and salesreturns structure based on step2.txt algorithm
 */
const processSalesData = (data: any): Cohort[] => {
  const salesOrders = data.salesorders || data.sales_orders || [];
  const salesReturns = data.salesreturns || data.sales_returns || [];
  const customerName = data.customer?.contact_name || "Unknown Customer";
  
  console.log(`Processing data for customer: ${customerName}`);
  console.log(`Found ${salesOrders.length} SOs, ${salesReturns.length} SRs.`);
  
  // Prepare to track all endoscope shipments
  const TARGET_ENDOSCOPE_SKU = 'P313N00';
  const shipmentInstanceMap: Record<string, any> = {};
  const shipmentEvents: any[] = [];
  const allSerialNumbers = new Set<string>();

  // --- Step 1: Extract All Shipments for the Target SKU ---
  console.log("Extracting shipment events for endoscopes...");
  for (const so of salesOrders) {
    const soNumber = so.salesorder_number;
    
    // Extract from packages
    const packages = so.packages || [];
    for (const pkg of packages) {
      // Get package identifier
      const pkgNumber = pkg.package_number || (pkg.shipment_order?.shipment_number);
      if (!pkgNumber) continue;
      
      // Determine best date
      let dateStr = null;
      let date = null;
      // Try different date fields in order of preference
      const dateSources = [
        pkg.shipment_order?.delivery_date,
        pkg.delivery_date,
        pkg.shipment_order?.shipment_date,
        pkg.shipment_date,
        so.date
      ];
      
      for (const source of dateSources) {
        if (source && typeof source === 'string' && !['not shipped', 'not recorded', '', 'n/a'].includes(source.toLowerCase().trim())) {
          dateStr = source;
          try {
            // Simple date parsing - would be more robust in production
            date = new Date(source);
            if (!isNaN(date.getTime())) break;
          } catch (e) {
            console.warn(`Could not parse date: ${source}`);
          }
        }
      }
      
      // Process detailed line items in package
      const detailedLines = pkg.detailed_line_items || [];
      for (const line of detailedLines) {
        if (line.sku === TARGET_ENDOSCOPE_SKU) {
          let serials = line.serial_numbers || [];
          // Handle single string or array
          if (!Array.isArray(serials)) {
            serials = serials ? [String(serials).trim()] : [];
          } else {
            serials = serials.map((s: any) => String(s).trim()).filter(Boolean);
          }
          
          // Record event for each serial
          for (const sn of serials) {
            allSerialNumbers.add(sn);
            shipmentEvents.push({
              date,
              dateStr,
              soNumber,
              packageNumber: pkgNumber,
              serial: sn,
              sku: TARGET_ENDOSCOPE_SKU
            });
          }
        }
      }
    }
    
    // Also check line items directly for serial numbers (sometimes not in packages)
    const lineItems = so.line_items || [];
    for (const item of lineItems) {
      if (item.sku === TARGET_ENDOSCOPE_SKU) {
        // Check for serials in various places
        let serials = item.serial_numbers || [];
        
        // Convert to array if string
        if (!Array.isArray(serials)) {
          serials = serials ? [String(serials).trim()] : [];
        } else {
          serials = serials.map((s: any) => String(s).trim()).filter(Boolean);
        }
        
        // Sometimes serials are in custom fields
        if (serials.length === 0 && item.custom_field_hash) {
          const customFields = item.custom_field_hash;
          const serialField = Object.keys(customFields).find(key => 
            key.toLowerCase().includes('serial'));
          
          if (serialField && customFields[serialField]) {
            const serialValue = customFields[serialField];
            if (serialValue) {
              serials = Array.isArray(serialValue) ? serialValue : [serialValue];
            }
          }
        }
        
        // Use the SO date since we don't have package-specific date
        const date = new Date(so.date);
        
        // Record each serial
        for (const sn of serials) {
          if (!sn) continue;
          allSerialNumbers.add(sn);
          shipmentEvents.push({
            date,
            dateStr: so.date,
            soNumber,
            packageNumber: "NO_PACKAGE", // Placeholder
            serial: sn,
            sku: TARGET_ENDOSCOPE_SKU
          });
        }
      }
    }
  }
  
  console.log(`Extracted ${shipmentEvents.length} shipment events for ${allSerialNumbers.size} serial numbers`);
  
  // --- Step 2: Initialize the Shipment Instance Map ---
  for (const event of shipmentEvents) {
    const sn = event.serial;
    const soNum = event.soNumber;
    const pkgNum = event.packageNumber;
    
    if (!sn || !soNum || !pkgNum) {
      console.warn("Skipping shipment event due to missing key info:", event);
      continue;
    }
    
    // In step2.txt, instance_key is a tuple (sn, so_num, pkg_num)
    // In JavaScript, we'll use a string with a unique separator unlikely to appear in the values
    const instanceKey = `${sn}|||${soNum}|||${pkgNum}`;
    
    // Avoid duplicates
    if (shipmentInstanceMap[instanceKey]) continue;
    
    shipmentInstanceMap[instanceKey] = {
      instanceKey,
      serial: sn,
      soNumber: soNum,
      packageNumber: pkgNum,
      currentStatus: 'inField', // Initial status
      replacedBy: null,
      replacedScope: null,
      cohort: null, // Will be filled in later
      shipDate: event.dateStr,
      shipDateObj: event.date,
      model: TARGET_ENDOSCOPE_SKU
    };
  }
  
  console.log(`Initialized ${Object.keys(shipmentInstanceMap).length} shipment instances`);

  // --- Step 3: Process Returns to Mark Replacements ---
  const returnEvents: any[] = [];
  const processedReturns = new Set<string>(); // Track processed return serials
  
  for (const ret of salesReturns) {
    const rmaNumber = ret.salesreturn_number;
    
    // Try to find receipt records
    const receiptFields = ['salesreturnreceives', 'return_receipts', 'receipts'];
    let receipts: any[] = [];
    
    for (const field of receiptFields) {
      if (ret[field] && Array.isArray(ret[field])) {
        receipts = ret[field];
        break;
      }
    }
    
    for (const receipt of receipts) {
      // Get return date
      let date = null;
      try {
        if (receipt.date) date = new Date(receipt.date);
      } catch (e) {
        console.warn(`Could not parse return date: ${receipt.date}`);
      }
      
      // Skip invalid dates
      if (!date || isNaN(date.getTime())) continue;
      
      // Check line items for serials
      for (const line of (receipt.line_items || [])) {
        let serials = line.serial_numbers || [];
        
        // Ensure consistent format
        if (!Array.isArray(serials)) {
          serials = serials ? [String(serials).trim()] : [];
        } else {
          serials = serials.map((s: any) => String(s).trim()).filter(Boolean);
        }
        
        // Record returns for each endoscope serial
        for (const sn of serials) {
          if (!sn || processedReturns.has(sn)) continue;
          
          // Only process return if we have a shipment for this serial
          if (allSerialNumbers.has(sn)) {
            processedReturns.add(sn);
            returnEvents.push({
              date,
              dateStr: date.toISOString().split('T')[0],
              rmaNumber,
              serial: sn,
              replacedScope: null, // Will be set when matching replacements
              replacedBy: null     // Will be set when matching replacements
            });
          }
        }
      }
    }
  }
  
  console.log(`Extracted ${returnEvents.length} return events`);
  
  // --- Process replacement relationships ---
  // Sort return events by date to establish chronology
  returnEvents.sort((a, b) => a.date.getTime() - b.date.getTime());
  
  // Look for replacements (a return followed closely by a shipment of another scope)
  // This is a simplified approach to match the step2.txt algorithm's logic
  for (const retEvent of returnEvents) {
    if (retEvent.replacedBy) continue; // Already processed
    
    // Find all shipment instances for this serial
    const returnedSerial = retEvent.serial;
    const relatedInstances = Object.values(shipmentInstanceMap).filter(
      (instance: any) => instance.serial === returnedSerial
    );
    
    // Skip if no instances found
    if (relatedInstances.length === 0) continue;
    
    // Get the instance keys and mark them as returned
    for (const instance of relatedInstances) {
      // Skip if already processed
      if (instance.currentStatus !== 'inField') continue;
      
      // Mark as returned
      instance.currentStatus = 'returned';
      instance.rmaDate = retEvent.dateStr;
      instance.rmaDateObj = retEvent.date;
      
      // Find a potential replacement - the next scope shipped after this return
      // within a reasonable timeframe (e.g., 90 days)
      const cutoffDate = new Date(retEvent.date);
      cutoffDate.setDate(cutoffDate.getDate() + 90); // 90 day window
      
      // Find replacements that shipped after this return but before cutoff
      const potentialReplacements = Object.values(shipmentInstanceMap).filter(
        (replacement: any) =>
          // Different serial number
          replacement.serial !== returnedSerial &&
          // Same cohort
          replacement.cohort === instance.cohort &&
          // Shipped after the return but within cutoff
          replacement.shipDateObj > retEvent.date &&
          replacement.shipDateObj < cutoffDate &&
          // Not already a replacement for something else
          !replacement.replacedScope &&
          // Currently in field (not yet returned itself)
          replacement.currentStatus === 'inField'
      );
      
      // Sort by ship date to get the earliest replacement
      potentialReplacements.sort((a: any, b: any) => 
        a.shipDateObj.getTime() - b.shipDateObj.getTime()
      );
      
      // Connect the replacement relationship if found
      if (potentialReplacements.length > 0) {
        const replacement = potentialReplacements[0];
        
        // Update the return event
        retEvent.replacedBy = replacement.instanceKey;
        
        // Update the returned instance
        instance.replacedBy = replacement.instanceKey;
        
        // Update the replacement instance
        replacement.replacedScope = instance.instanceKey;
        
        console.log(`Found replacement: ${returnedSerial} returned on ${retEvent.dateStr} replaced by ${replacement.serial} shipped on ${replacement.shipDate}`);
      }
    }
  }

  // --- Step 4: Identify CSA Cohorts ---
  const csaCohorts: any[] = [];
  
  // CSA keywords to identify cohort orders
  const csaKeywords = ['hifcsa-1yr', 'hifcsa-2yr'];
  const csaNameKeywords = ['csa', 'prepaid'];
  
  for (const so of salesOrders) {
    const soNum = so.salesorder_number;
    const lines = so.line_items || [];
    
    // Skip if no line items
    if (!Array.isArray(lines)) continue;
    
    // Check if this SO has CSA line items
    let hasCSA = false;
    let csaLength = "Unknown";
    
    for (const item of lines) {
      if (!item) continue;
      
      const sku = (item.sku || '').toLowerCase();
      const name = (item.name || '').toLowerCase();
      
      // Check for CSA indicators - Match exactly how step2.txt does it
      // Check SKU for explicit CSA keywords
      const isCSASku = csaKeywords.some(k => sku.includes(k));
      // Check name for general CSA keywords - need ALL keywords to match
      const isCSAName = csaNameKeywords.every(k => name.includes(k));
      
      if (isCSASku || isCSAName) {
        hasCSA = true;
        
        // Determine length from name or SKU
        if (name.includes('2 year') || sku.includes('2yr')) {
          csaLength = "2 year";
        } else if ((name.includes('1 year') || sku.includes('1yr')) && csaLength !== "2 year") {
          csaLength = "1 year";
        }
      }
    }
    
    if (!hasCSA) continue; // Skip if not a CSA order
    
    // Find target endoscope instances for this SO
    const cohortInstanceKeys: string[] = [];
    const shipDates: Date[] = [];
    let foundTargetSku = false;
    
    // Look through packages first
    for (const pkg of (so.packages || [])) {
      const pkgNum = pkg.package_number;
      
      // Get valid date for this package
      let pkgDate = null;
      const dateSources = [
        pkg.shipment_order?.delivery_date,
        pkg.delivery_date,
        pkg.shipment_order?.shipment_date,
        pkg.shipment_date
      ];
      
      for (const source of dateSources) {
        if (source && typeof source === 'string') {
          try {
            pkgDate = new Date(source);
            if (!isNaN(pkgDate.getTime())) break;
          } catch (e) {}
        }
      }
      
      // Process line items in this package
      for (const line of (pkg.detailed_line_items || [])) {
        if (line.sku === TARGET_ENDOSCOPE_SKU) {
          foundTargetSku = true;
          
          let serials = line.serial_numbers || [];
          if (!Array.isArray(serials)) {
            serials = serials ? [String(serials).trim()] : [];
          } else {
            serials = serials.map((s: any) => String(s).trim()).filter(Boolean);
          }
          
          for (const sn of serials) {
            if (!sn || !pkgNum) continue;
            
            const instanceKey = `${sn}|||${soNum}|||${pkgNum}`;
            
            // Add to cohort if instance exists
            if (shipmentInstanceMap[instanceKey]) {
              cohortInstanceKeys.push(instanceKey);
              if (pkgDate) shipDates.push(pkgDate);
            }
          }
        }
      }
    }
    
    // Also check line items directly
    for (const item of (so.line_items || [])) {
      if (item.sku === TARGET_ENDOSCOPE_SKU) {
        foundTargetSku = true;
        
        // Check for serials in various places
        let serials = item.serial_numbers || [];
        
        // Convert to array if string
        if (!Array.isArray(serials)) {
          serials = serials ? [String(serials).trim()] : [];
        } else {
          serials = serials.map((s: any) => String(s).trim()).filter(Boolean);
        }
        
        // Sometimes serials are in custom fields
        if (serials.length === 0 && item.custom_field_hash) {
          const customFields = item.custom_field_hash;
          const serialField = Object.keys(customFields).find(key => 
            key.toLowerCase().includes('serial'));
          
          if (serialField && customFields[serialField]) {
            const serialValue = customFields[serialField];
            if (serialValue) {
              serials = Array.isArray(serialValue) ? serialValue : [serialValue];
            }
          }
        }
        
        // Add all found serials to cohort
        for (const sn of serials) {
          if (!sn) continue;
          
          // Look for this serial in the shipment map
          // Use a placeholder package ID since we don't have one
          const instanceKey = `${sn}|||${soNum}|||NO_PACKAGE`;
          
          if (shipmentInstanceMap[instanceKey]) {
            cohortInstanceKeys.push(instanceKey);
            // Use SO date since we don't have package date
            const date = new Date(so.date);
            if (!isNaN(date.getTime())) shipDates.push(date);
          }
        }
      }
    }
    
    // Only create cohort if it had target endoscope
    if (!foundTargetSku) continue;
    
    // Determine cohort start date from earliest package date
    let startDate: Date | null = null;
    if (shipDates.length > 0) {
      startDate = new Date(Math.min(...shipDates.map(d => d.getTime())));
    } else {
      // Fall back to SO date
      try {
        startDate = new Date(so.date);
        if (isNaN(startDate.getTime())) startDate = null;
      } catch (e) {
        startDate = null;
      }
    }
    
    // Calculate end date based on CSA length
    let endDate: Date | null = null;
    if (startDate && csaLength !== "Unknown") {
      endDate = new Date(startDate);
      if (csaLength === "1 year") {
        endDate.setFullYear(endDate.getFullYear() + 1);
      } else if (csaLength === "2 year") {
        endDate.setFullYear(endDate.getFullYear() + 2);
      }
    }
    
    // Initial scope count and allowed replacements
    const initialScopesCount = cohortInstanceKeys.length;
    const totalReplacementsAllowed = initialScopesCount * 4; // Ensure 4 per scope as in step2.txt
    
    // Build cohort object
    const cohortInfo = {
      orderId: soNum,
      startDate: startDate ? startDate.toISOString().split('T')[0] : null,
      startDateObj: startDate,
      csaScopeInstanceKeys: cohortInstanceKeys,
      initialScopeCount: initialScopesCount,
      totalReplacements: totalReplacementsAllowed,
      remainingReplacements: totalReplacementsAllowed,
      csaLength: csaLength,
      endDate: endDate ? endDate.toISOString().split('T')[0] : null,
      endDateObj: endDate
    };
    
    csaCohorts.push(cohortInfo);
    
    // Update shipmentInstanceMap to mark the cohort assignment
    for (const key of cohortInstanceKeys) {
      if (shipmentInstanceMap[key]) {
        shipmentInstanceMap[key].cohort = soNum;
      }
    }
  }
  
  // Sort cohorts by start date
  csaCohorts.sort((a, b) => {
    // Sort null dates to the end
    if (!a.startDateObj && !b.startDateObj) return 0;
    if (!a.startDateObj) return 1;
    if (!b.startDateObj) return -1;
    return a.startDateObj.getTime() - b.startDateObj.getTime();
  });
  
  console.log(`Identified ${csaCohorts.length} CSA cohorts`);

  // --- Step 5: Convert to our Cohort format ---
  const cohorts: Cohort[] = [];
  
  // Build replacement chains for each cohort
  for (const cohort of csaCohorts) {
    const cohortId = cohort.orderId;
    
    // Track chains and their detailed info
    const validatedChains: any[] = [];
    const orphanChains: any[] = [];
    
    // Process all instance keys to find chains
    for (const startInstanceKey of cohort.csaScopeInstanceKeys) {
      const startInstance = shipmentInstanceMap[startInstanceKey];
      if (!startInstance) continue;
      
      // Skip if already part of a chain
      if (startInstance.processed) continue;
      
      // Start building a chain from this instance
      const chain: string[] = [startInstanceKey];
      const handoffs: any[] = [];
      let currentKey = startInstanceKey;
      let finalStatus = 'In Field'; // Default status
      
      // Mark as processed
      startInstance.processed = true;
      
      // Follow the chain of replacements
      while (shipmentInstanceMap[currentKey]?.replacedBy) {
        const currentInstance = shipmentInstanceMap[currentKey];
        const replacementKey = currentInstance.replacedBy;
        const replacementInstance = shipmentInstanceMap[replacementKey];
        
        if (!replacementInstance) break;
        
        // Add to chain
        chain.push(replacementKey);
        
        // Record handoff details
        handoffs.push({
          returnedSerial: currentInstance.serial,
          returnDate: currentInstance.rmaDate,
          replacementSerial: replacementInstance.serial,
          replacementShipDate: replacementInstance.shipDate
        });
        
        // Move to the next in chain
        currentKey = replacementKey;
        
        // Mark as processed
        replacementInstance.processed = true;
      }
      
      // Determine final status of the chain
      const finalInstance = shipmentInstanceMap[currentKey];
      if (finalInstance.currentStatus === 'returned') {
        // If the final scope was also returned but has no replacement, mark accordingly
        finalStatus = 'Returned (No Replacement Found)';
      }
      
      // Add this chain to validated chains
      validatedChains.push({
        chain,
        handoffs,
        finalStatus,
        startSerial: startInstance.serial,
        finalSerial: finalInstance.serial
      });
    }
    
    // Now let's find orphan chains (scopes that have no known starting point but were in returns)
    // These are chains that start with a scope that was not in the original cohort
    // but could be speculatively assigned to this cohort
    const cohortInstanceSet = new Set(cohort.csaScopeInstanceKeys);
    
    const potentialOrphans = Object.values(shipmentInstanceMap).filter((instance: any) => 
      // Not already in a chain
      !instance.processed &&
      // Either has the same cohort or no cohort assigned
      (instance.cohort === cohortId || !instance.cohort) &&
      // Has no replacement parent (it's a starting point)
      !instance.replacedScope
    );
    
    for (const orphanStart of potentialOrphans) {
      if (orphanStart.processed) continue;
      
      // Build the orphan chain
      const chain: string[] = [orphanStart.instanceKey];
      const handoffs: any[] = [];
      let currentKey = orphanStart.instanceKey;
      let finalStatus = orphanStart.currentStatus === 'returned' ? 
                       'Returned & Replaced' : 'In Field';
      
      // Mark as processed
      orphanStart.processed = true;
      
      // Follow the chain of replacements
      while (shipmentInstanceMap[currentKey]?.replacedBy) {
        const currentInstance = shipmentInstanceMap[currentKey];
        const replacementKey = currentInstance.replacedBy;
        const replacementInstance = shipmentInstanceMap[replacementKey];
        
        if (!replacementInstance) break;
        
        // Add to chain
        chain.push(replacementKey);
        
        // Record handoff details
        handoffs.push({
          returnedSerial: currentInstance.serial,
          returnDate: currentInstance.rmaDate,
          replacementSerial: replacementInstance.serial,
          replacementShipDate: replacementInstance.shipDate
        });
        
        // Move to the next in chain
        currentKey = replacementKey;
        
        // Mark as processed
        replacementInstance.processed = true;
      }
      
      // Add orphan chain
      orphanChains.push({
        chain,
        handoffs,
        finalStatus,
        startSerial: orphanStart.serial,
        initialShipDate: orphanStart.shipDate,
        finalSerial: shipmentInstanceMap[currentKey].serial
      });
    }
    
    // Now convert to our Cohort format with chain information
    const startDate = cohort.startDate || '';
    const endDate = cohort.endDate || '';
    
    // Get all serials for this cohort with their status
    const serials: Serial[] = [];
    const processedSerials = new Set<string>(); // To avoid duplicates
    
    // Process chains to build serials list
    for (const chainInfo of [...validatedChains, ...orphanChains]) {
                  // Add isOrphan flag for proper chain type identification
                  const isOrphan = orphanChains.includes(chainInfo);
      for (const instanceKey of chainInfo.chain) {
        const instance = shipmentInstanceMap[instanceKey];
        if (!instance) continue;
        
        const serialNumber = instance.serial;
        if (!serialNumber || processedSerials.has(serialNumber)) continue;
        processedSerials.add(serialNumber);
        
        // Determine status based on chain position and return status
        let status: 'active' | 'replaced' | 'retired' = 'active';
        let replacementDate = null;
        
        // If it's in a chain but not the last one, it was replaced
        const isLastInChain = instanceKey === chainInfo.chain[chainInfo.chain.length - 1];
        
        if (!isLastInChain) {
          status = 'replaced';
          
          // Find the handoff that has this serial as the returned one
          const handoff = chainInfo.handoffs.find(h => h.returnedSerial === serialNumber);
          if (handoff) {
            replacementDate = handoff.returnDate;
          }
        } 
        // If it's the last in chain but returned with no replacement
        else if (instance.currentStatus === 'returned') {
          status = 'retired';
          replacementDate = instance.rmaDate;
        }
        
        serials.push({
          id: serialNumber,
          model: instance.model || TARGET_ENDOSCOPE_SKU,
          status,
          replacementDate,
          // Add chain visualization info
          chainInfo: {
            isPartOfChain: chainInfo.chain.length > 1,
            isLastInChain,
            chainLength: chainInfo.chain.length,
            chainPosition: chainInfo.chain.indexOf(instanceKey) + 1,
            chainType: isOrphan ? 'orphan' : 'validated'
          }
        });
      }
    }
    
    // Count active units - include both validated and orphaned active units
    const activeUnits = serials.filter(s => s.status === 'active').length;
    
    console.log(`Cohort ${cohortId}: Found ${activeUnits} active units out of ${serials.length} total units`);
    
    // Determine cohort status
    let status: 'active' | 'maxed' | 'expired' = 'active';
    if (cohort.remainingReplacements <= 0) {
      status = 'maxed';
    } else if (cohort.endDateObj && cohort.endDateObj < new Date()) {
      status = 'expired';
    }
    
    // Store chain visualization data
    const chainData = {
      validatedChains: validatedChains.map(vc => ({
        serials: vc.chain.map(key => shipmentInstanceMap[key]?.serial).filter(Boolean),
        handoffs: vc.handoffs,
        finalStatus: vc.finalStatus
      })),
      orphanChains: orphanChains.map(oc => ({
        serials: oc.chain.map(key => shipmentInstanceMap[key]?.serial).filter(Boolean),
        handoffs: oc.handoffs,
        finalStatus: oc.finalStatus,
        initialShipDate: oc.initialShipDate
      }))
    };
    
    // Create cohort
    cohorts.push({
      id: cohortId,
      customer: customerName,
      totalUnits: serials.length,
      activeUnits,
      replacementsUsed: cohort.totalReplacements - cohort.remainingReplacements,
      replacementsTotal: cohort.totalReplacements,
      startDate,
      endDate,
      status,
      serials,
      chainData // Add chain data for visualization
    });
  }
  
  return cohorts;
};

/**
 * Fetch aggregated clinic CSA data from the public directory
 */
export const fetchAggregatedClinicData = async (
  setIsLoading?: (loading: boolean) => void,
  setError?: (error: string | null) => void
): Promise<Record<string, Cohort[]>> => {
  if (setIsLoading) setIsLoading(true);
  if (setError) setError(null);

  try {
    const response = await fetch('/all_clinics_aggregated_csa_data.json');
    if (!response.ok) {
      throw new Error(`Failed to fetch aggregated data: ${response.status} ${response.statusText}`);
    }
    const rawData = await response.json();
    const result: Record<string, Cohort[]> = {};
    for (const [clinicName, clinicData] of Object.entries<any>(rawData)) {
      result[clinicName] = processZohoData(clinicData);
    }
    return result;
  } catch (err) {
    if (setError) setError(err instanceof Error ? err.message : String(err));
    throw err;
  } finally {
    if (setIsLoading) setIsLoading(false);
  }
};
