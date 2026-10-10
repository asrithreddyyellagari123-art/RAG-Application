import { MAX_NUMBER_OF_SELECTED_DOCUMENTS } from "~/hooks/useDocumentSelector";
import { BackendDocument, BackendDocumentType } from "~/types/backend/document";
import { SecDocument, DocumentType } from "~/types/document";
import { documentColors } from "~/utils/colors";
import _ from "lodash";

export const fromBackendDocumentToFrontend = (
  backendDocuments: BackendDocument[]
) => {
  // sort by created_at so that de-dupe filter later keeps oldest duplicate docs
  backendDocuments = _.sortBy(backendDocuments, 'created_at');
  let frontendDocs: SecDocument[] = backendDocuments
  .filter((backendDoc) => ('sec_document' in backendDoc.metadata_map) || ('rag_document' in backendDoc.metadata_map))
  .map((backendDoc, index) => {
    const docMeta = backendDoc.metadata_map.rag_document || backendDoc.metadata_map.sec_document!;
    const backendDocType = docMeta.doc_type;
    const frontendDocType =
      backendDocType === BackendDocumentType.TenK
        ? DocumentType.TenK
        : DocumentType.TenQ;

    // we have 10 colors for 10 documents
    const colorIndex = index < 10 ? index : 0;
    return {
      id: backendDoc.id,
      url: `/api/pdf/${backendDoc.id}`,
      ticker: docMeta.company_ticker,
      fullName: docMeta.company_name,
      year: String(docMeta.year),
      docType: frontendDocType,
      color: documentColors[colorIndex],
      quarter: docMeta.quarter || "",
    } as SecDocument;
  });
  // de-dupe hotfix
  const getDocDeDupeKey = (doc: SecDocument) => `${doc.ticker}-${doc.year}-${doc.quarter || ''}`;
  frontendDocs = _.chain(frontendDocs).sortBy(getDocDeDupeKey).sortedUniqBy(getDocDeDupeKey).value();

  return frontendDocs;
};
