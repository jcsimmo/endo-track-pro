import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "components/Spinner";
import { toast } from "sonner";
import brain from "brain";

interface Customer {
  contact_id: string;
  contact_name: string;
}

interface TaskStatus {
  task_id: string;
  status: string;
  progress?: number | null;
  error?: string | null;
  output?: string | null;
  json_key?: string | null;
}

interface Props {
  className?: string;
}

export function ZohoDataExtraction({ className }: Props) {
  const [isLoading, setIsLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<string>("Oasis");
  const [extractionOutput, setExtractionOutput] = useState<string>("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [jsonKey, setJsonKey] = useState<string | null>(null);
  const [customersLoading, setCustomersLoading] = useState(true);
  const [customersError, setCustomersError] = useState<string | null>(null);

  // Load customers on component mount
  useEffect(() => {
    const loadCustomers = async () => {
      try {
        const response = await brain.list_customers();
        if (!response.ok) {
          throw new Error(`Failed to fetch customers: ${response.statusText}`);
        }
        const data = await response.json();
        setCustomers(data.customers || []);
      } catch (error) {
        console.error("Error loading customers:", error);
        setCustomersError("Failed to load customers. Please check Zoho API connection.");
      } finally {
        setCustomersLoading(false);
      }
    };

    loadCustomers();
  }, []);

  // Poll task status when taskId is available
  useEffect(() => {
    // Only start polling if we have a task ID and it's not already completed/failed
    if (!taskId || taskStatus === "completed" || taskStatus === "failed") {
      return;
    }

    console.log(`Setting up polling interval for task ID: ${taskId}`);
    
    const pollInterval = setInterval(async () => {
      try {
        // Double-check taskId is still valid before making the request
        if (!taskId) {
          console.log("TaskId became invalid, stopping polling");
          clearInterval(pollInterval);
          return;
        }
        
        console.log(`Polling task status for ID: ${taskId}`);
        const response = await brain.get_task_status({ taskId });
        
        if (!response.ok) {
          const errorText = response.statusText;
          console.error(`Error polling task status ${response.status}: ${errorText}`);
          
          // Stop polling on 404 or other serious errors
          if (response.status === 404) {
            setIsLoading(false);
            setTaskStatus("failed");
            toast.error(`Task not found: ${taskId}`);
            clearInterval(pollInterval);
            return;
          }
          throw new Error(`Failed to fetch task status: ${errorText}`);
        }
        
        const data = await response.json();
        console.log("Received task status data:", data);
        
        setTaskStatus(data.status);
        if (data.output) {
          setExtractionOutput(data.output);
        }
        
        if (data.json_key) {
          setJsonKey(data.json_key);
        }
        
        if (data.status === "completed") {
          toast.success("Data extraction completed successfully");
          setIsLoading(false);
          clearInterval(pollInterval);
        } else if (data.status === "failed") {
          toast.error("Data extraction failed");
          setIsLoading(false);
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error("Error polling task status:", error);
        setIsLoading(false);
        setTaskStatus("failed");
        clearInterval(pollInterval);
      }
    }, 3000); // Poll every 3 seconds for better performance

    // Cleanup function
    return () => {
      console.log("Cleaning up polling interval");
      clearInterval(pollInterval);
    };
  }, [taskId, taskStatus]); // Re-run effect when taskId or taskStatus changes

  const handleStartExtraction = async () => {
    setIsLoading(true);
    setExtractionOutput("");
    setTaskId(null);
    setTaskStatus(null);
    setJsonKey(null);
    
    try {
      // Make sure we have a customer name
      if (!selectedCustomer) {
        toast.error("Please select a customer first");
        setIsLoading(false);
        return;
      }
      
      console.log("Starting extraction for customer:", selectedCustomer);
      const response = await brain.run_data_extraction({ customer_name: selectedCustomer });
      if (!response.ok) {
        throw new Error(`Failed to start extraction: ${response.statusText}`);
      }
      const data = await response.json();
      
      console.log("Extraction response data:", data);
      if (!data.task_id) {
        throw new Error("No task ID returned from the server");
      }
      
      setTaskId(data.task_id);
      setTaskStatus("running");
      toast.info(`Started data extraction for ${selectedCustomer}`);
    } catch (error) {
      console.error("Error starting extraction:", error);
      toast.error("Failed to start data extraction");
      setIsLoading(false);
      setTaskStatus("failed");
    }
  };

  const handleDownloadJson = async () => {
    if (!jsonKey) return;
    
    try {
      const response = await brain.download_json({ jsonKey });
      if (!response.ok) {
        throw new Error(`Failed to download JSON: ${response.statusText}`);
      }
      const data = await response.json();
      
      // Create a download link
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedCustomer.toLowerCase()}_zoho_data.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success("Downloaded JSON file");
    } catch (error) {
      console.error("Error downloading JSON:", error);
      toast.error("Failed to download JSON file");
    }
  };

  return (
    <div className={className}>
      <Card>
        <CardContent className="p-6">
          <h3 className="text-lg font-medium mb-4">Zoho Data Extraction</h3>
          
          {customersError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{customersError}</AlertDescription>
            </Alert>
          )}
          
          <div className="space-y-4">
            <div className="flex flex-col space-y-2">
              <label htmlFor="customer-select" className="text-sm font-medium">
                Select Customer
              </label>
              <div className="flex space-x-4">
                <Select 
                  value={selectedCustomer} 
                  onValueChange={setSelectedCustomer}
                  disabled={customersLoading || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a customer" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Oasis">Oasis</SelectItem>
                    {customers.map((customer) => (
                      <SelectItem key={customer.contact_id} value={customer.contact_name}>
                        {customer.contact_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Button 
                  onClick={handleStartExtraction} 
                  disabled={customersLoading || isLoading || !selectedCustomer || taskStatus === "running"}
                >
                  {taskStatus === "running" ? (
                    <>
                      <Spinner className="mr-2 h-4 w-4" />
                      Processing...
                    </>
                  ) : "Extract Data"}
                </Button>
              </div>
            </div>
            
            {extractionOutput && (
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-2">Extraction Log</h4>
                <ScrollArea className="h-64 border rounded-md p-4 bg-muted/30">
                  <pre className="text-xs whitespace-pre-wrap">{extractionOutput}</pre>
                </ScrollArea>
              </div>
            )}
            
            {jsonKey && taskStatus === "completed" && (
              <div className="mt-4 flex justify-end">
                <Button onClick={handleDownloadJson} variant="outline">
                  Download JSON
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}