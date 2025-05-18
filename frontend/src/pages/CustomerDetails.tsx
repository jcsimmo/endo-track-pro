import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useUserGuardContext } from "app";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, ChevronDown, ChevronRight } from "lucide-react";
import { Cohort, Serial, ChainData } from "utils/cohort-types";
import { fetchZohoData } from "utils/zoho-data";
import { Spinner } from "components/Spinner";
import { XCircle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CohortDetailView } from "components/CohortDetailView";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { toast } from "sonner";

interface OrphanChain {
  lastSerial: Serial;
  chain: Serial[];
  finalStatus: string;
}

export default function CustomerDetails() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useUserGuardContext();
  
  // Get the customer name from URL query params
  const customerName = searchParams.get('customer');
  
  // State for Zoho data
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [customerCohorts, setCustomerCohorts] = useState<Cohort[]>([]);
  null
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // State for orphan scopes
  const [orphanChains, setOrphanChains] = useState<OrphanChain[]>([]);
  const [selectedOrphanId, setSelectedOrphanId] = useState<string | null>(null);
  const [targetCohortId, setTargetCohortId] = useState<string>("");
  const [expandedChains, setExpandedChains] = useState<Record<string, boolean>>({});
  
  // Fetch data on component mount
  useEffect(() => {
    const loadData = async () => {
      // Wrap the state updates that might cause suspension in startTransition
      React.startTransition(() => {
        fetchZohoData(setIsLoading, setError)
          .then(cohortsData => {
            setCohorts(cohortsData);

            if (customerName) {
              const filtered = cohortsData.filter(c =>
                c.customer.toLowerCase() === decodeURIComponent(customerName).toLowerCase());
              setCustomerCohorts(filtered);

              if (filtered.length > 0) {
                // setSelectedCohortId(filtered[0].id); // No longer needed
              }

              processOrphanChains(cohortsData);
            }
          })
          .catch(err => {
            // Error is already handled in fetchZohoData
          });
      });
    };

    loadData();
  }, [customerName]);
  
  // Process orphan chains from all cohorts
  const processOrphanChains = (cohortsData: Cohort[]) => {
    const chains: OrphanChain[] = [];
    
    cohortsData.forEach(cohort => {
      // Skip if no chain data
      if (!cohort.chainData) return;
      
      // Process orphan chains
      cohort.chainData.orphanChains.forEach(chain => {
        // Find all serials in this chain
        const chainSerials = chain.serials
          .map(serialId => cohort.serials.find(s => s.id === serialId))
          .filter((s): s is Serial => s !== undefined);
        
        // Sort by chain position
        chainSerials.sort((a, b) => {
          const posA = a.chainInfo?.chainPosition || 0;
          const posB = b.chainInfo?.chainPosition || 0;
          return posA - posB;
        });
        
        // Get the last serial in the chain
        const lastSerial = chainSerials[chainSerials.length - 1];
        
        if (lastSerial) {
          chains.push({
            lastSerial,
            chain: chainSerials,
            finalStatus: chain.finalStatus
          });
        }
      });
    });
    
    console.log(`Found ${chains.length} orphan chains`);
    setOrphanChains(chains);
  };
  
  // Toggle chain expansion
  const toggleChainExpansion = (serialId: string) => {
    setExpandedChains(prev => ({
      ...prev,
      [serialId]: !prev[serialId]
    }));
  };
  
  // Assign orphan to cohort
  const assignOrphanToCohort = () => {
    if (!selectedOrphanId || !targetCohortId) return;
    
    // Find the selected orphan chain
    const selectedChain = orphanChains.find(chain => chain.lastSerial.id === selectedOrphanId);
    if (!selectedChain) return;
    
    // Find the target cohort
    const targetCohort = customerCohorts.find(c => c.id === targetCohortId);
    if (!targetCohort) return;
    
    // In a real implementation, we would call the backend API to perform the assignment
    // For now, we'll just show a success message
    toast.success(`Assigned serial ${selectedOrphanId} to cohort ${targetCohortId}`, {
      description: `This is a UI demonstration. In the final app, this would update the database.`
    });
    
    // Clear selection
    setSelectedOrphanId(null);
    setTargetCohortId("");
  };
  
  // Function to retry data loading
  const retryLoading = () => {
    setIsLoading(true);
    setError(null);
    
    const loadData = async () => {
      try {
        const cohortsData = await fetchZohoData(setIsLoading, setError);
        setCohorts(cohortsData);
      } catch (err) {
        // Error is already handled in fetchZohoData
      }
    };
    
    loadData();
  };
  
  null
  
  // Calculate customer statistics
  const calculateCustomerStats = () => {
    if (!customerCohorts.length) return { totalCohorts: 0, activeUnits: 0, totalUnits: 0, usedReplacements: 0, totalReplacements: 0 };
    
    return {
      totalCohorts: customerCohorts.length,
      activeUnits: customerCohorts.reduce((sum, c) => sum + c.activeUnits, 0),
      totalUnits: customerCohorts.reduce((sum, c) => sum + c.totalUnits, 0),
      usedReplacements: customerCohorts.reduce((sum, c) => sum + c.replacementsUsed, 0),
      totalReplacements: customerCohorts.reduce((sum, c) => sum + c.replacementsTotal, 0),
    };
  };
  
  const stats = calculateCustomerStats();
  
  // Display loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Spinner className="h-8 w-8 mb-4" />
          <h2 className="text-xl font-medium mb-2">Loading Customer Data</h2>
          <p className="text-muted-foreground">Please wait while we retrieve the latest information...</p>
        </div>
      </div>
    );
  }
  
  // Display error state
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-md">
          <XCircle className="h-12 w-12 text-red-500 mb-4 mx-auto" />
          <h2 className="text-xl font-medium mb-2">Error Loading Data</h2>
          <p className="text-muted-foreground mb-4 whitespace-pre-line">{error}</p>
          <Button 
            onClick={retryLoading}
            variant="outline"
          >
            Try Again
          </Button>
        </div>
      </div>
    );
  }
  
  // Customer not found
  if (!customerName || customerCohorts.length === 0) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-md">
          <XCircle className="h-12 w-12 text-amber-500 mb-4 mx-auto" />
          <h2 className="text-xl font-medium mb-2">Customer Not Found</h2>
          <p className="text-muted-foreground mb-4">The requested customer could not be found or has no cohorts.</p>
          <Button 
            onClick={() => navigate('/dashboard')}
            variant="outline"
          >
            Return to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="py-4 px-6 border-b">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-semibold">EP</span>
            </div>
            <h1 className="text-xl font-semibold">EndoTrack Pro</h1>
          </div>
          <div className="flex items-center space-x-4">
            <Button 
              variant="ghost"
              onClick={() => navigate("/dashboard")}
            >
              Dashboard
            </Button>
            <Button 
              variant="outline"
              onClick={() => navigate("/login")}
            >
              Log Out
            </Button>
          </div>
        </div>
      </header>
      
      <main className="container mx-auto py-8 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center mb-6">
            <Button 
              variant="ghost" 
              className="mr-2" 
              onClick={() => navigate('/dashboard')}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back to Dashboard
            </Button>
          </div>
          
          <div className="mb-8">
            <h1 className="text-3xl font-bold">{customerName}</h1>
            <p className="text-muted-foreground mt-1">
              Customer CSA Plans and Scope Management
            </p>
          </div>
          
          {/* Customer Statistics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card className="bg-white overflow-hidden border-l-4 border-l-primary shadow-sm">
              <CardHeader className="pb-2">
                <CardDescription className="text-gray-600 font-medium">Total CSA Plans</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-gray-800">{stats.totalCohorts}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Active customer service agreements
                </p>
              </CardContent>
            </Card>
            
            <Card className="bg-white overflow-hidden border-l-4 border-l-green-500 shadow-sm">
              <CardHeader className="pb-2">
                <CardDescription className="text-gray-600 font-medium">Units in Field</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-gray-800">{stats.activeUnits}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Out of {stats.totalUnits} total units
                </p>
              </CardContent>
            </Card>
            
            <Card className="bg-white overflow-hidden border-l-4 border-l-amber-500 shadow-sm">
              <CardHeader className="pb-2">
                <CardDescription className="text-gray-600 font-medium">Replacements Used</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-gray-800">{stats.usedReplacements}/{stats.totalReplacements}</div>
                <div className="mt-1">
                  <Progress 
                    value={(stats.usedReplacements / Math.max(1, stats.totalReplacements)) * 100} 
                    className="h-2" 
                  />
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-white overflow-hidden border-l-4 border-l-blue-500 shadow-sm">
              <CardHeader className="pb-2">
                <CardDescription className="text-gray-600 font-medium">Remaining Replacements</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-gray-800">{stats.totalReplacements - stats.usedReplacements}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Available across all plans
                </p>
              </CardContent>
            </Card>
          </div>
          
          <Tabs defaultValue="plans" className="space-y-4">
            <TabsList>
              <TabsTrigger value="plans">CSA Plans</TabsTrigger>
              <TabsTrigger value="orphans">Orphan Scope Management</TabsTrigger>
            </TabsList>
            
            <TabsContent value="plans" className="space-y-4">
              {/* Cohort List Only */}
              <Card className="lg:max-w-md"> {/* Adjusted width */}
                <CardHeader>
                  <CardTitle>CSA Cohorts</CardTitle>
                  <CardDescription>Select a cohort to view details</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {customerCohorts.map(cohort => (
                      <div 
                        key={cohort.id}
                        className={`p-3 rounded-md cursor-pointer transition-colors hover:bg-muted border border-transparent hover:border-primary/50`}
                        onClick={() => navigate(`/CohortDetails?id=${cohort.id}`)}
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-sm">{cohort.id}</p>
                            <div className="flex items-center mt-1">
                              <Badge 
                                variant={cohort.status === 'active' ? 'default' : 
                                  cohort.status === 'maxed' ? 'destructive' : 'outline'}
                                className="text-xs"
                              >
                                {cohort.status}
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <div className="mt-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-muted-foreground">Replacements</span>
                            <span>{cohort.replacementsUsed}/{cohort.replacementsTotal}</span>
                          </div>
                          <Progress value={(cohort.replacementsUsed / cohort.replacementsTotal) * 100} className="h-1" />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="orphans">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Orphan Scopes List - Only showing last scope in each chain */}
                <Card>
                  <CardHeader>
                    <CardTitle>Orphaned Scope Chains</CardTitle>
                    <CardDescription>
                      Scopes without a proper replacement chain
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {orphanChains.length > 0 ? (
                      <div className="space-y-2 max-h-[500px] overflow-y-auto">
                        {orphanChains.map(chain => (
                          <Collapsible 
                            key={chain.lastSerial.id}
                            open={expandedChains[chain.lastSerial.id]}
                            className={`p-3 rounded-md transition-colors border 
                              ${selectedOrphanId === chain.lastSerial.id ? 'bg-primary/10 border-primary' : 'hover:bg-muted'}`}
                          >
                            <div className="flex justify-between items-start">
                              <div 
                                className="flex-1 cursor-pointer"
                                onClick={() => setSelectedOrphanId(chain.lastSerial.id)}
                              >
                                <p className="font-mono text-sm mb-1">{chain.lastSerial.id}</p>
                                <div className="flex justify-between items-center">
                                  <Badge variant="outline" className="text-xs">{chain.lastSerial.model}</Badge>
                                  <Badge variant={chain.finalStatus.includes('Field') ? 'default' : 'secondary'} className="text-xs">
                                    {chain.finalStatus}
                                  </Badge>
                                </div>
                              </div>
                              
                              {chain.chain.length > 1 && (
                                <CollapsibleTrigger
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleChainExpansion(chain.lastSerial.id);
                                  }}
                                  className="ml-2 p-1 hover:bg-muted rounded-full"
                                >
                                  {expandedChains[chain.lastSerial.id] ? 
                                    <ChevronDown className="h-4 w-4" /> : 
                                    <ChevronRight className="h-4 w-4" />
                                  }
                                </CollapsibleTrigger>
                              )}
                            </div>
                            
                            {chain.chain.length > 1 && (
                              <CollapsibleContent className="mt-3">
                                <div className="text-xs text-muted-foreground mb-2">Full replacement chain:</div>
                                <div className="space-y-2 pl-2 border-l-2 border-muted">
                                  {chain.chain.map((serial, index) => (
                                    <div key={serial.id} className="flex items-start">
                                      <div className="flex-1">
                                        <p className="font-mono">{serial.id}</p>
                                        <div className="flex items-center mt-1">
                                          <Badge variant="outline" className="text-xs mr-2">
                                            {index === chain.chain.length - 1 ? 'Current' : 'Replaced'}
                                          </Badge>
                                          {serial.replacementDate && (
                                            <span className="text-xs text-muted-foreground">
                                              {index < chain.chain.length - 1 ? 'Returned' : 'Received'} on {new Date(serial.replacementDate).toLocaleDateString()}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </CollapsibleContent>
                            )}
                          </Collapsible>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center p-6 bg-muted/20 rounded-md border">
                        <p className="text-muted-foreground">No orphaned scopes found</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
                
                {/* Orphan Assignment */}
                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle>Assign to CSA Plan</CardTitle>
                    <CardDescription>
                      Add an orphaned scope chain to an existing CSA plan for this customer
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {selectedOrphanId ? (
                      <div className="space-y-4">
                        <div className="p-4 bg-muted/20 rounded-md border">
                          <h3 className="font-medium mb-2">Selected Scope Chain</h3>
                          
                          {/* Show selected chain details */}
                          {(() => {
                            const selectedChain = orphanChains.find(chain => chain.lastSerial.id === selectedOrphanId);
                            if (!selectedChain) return null;
                            
                            return (
                              <div className="space-y-3">
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  <div className="text-muted-foreground">Final Serial:</div>
                                  <div className="font-mono">{selectedChain.lastSerial.id}</div>
                                  
                                  <div className="text-muted-foreground">Model:</div>
                                  <div>{selectedChain.lastSerial.model}</div>
                                  
                                  <div className="text-muted-foreground">Status:</div>
                                  <div>{selectedChain.finalStatus}</div>
                                  
                                  <div className="text-muted-foreground">Chain Length:</div>
                                  <div>{selectedChain.chain.length} unit{selectedChain.chain.length !== 1 ? 's' : ''}</div>
                                </div>
                                
                                {selectedChain.chain.length > 1 && (
                                  <div className="mt-2 pt-2 border-t">
                                    <p className="text-xs text-muted-foreground mb-1">This chain includes:</p>
                                    <div className="text-xs font-mono pl-2 border-l-2 border-muted">
                                      {selectedChain.chain.map(serial => (
                                        <div key={serial.id} className="mb-1">{serial.id}</div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                        
                        <div className="space-y-3">
                          <h3 className="font-medium">Target CSA Plan</h3>
                          <Select
                            value={targetCohortId}
                            onValueChange={setTargetCohortId}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select a CSA plan" />
                            </SelectTrigger>
                            <SelectContent>
                              {customerCohorts
                                .filter(c => c.status === 'active')
                                .map(cohort => (
                                  <SelectItem key={cohort.id} value={cohort.id}>
                                    {cohort.id} ({cohort.activeUnits}/{cohort.totalUnits} units)
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                          
                          <Button 
                            className="w-full mt-4" 
                            disabled={!targetCohortId}
                            onClick={assignOrphanToCohort}
                          >
                            Assign to Plan
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center p-12 bg-muted/20 rounded-md border border-dashed">
                        <p className="text-muted-foreground mb-4">Select an orphaned scope from the list to assign it to a CSA plan</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
