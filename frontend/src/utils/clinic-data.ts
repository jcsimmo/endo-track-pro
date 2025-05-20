import brain from "brain";

/**
 * Fetches aggregated clinic data by triggering backend processing
 * and polling for completion.
 * @param setIsLoading - Optional loading state setter
 * @param setError - Optional error state setter
 * @returns Promise resolving to the aggregated clinic JSON data
 */
export const fetchClinicData = async (
  setIsLoading?: (loading: boolean) => void,
  setError?: (error: string | null) => void
): Promise<any> => {
  if (setIsLoading) setIsLoading(true);
  if (setError) setError(null);

  try {
    // Step 1: Start clinic processing
    const startResponse = await brain.process_clinics();
    if (!startResponse.ok) {
      throw new Error(
        `Failed to start clinic processing: ${startResponse.status} ${startResponse.statusText}`
      );
    }

    const startData = await startResponse.json();
    const taskId = startData.task_id as string | undefined;
    if (!taskId) {
      throw new Error("No task ID returned from process-clinics endpoint");
    }

    // Step 2: Poll task status until completion
    let statusData: any = null;
    for (let attempts = 0; attempts < 60; attempts++) {
      await new Promise((r) => setTimeout(r, 2000));

      const statusResponse = await brain.get_task_status({ taskId });
      if (!statusResponse.ok) {
        throw new Error(
          `Failed to fetch task status: ${statusResponse.status} ${statusResponse.statusText}`
        );
      }
      statusData = await statusResponse.json();

      if (statusData.status === "completed" || statusData.status === "failed") {
        break;
      }
    }

    if (!statusData || statusData.status !== "completed" || !statusData.json_key) {
      const reason = statusData?.error || "Task did not complete successfully";
      throw new Error(`Clinic processing failed: ${reason}`);
    }

    const jsonKey = statusData.json_key as string;

    // Step 3: Download aggregated JSON
    const dataResponse = await brain.download_aggregated_json({ jsonKey });
    if (!dataResponse.ok) {
      throw new Error(
        `Failed to download aggregated data: ${dataResponse.status} ${dataResponse.statusText}`
      );
    }

    return await dataResponse.json();
  } catch (err) {
    console.error("Error fetching clinic data:", err);
    if (setError) {
      setError(err instanceof Error ? err.message : String(err));
    }
    throw err;
  } finally {
    if (setIsLoading) setIsLoading(false);
  }
};
