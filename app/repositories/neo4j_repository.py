from typing import Dict, List
from neo4j import GraphDatabase
from core.settings import settings


NEO4J_URI = settings.NEO4J_URI
NEO4J_USER = settings.NEO4J_USER
NEO4J_PASSWORD = settings.NEO4J_PASSWORD
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def list_vocab_terms(limit: int = 300000) -> list[str]:
    with driver.session() as sess:
        rows = sess.run(
            "MATCH (c:Concept) RETURN toLower(c.term) AS t LIMIT $limit",
            limit=limit,
        )
        return [r["t"] for r in rows if r["t"]]


def lookup_concept_ids(term: str) -> List[Dict[str, str]]:
    """先 exact / contains；若無結果回空，模糊比對由上層處理。"""
    term = (term or "").strip()
    if not term:
        return []

    with driver.session() as session:
        query = """
        // exact match first
        MATCH (d:Description)-[:DESCRIBES]->(c:Concept)
        WHERE toLower(d.term) = toLower($t)
          AND d.typeId = '900000000000003001'
          AND NOT toLower(d.term) CONTAINS 'screening'
        RETURN DISTINCT c.conceptId AS conceptId, d.term AS term, 100 AS score
        UNION
        // then contains
        MATCH (d:Description)-[:DESCRIBES]->(c:Concept)
        WHERE toLower(d.term) CONTAINS toLower($t)
          AND d.typeId = '900000000000003001'
          AND NOT toLower(d.term) CONTAINS 'screening'
        RETURN DISTINCT c.conceptId AS conceptId, d.term AS term, 50 AS score
        ORDER BY score DESC, size(term) ASC
        LIMIT 5
        """
        result = session.run(query, t=term)
        return [{"conceptId": r["conceptId"], "term": r["term"]} for r in result]


def get_subgraph(concept_id: str) -> List[Dict[str, str]]:
    """Expand to depth 1..3; only IS-A (116680003)."""
    with driver.session() as session:
        query = """
        MATCH path=(c:Concept {conceptId: $conceptId})-[:HAS_RELATIONSHIP*1..3]->(related:Concept)
        WHERE ALL(r IN relationships(path) WHERE r.typeId = '116680003')   // IS-A
        OPTIONAL MATCH (c)<-[:DESCRIBES]-(cd:Description)
        OPTIONAL MATCH (related)<-[:DESCRIBES]-(rd:Description)
        WITH DISTINCT cd.term AS sourceTerm, rd.term AS targetTerm
        RETURN sourceTerm, targetTerm
        LIMIT 50
        """
        result = session.run(query, conceptId=concept_id)
        return result.data()
