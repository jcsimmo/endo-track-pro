import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Cohort } from "utils/cohort-types";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";

interface Props {
  cohort: Cohort;
  isSelected: boolean;
  onClick: () => void;
}

export function CohortCard({ cohort, isSelected, onClick }: Props) {
  return (
    <div 
      className={`p-3 rounded-md cursor-pointer transition-colors ${isSelected ? 'bg-primary/10 border-l-4 border-primary' : 'hover:bg-muted'}`}
      onClick={onClick}
    >
      <div className="flex justify-between items-start">
        <div>
          <p className="font-medium">{cohort.customer}</p>
          <p className="text-sm font-mono text-muted-foreground">{cohort.id}</p>
        </div>
        <Badge variant={cohort.status === 'active' ? 'default' : cohort.status === 'maxed' ? 'destructive' : 'outline'}>
          {cohort.status === 'active' ? 'Active' : cohort.status === 'maxed' ? 'Max Replacements' : cohort.status}
        </Badge>
      </div>
      <div className="mt-2">
        <div className="flex justify-between text-sm mb-1">
          <span>Replacements Used</span>
          <span className="font-medium">{cohort.replacementsUsed}/{cohort.replacementsTotal}</span>
        </div>
        <Progress value={(cohort.replacementsUsed / cohort.replacementsTotal) * 100} className="h-2" />
      </div>
    </div>
  );
}

interface CohortListProps {
  cohorts: Cohort[];
  selectedCohortId: string | null;
  onSelectCohort: (id: string) => void;
}

type SortField = 'customer' | 'id' | 'startDate' | 'replacementsUsed';
type SortDirection = 'asc' | 'desc';

export function CohortList({ cohorts, selectedCohortId, onSelectCohort }: CohortListProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("startDate");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  
  // Check if we have any cohorts to display
  const hasCohorts = cohorts.length > 0;
  
  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if already sorting by this field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field and default to ascending
      setSortField(field);
      setSortDirection('asc');
    }
  };
  
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
      case 'startDate':
        comparison = new Date(a.startDate).getTime() - new Date(b.startDate).getTime();
        break;
      case 'replacementsUsed':
        // Sort by percentage used for better comparison
        const aPercentage = a.replacementsUsed / a.replacementsTotal;
        const bPercentage = b.replacementsUsed / b.replacementsTotal;
        comparison = aPercentage - bPercentage;
        break;
    }
    
    return sortDirection === 'asc' ? comparison : -comparison;
  });
  
  // Render sort indicator
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    
    return (
      <span className="ml-1">
        {sortDirection === 'asc' ? '↑' : '↓'}
      </span>
    );
  };
  
  if (!hasCohorts) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cohorts</CardTitle>
          <CardDescription>No cohorts available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-8 text-center bg-muted/20 rounded-lg border border-dashed flex flex-col items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-muted-foreground mb-4">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <h3 className="text-lg font-medium mb-2">No CSA Cohorts</h3>
            <p className="text-muted-foreground text-center mb-4">
              There are no Customer Service Agreement cohorts in the system yet.
            </p>
            <Button variant="outline">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
                <path d="M5 12h14" />
                <path d="M12 5v14" />
              </svg>
              Import CSA Data
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cohorts</CardTitle>
        <CardDescription>Select a cohort to view details</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Input 
            placeholder="Search cohorts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="mb-2"
          />
          
          <Select
            value={statusFilter}
            onValueChange={setStatusFilter}
          >
            <SelectTrigger>
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="maxed">Max Replacements</SelectItem>
              <SelectItem value="expired">Expired</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <div className="text-xs text-muted-foreground border-b pb-1 flex justify-between">
          <button
            className={`font-medium hover:text-foreground ${sortField === 'customer' ? 'text-foreground' : ''}`}
            onClick={() => toggleSort('customer')}
          >
            Customer <SortIndicator field="customer" />
          </button>
          <button
            className={`font-medium hover:text-foreground ${sortField === 'replacementsUsed' ? 'text-foreground' : ''}`}
            onClick={() => toggleSort('replacementsUsed')}
          >
            Usage <SortIndicator field="replacementsUsed" />
          </button>
        </div>
        
        <div className="space-y-2">
          {sortedCohorts.length > 0 ? (
            sortedCohorts.map(cohort => (
              <CohortCard
                key={cohort.id}
                cohort={cohort}
                isSelected={selectedCohortId === cohort.id}
                onClick={() => onSelectCohort(cohort.id)}
              />
            ))
          ) : (
            <div className="p-4 text-center text-muted-foreground bg-muted/20 rounded-lg">
              No cohorts match your search criteria
            </div>
          )}
        </div>
      </CardContent>
      <CardFooter>
        <p className="text-sm text-muted-foreground">
          {sortedCohorts.length === cohorts.length
            ? `Total: ${cohorts.length} cohorts`
            : `Showing ${sortedCohorts.length} of ${cohorts.length} cohorts`
          }
        </p>
      </CardFooter>
    </Card>
  );
}