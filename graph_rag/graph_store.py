import os
from neo4j import GraphDatabase
from openai import OpenAI

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

client = OpenAI()


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


EXTRACTION_PROMPT = """Extract entities and relationships from this financial/tax document chunk.
Return ONLY JSON, no preamble:
{{
  "entities": [{{"name": "...", "type": "Income|Entity|Deduction|Asset|Amount|Date|Other"}}],
  "relations": [{{"source": "...", "relation": "...", "target": "..."}}]
}}

Text:
{text}
"""


def extract_graph_elements(chunk: str) -> dict:
    import json
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1000,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=chunk)}],
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"entities": [], "relations": []}


class GraphRAGStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def ingest_document(self, client_id: int, doc_id: int, full_text: str):
        chunks = chunk_text(full_text)
        for idx, chunk in enumerate(chunks):
            elements = extract_graph_elements(chunk)
            self._write_chunk(client_id, doc_id, idx, chunk, elements)

    def _write_chunk(self, client_id: int, doc_id: int, chunk_idx: int, chunk_text: str, elements: dict):
        with self.driver.session() as session:
            session.execute_write(self._create_chunk_tx, client_id, doc_id, chunk_idx, chunk_text, elements)

    @staticmethod
    def _create_chunk_tx(tx, client_id, doc_id, chunk_idx, chunk_text, elements):
        tx.run(
            """
            MERGE (c:Client {id: $client_id})
            MERGE (d:Document {id: $doc_id})-[:BELONGS_TO]->(c)
            MERGE (ch:Chunk {id: $chunk_id})-[:PART_OF]->(d)
            SET ch.text = $chunk_text
            """,
            client_id=client_id,
            doc_id=doc_id,
            chunk_id=f"{doc_id}_{chunk_idx}",
            chunk_text=chunk_text,
        )

        for ent in elements.get("entities", []):
            tx.run(
                """
                MATCH (ch:Chunk {id: $chunk_id})
                MERGE (e:Entity {name: $name})
                SET e.type = $type
                MERGE (ch)-[:MENTIONS]->(e)
                """,
                chunk_id=f"{doc_id}_{chunk_idx}",
                name=ent["name"],
                type=ent.get("type", "Other"),
            )

        for rel in elements.get("relations", []):
            tx.run(
                """
                MERGE (s:Entity {name: $source})
                MERGE (t:Entity {name: $target})
                MERGE (s)-[r:RELATION {type: $relation}]->(t)
                """,
                source=rel["source"],
                target=rel["target"],
                relation=rel["relation"],
            )

    def retrieve_context(self, client_id: int, query_terms: list[str], limit: int = 10) -> list[str]:
        """Simple keyword-based traversal retrieval (v1)."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Client {id: $client_id})<-[:BELONGS_TO]-(d:Document)<-[:PART_OF]-(ch:Chunk)-[:MENTIONS]->(e:Entity)
                WHERE any(term IN $terms WHERE toLower(e.name) CONTAINS toLower(term))
                RETURN DISTINCT ch.text AS text
                LIMIT $limit
                """,
                client_id=client_id,
                terms=query_terms,
                limit=limit,
            )
            return [r["text"] for r in result]
