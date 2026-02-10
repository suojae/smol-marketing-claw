"""Vector DB-based emotional episode memory using ChromaDB + Sentence-Transformers."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

# Graceful fallback: ChromaDB / sentence-transformers may not be installed
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    _HAS_CHROMADB = True
except ImportError:
    _HAS_CHROMADB = False

try:
    from sentence_transformers import SentenceTransformer

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

VECTOR_DB_AVAILABLE = _HAS_CHROMADB and _HAS_SENTENCE_TRANSFORMERS


@dataclass
class HormoneEpisode:
    """A single emotional episode snapshot."""

    timestamp: str = ""
    dopamine: float = 0.5
    cortisol: float = 0.0
    energy: float = 1.0
    emotional_state: str = "balanced"
    events: str = ""
    decision_action: str = "none"
    decision_message: str = ""
    outcome_summary: str = ""


class HormoneMemory:
    """Stores and retrieves emotional episodes via vector similarity search.

    Falls back to no-op when ChromaDB or sentence-transformers are unavailable.
    """

    COLLECTION_NAME = "hormone_episodes"
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, persist_dir: str = "memory/chroma"):
        self.enabled = False
        self._collection = None
        self._embedder = None

        if not VECTOR_DB_AVAILABLE:
            print(
                "HormoneMemory disabled: "
                "chromadb or sentence-transformers not installed"
            )
            return

        try:
            self._embedder = SentenceTransformer(self.EMBEDDING_MODEL)
            self._client = chromadb.PersistentClient(path=persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self.enabled = True
            print(f"HormoneMemory initialized ({persist_dir})")
        except Exception as e:
            print(f"HormoneMemory init failed (falling back to no-op): {e}")

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------
    def record_episode(self, episode: HormoneEpisode):
        """Vectorize and store an emotional episode."""
        if not self.enabled:
            return

        text = self._episode_to_text(episode)
        try:
            embedding = self._embedder.encode(text).tolist()
            doc_id = str(uuid.uuid4())
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[
                    {
                        "timestamp": episode.timestamp or datetime.now().isoformat(),
                        "dopamine": episode.dopamine,
                        "cortisol": episode.cortisol,
                        "energy": episode.energy,
                        "emotional_state": episode.emotional_state,
                        "action": episode.decision_action,
                        "message": episode.decision_message[:200],
                        "outcome": episode.outcome_summary[:200],
                    }
                ],
            )
        except Exception as e:
            print(f"HormoneMemory record failed: {e}")

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------
    def recall_similar(
        self, current_state: str, n_results: int = 3
    ) -> List[Dict]:
        """Find past episodes similar to the current situation."""
        if not self.enabled or not self._collection:
            return []

        try:
            count = self._collection.count()
            if count == 0:
                return []

            embedding = self._embedder.encode(current_state).tolist()
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, count),
            )

            episodes = []
            if results and results["metadatas"]:
                for meta, doc in zip(
                    results["metadatas"][0], results["documents"][0]
                ):
                    episodes.append(
                        {
                            "emotional_state": meta.get("emotional_state", ""),
                            "action": meta.get("action", ""),
                            "outcome": meta.get("outcome", ""),
                            "dopamine": meta.get("dopamine", 0),
                            "cortisol": meta.get("cortisol", 0),
                            "energy": meta.get("energy", 0),
                            "timestamp": meta.get("timestamp", ""),
                            "document": doc,
                        }
                    )
            return episodes
        except Exception as e:
            print(f"HormoneMemory recall failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Context generation for think()
    # ------------------------------------------------------------------
    def get_experience_context(self, current_state: str) -> str:
        """Build a past-experience context block to inject into prompts."""
        episodes = self.recall_similar(current_state)
        if not episodes:
            return ""

        lines = ["[Past Similar Experiences]"]
        for i, ep in enumerate(episodes, 1):
            lines.append(
                f"{i}. State:{ep['emotional_state']} → "
                f"Action:{ep['action']} → "
                f"Outcome:{ep['outcome']}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _episode_to_text(episode: HormoneEpisode) -> str:
        """Convert an episode to a searchable text representation."""
        return (
            f"감정:{episode.emotional_state} "
            f"이벤트:{episode.events} "
            f"행동:{episode.decision_action} "
            f"결과:{episode.outcome_summary}"
        )
