export enum BackendDocumentType {
  TenK = "10-K",
  TenQ = "10-Q",
}

export interface BackendDocument {
  created_at: string;
  id: string;
  updated_at: string;
  metadata_map: BackendMetadataMap;
  url: string;
}

export interface BackendMetadataMap {
  sec_document?: BackendRagDocument;
  rag_document?: BackendRagDocument;
}

export interface BackendRagDocument {
  company_name: string;
  company_ticker: string;
  doc_type: BackendDocumentType;
  year: number;
  quarter: number;
}

export type BackendSecDocument = BackendRagDocument;
