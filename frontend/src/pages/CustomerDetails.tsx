import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/extensions/shadcn/components/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/extensions/shadcn/components/accordion";
import { Badge } from "@/extensions/shadcn/components/badge";
import { Alert, AlertDescription, AlertTitle } from "@/extensions/shadcn/components/alert";
import { Skeleton } from "@/extensions/shadcn/components/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/extensions/shadcn/components/tooltip";
import brain from "brain"; // This might need to be passed to fetchDetailedCustomerData if not global
import { ArrowLeft, Info, ChevronDown, ChevronRight } from 'lucide-react';
import {
  fetchDetailedCustomerData,
  transformStep2DataToCustomerPageData, // Though fetchDetailedCustomerData calls this internally
  CustomerPageData,
  // Import other interfaces if directly used in this file's rendering, e.g. ChainInfo, CohortDisplayData
  ChainInfo,
  CohortDisplayData,
  OrphanInfo,
  ScopeDetail
} from 'utils/customer-data-processing';

// ScopeStatusBadge component (Plan 4.1.4)
const ScopeStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  let variant: "default" | "destructive" | "outline" | "secondary" = "default";
  let statusText = status;

  if (status.toLowerCase().includes('in field')) {
    variant = "default";
    statusText = "In Field";
  } else if (status.toLowerCase().includes('returned') && status.toLowerCase().includes('no replacement')) {
    variant = "destructive";
    statusText = "Returned (No Replacement)";
  } else if (status.toLowerCase().includes('returned_replaced')) {
    variant = "secondary";
    statusText = "Returned (Replaced)";
  } else {
    variant = "outline";
  }

  return <Badge variant={variant} className="whitespace-nowrap">{statusText}</Badge>;
};

// Functions fetchDetailedCustomerData (formerly fetchCustomerDataByCustomerName)
// and transformStep2DataToCustomerPageData are now imported from 'utils/customer-data-processing'

const CustomerDetailsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const customerNameQueryParam = searchParams.get('customer');

  const [customerData, setCustomerData] = useState<CustomerPageData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedChains, setExpandedChains] = useState<Set<string>>(new Set());

  const toggleChainDetails = (chainId: string) => {
    setExpandedChains(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chainId)) {
        newSet.delete(chainId);
      } else {
        newSet.add(chainId);
      }
      return newSet;
    });
  };

  useEffect(() => {
    if (customerNameQueryParam) {
      const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
          const data = await fetchDetailedCustomerData(customerNameQueryParam); // Use imported function
          setCustomerData(data);
        } catch (e: any) {
          setError(e.message || "Failed to fetch customer data.");
        } finally {
          setLoading(false);
        }
      };
      loadData();
    } else {
      setError("No customer specified in URL.");
      setLoading(false);
    }
  }, [customerNameQueryParam]);

  if (loading) {
    return (
      <div className="container mx-auto p-4 space-y-4">
        <Skeleton className="h-12 w-1/2" />
        <Skeleton className="h-8 w-1/4" />
        <Card>
          <CardHeader><Skeleton className="h-8 w-3/4" /></CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!customerData) {
    return (
      <div className="container mx-auto p-4">
        <Alert>
          <AlertTitle>No Data</AlertTitle>
          <AlertDescription>Customer data could not be loaded for "{customerNameQueryParam}".</AlertDescription>
        </Alert>
      </div>
    );
  }

  // Calculate summary counts for display
  const totalInFieldScopes = customerData.cohorts.reduce((sum, cohort) => sum + cohort.inFieldScopeCount, 0);
  
  // Calculate total returned scopes (count individual scopes that were returned, not just chains)
  const totalReturnedScopes = customerData.cohorts.reduce((sum, cohort) => {
    return sum + cohort.allChains.reduce((chainSum, chain) => {
      if (!chain.finalStatus.toLowerCase().includes('in field')) {
        // Count the number of scopes in the chain (chain.chain.length)
        return chainSum + (chain.chain?.length || 1);
      }
      // For in-field chains, count all returned scopes in the chain except the final one
      return chainSum + Math.max(0, (chain.chain?.length || 1) - 1);
    }, 0);
  }, 0);
  const totalOrphanedScopesGlobal = customerData.orphanedScopesGlobal.length;

  // New calculations for "Total Endoscopes Under Plan"
  const activeCohorts = customerData.cohorts.filter(cohort => !(new Date(cohort.endDate) < new Date()));
  const expiredCohorts = customerData.cohorts.filter(cohort => new Date(cohort.endDate) < new Date());

  const activeInFieldFromCohorts = activeCohorts.reduce((sum, cohort) => sum + cohort.inFieldScopeCount, 0);
  const expiredInFieldFromCohorts = expiredCohorts.reduce((sum, cohort) => sum + cohort.inFieldScopeCount, 0);

  const inFieldGlobalOrphans = customerData.orphanedScopesGlobal.filter(
    orphan => orphan.status && orphan.status.toLowerCase().includes('in field')
  ).length;

  const totalActiveScopesGreen = activeInFieldFromCohorts + inFieldGlobalOrphans;
  const totalExpiredScopesRed = expiredInFieldFromCohorts;

  // New calculation for "Total Endoscopes in Customer's possession"
  const totalScopesInPossession = totalActiveScopesGreen + totalOrphanedScopesGlobal + totalExpiredScopesRed;

  return (
    <div className="container mx-auto p-2 space-y-4">
      <div className="my-4"> {/* Changed mb-4 to my-4 for consistent vertical spacing */}
        <Link to="/dashboard" className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 hover:underline"> {/* Changed to="/dashboard" */}
          <ArrowLeft className="mr-1 h-4 w-4" />
          Return to Dashboard
        </Link>
      </div>
      {/* Customer Header */}
      <Card>
        <CardHeader className="p-4">
          <CardTitle className="text-xl">{customerData.customerName}</CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            <div>
              <span className="font-semibold">Total Endoscopes Under Plan:</span>
              <div className="text-base">
                <span className="text-green-600">{totalActiveScopesGreen}</span>
                <span className="text-gray-600"> (Expired: </span>
                <span className="text-red-600">{totalExpiredScopesRed}</span>
                <span className="text-gray-600">)</span>
              </div>
            </div>
            <div>
              <span className="font-semibold">Total Endoscopes in Customer's possession:</span>
              <div className="text-base text-blue-600">{totalScopesInPossession}</div>
              <div className="text-xs text-gray-500 mt-1">
                <div>Scopes under CSA plan: <span className="text-green-600">{totalActiveScopesGreen}</span></div>
                <div>Scopes with expired CSA plan: <span className="text-red-600">{totalExpiredScopesRed}</span></div>
                <div>Scopes never part of CSA plan: <span className="text-orange-600">{totalOrphanedScopesGlobal}</span></div>
              </div>
            </div>
            <div>
              <span className="font-semibold">Total Returned Scopes:</span>
              <div className="text-base text-gray-600">{totalReturnedScopes}</div>
            </div>
            <div>
              <span className="font-semibold">Global Orphans:</span>
              <div className="text-base text-orange-600">{totalOrphanedScopesGlobal}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cohorts Section */}
      {customerData.cohorts
        .sort((a, b) => {
          // Sort active cohorts before expired ones
          const aExpired = new Date(a.endDate) < new Date();
          const bExpired = new Date(b.endDate) < new Date();
          if (aExpired !== bExpired) {
            return aExpired ? 1 : -1; // Active (not expired) first
          }
          // Within the same category, sort by order ID
          return a.orderId.localeCompare(b.orderId);
        })
        .map((cohort, cohortIndex) => {
        const isExpired = new Date(cohort.endDate) < new Date();
        const inFieldChains = cohort.allChains.filter(c => c.finalStatus.toLowerCase().includes('in field'));
        const returnedChains = cohort.allChains.filter(c => !c.finalStatus.toLowerCase().includes('in field'));
        
        // Calculate total returned scopes for this cohort
        const returnedScopesCount = cohort.allChains.reduce((sum, chain) => {
          if (!chain.finalStatus.toLowerCase().includes('in field')) {
            // Count all scopes in fully returned chains
            return sum + (chain.chain?.length || 1);
          }
          // For in-field chains, count all returned scopes except the final one
          return sum + Math.max(0, (chain.chain?.length || 1) - 1);
        }, 0);
        
        // Calculate warning logic for approaching return limit (percentage-based)
        const totalReplacements = cohort.totalCSASlots;
        const remainingReturns = totalReplacements - returnedScopesCount;
        const usagePercentage = totalReplacements > 0 ? (returnedScopesCount / totalReplacements) * 100 : 0;
        const shouldShowWarning = usagePercentage >= 80 && remainingReturns > 0; // Show warning when 80% or more returns used

        return (
          <Card key={`${cohort.orderId}-${cohort.sku}-${cohortIndex}`} className={isExpired ? 'border-red-500 border-2' : ''}>
            <CardHeader className="p-4">
              <div className="flex justify-between items-start">
                <CardTitle>Cohort: {cohort.orderId} ({cohort.sku})</CardTitle>
                {isExpired && <Badge variant="destructive">EXPIRED</Badge>}
              </div>
              <div className="text-sm text-muted-foreground grid grid-cols-1 md:grid-cols-3 gap-2">
                <span>
                  Returns: {returnedScopesCount}/{totalReplacements}
                  {shouldShowWarning && (
                    <span className="ml-2 text-orange-600 font-medium">
                      ({remainingReturns} more allowed)
                    </span>
                  )}
                </span>
                <span>Start: {cohort.startDate} | End: {cohort.endDate}</span>
                <span>Warning: {cohort.warningDate}</span>
              </div>
              <div className="flex gap-2 text-sm mt-2">
                <Badge variant="default" className="bg-green-100 text-green-800">In-Field: {cohort.inFieldScopeCount}</Badge>
                <Badge variant="outline" className="bg-gray-100 text-gray-800">Returned Scopes: {returnedScopesCount}</Badge>
                <Badge variant="secondary">CSA Length: {cohort.csaLength}</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-4">
              <Accordion type="multiple" defaultValue={inFieldChains.length > 0 ? [`in-field-${cohortIndex}`] : []}>
                {/* In-Field Scopes */}
                {inFieldChains.length > 0 && (
                  <AccordionItem value={`in-field-${cohortIndex}`}>
                    <AccordionTrigger className="text-green-700 font-semibold py-2">
                      In-Field Scopes ({inFieldChains.length})
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-1">
                        {inFieldChains.map((scope, scopeIndex) => {
                          console.log(`🎨 DEBUG: Rendering scope ${scope.chain[0]} - isOrphan: ${scope.isOrphan}`);
                          const chainId = `infield-${cohort.orderId}-${cohort.sku}-${scopeIndex}`;
                          const isExpanded = expandedChains.has(chainId);
                          return (
                            <div key={chainId}>
                              <div
                                className={`flex items-center justify-between p-2 border rounded cursor-pointer hover:bg-gray-50 ${scope.isOrphan ? 'bg-blue-50 border-blue-300' : 'bg-white'}`}
                                style={scope.isOrphan ? {backgroundColor: '#dbeafe', borderColor: '#93c5fd'} : {}}
                                onClick={() => toggleChainDetails(chainId)}
                              >
                                <div className="flex items-center flex-grow">
                                  {isExpanded ? <ChevronDown className="h-4 w-4 mr-2" /> : <ChevronRight className="h-4 w-4 mr-2" />}
                                  <span className="font-mono text-sm">
                                    {scope.chain.join(' → ')} ({scope.displaySku})
                                  </span>
                                  {scope.isOrphan && (
                                    <TooltipProvider>
                                      <Tooltip delayDuration={300}>
                                        <TooltipTrigger asChild>
                                          <Info className="h-4 w-4 ml-2 text-blue-600 cursor-pointer" />
                                        </TooltipTrigger>
                                        <TooltipContent className="w-80">
                                          <p className="font-semibold">Assigned Orphan Scope</p>
                                          <p className="text-xs text-muted-foreground">
                                            This scope chain was not part of the original CSA order but has been programmatically linked to this cohort.
                                          </p>
                                          {scope.assignmentReason && (
                                            <p className="text-xs mt-1">
                                              <span className="font-medium">Assignment Reason:</span> {scope.assignmentReason}
                                            </p>
                                          )}
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  )}
                                </div>
                                <div className="ml-2"> {/* Ensure badge doesn't get squished */}
                                  <ScopeStatusBadge status={scope.finalStatus} />
                                </div>
                              </div>
                              {isExpanded && (
                                <div className="p-2 mt-1 border-l-2 border-gray-200 ml-3 bg-gray-25">
                                  <p className="text-xs text-gray-700">Detailed scope information for: {scope.chain.join(' → ')}</p>
                                  {/* Placeholder for detailed scope rendering */}
                                  {scope.detailedScopes && scope.detailedScopes.length > 0 ? (
                                    scope.detailedScopes.map((detail, detailIndex) => (
                                      <div key={detailIndex} className="p-2 my-2 border rounded bg-white text-xs">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                                          <p><strong>Serial:</strong> {detail.serial}</p>
                                          <p><strong>Status:</strong> {detail.status}</p>
                                          {detail.salesOrder && <p><strong>Sales Order:</strong> {detail.salesOrder}</p>}
                                          {detail.salesOrderDate && <p><strong>Order Date:</strong> {detail.salesOrderDate}</p>}
                                          {detail.packageNumber && <p><strong>Package:</strong> {detail.packageNumber}</p>}
                                          {detail.shipmentNumber && <p><strong>Shipment:</strong> {detail.shipmentNumber}</p>}
                                          {detail.shipmentDate && <p><strong>Shipped:</strong> {detail.shipmentDate}</p>}
                                          {detail.deliveryStatus && <p><strong>Delivery Status:</strong> {detail.deliveryStatus}</p>}
                                          {detail.carrier && <p><strong>Carrier:</strong> {detail.carrier}</p>}
                                          {detail.rmaNumber && <p><strong>RMA:</strong> {detail.rmaNumber}</p>}
                                          {detail.rmaDate && <p><strong>RMA Date:</strong> {detail.rmaDate}</p>}
                                        </div>
                                        {detail.productName && (
                                          <p className="mt-1 text-gray-600"><strong>Product:</strong> {detail.productName}</p>
                                        )}
                                        {detail.itemSku && (
                                          <p className="mt-1 text-gray-600"><strong>SKU:</strong> {detail.itemSku}</p>
                                        )}
                                        {detail.itemCustomerName && (
                                          <p className="mt-1 text-gray-600"><strong>Customer (SO):</strong> {detail.itemCustomerName}</p>
                                        )}
                                        {detail.trackingNumber && (
                                          <div className="mt-1">
                                            <strong>Tracking:</strong>
                                            {detail.trackingUrl ? (
                                              <a
                                                href={detail.trackingUrl}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="ml-1 text-blue-600 hover:text-blue-800 underline"
                                              >
                                                {detail.trackingNumber}
                                              </a>
                                            ) : (
                                              <span className="ml-1">{detail.trackingNumber}</span>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-xs text-gray-500 italic">No detailed scope data available for this chain yet.</p>
                                  )}
                                  {scope.handoffs.length > 0 && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                      <strong>Handoffs:</strong>
                                      {scope.handoffs.map((handoff, i) => (
                                        <div key={i}>• {handoff}</div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )}

                {/* Returned Scopes */}
                {returnedChains.length > 0 && (
                  <AccordionItem value={`returned-${cohortIndex}`}>
                    <AccordionTrigger className="text-gray-600 font-semibold py-2 text-sm">
                      Returned Scope Chains ({returnedChains.length})
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-1 opacity-75"> {/* Greyed out effect */}
                        {returnedChains.map((scope, scopeIndex) => {
                          console.log(`🎨 DEBUG: Rendering returned scope ${scope.chain[0]} - isOrphan: ${scope.isOrphan}`);
                          const chainId = `returned-${cohort.orderId}-${cohort.sku}-${scopeIndex}`;
                          const isExpanded = expandedChains.has(chainId);
                          return (
                            <div key={chainId}>
                              <div
                                className={`flex items-center justify-between p-1.5 border rounded text-sm cursor-pointer hover:bg-gray-100 ${scope.isOrphan ? 'bg-blue-50 border-blue-200' : 'bg-gray-50'}`}
                                style={scope.isOrphan ? {backgroundColor: '#dbeafe', borderColor: '#93c5fd'} : {}}
                                onClick={() => toggleChainDetails(chainId)}
                              >
                                <div className="flex items-center flex-grow">
                                  {isExpanded ? <ChevronDown className="h-3 w-3 mr-1.5" /> : <ChevronRight className="h-3 w-3 mr-1.5" />}
                                  <span className="font-mono text-xs"> {/* Smaller text */}
                                    {scope.chain.join(' → ')} ({scope.displaySku})
                                  </span>
                                  {scope.isOrphan && (
                                    <TooltipProvider>
                                      <Tooltip delayDuration={300}>
                                        <TooltipTrigger asChild>
                                          <Info className="h-3 w-3 ml-1.5 text-blue-500 cursor-pointer" />
                                        </TooltipTrigger>
                                        <TooltipContent className="w-80">
                                          <p className="font-semibold">Assigned Orphan Scope</p>
                                          <p className="text-xs text-muted-foreground">
                                            This scope chain was not part of the original CSA order but has been programmatically linked to this cohort.
                                          </p>
                                          {scope.assignmentReason && (
                                            <p className="text-xs mt-1">
                                              <span className="font-medium">Assignment Reason:</span> {scope.assignmentReason}
                                            </p>
                                          )}
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  )}
                                </div>
                                <div className="ml-2"> {/* Ensure badge doesn't get squished */}
                                 <ScopeStatusBadge status={scope.finalStatus} />
                                </div>
                              </div>
                              {isExpanded && (
                                <div className="p-1.5 mt-1 border-l-2 border-gray-200 ml-2.5 bg-gray-25 text-xs">
                                  <p className="text-xs text-gray-600">Detailed scope information for: {scope.chain.join(' → ')}</p>
                                  {/* Placeholder for detailed scope rendering */}
                                  {scope.detailedScopes && scope.detailedScopes.length > 0 ? (
                                    scope.detailedScopes.map((detail, detailIndex) => (
                                      <div key={detailIndex} className="p-2 my-1 border rounded bg-white text-xs">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                                          <p><strong>Serial:</strong> {detail.serial}</p>
                                          <p><strong>Status:</strong> {detail.status}</p>
                                          {detail.salesOrder && <p><strong>Sales Order:</strong> {detail.salesOrder}</p>}
                                          {detail.salesOrderDate && <p><strong>Order Date:</strong> {detail.salesOrderDate}</p>}
                                          {detail.packageNumber && <p><strong>Package:</strong> {detail.packageNumber}</p>}
                                          {detail.shipmentNumber && <p><strong>Shipment:</strong> {detail.shipmentNumber}</p>}
                                          {detail.shipmentDate && <p><strong>Shipped:</strong> {detail.shipmentDate}</p>}
                                          {detail.deliveryStatus && <p><strong>Delivery Status:</strong> {detail.deliveryStatus}</p>}
                                          {detail.carrier && <p><strong>Carrier:</strong> {detail.carrier}</p>}
                                          {detail.rmaNumber && <p><strong>RMA:</strong> {detail.rmaNumber}</p>}
                                          {detail.rmaDate && <p><strong>RMA Date:</strong> {detail.rmaDate}</p>}
                                        </div>
                                        {detail.productName && (
                                          <p className="mt-1 text-gray-600"><strong>Product:</strong> {detail.productName}</p>
                                        )}
                                        {detail.itemSku && (
                                          <p className="mt-1 text-gray-600"><strong>SKU:</strong> {detail.itemSku}</p>
                                        )}
                                        {detail.itemCustomerName && (
                                          <p className="mt-1 text-gray-600"><strong>Customer (SO):</strong> {detail.itemCustomerName}</p>
                                        )}
                                        {detail.trackingNumber && (
                                          <div className="mt-1">
                                            <strong>Tracking:</strong>
                                            {detail.trackingUrl ? (
                                              <a
                                                href={detail.trackingUrl}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="ml-1 text-blue-600 hover:text-blue-800 underline"
                                              >
                                                {detail.trackingNumber}
                                              </a>
                                            ) : (
                                              <span className="ml-1">{detail.trackingNumber}</span>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-xs text-gray-400 italic">No detailed scope data available for this chain yet.</p>
                                  )}
                                  {scope.handoffs.length > 0 && (
                                    <div className="text-xs text-muted-foreground mt-0.5">
                                      <strong>Handoffs:</strong>
                                      {scope.handoffs.map((handoff, i) => (
                                        <div key={i}>• {handoff}</div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )}
              </Accordion>
            </CardContent>
          </Card>
        );
      })}

      {/* Orphaned Scopes Section - For truly unassigned orphans */}
      {customerData.orphanedScopesGlobal.length > 0 && (
        <Card>
          <CardHeader className="p-4">
            <CardTitle>Unassigned Orphaned Scopes ({customerData.orphanedScopesGlobal.length})</CardTitle>
            <p className="text-xs text-muted-foreground">These scopes could not be automatically assigned to a CSA cohort due to capacity constraints or other reasons.</p>
          </CardHeader>
          <CardContent className="p-4">
            <Accordion type="single" collapsible defaultValue="global-orphans">
              <AccordionItem value="global-orphans">
                <AccordionTrigger className="text-orange-700 py-2">
                  View Unassigned Orphaned Scopes
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2">
                    {customerData.orphanedScopesGlobal.map((orphan, orphanIndex) => (
                      <div key={`global-orphan-${orphanIndex}-${orphan.serial}`} className="flex items-center justify-between p-3 border rounded bg-orange-50 border-orange-200">
                        <div className="flex-grow">
                          <div className="font-mono text-sm font-semibold">
                            {orphan.chain ? orphan.chain.join(' → ') : orphan.serial} ({orphan.sku})
                          </div>
                           {orphan.initialShipDate && (
                            <div className="text-xs text-muted-foreground mt-1">
                              Shipped: {orphan.initialShipDate}
                            </div>
                          )}
                          {orphan.handoffs && orphan.handoffs.length > 0 && (
                                <div className="text-xs text-muted-foreground mt-1">
                                  {orphan.handoffs.map((handoff, i) => (
                                    <div key={`go-h-${i}`}>• {handoff}</div>
                                  ))}
                                </div>
                          )}
                          {orphan.assignmentReason && (
                            <div className="text-xs text-orange-700 mt-2 p-2 bg-orange-100 rounded">
                              <span className="font-medium">Assignment Issue:</span> {orphan.assignmentReason}
                            </div>
                          )}
                        </div>
                        <div className="ml-3">
                          <ScopeStatusBadge status={orphan.status} />
                        </div>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CustomerDetailsPage;
