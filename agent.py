"""Agent central qui enchaîne toutes les capacités."""
from db_connector import DBConnector
from query_analyzer import QueryAnalyzer
from slow_query_detector import SlowQueryDetector
from index_advisor import IndexAdvisor
from performance_explainer import PerformanceExplainer
from sql_generator import SQLGenerator
from llm_client import LLMClient

class DBAgent:
    def __init__(self, db_path: str, slow_threshold_ms: float = 100.0):
        self.db = DBConnector(db_path)
        self.llm = LLMClient()
        self.analyzer = QueryAnalyzer(self.db)
        self.detector = SlowQueryDetector(self.db, slow_threshold_ms)
        self.advisor = IndexAdvisor(self.db)
        self.explainer = PerformanceExplainer()
        self.sql_gen = SQLGenerator(self.db, self.llm)
 
    def full_diagnostic(self, query: str) -> dict:
        """Analyse complète : requête → analyse → benchmark → index → explication."""
        analysis = self.analyzer.analyze(query)
        benchmark = self.detector.benchmark(query)
        suggestions = self.advisor.recommend(query)
        report = self.explainer.explain(analysis, benchmark, suggestions)

        # enrichissement LLM optionnel
        llm_note = None
        if self.llm.is_available():
            llm_note = self.llm.ask(
                f"Requête SQL : {query}\n\nPlan : {benchmark['plan']}\n\n"
                f"Problèmes : {analysis['issues']}\n\n"
                f"Explique en 3 phrases les causes de lenteur et 2 optimisations prioritaires.",
                system="Tu es un DBA senior. Réponds en français, de façon concise et technique.",
            )

        return {
            "analysis": analysis,
            "benchmark": benchmark,
            "index_suggestions": suggestions,
            "report": report,
            "llm_advice": llm_note,
        }

    def nl2sql(self, question: str) -> dict:
        return self.sql_gen.generate(question)

    def close(self):
        self.db.close()