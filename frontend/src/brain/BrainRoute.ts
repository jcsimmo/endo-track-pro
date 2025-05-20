import {
  CheckHealthData,
  CheckZohoHealthData,
  ConfigureZohoPromptData,
  DownloadJsonData,
  GetInventoryItemsData,
  GetTaskStatusData,
  ListCustomersData,
  ProcessRequest,
  ProcessSalesDataEndpointData,
  DownloadAggregatedData,
  RunDataExtractionData,
} from "./data-contracts";

export namespace Brain {
  /**
   * @description Check health of application. Returns 200 when OK, 500 when not.
   * @name check_health
   * @summary Check Health
   * @request GET:/_healthz
   */
  export namespace check_health {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = CheckHealthData;
  }

  /**
   * @description Check the health of the Zoho API connection
   * @tags dbtn/module:zoho, dbtn/hasAuth
   * @name check_zoho_health
   * @summary Check Zoho Health
   * @request GET:/routes/health
   */
  export namespace check_zoho_health {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = CheckZohoHealthData;
  }

  /**
   * @description Get inventory items from Zoho Inventory
   * @tags dbtn/module:zoho, dbtn/hasAuth
   * @name get_inventory_items
   * @summary Get Inventory Items
   * @request GET:/routes/inventory/items
   */
  export namespace get_inventory_items {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = GetInventoryItemsData;
  }

  /**
   * @description Check which Zoho secrets are missing and provide instructions
   * @tags dbtn/module:zoho, dbtn/hasAuth
   * @name configure_zoho_prompt
   * @summary Configure Zoho Prompt
   * @request GET:/routes/configure-prompt
   */
  export namespace configure_zoho_prompt {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = ConfigureZohoPromptData;
  }

  /**
   * @description List available customers from Zoho
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name list_customers
   * @summary List Customers
   * @request GET:/routes/customers
   */
  export namespace list_customers {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = ListCustomersData;
  }

  /**
   * @description Run the data extraction for a specific customer
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name run_data_extraction
   * @summary Run Data Extraction
   * @request GET:/routes/run-extraction
   */
  export namespace run_data_extraction {
    export type RequestParams = {};
    export type RequestQuery = {
      /**
       * Customer Name
       * @default "Oasis"
       */
      customer_name?: string;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = RunDataExtractionData;
  }

  /**
   * @description Get the status of a running task
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name get_task_status
   * @summary Get Task Status
   * @request GET:/routes/task-status/{task_id}
   */
  export namespace get_task_status {
    export type RequestParams = {
      /** Task Id */
      taskId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = GetTaskStatusData;
  }

  /**
   * @description Download the generated JSON data
   * @tags dbtn/module:zoho_data, dbtn/hasAuth
   * @name download_json
   * @summary Download Json
   * @request GET:/routes/download-json/{json_key}
   */
  export namespace download_json {
    export type RequestParams = {
      /** Json Key */
      jsonKey: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = DownloadJsonData;
  }

  /**
   * @description Endpoint to trigger the processing of sales data. Initially, this read from a stored JSON file via request.data_key. Now, it fetches live data from Zoho and then processes it.
   * @tags DataProcessing, dbtn/module:data_processing, dbtn/hasAuth
   * @name process_sales_data_endpoint
   * @summary Process raw sales and returns data from Zoho
   * @request POST:/routes/process-sales-data
   */
  export namespace process_sales_data_endpoint {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = ProcessRequest;
    export type RequestHeaders = {};
    export type ResponseBody = ProcessSalesDataEndpointData;
  }

  /**
   * @name process_clinics
   * @request GET:/routes/process-clinics
   */
  export namespace process_clinics {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = any;
  }

  /**
   * @name download_aggregated_json
   * @request GET:/routes/download-aggregated/{json_key}
   */
  export namespace download_aggregated_json {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = DownloadAggregatedData;
  }
}
