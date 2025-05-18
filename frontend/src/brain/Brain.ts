import {
  CheckHealthData,
  CheckZohoHealthData,
  ConfigureZohoPromptData,
  DownloadJsonData,
  DownloadJsonError,
  DownloadJsonParams,
  GetInventoryItemsData,
  GetTaskStatusData,
  GetTaskStatusError,
  GetTaskStatusParams,
  ListCustomersData,
  ProcessRequest,
  ProcessSalesDataEndpointData,
  ProcessSalesDataEndpointError,
  RunDataExtractionData,
  RunDataExtractionError,
  RunDataExtractionParams,
} from "./data-contracts";
import { ContentType, HttpClient, RequestParams } from "./http-client";

export class Brain<SecurityDataType = unknown> extends HttpClient<SecurityDataType> {
  /**
   * @description Check health of application. Returns 200 when OK, 500 when not.
   *
   * @name check_health
   * @summary Check Health
   * @request GET:/_healthz
   */
  check_health = (params: RequestParams = {}) =>
    this.request<CheckHealthData, any>({
      path: `/_healthz`,
      method: "GET",
      ...params,
    });

  /**
   * @description Check the health of the Zoho API connection
   *
   * @tags dbtn/module:zoho, dbtn/hasAuth
   * @name check_zoho_health
   * @summary Check Zoho Health
   * @request GET:/routes/health
   */
  check_zoho_health = (params: RequestParams = {}) =>
    this.request<CheckZohoHealthData, any>({
      path: `/routes/health`,
      method: "GET",
      ...params,
    });

  /**
   * @description Get inventory items from Zoho Inventory
   *
   * @tags dbtn/module:zoho, dbtn/hasAuth
   * @name get_inventory_items
   * @summary Get Inventory Items
   * @request GET:/routes/inventory/items
   */
  get_inventory_items = (params: RequestParams = {}) =>
    this.request<GetInventoryItemsData, any>({
      path: `/routes/inventory/items`,
      method: "GET",
      ...params,
    });

  /**
   * @description Check which Zoho secrets are missing and provide instructions
   *
   * @tags dbtn/module:zoho, dbtn/hasAuth
   * @name configure_zoho_prompt
   * @summary Configure Zoho Prompt
   * @request GET:/routes/configure-prompt
   */
  configure_zoho_prompt = (params: RequestParams = {}) =>
    this.request<ConfigureZohoPromptData, any>({
      path: `/routes/configure-prompt`,
      method: "GET",
      ...params,
    });

  /**
   * @description List available customers from Zoho
   *
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name list_customers
   * @summary List Customers
   * @request GET:/routes/customers
   */
  list_customers = (params: RequestParams = {}) =>
    this.request<ListCustomersData, any>({
      path: `/routes/customers`,
      method: "GET",
      ...params,
    });

  /**
   * @description Run the data extraction for a specific customer
   *
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name run_data_extraction
   * @summary Run Data Extraction
   * @request GET:/routes/run-extraction
   */
  run_data_extraction = (query: RunDataExtractionParams, params: RequestParams = {}) =>
    this.request<RunDataExtractionData, RunDataExtractionError>({
      path: `/routes/run-extraction`,
      method: "GET",
      query: query,
      ...params,
    });

  /**
   * @description Get the status of a running task
   *
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name get_task_status
   * @summary Get Task Status
   * @request GET:/routes/task-status/{task_id}
   */
  get_task_status = ({ taskId, ...query }: GetTaskStatusParams, params: RequestParams = {}) =>
    this.request<GetTaskStatusData, GetTaskStatusError>({
      path: `/routes/task-status/${taskId}`,
      method: "GET",
      ...params,
    });

  /**
   * @description Download the generated JSON data
   *
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name download_json
   * @summary Download Json
   * @request GET:/routes/download-json/{json_key}
   */
  download_json = ({ jsonKey, ...query }: DownloadJsonParams, params: RequestParams = {}) =>
    this.request<DownloadJsonData, DownloadJsonError>({
      path: `/routes/download-json/${jsonKey}`,
      method: "GET",
      ...params,
    });

  /**
   * @description Endpoint to trigger the processing of sales data. Initially, this read from a stored JSON file via request.data_key. Now, it fetches live data from Zoho and then processes it.
   *
   * @tags DataProcessing, dbtn/module:data_processing, dbtn/hasAuth
   * @name process_sales_data_endpoint
   * @summary Process raw sales and returns data from Zoho
   * @request POST:/routes/process-sales-data
   */
  process_sales_data_endpoint = (data: ProcessRequest, params: RequestParams = {}) =>
    this.request<ProcessSalesDataEndpointData, ProcessSalesDataEndpointError>({
      path: `/routes/process-sales-data`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
}
