import React, { useState, useEffect } from "react";
import { useUserGuardContext } from "app";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RefreshCw } from "lucide-react";
// fetchAggregatedClinicData might still be needed to get the list of clinic names
import { fetchAggregatedClinicData, triggerManualSync } from "utils/zoho-data";
// processAllClinicsToSummary and ClinicSummary are replaced by new logic
// import { processAllClinicsToSummary, ClinicSummary } from "utils/clinic-summary";
import { fetchDetailedCustomerData, CustomerPageData } from "utils/customer-data-processing";
import ClinicListItem from "components/ClinicListItem";
import { Spinner } from "components/Spinner";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Calendar } from "lucide-react";

export function Dashboard() {
  const { user } = useUserGuardContext();

  // State for aggregated clinic data
  // const [clinicData, setClinicData] = useState<Record<string, any>>({}); // Raw aggregated data, might still be used for clinic list
  const [clinicNames, setClinicNames] = useState<string[]>([]); // To store just the names
  const [detailedClinicDataList, setDetailedClinicDataList] = useState<CustomerPageData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Sync state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  // Search state
  const [serialSearch, setSerialSearch] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<any | null>(null);

  // Helper function to get expiring cohorts
  const getExpiringCohorts = () => {
    const expiringCohorts: any[] = [];
    const today = new Date();
    
    // Needs to adapt to detailedClinicDataList which contains CustomerPageData objects
    // CustomerPageData.cohorts are CohortDisplayData, which have endDate
    for (const customerPageData of detailedClinicDataList) {
      for (const cohort of customerPageData.cohorts) {
        const endDate = new Date(cohort.endDate);
        const daysUntilExpiration = Math.ceil((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
        
        if (daysUntilExpiration <= 60 && daysUntilExpiration >= 0) {
          expiringCohorts.push({ // Ensure this structure matches what the rendering part expects
            orderId: cohort.orderId, // Assuming CohortDisplayData has orderId
            endDate: cohort.endDate,
            // Add other fields if needed by the expiring cohorts display
            clinicName: customerPageData.customerName,
            daysUntilExpiration
          });
        }
      }
    }
    
    return expiringCohorts.sort((a, b) => a.daysUntilExpiration - b.daysUntilExpiration);
  };

  const expiringCohorts = getExpiringCohorts();

  // Load initial clinic data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setError(null);
      console.log("loadInitialData: Fetching initial list of clinics...");
      // Step 1: Fetch initial data to get clinic names.
      // Assuming fetchAggregatedClinicData returns an object where keys are clinic names
      // or a structure from which names can be extracted.
      // This part might need adjustment based on actual return type of fetchAggregatedClinicData.
      const aggregatedData = await fetchAggregatedClinicData(setIsLoading, setError);
      const names = Object.keys(aggregatedData || {}); // Example: get names from keys
      setClinicNames(names);
      console.log(`loadInitialData: Found ${names.length} clinic names.`);

      if (names.length === 0) {
        setDetailedClinicDataList([]);
        setIsLoading(false);
        return;
      }

      // Step 2: Fetch detailed data for each clinic
      console.log("loadInitialData: Fetching detailed data for each clinic...");
      const detailedDataPromises = names.map(name =>
        fetchDetailedCustomerData(name).catch(e => {
          console.error(`Error fetching detailed data for ${name}:`, e);
          return null; // Return null for failed fetches to not break Promise.all
        })
      );
      
      const results = await Promise.all(detailedDataPromises);
      const successfullyFetchedData = results.filter(data => data !== null) as CustomerPageData[];
      
      // Sort by clinic name (customerName in CustomerPageData)
      successfullyFetchedData.sort((a, b) => a.customerName.localeCompare(b.customerName));
      
      setDetailedClinicDataList(successfullyFetchedData);
      console.log("loadInitialData: Detailed data fetched and processed for all clinics.");

    } catch (err) {
      console.error("Error loading initial data:", err);
      setError(err instanceof Error ? err.message : "Failed to load clinic data");
    } finally {
      setIsLoading(false);
    }
  };

  // Manual sync handler
  const handleManualSync = async () => {
    setIsSyncing(true);
    setSyncMessage(null);
    try {
      console.log("handleManualSync: Starting manual sync");
      const result = await triggerManualSync();
      console.log("handleManualSync: Manual sync result:", result);
      setSyncMessage("Sync completed successfully");
      
      // Refresh the dashboard data after sync - now calls loadInitialData which does the detailed fetch
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait for backend
      await loadInitialData(); // Reload all data
      
    } catch (err) {
      console.error("Manual sync failed:", err);
      setSyncMessage(`Sync failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Serial search handler
  const searchForSerial = async () => {
    if (!serialSearch.trim()) return;
    
    setIsSearching(true);
    setSearchResult(null);
    
    try {
      // Search across all clinics and cohorts
      // Serial search needs to adapt to detailedClinicDataList
      for (const customerPageData of detailedClinicDataList) {
        for (const cohort of customerPageData.cohorts) { // CohortDisplayData
          for (const chain of cohort.allChains) { // ChainInfo
            // Search within the chain's serials
            const serialToSearch = serialSearch.toLowerCase();
            const foundInChain = chain.chain.find(s => s.toLowerCase().includes(serialToSearch));
            if (foundInChain) {
              // Try to find more details about this specific serial if possible,
              // for now, use the first serial of the chain as representative if found.
              // The `status` here is the chain's finalStatus.
              setSearchResult({
                serial: { id: foundInChain, status: chain.finalStatus }, // Simplified serial info
                cohort: {
                  id: cohort.orderId,
                  customer: customerPageData.customerName,
                  endDate: cohort.endDate
                },
                clinic: customerPageData.customerName
              });
              return;
            }
          }
        }
      }
      
      // If no result found, set searchResult to null to show "not found" message
      setSearchResult(null);
    } catch (err) {
      console.error("Error searching for serial:", err);
      setSearchResult(null);
    } finally {
      setIsSearching(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Spinner />
          <p className="mt-4 text-muted-foreground">Loading clinic data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error Loading Data</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadInitialData} className="w-full">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto py-8 px-4">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">CSA Dashboard</h1>
              <p className="text-sm text-gray-600 mt-1">
                Welcome back, {user?.firstName || "User"}
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              {syncMessage && (
                <div className="text-xs text-gray-500 bg-green-50 px-2 py-1 rounded">
                  {syncMessage}
                </div>
              )}
              <Button
                onClick={handleManualSync}
                disabled={isSyncing}
                variant="outline"
                size="sm"
              >
                {isSyncing ? (
                  <>
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Sync Data
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Clinic List */}
          <div className="lg:col-span-2 space-y-4">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Clinic Overview</h2>
              <p className="text-sm text-gray-600">
                {detailedClinicDataList.length} clinic{detailedClinicDataList.length !== 1 ? 's' : ''} with active CSA agreements
              </p>
            </div>
            
            {/* Clinic List */}
            <div className="space-y-3">
              {detailedClinicDataList.length > 0 ? (
                detailedClinicDataList.map((customerData, index) => (
                  // ClinicListItem will now expect CustomerPageData or a compatible structure
                  <ClinicListItem key={`${customerData.customerName}-${index}`} clinic={customerData as any} />
                ))
              ) : (
                <Card className="p-6 text-center">
                  <CardContent>
                    <p className="text-sm text-gray-500">No clinic data available</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-4">
            {/* Expiring Cohorts */}
            {expiringCohorts.length > 0 && (
              <Card className="border-amber-200 bg-amber-50/30">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <CardTitle className="text-sm font-semibold text-amber-800">
                      Cohorts Expiring Soon
                    </CardTitle>
                  </div>
                  <CardDescription className="text-xs text-amber-700">
                    {expiringCohorts.length} cohort{expiringCohorts.length !== 1 ? 's' : ''} expiring within 60 days
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {expiringCohorts.slice(0, 10).map((cohort, index) => (
                      <div key={`${cohort.orderId}-${index}`} className="flex items-center justify-between p-2 bg-white rounded border border-amber-100">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs text-gray-900 truncate">
                            {cohort.orderId}
                          </div>
                          <div className="text-xs text-gray-500 truncate">
                            {cohort.clinicName}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-amber-600" />
                          <span className="text-xs font-medium text-amber-700">
                            {cohort.daysUntilExpiration}d
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  {expiringCohorts.length > 10 && (
                    <div className="text-xs text-center text-amber-600 mt-2 pt-2 border-t border-amber-200">
                      + {expiringCohorts.length - 10} more expiring cohorts
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Serial Search Section */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">Serial Number Search</CardTitle>
                <CardDescription className="text-xs">Find CSA information for a specific scope</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter serial number..."
                    value={serialSearch}
                    onChange={(e) => setSerialSearch(e.target.value)}
                    className="flex-1 text-sm"
                    onKeyPress={(e) => e.key === 'Enter' && searchForSerial()}
                  />
                  <Button
                    onClick={searchForSerial}
                    disabled={!serialSearch.trim() || isSearching}
                    size="sm"
                  >
                    {isSearching ? (
                      <RefreshCw className="h-3 w-3 animate-spin" />
                    ) : (
                      "Search"
                    )}
                  </Button>
                </div>
                
                {searchResult && (
                  <div className="mt-3 p-3 border rounded-md bg-green-50 border-green-200">
                    <h4 className="font-medium text-sm mb-2 text-green-800">Scope Found</h4>
                    <div className="text-xs space-y-1">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Serial:</span>
                        <span className="font-mono text-green-700">{searchResult.serial.id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Status:</span>
                        <Badge variant="outline" className="text-xs">{searchResult.serial.status}</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Cohort:</span>
                        <span className="font-mono text-xs">{searchResult.cohort.id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Clinic:</span>
                        <span className="text-xs">{searchResult.clinic}</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {serialSearch && !searchResult && !isSearching && (
                  <div className="mt-3 p-3 border rounded-md bg-red-50 border-red-200">
                    <p className="text-xs text-red-700">No scope found with serial number "{serialSearch}"</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;