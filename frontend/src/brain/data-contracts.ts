/** CustomerListResponse */
export interface CustomerListResponse {
  /** Customers */
  customers: CustomerResponse[];
}

/** CustomerResponse */
export interface CustomerResponse {
  /** Contact Id */
  contact_id: string;
  /** Contact Name */
  contact_name: string;
}

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

/** ProcessRequest */
export interface ProcessRequest {
  /** Data Key */
  data_key: string;
}

/** TaskStatusResponse */
export interface TaskStatusResponse {
  /** Task Id */
  task_id: string;
  /** Status */
  status: string;
  /** Progress */
  progress?: number | null;
  /** Error */
  error?: string | null;
  /** Output */
  output?: string | null;
  /** Json Key */
  json_key?: string | null;
}

/** ValidationError */
export interface ValidationError {
  /** Location */
  loc: (string | number)[];
  /** Message */
  msg: string;
  /** Error Type */
  type: string;
}

/** ZohoInventoryItem */
export interface ZohoInventoryItem {
  /** Item Id */
  item_id: string;
  /** Name */
  name: string;
  /** Description */
  description?: string | null;
  /** Sku */
  sku?: string | null;
  /** Status */
  status?: string | null;
  /** Custom Fields */
  custom_fields?: Record<string, any> | null;
}

/** ZohoInventoryResponse */
export interface ZohoInventoryResponse {
  /** Items */
  items: ZohoInventoryItem[];
  /** Page Context */
  page_context?: Record<string, any> | null;
}

/** HealthResponse */
export interface AppApisZohoHealthResponse {
  /** Status */
  status: string;
  /** Message */
  message: string;
}

/** HealthResponse */
export interface DatabuttonAppMainHealthResponse {
  /** Status */
  status: string;
}

export type CheckHealthData = DatabuttonAppMainHealthResponse;

export type CheckZohoHealthData = AppApisZohoHealthResponse;

export type GetInventoryItemsData = ZohoInventoryResponse;

export type ConfigureZohoPromptData = any;

export type ListCustomersData = CustomerListResponse;

export interface RunDataExtractionParams {
  /**
   * Customer Name
   * @default "Oasis"
   */
  customer_name?: string;
}

export type RunDataExtractionData = any;

export type RunDataExtractionError = HTTPValidationError;

export interface GetTaskStatusParams {
  /** Task Id */
  taskId: string;
}

export type GetTaskStatusData = TaskStatusResponse;

export type GetTaskStatusError = HTTPValidationError;

export interface DownloadJsonParams {
  /** Json Key */
  jsonKey: string;
}

export type DownloadJsonData = any;

export type DownloadJsonError = HTTPValidationError;

/** Response Process Sales Data Endpoint */
export type ProcessSalesDataEndpointData = Record<string, any>;

export type ProcessSalesDataEndpointError = HTTPValidationError;
