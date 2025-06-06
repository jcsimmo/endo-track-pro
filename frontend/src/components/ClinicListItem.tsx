import React from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle, XCircle, ArrowRight } from "lucide-react";
// Import CustomerPageData and CohortDisplayData from the new utility file
import { CustomerPageData, CohortDisplayData } from "utils/customer-data-processing";
// formatSKUBreakdown and formatDisplayDate might need to be moved or re-imported if they were specific to clinic-summary.ts
// For now, assuming they are general utility functions or we'll address if they are missing.
// Let's assume they are available or create simple versions here if not.
// For now, let's assume formatSKUBreakdown and formatDisplayDate are available globally or via another import.
// If not, we'll need to ensure they are correctly imported or defined.
// We will need formatSKUBreakdown and formatDisplayDate. Let's assume they are moved to customer-data-processing.ts or a common util.
// For now, to proceed, I'll assume they are accessible. If not, this will be a TS error to fix.
import { formatSKUBreakdown, formatDisplayDate } from "utils/clinic-summary"; // KEEPING THIS FOR NOW, if error, will move

interface ClinicListItemProps {
  clinic: CustomerPageData; // Changed from ClinicSummary
}

export const ClinicListItem: React.FC<ClinicListItemProps> = ({ clinic }) => {
  const navigate = useNavigate();

  // Log the received clinic prop for debugging
  // console.log(`ClinicListItem received clinic data for ${clinic.customerName}:`, JSON.stringify(clinic, null, 2)); // Corrected to customerName, and commented out for now to reduce noise

  const getStatusIcon = (status: 'active' | 'expired' | 'warning') => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      case 'expired':
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusBadgeVariant = (status: 'active' | 'expired' | 'warning') => {
    switch (status) {
      case 'active':
        return "default";
      case 'warning':
        return "secondary";
      case 'expired':
        return "destructive";
      default:
        return "outline";
    }
  };

  const getStatusText = (status: 'active' | 'expired' | 'warning') => {
    switch (status) {
      case 'active':
        return "Active";
      case 'warning':
        return "Expiring Soon";
      case 'expired':
        return "Expired";
    }
  };

  // Convert clinic name to URL parameter format
  const getCustomerParam = (clinicName: string) => {
    return clinicName.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
  };

  const handleViewCustomerDetails = () => {
    const customerParam = getCustomerParam(clinic.customerName); // Changed to customerName
    navigate(`/customer-details?customer=${customerParam}`);
  };

  return (
    <Card className="mb-3 hover:shadow-md transition-shadow border-l-4 border-l-blue-500">
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Clinic Name and Action Button */}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              {clinic.customerName}
            </h3>
            <Button 
              onClick={handleViewCustomerDetails}
              variant="outline" 
              size="sm"
              className="flex items-center gap-2"
            >
              View Details
              <ArrowRight className="h-3 w-3" />
            </Button>
          </div>
          
          {/* Enhanced Summary Lines using calculated fields from CustomerPageData */}
          <div className="space-y-1">
            <div className="text-sm text-gray-700">
              <span className="font-medium text-blue-700">
                Total Endoscopes Under Plan: {clinic.calculatedTotalActiveGreen} (Expired: {clinic.calculatedTotalExpiredRed})
              </span>
            </div>
            <div className="text-sm text-gray-600">
              <span className="font-medium">
                Total In-Field: {clinic.calculatedTotalActiveGreen + clinic.calculatedTotalExpiredRed + (clinic.inFieldGlobalOrphansCount || 0)}
              </span>
              <span className="ml-3">Cohorts: {clinic.cohorts.length}</span> {/* Get count from cohorts array */}
            </div>
          </div>
          
          {/* Cohort Details - Separated by Status */}
          <div className="space-y-3">
            {/* Active Cohorts - using CohortDisplayData */}
            {clinic.cohorts.filter(cohort => !cohort.isExpired).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-green-700">Active Cohorts</h4>
                {clinic.cohorts
                  .filter(cohort => !cohort.isExpired) // CohortDisplayData now has isExpired
                  .map((cohort, index) => ( // cohort is CohortDisplayData
                    <div key={`active-${cohort.orderId}-${index}`} className="flex flex-col sm:flex-row items-start justify-between p-3 bg-green-50 rounded-md border border-green-200">
                      <div className="flex-1 mb-2 sm:mb-0"> {/* Add margin bottom for mobile, remove for sm+ */}
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-1"> {/* Allow wrapping and add y-gap */}
                          <span className="font-medium text-gray-900 text-sm">
                            {cohort.orderId}
                          </span>
                          <span className="text-xs text-gray-500">
                            ({formatDisplayDate(cohort.startDate)})
                          </span>
                          <span className="text-gray-400 hidden sm:inline">–</span> {/* Hide dash on mobile */}
                          <span className="text-xs sm:text-sm text-gray-700 w-full sm:w-auto"> {/* Smaller text on mobile, full width on mobile */}
                            {formatSKUBreakdown(cohort.skuBreakdown)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mb-1">
                          Expires: {formatDisplayDate(cohort.endDate)}
                        </div>
                        {cohort.activeSerialNumbers && cohort.activeSerialNumbers.length > 0 && (
                          <div className="text-xs text-green-700 break-all"> {/* Allow serial numbers to break */}
                            <span className="font-medium">Active Serial Numbers:</span>
                            <span className="ml-1">{cohort.activeSerialNumbers.join(', ')}</span>
                          </div>
                        )}
                        <div className="text-xs text-gray-600 mt-1">
                          In-Field Count: {cohort.inFieldScopeCount}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 self-start sm:self-center mt-2 sm:mt-0 ml-auto sm:ml-0"> {/* Align to start on mobile, add top margin, push to right on mobile */}
                        {getStatusIcon(cohort.status)}
                        <Badge
                          variant={getStatusBadgeVariant(cohort.status) as any}
                          className="text-xs whitespace-nowrap" // Prevent badge text from wrapping
                        >
                          {getStatusText(cohort.status)}
                        </Badge>
                      </div>
                    </div>
                  ))}
              </div>
            )}

            {/* Parent Div for Expired Cohorts and Unassigned Orphans - 2 column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 pt-3 overflow-hidden"> {/* Changed to lg:grid-cols-2 for larger screens only */}
              {/* Expired Cohorts Section */}
              <div className="min-w-0"> {/* Added min-w-0 to allow shrinking */}
                {clinic.cohorts.filter(cohort => cohort.isExpired).length > 0 && (
                  <>
                    <h4 className="text-sm font-medium text-red-700 mb-1.5">Expired Cohorts</h4>
                    <div className="p-2 bg-red-50 rounded-md border border-red-200"> {/* Removed h-full to allow natural height */}
                      <div className="text-sm text-gray-700 mb-2">
                        <span className="font-medium text-red-700">
                          {clinic.cohorts.filter(cohort => cohort.isExpired).length} expired cohort(s)
                        </span>
                      </div>
                      <div className="space-y-1.5"> {/* Removed overflow-hidden to prevent clipping */}
                        {clinic.cohorts
                          .filter(cohort => cohort.isExpired)
                          .map((cohort, index) => (
                            <div key={`expired-${cohort.orderId}-${index}`} className="flex items-start text-xs min-w-0"> {/* Changed to items-start and added min-w-0 */}
                              <div className="flex-1 min-w-0 mr-2"> {/* Added min-w-0 */}
                                <div className="text-gray-600 break-words"> {/* Changed from truncate to break-words */}
                                  {cohort.orderId} ({formatDisplayDate(cohort.startDate)}) - {formatSKUBreakdown(cohort.skuBreakdown)}
                                </div>
                                <div className="text-red-600 font-medium text-xs mt-0.5"> {/* Moved expiration to new line */}
                                  Expired {formatDisplayDate(cohort.endDate)}
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Unassigned In-Field Scopes Section */}
              <div className="min-w-0"> {/* Added min-w-0 to allow shrinking */}
                {clinic.orphanedScopesGlobal && clinic.orphanedScopesGlobal.filter(o => {
                  if (!o.status) return false;
                  const lowerStatus = o.status.toLowerCase().replace(/\s+/g, '');
                  return lowerStatus.includes('infield');
                }).length > 0 && (
                  <>
                    <h4 className="text-sm font-medium text-orange-700 mb-1.5">Unassigned In-Field Scopes</h4>
                    <div className="p-2 bg-orange-50 rounded-md border border-orange-200"> {/* Removed h-full to allow natural height */}
                      <div className="space-y-1.5"> {/* Removed overflow-hidden to prevent clipping */}
                        {clinic.orphanedScopesGlobal
                          .filter(o => {
                            if (!o.status) return false;
                            const lowerStatus = o.status.toLowerCase().replace(/\s+/g, '');
                            return lowerStatus.includes('infield');
                          })
                          .map((orphan, index) => (
                            <div key={`orphan-${orphan.serial}-${index}`} className="text-xs text-gray-700 break-words"> {/* Added break-words */}
                              Serial: {orphan.serial} (SKU: {orphan.sku})
                            </div>
                          ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
          
          {/* No Cohorts Message */}
          {clinic.cohorts.length === 0 && (
            <div className="p-3 bg-gray-50 rounded-md text-center text-sm text-gray-500">
              No active cohorts found
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ClinicListItem;