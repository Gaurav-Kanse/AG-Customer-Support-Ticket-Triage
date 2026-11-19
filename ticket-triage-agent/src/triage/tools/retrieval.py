"""TF-IDF retrieval over synthetic policy documents."""

from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from triage.config import KB_DIR
from triage.schemas import Evidence


class PolicySearch:
    def __init__(self, directory: Path = KB_DIR):
        self.chunks = []
        for path in sorted(directory.glob("*.md")):
            for i, chunk in enumerate(
                x.strip() for x in path.read_text().split("\n\n") if x.strip()
            ):
                self.chunks.append((path.name, f"{path.stem}:{i}", chunk))
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform([x[2] for x in self.chunks])

    def search_policy(self, query: str, top_k: int = 3) -> list[Evidence]:
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        ix = scores.argsort()[::-1][:top_k]
        return [
            Evidence(
                doc=self.chunks[i][0],
                chunk_id=self.chunks[i][1],
                text=self.chunks[i][2],
                score=float(scores[i]),
            )
            for i in ix
            if scores[i] > 0
        ]
