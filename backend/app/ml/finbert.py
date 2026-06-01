"""
FinBERT singleton wrapper.

Loaded once at process startup; inference always runs in a thread-pool executor
so the FastAPI event loop is never blocked.
"""
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_BATCH_SIZE = 16
_MODEL_NAME = "ProsusAI/finbert"

_pipeline = None
_loading = False
_load_error: Exception | None = None
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="finbert")


def _load_pipeline() -> None:
    global _pipeline, _loading, _load_error
    _loading = True
    cache_dir = os.environ.get("TRANSFORMERS_CACHE", "/app/models")
    logger.info("Loading FinBERT model from HuggingFace (cache: %s)", cache_dir)
    try:
        from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
        # Load tokenizer and model separately so we control cache_dir
        # without forwarding it to the tokenizer __call__ during inference.
        tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, cache_dir=cache_dir)
        model = AutoModelForSequenceClassification.from_pretrained(
            _MODEL_NAME, cache_dir=cache_dir
        )
        _pipeline = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            return_all_scores=True,
            max_length=512,
            truncation=True,
        )
        logger.info("FinBERT loaded successfully")
    except Exception as exc:
        _load_error = exc
        logger.error("FinBERT failed to load: %s", exc)
    finally:
        _loading = False


def start_loading() -> None:
    """Call once from FastAPI lifespan to begin background model download."""
    _executor.submit(_load_pipeline)


def is_loaded() -> bool:
    return _pipeline is not None


def is_loading() -> bool:
    return _loading


def _score_batch_sync(texts: list[str]) -> list[dict]:
    """Synchronous inference — runs inside the thread executor."""
    if not texts:
        return []
    results = _pipeline(texts, batch_size=_BATCH_SIZE)
    output = []
    for item in results:
        scores = {entry["label"].lower(): entry["score"] for entry in item}
        label = max(scores, key=lambda k: scores[k])
        output.append({
            "positive": scores.get("positive", 0.0),
            "negative": scores.get("negative", 0.0),
            "neutral": scores.get("neutral", 0.0),
            "label": label,
        })
    return output


async def score_texts(texts: list[str]) -> list[dict]:
    """
    Async entry point — offloads FinBERT inference to the thread executor.
    Returns list of {positive, negative, neutral, label} dicts.
    """
    if not texts:
        return []
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _score_batch_sync, texts)
