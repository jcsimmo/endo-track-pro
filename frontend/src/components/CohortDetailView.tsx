import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Cohort } from "utils/cohort-types";

interface Props {
  cohort: Cohort;
}

export function CohortDetailView({ cohort }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle>{cohort.customer}</CardTitle>
            <CardDescription className="font-mono">{cohort.id}</CardDescription>
          </div>
          <Badge variant={cohort.status === 'active' ? 'default' : cohort.status === 'maxed' ? 'destructive' : 'outline'} className="ml-2">
            {cohort.status === 'active' ? 'Active' : cohort.status === 'maxed' ? 'Max Replacements' : cohort.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList className="mb-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="serials">Serials</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Agreement Period</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-medium">{new Date(cohort.startDate).getFullYear()}-{new Date(cohort.endDate).getFullYear()}</div>
                  <p className="text-xs text-muted-foreground">
                    {new Date(cohort.startDate).toLocaleDateString()} - {new Date(cohort.endDate).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Units in Field</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-medium">{cohort.activeUnits}/{cohort.totalUnits}</div>
                  <p className="text-xs text-muted-foreground">
                    Active units
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Replacements</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-medium">{cohort.replacementsUsed}/{cohort.replacementsTotal}</div>
                  <div className="mt-1">
                    <Progress 
                      value={(cohort.replacementsUsed / cohort.replacementsTotal) * 100} 
                      className="h-2" 
                    />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Remaining</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-medium">{cohort.replacementsTotal - cohort.replacementsUsed}</div>
                  <p className="text-xs text-muted-foreground">
                    Available replacements
                  </p>
                </CardContent>
              </Card>
            </div>
            
            <Card>
              <CardHeader>
                <CardTitle>Replacement Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative pt-6">
                  <div className="absolute top-0 left-0 right-0 flex justify-between">
                    <span className="text-xs text-muted-foreground">Start: {new Date(cohort.startDate).toLocaleDateString()}</span>
                    <span className="text-xs text-muted-foreground">End: {new Date(cohort.endDate).toLocaleDateString()}</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full w-full">
                    {/* Calculate position based on time elapsed */}
                    {(() => {
                      const start = new Date(cohort.startDate).getTime();
                      const end = new Date(cohort.endDate).getTime();
                      const now = new Date().getTime();
                      const progress = Math.max(0, Math.min(100, ((now - start) / (end - start)) * 100));
                      return (
                        <div 
                          className="absolute h-4 w-4 bg-primary rounded-full top-6 -mt-1 -ml-2" 
                          style={{ left: `${progress}%` }}
                        />
                      );
                    })()}
                  </div>
                </div>
                
                <div className="mt-6 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm">Total allowed replacements:</span>
                    <span className="text-sm font-medium">{cohort.replacementsTotal}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Replacements used:</span>
                    <span className="text-sm font-medium">{cohort.replacementsUsed}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Remaining replacements:</span>
                    <span className="text-sm font-medium">{cohort.replacementsTotal - cohort.replacementsUsed}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Replacement rate:</span>
                    <span className="text-sm font-medium">
                      {(cohort.replacementsUsed / ((new Date().getTime() - new Date(cohort.startDate).getTime()) / (1000 * 60 * 60 * 24 * 365))).toFixed(1)} per year
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="serials">
            <div className="rounded-md border">
              {cohort.serials && cohort.serials.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="py-2 px-4 text-left font-medium">Serial Number</th>
                      <th className="py-2 px-4 text-left font-medium">Model</th>
                      <th className="py-2 px-4 text-left font-medium">Status</th>
                      <th className="py-2 px-4 text-left font-medium">Last Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cohort.serials.map(serial => (
                      <tr key={serial.id} className="border-b hover:bg-muted/50">
                        <td className="py-2 px-4 font-mono">{serial.id}</td>
                        <td className="py-2 px-4">{serial.model}</td>
                        <td className="py-2 px-4">
                          <div className="flex items-center">
                            <div className={`h-2 w-2 rounded-full mr-2 ${serial.status === 'active' ? 'bg-green-500' : serial.status === 'replaced' ? 'bg-amber-500' : 'bg-red-500'}`} />
                            <span className="capitalize">{serial.status}</span>
                          </div>
                        </td>
                        <td className="py-2 px-4">{serial.replacementDate ? new Date(serial.replacementDate).toLocaleDateString() : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-8 text-center text-muted-foreground">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mx-auto mb-2">
                    <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                    <line x1="3" x2="21" y1="9" y2="9" />
                    <path d="m9 16 3-3 3 3" />
                  </svg>
                  <p>No serial numbers found for this cohort</p>
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="timeline">
            <div className="p-4 bg-muted/20 rounded-lg">
              <div className="relative">
                {/* Timeline visualization */}
                <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-muted"></div>
                
                <div className="space-y-8 relative">
                  <div className="ml-10 relative">
                    <div className="absolute -left-10 mt-1.5">
                      <div className="h-6 w-6 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                          <path d="M12 5v14" />
                          <path d="M18 13l-6 6" />
                          <path d="M6 13l6 6" />
                        </svg>
                      </div>
                    </div>
                    <div className="pb-4">
                      <div className="text-sm font-semibold">{new Date(cohort.startDate).toLocaleDateString()}</div>
                      <div className="mt-1 text-muted-foreground text-sm">CSA Agreement Start</div>
                      <div className="mt-2 bg-card rounded-md p-2 text-sm border">
                        <p>Initial delivery of {cohort.totalUnits} units</p>
                      </div>
                    </div>
                  </div>
                  
                  {cohort.serials
                    .filter(serial => serial.replacementDate)
                    .sort((a, b) => new Date(a.replacementDate!).getTime() - new Date(b.replacementDate!).getTime())
                    .map((serial, index) => (
                      <div key={serial.id} className="ml-10 relative">
                        <div className="absolute -left-10 mt-1.5">
                          <div className="h-6 w-6 rounded-full bg-amber-500/10 border-2 border-amber-500 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
                              <path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2" />
                              <path d="M8 5V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-1" />
                            </svg>
                          </div>
                        </div>
                        <div className="pb-4">
                          <div className="text-sm font-semibold">{new Date(serial.replacementDate!).toLocaleDateString()}</div>
                          <div className="mt-1 text-muted-foreground text-sm">Replacement #{index + 1}</div>
                          <div className="mt-2 bg-card rounded-md p-2 text-sm border">
                            <p>Serial <span className="font-mono">{serial.id}</span> was replaced</p>
                          </div>
                        </div>
                      </div>
                    ))
                  }
                  
                  <div className="ml-10 relative">
                    <div className="absolute -left-10 mt-1.5">
                      <div className={`h-6 w-6 rounded-full ${new Date(cohort.endDate).getTime() < new Date().getTime() ? 'bg-red-500/10 border-2 border-red-500' : 'bg-muted border-2 border-muted-foreground'} flex items-center justify-center`}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={new Date(cohort.endDate).getTime() < new Date().getTime() ? 'text-red-500' : 'text-muted-foreground'}>
                          <path d="M18 6 6 18" />
                          <path d="m6 6 12 12" />
                        </svg>
                      </div>
                    </div>
                    <div className="pb-4">
                      <div className="text-sm font-semibold">{new Date(cohort.endDate).toLocaleDateString()}</div>
                      <div className="mt-1 text-muted-foreground text-sm">CSA Agreement End</div>
                      <div className="mt-2 bg-card rounded-md p-2 text-sm border">
                        <p>Contract expires</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

export function CohortEmptyState() {
  return (
    <div className="h-full flex items-center justify-center p-12 bg-muted/20 rounded-lg border border-dashed">
      <div className="text-center">
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mx-auto mb-4 text-muted-foreground">
          <path d="M17 6.1H3" />
          <path d="M21 12.1H3" />
          <path d="M15.1 18H3" />
        </svg>
        <h3 className="text-lg font-medium mb-2">No Cohort Selected</h3>
        <p className="text-muted-foreground mb-4">Select a cohort from the list to view detailed information.</p>
      </div>
    </div>
  );
}