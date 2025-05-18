import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useUserGuardContext } from "app";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { ChevronLeft } from "lucide-react";
import { CohortDetailView, CohortEmptyState } from "components/CohortDetailView";
import { Cohort } from "utils/cohort-types";
import { fetchZohoData } from "utils/zoho-data";
import { Spinner } from "components/Spinner";
import { Progress } from "@/components/ui/progress";
import { XCircle } from "lucide-react";

export default function CohortDetails() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useUserGuardContext();
  
  // Get the cohort ID from URL query params
  const cohortId = searchParams.get('id');
  
  // State for Zoho data
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Fetch data on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const cohortsData = await fetchZohoData(setIsLoading, setError);
        setCohorts(cohortsData);
      } catch (err) {
        // Error is already handled in fetchZohoData
      }
    };
    
    loadData();
  }, []);
  
  // Find the selected cohort
  const selectedCohort = cohortId ? cohorts.find(c => c.id === cohortId) : null;
  
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
            <h1 className="text-3xl font-bold">Cohort Details</h1>
            <p className="text-muted-foreground mt-1">
              {selectedCohort 
                ? `Viewing details for ${selectedCohort.customer} - ${selectedCohort.id}` 
                : "Select a cohort from the dashboard to view details"}
            </p>
          </div>
          
          {selectedCohort && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Card className="bg-white overflow-hidden border-l-4 border-l-primary shadow-sm">
                <CardHeader className="pb-2">
                  <CardDescription className="text-gray-600 font-medium">Agreement Period</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold text-gray-800">{new Date(selectedCohort.startDate).getFullYear()}-{new Date(selectedCohort.endDate).getFullYear()}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(selectedCohort.startDate).toLocaleDateString()} - {new Date(selectedCohort.endDate).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-white overflow-hidden border-l-4 border-l-green-500 shadow-sm">
                <CardHeader className="pb-2">
                  <CardDescription className="text-gray-600 font-medium">Units in Field</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold text-gray-800">{selectedCohort.activeUnits}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Out of {selectedCohort.totalUnits} total units
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-white overflow-hidden border-l-4 border-l-amber-500 shadow-sm">
                <CardHeader className="pb-2">
                  <CardDescription className="text-gray-600 font-medium">Replacements Used</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold text-gray-800">{selectedCohort.replacementsUsed}/{selectedCohort.replacementsTotal}</div>
                  <div className="mt-1">
                    <Progress 
                      value={(selectedCohort.replacementsUsed / Math.max(1, selectedCohort.replacementsTotal)) * 100} 
                      className="h-2" 
                    />
                  </div>
                </CardContent>
              </Card>
              
              <Card className="bg-white overflow-hidden border-l-4 border-l-blue-500 shadow-sm">
                <CardHeader className="pb-2">
                  <CardDescription className="text-gray-600 font-medium">Days Remaining</CardDescription>
                </CardHeader>
                <CardContent>
                  {(() => {
                    const endDate = new Date(selectedCohort.endDate);
                    const today = new Date();
                    const daysRemaining = Math.ceil((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                    return (
                      <>
                        <div className="text-2xl font-semibold text-gray-800">{daysRemaining > 0 ? daysRemaining : 0}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {daysRemaining > 0 ? "Days until expiration" : "Plan has expired"}
                        </p>
                      </>
                    );
                  })()}
                </CardContent>
              </Card>
            </div>
          )}
          
          {selectedCohort ? (
            <div className="space-y-6">
              <CohortDetailView cohort={selectedCohort} />
              
              {/* Orphan Assignment Section */}
              <Card>
                <CardHeader>
                  <CardTitle>Orphan Scope Assignment</CardTitle>
                  <CardDescription>
                    Assign orphaned scopes to this customer's CSA plan
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-muted/20 p-4 rounded-md mb-4 border">
                    <p className="text-sm text-muted-foreground">Orphaned scopes are those that have been identified in your inventory but are not yet assigned to any CSA plan. Assigning them to this customer's plan will include them in replacement tracking.</p>
                  </div>
                  <div className="text-center py-4">
                    <p className="text-muted-foreground mb-4">Orphan management features coming soon</p>
                    <Button variant="outline" disabled>Assign Orphaned Scopes</Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card className="p-8">
              <CohortEmptyState />
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
