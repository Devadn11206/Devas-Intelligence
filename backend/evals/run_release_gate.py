"""Unified CLI Release Gate Runner for DEVA Intelligence CI/CD.

Executes both Retrieval and RAG Faithfulness benchmarks.
Enforces quantitative thresholds:
1. Retrieval Recall@10 >= 0.80
2. Citation Resolution Rate == 1.0 (100%)
3. Unanswerable Refusal Rate == 1.0 (100%)
4. Entity Linker Ground-Truth Resolution >= 0.85

Exits with code 0 on success, or code 1 on failure to block production release.
"""
import sys
import asyncio
import logging
from evals.retrieval_eval import evaluate_retrieval
from evals.rag_and_linker_eval import evaluate_rag_and_linker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evals.gate")


async def run_all_gates() -> bool:
    logger.info("==================================================================")
    logger.info("STARTING DEVA INTELLIGENCE QUANTITATIVE MLFLOW RELEASE GATES")
    logger.info("==================================================================")

    passed = True

    # 1. Retrieval Benchmarks
    logger.info("--> Executing Retrieval & Reranking Benchmarks...")
    retrieval_metrics = await evaluate_retrieval()
    hybrid_rec10 = retrieval_metrics["hybrid"]["recall_at_10"]
    hybrid_mrr = retrieval_metrics["hybrid"]["mrr_at_10"]

    if hybrid_rec10 < 0.80:
        logger.error(f"[GATE FAILED] Hybrid Recall@10={hybrid_rec10} < 0.80 threshold")
        passed = False
    else:
        logger.info(f"[GATE PASSED] Hybrid Recall@10={hybrid_rec10} >= 0.80 (MRR={hybrid_mrr})")

    # 2. RAG Faithfulness & Linker Benchmarks
    logger.info("--> Executing RAG Faithfulness & Entity Linker Benchmarks...")
    rag_metrics = await evaluate_rag_and_linker()

    citation_rate = rag_metrics["citation_resolution_rate"]
    refusal_rate = rag_metrics["unanswerable_refusal_rate"]
    linker_rate = rag_metrics["linker_precision_recall"]

    if citation_rate < 1.0:
        logger.error(f"[GATE FAILED] Citation Resolution Rate={citation_rate} < 1.0")
        passed = False
    else:
        logger.info(f"[GATE PASSED] Citation Resolution Rate={citation_rate} (100% verified provenance)")

    if refusal_rate < 1.0:
        logger.error(f"[GATE FAILED] Unanswerable Refusal Rate={refusal_rate} < 1.0")
        passed = False
    else:
        logger.info(f"[GATE PASSED] Unanswerable Refusal Rate={refusal_rate} (100% anti-hallucination)")

    if linker_rate < 0.85:
        logger.error(f"[GATE FAILED] Entity Linker Precision={linker_rate} < 0.85")
        passed = False
    else:
        logger.info(f"[GATE PASSED] Entity Linker Precision={linker_rate} >= 0.85")

    logger.info("==================================================================")
    if passed:
        logger.info("ALL DEVA INTELLIGENCE RELEASE GATES PASSED SUCCESSFULLY!")
        logger.info("Artifacts & metrics recorded in MLflow tracking registry.")
    else:
        logger.error("ONE OR MORE RELEASE GATES FAILED. PRODUCTION DEPLOYMENT HALTED.")
    logger.info("==================================================================")

    return passed


def main():
    success = asyncio.run(run_all_gates())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
