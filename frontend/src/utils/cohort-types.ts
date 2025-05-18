export interface Serial {
  id: string;
  model: string;
  status: 'active' | 'replaced' | 'retired';
  replacementDate: string | null;
  chainInfo?: {
    isPartOfChain: boolean;
    isLastInChain: boolean;
    chainLength: number;
    chainPosition: number;
    chainType: 'validated' | 'orphan';
  };
}

export interface ChainHandoff {
  returnedSerial: string;
  returnDate: string;
  replacementSerial: string;
  replacementShipDate: string;
}

export interface ChainData {
  validatedChains: {
    serials: string[];
    handoffs: ChainHandoff[];
    finalStatus: string;
  }[];
  orphanChains: {
    serials: string[];
    handoffs: ChainHandoff[];
    finalStatus: string;
    initialShipDate?: string;
  }[];
}

export interface Cohort {
  id: string;
  customer: string;
  totalUnits: number;
  activeUnits: number;
  replacementsUsed: number;
  replacementsTotal: number;
  startDate: string;
  endDate: string;
  status: 'active' | 'maxed' | 'expired';
  serials: Serial[];
  chainData?: ChainData;
}
