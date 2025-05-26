import openai, uuid, datetime
from pinecone import Pinecone, ServerlessSpec
from datetime import timezone
import config

# Inicializace Pinecone klienta
pc = Pinecone(api_key=config.PINECONE_API_KEY, environment=config.PINECONE_ENVIRONMENT)
# Vytvoření indexu, pokud neexistuje
if config.INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=config.INDEX_NAME,
        dimension=config.INDEX_DIMENSION,
        metric=config.INDEX_METRIC,
        spec=ServerlessSpec(cloud="aws", region=config.PINECONE_ENVIRONMENT)
    )
memory_index = pc.Index(config.INDEX_NAME)

# Uložení embeddingu do Pinecone
def store_memory(text: str, meta: dict):
    resp = openai.OpenAI(api_key=config.OPENAI_API_KEY).embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    emb = resp.data[0].embedding
    memory_index.upsert(vectors=[(meta['id'], emb, meta)])

# Načtení relevantních embeddingů
def retrieve_memories(query: str, top_k: int = 5) -> list[str]:
    resp = openai.OpenAI(api_key=config.OPENAI_API_KEY).embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    q_emb = resp.data[0].embedding
    res = memory_index.query(vector=q_emb, top_k=top_k, include_metadata=True)
    return [m['metadata']['text'] for m in res.matches]
