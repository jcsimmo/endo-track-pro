import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useUserGuardContext } from "app";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Cohort, Serial } from "utils/cohort-types";
import { fetchAggregatedClinicData } from "utils/zoho-data";
import { XCircle, ChevronDown, ChevronRight, AlertTriangle, CheckCircle } from "lucide-react";
import { Spinner } from "components/Spinner";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

// Dashboard statistics calculation
const calculateStats = (cohorts: Cohort[]) => {
  const activeCohorts = cohorts.filter(c => c.status === 'active');
  const totalUnits = cohorts.reduce((sum, c) => sum + c.totalUnits, 0);
  const activeUnits = cohorts.reduce((sum, c) => sum + c.activeUnits, 0);
  const totalReplacements = cohorts.reduce((sum, c) => sum + c.replacementsTotal, 0);
  const usedReplacements = cohorts.reduce((sum, c) => sum + c.replacementsUsed, 0);

  // Find cohort with earliest expiration
  const today = new Date();
  const activeDates = activeCohorts
    .map(c => ({ id: c.id, customer: c.customer, date: new Date(c.endDate) }))
    .filter(d => d.date > today)
    .sort((a, b) => a.date.getTime() - b.date.getTime());

  const nextExpiring = activeDates.length > 0 ? activeDates[0] : null;

  // Calculate cohorts expiring in next 90 days
  const ninetyDaysFromNow = new Date();
  ninetyDaysFromNow.setDate(ninetyDaysFromNow.getDate() + 90);

  const expiringCohorts = activeDates.filter(
    d => d.date <= ninetyDaysFromNow
  );

  return {
    totalCohorts: cohorts.length,
    activeCohorts: activeCohorts.length,
    totalUnits,
    activeUnits,
    totalReplacements,
    usedReplacements,
    nextExpiring,
    expiringCohorts
  };
};

