class ConsensusIntelligenceEngine:

    def __init__(self):
        self.engine_weights = {
            "forensic_score": 35,
            "origin_score": 25,
            "metadata_score": 15,
            "manipulation_score": 15,
            "human_authenticity_score": 10,
        }

    def normalize_score(self, value):
        if value is None:
            return 0

        return max(0, min(100, value))

    def calculate_consensus(self, engine_scores):
        total = 0
        weight_total = 0

        for engine_name, weight in self.engine_weights.items():
            score = self.normalize_score(engine_scores.get(engine_name))

            total += score * weight
            weight_total += weight

        if weight_total == 0:
            return 0

        return round(total / weight_total, 2)

    def classify_consensus(self, consensus_score):
        if consensus_score >= 85:
            return "Strong AI / Synthetic Consensus"

        if consensus_score >= 65:
            return "Likely AI / Synthetic Consensus"

        if consensus_score >= 45:
            return "Mixed / Inconclusive Consensus"

        if consensus_score >= 20:
            return "Likely Human / Authentic Consensus"

        return "Strong Human / Authentic Consensus"

    def explain_consensus(self, engine_scores):
        explanations = []

        for engine_name, score in engine_scores.items():
            explanations.append({
                "engine": engine_name,
                "score": self.normalize_score(score),
                "weight": self.engine_weights.get(engine_name, 0),
            })

        return explanations

    def build_consensus_result(self, engine_scores):
        consensus_score = self.calculate_consensus(engine_scores)
        consensus_label = self.classify_consensus(consensus_score)
        explanation = self.explain_consensus(engine_scores)

        return {
            "consensus_score": consensus_score,
            "consensus_label": consensus_label,
            "engine_breakdown": explanation,
        }
