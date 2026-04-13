from langchain_core.documents import Document


def test_add_and_search_documents(temp_chroma):
    from rag.vectorstore import clear_collection, add_documents, search

    clear_collection()

    docs = [
        Document(
            page_content="AU Post label generation creates shipping labels via the AU Post REST API.",
            metadata={"source": "test", "source_url": "test://doc1", "source_type": "test"},
        ),
        Document(
            page_content="The Australia Post Shopify App supports Ground, Express, and SmartPost services.",
            metadata={"source": "test", "source_url": "test://doc2", "source_type": "test"},
        ),
    ]
    add_documents(docs)

    results = search("label generation", k=1)
    assert len(results) == 1
    assert "label" in results[0].page_content.lower()


def test_clear_collection_removes_documents(temp_chroma):
    from rag.vectorstore import clear_collection, add_documents, search

    docs = [
        Document(
            page_content="Pickup scheduling allows merchants to request an Australia Post courier.",
            metadata={"source": "test", "source_url": "test://doc3", "source_type": "test"},
        )
    ]
    add_documents(docs)
    clear_collection()

    results = search("pickup scheduling", k=5)
    assert len(results) == 0
