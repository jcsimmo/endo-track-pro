import { useState, useEffect } from "react";
import { useUserGuardContext } from "app";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { AlertCircle, CheckCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import brain from "brain";

export interface Props {
  showFullDetails?: boolean;
}

export function ZohoConfiguration({ showFullDetails = false }: Props) {
  const { user } = useUserGuardContext();
  const [connectionStatus, setConnectionStatus] = useState<string>("unchecked");
  const [missingSecrets, setMissingSecrets] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const checkZohoConfig = async () => {
    setIsLoading(true);
    try {
      const response = await brain.configure_zoho_prompt();
      const data = await response.json();
      
      if (data.status === "ok") {
        setMissingSecrets([]);
        setConnectionStatus("configured");
      } else {
        setMissingSecrets(data.missing_secrets || []);
        setConnectionStatus("missing_secrets");
      }
    } catch (error) {
      console.error("Error checking Zoho config:", error);
      toast.error("Failed to check Zoho configuration");
      setConnectionStatus("error");
    } finally {
      setIsLoading(false);
    }
  };

  const testZohoConnection = async () => {
    setIsLoading(true);
    try {
      const response = await brain.check_zoho_health();
      const data = await response.json();
      
      if (data.status === "ok") {
        toast.success("Zoho connection is healthy");
        setConnectionStatus("healthy");
      } else {
        toast.error(`Zoho connection error: ${data.message}`);
        setConnectionStatus("unhealthy");
      }
    } catch (error) {
      console.error("Error testing Zoho connection:", error);
      toast.error("Failed to test Zoho connection");
      setConnectionStatus("error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Check Zoho configuration status on component mount
    checkZohoConfig();
  }, []);

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Zoho Integration</CardTitle>
        <CardDescription>
          Status of your Zoho API connection for inventory management
        </CardDescription>
      </CardHeader>
      <CardContent>
        {connectionStatus === "unchecked" && (
          <div className="flex items-center justify-center p-4">
            <RefreshCw className="h-5 w-5 animate-spin mr-2" />
            <span>Checking Zoho configuration...</span>
          </div>
        )}

        {connectionStatus === "configured" && (
          <Alert className="bg-green-50 border-green-200">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertTitle>Zoho API Configured</AlertTitle>
            <AlertDescription>
              All required Zoho credentials are properly configured.
            </AlertDescription>
          </Alert>
        )}

        {connectionStatus === "missing_secrets" && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Missing Zoho Credentials</AlertTitle>
            <AlertDescription>
              The following Zoho credentials are missing from your Databutton secrets:
              <ul className="list-disc pl-5 mt-2">
                {missingSecrets.map((secret) => (
                  <li key={secret}>{secret}</li>
                ))}
              </ul>
              <p className="mt-2">
                Please add these secrets in the Databutton secrets management interface.
              </p>
            </AlertDescription>
          </Alert>
        )}

        {connectionStatus === "healthy" && (
          <Alert className="bg-green-50 border-green-200">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertTitle>Connection Successful</AlertTitle>
            <AlertDescription>
              Successfully connected to Zoho API.
            </AlertDescription>
          </Alert>
        )}

        {connectionStatus === "unhealthy" && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Connection Failed</AlertTitle>
            <AlertDescription>
              Could not connect to Zoho API. Please check your credentials and try again.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex gap-3 mt-4">
          <Button
            onClick={checkZohoConfig}
            disabled={isLoading}
            variant="outline"
          >
            {isLoading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                Checking...
              </>
            ) : (
              "Check Configuration"
            )}
          </Button>
          <Button
            onClick={testZohoConnection}
            disabled={isLoading || connectionStatus === "missing_secrets"}
          >
            {isLoading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                Testing...
              </>
            ) : (
              "Test Connection"
            )}
          </Button>
        </div>

        {showFullDetails && connectionStatus === "configured" && (
          <div className="mt-6">
            <Separator className="my-4" />
            <div className="text-sm">
              <p className="font-medium mb-2">API Configuration Details:</p>
              <ul className="list-disc pl-5">
                <li>API Domain: https://www.zohoapis.com</li>
                <li>Organization ID: 792214781</li>
                <li>Services: Inventory</li>
              </ul>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
