"""Embedding-based intent classifier.

Each user input is classified into one of seven intents. Useful for:
  1. Telling the agent what kind of help is being asked for (the intent
     label is prepended to the system context for that turn).
  2. Detecting CORRECTION turns so we can persist the correction to the
     long-term memory store.
  3. Detecting COMMIT_REQUEST turns for the safety dashboard.
  4. CLI / log instrumentation.

Why embedding-based and not LLM-based:
  - Free — uses the same `all-MiniLM-L6-v2` model already loaded for RAG.
  - Fast — ~10ms per classification, runs locally.
  - Stable — no LLM nondeterminism.
  - Sufficient for a 7-class problem with hand-curated prototypes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# These prototypes are mean-pooled at class-init to form a centroid per
# intent. Classification = nearest centroid by cosine similarity.
_PROTOTYPES: dict[str, list[str]] = {
    "triage_request": [
        "Triage shipment FRT-1042",
        "What's wrong with this shipment",
        "Help me handle this exception",
        "What's going on with FRT-1043",
        "I need to triage a customs hold",
        "Diagnose this shipment for me",
    ],
    "follow_up": [
        "What about the alternate carrier",
        "And the demurrage exposure?",
        "What if the shipper doesn't respond?",
        "Tell me more about that",
        "What's the next step",
        "OK now what",
    ],
    "policy_question": [
        "What does our SOP say about this",
        "What's our policy on customs holds",
        "How do we usually handle weather delays",
        "What are our escalation thresholds",
        "What's the SLA window for Gold tier",
        "What's the procedure for HBL/MBL mismatch",
    ],
    "draft_request": [
        "Draft a customer email",
        "Write the LOI request",
        "Draft an escalation message",
        "Can you draft the carrier notification",
        "Write me a holding comm for the customer",
        "Draft a follow-up email",
    ],
    "correction": [
        "Actually, the carrier is MSC, not Maersk",
        "No, the customer is Platinum tier, not Gold",
        "You misread the data — the ETA is 2026-05-29",
        "That's wrong — the demurrage rate is $200, not $175",
        "Correction: the consignee is in London, not Liverpool",
        "Wait, you got the SLA wrong — it's 4 hours not 8",
    ],
    "commit_request": [
        "Send the email for me",
        "Book the alternate carrier now",
        "Cancel this booking",
        "Auto-correct the HBL and ship it",
        "Just submit it for me",
        "Charge the customer the demurrage now",
    ],
    "meta": [
        "How do you work",
        "What can you do",
        "Are you sure about that",
        "Why did you say that",
        "What tools do you have",
        "Show me your reasoning",
    ],
}


@dataclass
class IntentResult:
    intent: str
    confidence: float  # cosine similarity to top centroid in [0, 1]
    runner_up: str | None  # second-best intent label
    margin: float  # (top sim - runner-up sim); >0.05 = clear winner


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.clip(n, 1e-8, None)


class IntentClassifier:
    """Lazy-loaded so the embedding model isn't imported at module-load time."""

    def __init__(self, embed_model_name: str | None = None) -> None:
        self._embed_model_name = embed_model_name or "all-MiniLM-L6-v2"
        self._embed_fn: SentenceTransformerEmbeddingFunction | None = None
        self._labels: list[str] = list(_PROTOTYPES.keys())
        self._centroids: np.ndarray | None = None

    def _ensure_loaded(self) -> None:
        if self._centroids is not None:
            return
        self._embed_fn = SentenceTransformerEmbeddingFunction(
            model_name=self._embed_model_name
        )
        # Embed all prototype examples and mean-pool per intent.
        rows = []
        for label in self._labels:
            examples = _PROTOTYPES[label]
            embeds = np.asarray(self._embed_fn(examples))
            embeds = _normalize(embeds)
            rows.append(embeds.mean(axis=0))
        self._centroids = _normalize(np.stack(rows))

    def classify(self, text: str) -> IntentResult:
        self._ensure_loaded()
        assert self._embed_fn is not None
        assert self._centroids is not None

        emb = np.asarray(self._embed_fn([text]))
        emb = _normalize(emb)
        sims = (emb @ self._centroids.T).flatten()  # cosine since both normalized

        order = np.argsort(-sims)
        top = order[0]
        ru = order[1] if len(order) > 1 else None
        runner_up_label = self._labels[ru] if ru is not None else None
        margin = float(sims[top] - (sims[ru] if ru is not None else 0.0))
        return IntentResult(
            intent=self._labels[top],
            confidence=float(sims[top]),
            runner_up=runner_up_label,
            margin=margin,
        )


# Module-level singleton so callers don't re-load the embedding model.
_singleton: IntentClassifier | None = None


def classify(text: str) -> IntentResult:
    """Classify a user input. Lazy-loads the embedding model on first call."""
    global _singleton
    if _singleton is None:
        _singleton = IntentClassifier()
    return _singleton.classify(text)


__all__ = ["IntentResult", "IntentClassifier", "classify"]
