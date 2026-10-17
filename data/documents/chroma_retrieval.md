# Chroma Vector Store and Retrieval

## Embeddings
An embedding model converts text into a numeric vector. Texts with related meanings are expected to have vectors that are close in the embedding space. Embeddings allow semantic retrieval even when the question and source use different words.

## Chroma
Chroma is a vector database that can store document text, embeddings, and metadata. A persistent local collection can be reopened by using the same persistence directory and collection name. Metadata can record the source filename, URL, and chunk identifier.

## Similarity search
A vector store similarity search returns chunks that are semantically close to the query. The `k` argument controls how many results to return. A larger `k` can improve coverage but may add irrelevant context and increase processing time.

## Chunking
Long documents are commonly split into smaller chunks before embedding. Recursive character splitting attempts to split at natural boundaries such as headings, paragraphs, and lines. Chunk overlap preserves some context across adjacent chunks. Chunk size and overlap should be adjusted based on the document structure and retrieval quality.

## Metadata and citations
Keep source metadata on every chunk. When generating an answer, use the source metadata to identify where evidence came from. The language model should cite retrieved sources and should say when the available documents do not support an answer.