type SortField = 'customer' | 'id' | 'activeUnits' | 'replacementsUsed' | 'endDate';
type SortDirection = 'asc' | 'desc';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useUserGuardContext();

  // State for filtering and sorting
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortField, setSortField] = useState<SortField>("endDate");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [expandedCustomers, setExpandedCustomers] = useState<Record<string, boolean>>({});

  // State for serial number search
  const [serialSearch, setSerialSearch] = useState("");
  const [searchResult, setSearchResult] = useState<{serial: Serial, cohort: Cohort} | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // Function to search for a serial number
  const searchForSerial = () => {
    if (!serialSearch.trim()) return;

    setIsSearching(true);

    // Search for the serial in all cohorts
    let found = false;

    for (const cohort of cohorts) {
      const matchingSerial = cohort.serials.find(serial => 
        serial.id.toLowerCase() === serialSearch.toLowerCase().trim()
      );

      if (matchingSerial) {
        setSearchResult({ serial: matchingSerial, cohort });
        found = true;
        break;
      }
    }

    if (!found) {
      setSearchResult(null);
    }

    setIsSearching(false);
  };

  // State for aggregated clinic data
  const [clinicCohorts, setClinicCohorts] = useState<Record<string, Cohort[]>>({});
  const [selectedClinic, setSelectedClinic] = useState<string>("");
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const clinicNames = Object.keys(clinicCohorts);

  // Fetch data on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchAggregatedClinicData(setIsLoading, setError);
        setClinicCohorts(data);
        const clinics = Object.keys(data);
        if (clinics.length > 0) {
          setSelectedClinic(clinics[0]);
          setCohorts(data[clinics[0]]);
        }
      } catch (err) {
        // Error is already handled in fetchAggregatedClinicData
      }
    };

    loadData();
  }, []);

  // Change selected clinic
  const handleClinicChange = (clinic: string) => {
    setSelectedClinic(clinic);
    setCohorts(clinicCohorts[clinic] || []);
  };

  // Function to retry data loading
  const retryLoading = () => {
    setIsLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        const data = await fetchAggregatedClinicData(setIsLoading, setError);
        setClinicCohorts(data);
        const clinics = Object.keys(data);
        if (clinics.length > 0) {
          setSelectedClinic(clinics[0]);
          setCohorts(data[clinics[0]]);
        } else {
          setCohorts([]);
        }
      } catch (err) {
        // Error is already handled in fetchAggregatedClinicData
      }
    };

    loadData();
  };

  // Calculate dashboard statistics
  const stats = calculateStats(cohorts);

  // Filter cohorts
  const filteredCohorts = cohorts.filter(cohort => {
    // Search term filtering (customer name or cohort ID)
    const matchesSearch = 
      cohort.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cohort.id.toLowerCase().includes(searchTerm.toLowerCase());

    // Status filtering
    const matchesStatus = 
      statusFilter === "all" || 
      cohort.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Sort cohorts
  const sortedCohorts = [...filteredCohorts].sort((a, b) => {
    let comparison = 0;

    switch (sortField) {
      case 'customer':
        comparison = a.customer.localeCompare(b.customer);
        break;
      case 'id':
        comparison = a.id.localeCompare(b.id);
        break;
      case 'activeUnits':
        comparison = a.activeUnits - b.activeUnits;
        break;
      case 'replacementsUsed':
        // Sort by percentage used for better comparison
        const percentageA = a.replacementsUsed / a.replacementsTotal;
        const percentageB = b.replacementsUsed / b.replacementsTotal;
        comparison = percentageA - percentageB;
        break;
      case 'endDate':
        comparison = new Date(a.endDate).getTime() - new Date(b.endDate).getTime();
        break;
      default:
        comparison = 0;
    }

    return sortDirection === 'asc' ? comparison : -comparison;
  });

  // Group cohorts by customer for hierarchy view
  const customerGroups = React.useMemo(() => {
    const groups: Record<string, Cohort[]> = {};

    filteredCohorts.forEach(cohort => {
      if (!groups[cohort.customer]) {
        groups[cohort.customer] = [];
      }
      groups[cohort.customer].push(cohort);
    });

    // Sort customers alphabetically
    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([customer, cohorts]) => ({
        customer,
        cohorts: cohorts.sort((a, b) => a.id.localeCompare(b.id)),
        activeCount: cohorts.filter(c => c.status === 'active').length,
        expiredCount: cohorts.filter(c => c.status === 'expired').length,
        maxedCount: cohorts.filter(c => c.status === 'maxed').length,
        totalUnits: cohorts.reduce((sum, c) => sum + c.totalUnits, 0),
        activeUnits: cohorts.reduce((sum, c) => sum + c.activeUnits, 0)
      }));
  }, [filteredCohorts]);

  // Toggle expansion of a customer in hierarchy view
  const toggleCustomerExpansion = (customer: string) => {
    setExpandedCustomers(prev => ({
      ...prev,
      [customer]: !prev[customer]
    }));
  };

  // Function to get status icon
  const getStatusIcon = (status: 'active' | 'maxed' | 'expired') => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'expired':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      case 'maxed':
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  // Display loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Spinner className="h-8 w-8 mb-4" />
          <h2 className="text-xl font-medium mb-2">Loading Cohort Data</h2>
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
              onClick={() => React.startTransition(() => navigate("/"))}
            >
              Home
            </Button>
            <Button
              variant="outline"
              onClick={() => React.startTransition(() => navigate("/login"))}
            >
              Log Out
            </Button>
          </div>
        </div>
      </header>
      
      <main className="container mx-auto py-8 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
            <div>
              <h1 className="text-4xl font-bold">Dashboard</h1>
              <p className="text-muted-foreground text-xl mt-2">
                Welcome, {user?.displayName || "Jonathan Simmonds"}
              </p>
            </div>
            <div>
              <Button
                variant="outline"
                onClick={() => React.startTransition(() => navigate("/admin"))}
              >
                Admin Access
              </Button>
            </div>
          </div>

          {clinicNames.length > 1 && (
            <Tabs value={selectedClinic} onValueChange={handleClinicChange} className="mb-6">
              <TabsList>
                {clinicNames.map(name => (
                  <TabsTrigger key={name} value={name}>
                    {name}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          )}

          {/* Main Layout */}
          <div className="space-y-6">
            {/* CSA Cohort Management */}
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="text-lg font-medium">CSA Cohort Management</div>
              </div>

              {/* Customer CSA Plans */}
              <Card className="mb-8">
                <CardHeader className="border-b pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle>Customer CSA Plans</CardTitle>
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <Input 
                          placeholder="Search customers or cohorts..." 
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="w-60 pl-9 focus-visible:ring-primary/20 h-9"
                        />
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                          />
                        </svg>
                      </div>
                      
                      <Select
                        value={statusFilter}
                        onValueChange={setStatusFilter}
                      >
                        <SelectTrigger className="w-[140px] h-9">
                          <SelectValue placeholder="All Statuses" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Statuses</SelectItem>
                          <SelectItem value="active">Active</SelectItem>
                          <SelectItem value="maxed">Max Replacements</SelectItem>
                          <SelectItem value="expired">Expired</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="max-h-[600px] overflow-y-auto">
                  {customerGroups.length > 0 ? (
                    <div className="space-y-1">
                      {customerGroups.map(group => (
                        <div key={group.customer} className="border rounded-md overflow-hidden mb-3">
                          <div
                            className="flex w-full items-center justify-between px-4 py-3 hover:bg-muted/30 cursor-pointer"
                            onClick={() => React.startTransition(() => navigate(`/customer-details?customer=${encodeURIComponent(group.customer)}`))}
                          >
                            <div className="flex items-center">
                              <div className="mr-2">
                                <ChevronRight className="h-4 w-4" />
                              </div>
                              <div>
                                <div className="font-medium">{group.customer}</div>
                                <div className="text-xs text-muted-foreground">
                                  {group.cohorts.length} cohort{group.cohorts.length !== 1 ? 's' : ''} · {group.activeUnits} active unit{group.activeUnits !== 1 ? 's' : ''} of {group.totalUnits} total
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="bg-green-50 text-green-700 hover:bg-green-100">
                                {group.activeCount} active
                              </Badge>
                              {group.expiredCount > 0 && (
                                <Badge variant="outline" className="bg-amber-50 text-amber-700 hover:bg-amber-100">
                                  {group.expiredCount} expired
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center p-8 rounded-lg border border-dashed">
                      <p className="text-muted-foreground">No cohorts match your search criteria</p>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Secondary Features in a Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Scope Serial Number Search */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Scope Serial Number Search</CardTitle>
                    <CardDescription>Find CSA information for a specific scope</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex gap-2">
                      <Input 
                        placeholder="Enter serial number..." 
                        value={serialSearch}
                        onChange={(e) => setSerialSearch(e.target.value)}
                        className="flex-1"
                      />
                      <Button 
                        onClick={searchForSerial}
                        disabled={!serialSearch.trim() || isSearching}
                      >
                        {isSearching ? <Spinner className="h-4 w-4 mr-2" /> : null}
                        Search
                      </Button>
                    </div>
                    
                    {searchResult && (
                      <div className="mt-4 p-3 border rounded-md bg-muted/20">
                        <h4 className="font-medium mb-1">Scope Found</h4>
                        <div className="text-sm grid grid-cols-2 gap-x-4 gap-y-1">
                          <div className="text-muted-foreground">Serial #:</div>
                          <div className="font-mono">{searchResult.serial.id}</div>
                          
                          <div className="text-muted-foreground">Status:</div>
                          <div>
                            <Badge variant={searchResult.serial.status === 'active' ? 'default' : searchResult.serial.status === 'replaced' ? 'secondary' : 'outline'}>
                              {searchResult.serial.status}
                            </Badge>
                          </div>
                          
                          <div className="text-muted-foreground">Customer:</div>
                          <div>{searchResult.cohort.customer}</div>
                          
                          <div className="text-muted-foreground">Cohort ID:</div>
                          <div className="font-mono text-xs">{searchResult.cohort.id}</div>
                          
                          <div className="text-muted-foreground">Valid Until:</div>
                          <div>{new Date(searchResult.cohort.endDate).toLocaleDateString()}</div>
                          
                          {searchResult.serial.chainInfo?.isPartOfChain && (
                            <>
                              <div className="text-muted-foreground">Chain Status:</div>
                              <div>
                                <Badge variant={searchResult.serial.chainInfo.chainType === 'validated' ? 'outline' : 'secondary'} className="mr-1">
                                  {searchResult.serial.chainInfo.chainType}
                                </Badge>
                                {searchResult.serial.chainInfo.isLastInChain ? 
                                  <Badge variant="default" className="text-xs">Current</Badge> : 
                                  <Badge variant="outline" className="text-xs">Replaced</Badge>
                                }
                              </div>
                              
                              <div className="text-muted-foreground">Chain Position:</div>
                              <div className="text-xs">
                                Position {searchResult.serial.chainInfo.chainPosition} of {searchResult.serial.chainInfo.chainLength}
                              </div>
                            </>
                          )}
                        </div>
                        <div className="mt-3">
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full"
                            onClick={() => React.startTransition(() => navigate(`/cohort-details?id=${searchResult.cohort.id}`))}
                          >
                            View Full Cohort Details
                          </Button>
                        </div>
                      </div>
                    )}
                    
                    {searchResult === null && serialSearch && !isSearching && (
                      <div className="mt-4 p-3 border rounded-md bg-red-50 text-red-700 text-sm">
                        No scope found with serial number "{serialSearch}"
                      </div>
                    )}
                  </CardContent>
                </Card>
                
                {/* Plans Expiring Soon */}
                {stats.expiringCohorts.length > 0 ? (
                  <Card>
                    <CardHeader className="border-b border-amber-100 bg-amber-50">
                      <div className="flex items-center gap-2">
                        <svg className="h-5 w-5 text-amber-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <CardTitle className="text-lg text-amber-800">Plans Expiring Soon</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-3">
                      <div className="space-y-3">
                        {stats.expiringCohorts.slice(0, 5).map(cohort => {
                          // Find the full cohort object to get customer name
                          const fullCohort = cohorts.find(c => c.id === cohort.id);
                          return (
                            <div key={cohort.id} className="flex items-center justify-between hover:bg-amber-50/50 p-2 rounded-md">
                              <div>
                                <div className="font-medium">{fullCohort?.customer}</div>
                                <div className="font-mono text-xs">{cohort.id}</div>
                              </div>
                              <div className="flex flex-col items-end">
                                <div className="text-amber-600 font-medium">{new Date(cohort.date).toLocaleDateString()}</div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 px-2"
                                  onClick={() => React.startTransition(() => navigate(`/cohort-details?id=${cohort.id}`))}
                                >
                                  Details
                                </Button>
                              </div>
                            </div>
                          );
                        })}
                        {stats.expiringCohorts.length > 5 && (
                          <div className="text-xs text-center text-muted-foreground pt-2 border-t">
                            + {stats.expiringCohorts.length - 5} more expiring in next 90 days
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardHeader>
                      <CardTitle>Plans Expiring Soon</CardTitle>
                      <CardDescription>
                        Monitor upcoming CSA plan expirations
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-8">
                      <p className="text-muted-foreground mb-4">No plans are expiring in the next 90 days</p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}