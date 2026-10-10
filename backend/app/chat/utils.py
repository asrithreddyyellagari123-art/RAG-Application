from app.schema import (
    Document as DocumentSchema,
    DocumentMetadataKeysEnum,
    SecDocumentMetadata,
)


def build_title_for_document(document: DocumentSchema) -> str:
    metadata_map = document.metadata_map or {}
    metadata_key = (
        DocumentMetadataKeysEnum.RAG_DOCUMENT
        if DocumentMetadataKeysEnum.RAG_DOCUMENT in metadata_map
        else (
            DocumentMetadataKeysEnum.SEC_DOCUMENT
            if DocumentMetadataKeysEnum.SEC_DOCUMENT in metadata_map
            else None
        )
    )
    if not metadata_key:
        return "No Title Document"

    sec_metadata = SecDocumentMetadata.model_validate(
        metadata_map[metadata_key]
    )
    time_period = (
        f"{sec_metadata.year} Q{sec_metadata.quarter}"
        if sec_metadata.quarter is not None
        else str(sec_metadata.year)
    )
    return f"{sec_metadata.company_name} ({sec_metadata.company_ticker}) {sec_metadata.doc_type.value} ({time_period})"
