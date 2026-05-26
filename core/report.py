class ForensicReportFormatter:

    def build_report(self, reasoning_result):

        analysis = reasoning_result.get("analysis", {})
        origin = reasoning_result.get("origin", {})
        consensus = reasoning_result.get("consensus", {})
        adversarial = reasoning_result.get("adversarial", {})
        provenance = reasoning_result.get("provenance", {})
        trace = reasoning_result.get("trace", {})

        report = {
            "summary": {
                "label": analysis.get("label"),
                "ai_score": analysis.get("ai_score"),
                "confidence": analysis.get("confidence"),
            },

            "origin_analysis": origin,

            "consensus_analysis": consensus,

            "adversarial_analysis": adversarial,

            "provenance_analysis": provenance,

            "trace_analysis": trace,

            "evidence": analysis.get("evidence", []),

            "warnings": reasoning_result.get("warnings", []),

            "constitutional_law":
                reasoning_result.get("constitution_law"),

            "highest_duty":
                reasoning_result.get("highest_duty"),
        }

        return report
