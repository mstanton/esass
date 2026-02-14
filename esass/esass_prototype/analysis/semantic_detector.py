"""
Semantic pattern detector using text similarity and tag co-occurrence.

Identifies conceptually related event clusters that share semantic content,
regardless of temporal ordering. Uses stdlib-only approach (no ML dependencies):
- Word frequency vectors for text similarity (TF-IDF-like)
- Tag co-occurrence matrix for topic clustering
- Greedy agglomerative clustering

Implements §5.1.3 of specification (simplified).
"""

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from esass_prototype.models import LogEntry, PatternDefinition, PatternType


class SemanticPatternDetector:
    """
    Detect semantically related event clusters in log data.

    Groups events by conceptual similarity using word frequency analysis
    and tag co-occurrence, then identifies recurring semantic themes.
    """

    def __init__(
        self,
        min_support: int = 5,
        min_confidence: float = 0.6,
        min_stability_days: int = 3,
        similarity_threshold: float = 0.4,
        min_cluster_size: int = 3,
        max_clusters: int = 20,
    ):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_stability_days = min_stability_days
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.max_clusters = max_clusters

        # Stopwords for text processing
        self._stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'and',
            'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'only', 'own', 'same',
            'than', 'too', 'very', 'just', 'because', 'if', 'when', 'then',
            'that', 'this', 'these', 'those', 'it', 'its', 'i', 'we',
            'they', 'them', 'their', 'what', 'which', 'who', 'whom',
            'how', 'where', 'there', 'here', 'up', 'out', 'about',
        }

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        """
        Find semantically related event clusters.

        Args:
            logs: List of log entries to analyze

        Returns:
            List of detected PatternDefinition objects
        """
        if len(logs) < self.min_cluster_size:
            return []

        # Step 1: Extract text features from each log entry
        features = self._extract_features(logs)

        # Step 2: Build document-term matrix (word frequency vectors)
        vocab, vectors = self._build_tfidf_vectors(features)

        # Step 3: Cluster by similarity
        clusters = self._cluster_events(logs, vectors)

        # Step 4: Build tag co-occurrence themes
        tag_themes = self._find_tag_themes(logs)

        # Step 5: Merge clusters and tag themes
        merged = self._merge_clusters(clusters, tag_themes, logs)

        # Step 6: Convert to PatternDefinitions
        patterns = []
        for cluster_key, cluster_entries in merged.items():
            if len(cluster_entries) >= self.min_support:
                pattern = self._create_pattern(cluster_key, cluster_entries, logs)
                if pattern and pattern.confidence >= self.min_confidence:
                    patterns.append(pattern)

        patterns.sort(key=lambda p: p.support, reverse=True)
        return patterns[:self.max_clusters]

    def _extract_features(self, logs: List[LogEntry]) -> List[Dict[str, any]]:
        """Extract text and tag features from log entries."""
        features = []
        for entry in logs:
            text_parts = []

            # Extract text from event_data
            for key, value in entry.event_data.items():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, list):
                    text_parts.extend(str(v) for v in value if isinstance(v, str))

            # Include event type and tags
            text_parts.append(entry.event_type)
            text_parts.extend(entry.tags)

            features.append({
                'text': ' '.join(text_parts),
                'tags': set(entry.tags),
                'event_type': entry.event_type,
                'words': self._tokenize(' '.join(text_parts)),
            })

        return features

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and filter text into meaningful words."""
        words = re.findall(r'[a-z_][a-z0-9_]*', text.lower())
        return [w for w in words if w not in self._stopwords and len(w) > 2]

    def _build_tfidf_vectors(
        self, features: List[Dict]
    ) -> Tuple[List[str], List[Dict[str, float]]]:
        """
        Build TF-IDF-like word frequency vectors.

        Returns:
            Tuple of (vocabulary list, list of sparse vectors as dicts)
        """
        # Document frequency: how many documents contain each word
        doc_freq = Counter()
        doc_words = []
        for f in features:
            words = set(f['words'])
            doc_words.append(Counter(f['words']))
            for w in words:
                doc_freq[w] += 1

        n_docs = len(features)
        if n_docs == 0:
            return [], []

        # Filter vocabulary: keep words appearing in >=2 docs but <80% of docs
        max_df = int(n_docs * 0.8) or 1
        vocab = [w for w, df in doc_freq.items() if 2 <= df <= max_df]

        if not vocab:
            # Fallback: use top-50 most frequent words with df >= 2
            vocab = [w for w, df in doc_freq.most_common(50) if df >= 2]

        vocab_set = set(vocab)

        # Build TF-IDF vectors
        vectors = []
        for word_counts in doc_words:
            vec = {}
            total_words = sum(word_counts.values()) or 1
            for w in vocab_set:
                tf = word_counts.get(w, 0) / total_words
                idf = math.log((n_docs + 1) / (doc_freq.get(w, 0) + 1)) + 1
                score = tf * idf
                if score > 0:
                    vec[w] = score
            vectors.append(vec)

        return vocab, vectors

    def _cosine_similarity(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors."""
        if not a or not b:
            return 0.0

        common_keys = set(a.keys()) & set(b.keys())
        if not common_keys:
            return 0.0

        dot = sum(a[k] * b[k] for k in common_keys)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def _cluster_events(
        self, logs: List[LogEntry], vectors: List[Dict[str, float]]
    ) -> Dict[str, List[int]]:
        """
        Greedy agglomerative clustering of events by text similarity.

        Returns dict mapping cluster label to list of log indices.
        """
        n = len(logs)
        if n == 0:
            return {}

        # Assign each event to a cluster; start with each in its own cluster
        cluster_of = list(range(n))
        active_clusters = set(range(n))

        # Greedy single-linkage: merge most similar pair until threshold
        # For efficiency, limit to O(n*k) comparisons per round
        changed = True
        max_rounds = 50
        rounds = 0
        while changed and rounds < max_rounds:
            changed = False
            rounds += 1
            clusters_list = list(active_clusters)

            for i_idx in range(len(clusters_list)):
                ci = clusters_list[i_idx]
                if ci not in active_clusters:
                    continue
                for j_idx in range(i_idx + 1, len(clusters_list)):
                    cj = clusters_list[j_idx]
                    if cj not in active_clusters:
                        continue

                    # Average linkage between cluster members
                    members_i = [k for k in range(n) if cluster_of[k] == ci]
                    members_j = [k for k in range(n) if cluster_of[k] == cj]

                    if len(members_i) + len(members_j) > n // 2:
                        continue  # Don't let one cluster swallow everything

                    sim = self._cluster_similarity(members_i, members_j, vectors)
                    if sim >= self.similarity_threshold:
                        # Merge cj into ci
                        for k in members_j:
                            cluster_of[k] = ci
                        active_clusters.discard(cj)
                        changed = True

        # Build cluster map
        clusters = defaultdict(list)
        for idx in range(n):
            clusters[f"text_cluster_{cluster_of[idx]}"].append(idx)

        # Filter small clusters
        return {k: v for k, v in clusters.items() if len(v) >= self.min_cluster_size}

    def _cluster_similarity(
        self,
        members_a: List[int],
        members_b: List[int],
        vectors: List[Dict[str, float]],
    ) -> float:
        """Average-linkage similarity between two clusters."""
        if not members_a or not members_b:
            return 0.0

        total = 0.0
        count = 0
        for i in members_a:
            for j in members_b:
                total += self._cosine_similarity(vectors[i], vectors[j])
                count += 1

        return total / count if count > 0 else 0.0

    def _find_tag_themes(self, logs: List[LogEntry]) -> Dict[str, List[int]]:
        """
        Find recurring tag combinations (co-occurrence themes).

        Returns dict mapping theme label to list of log indices.
        """
        # Count tag pair co-occurrences
        pair_counts = Counter()
        pair_indices = defaultdict(list)

        for idx, entry in enumerate(logs):
            tags = sorted(set(entry.tags))
            for i in range(len(tags)):
                for j in range(i + 1, len(tags)):
                    pair = (tags[i], tags[j])
                    pair_counts[pair] += 1
                    pair_indices[pair].append(idx)

        # Keep pairs with sufficient support
        themes = {}
        for pair, count in pair_counts.items():
            if count >= self.min_support:
                label = f"tag_theme:{pair[0]}+{pair[1]}"
                themes[label] = pair_indices[pair]

        return themes

    def _merge_clusters(
        self,
        text_clusters: Dict[str, List[int]],
        tag_themes: Dict[str, List[int]],
        logs: List[LogEntry],
    ) -> Dict[str, List[int]]:
        """Merge text clusters and tag themes, deduplicating overlapping groups."""
        merged = {}

        # Add text clusters
        for label, indices in text_clusters.items():
            merged[label] = indices

        # Add tag themes that don't significantly overlap with existing clusters
        for label, indices in tag_themes.items():
            indices_set = set(indices)
            is_redundant = False
            for existing_indices in merged.values():
                existing_set = set(existing_indices)
                overlap = len(indices_set & existing_set)
                if overlap > 0.7 * len(indices_set):
                    is_redundant = True
                    break

            if not is_redundant:
                merged[label] = indices

        return merged

    def _create_pattern(
        self,
        cluster_key: str,
        entry_indices: List[int],
        logs: List[LogEntry],
    ) -> Optional[PatternDefinition]:
        """Create a PatternDefinition from a semantic cluster."""
        entries = [logs[i] for i in entry_indices]
        if not entries:
            return None

        # Extract dominant event types as the "sequence"
        type_counts = Counter(e.event_type for e in entries)
        dominant_types = [t for t, _ in type_counts.most_common(5)]

        # Extract dominant tags
        all_tags = Counter()
        for e in entries:
            all_tags.update(e.tags)
        top_tags = [t for t, _ in all_tags.most_common(10)]

        # Build sequence signature: sorted unique event_type:top_tags
        sequence = []
        for et in dominant_types:
            relevant_tags = [t for t in top_tags if t != et][:3]
            tag_str = ','.join(relevant_tags) if relevant_tags else 'none'
            sequence.append(f"{et}:{tag_str}")

        # Calculate confidence: proportion of sessions containing this theme
        sessions = self._group_by_session(logs)
        cluster_sessions = set(entries[i].session_id for i, _ in enumerate(entries))
        total_sessions = len(sessions) or 1
        confidence = len(cluster_sessions) / total_sessions

        # Calculate stability
        dates = set()
        for e in entries:
            try:
                dates.add(datetime.fromisoformat(e.timestamp).date())
            except (ValueError, TypeError):
                pass
        stability_days = (max(dates) - min(dates)).days + 1 if dates else 0

        # Description
        description = self._generate_description(cluster_key, dominant_types, top_tags)

        # Exemplars
        exemplar_ids = [e.event_id for e in entries[:5]]

        # First/last seen
        timestamps = sorted(e.timestamp for e in entries)
        first_seen = timestamps[0] if timestamps else datetime.utcnow().isoformat()
        last_seen = timestamps[-1] if timestamps else datetime.utcnow().isoformat()

        skill_candidate = (
            len(entries) >= self.min_support
            and confidence >= self.min_confidence
            and stability_days >= self.min_stability_days
        )

        return PatternDefinition(
            pattern_type=PatternType.SEMANTIC.value,
            support=len(entries),
            confidence=round(confidence, 4),
            stability_days=stability_days,
            description=description,
            sequence=sequence,
            exemplar_ids=exemplar_ids,
            skill_candidate=skill_candidate,
            tags=top_tags,
            first_seen=first_seen,
            last_seen=last_seen,
        )

    def _group_by_session(self, logs: List[LogEntry]) -> Dict[str, List[LogEntry]]:
        """Group log entries by session_id."""
        sessions = defaultdict(list)
        for entry in logs:
            if entry.session_id:
                sessions[entry.session_id].append(entry)
        return dict(sessions)

    def _generate_description(
        self, cluster_key: str, types: List[str], tags: List[str]
    ) -> str:
        """Generate a human-readable description for a semantic cluster."""
        if cluster_key.startswith("tag_theme:"):
            theme = cluster_key.replace("tag_theme:", "")
            return f"Semantic theme around {theme} (types: {', '.join(types[:3])})"
        else:
            tag_str = ', '.join(tags[:4]) if tags else 'mixed'
            return f"Conceptual cluster [{tag_str}] (types: {', '.join(types[:3])})"
