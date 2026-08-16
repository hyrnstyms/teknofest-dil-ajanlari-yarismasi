import { fetchApi } from './api';

export interface EBYSStatus {
  adapter_type: string;
  connected: boolean;
  mode: string;
  message: string;
}

export async function getEBYSStatus(): Promise<EBYSStatus> {
  return fetchApi<EBYSStatus>('/api/integrations/ebys/status');
}
