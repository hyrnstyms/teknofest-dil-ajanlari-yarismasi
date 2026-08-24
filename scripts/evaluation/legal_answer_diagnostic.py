import difflib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


class AttributionStatus(str, Enum):
    HIGH_CONFIDENCE_SAME = "HIGH_CONFIDENCE_SAME"
    HIGH_CONFIDENCE_MISMATCH = "HIGH_CONFIDENCE_MISMATCH"
    AMBIGUOUS = "AMBIGUOUS"
    ANSWER_NOT_SUPPORTED = "ANSWER_NOT_SUPPORTED"
    MALFORMED = "MALFORMED"


@dataclass(frozen=True)
class ArticleSegment:
    article: str
    text: str


@dataclass(frozen=True)
class AnswerAttribution:
    status: AttributionStatus
    primary_article: str = ""
    confidence: float = 0.0
    margin: float = 0.0
    second_score: float = 0.0
    article_count: int = 0
    method: str = ""


# Limitation: GEÇİCİ MADDE 1 and MADDE 1 share the numeric identity "1".
# The checked repository datasets contain no context where those identities collide.
ARTICLE_HEADING_RE = re.compile(
    r"(?i)(?:\bGEÇİCİ\s+)?\bMADDE\s+(\d+(?:/[a-z])?)\s*\.?\s*[-–—]"
)
TOKEN_RE = re.compile(r"[a-zçğıöşü0-9/]+")
STOPWORDS = set(
    "ve veya ile bir bu şu o da de için gibi göre olarak olan ise mi mı mu mü ne "
    "hangi nasıl kadar daha en ancak fakat tarafından üzere ilgili dolayı karşı "
    "her aynı sonra önce içinde dışı".split()
)


def normalize_answer(value: Any) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value).strip())
    text = text.casefold().replace("̇", "")
    text = text.translate(str.maketrans({"â": "a", "î": "i", "û": "u"}))
    return " ".join(TOKEN_RE.findall(text))


def split_context_into_articles(
    context: Any,
    context_article_numbers: Any = "",
    normalize_article: Callable[[Any], str] = lambda value: str(value).strip().lower(),
) -> list[ArticleSegment]:
    text = "" if context is None else str(context).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return []
    matches = list(ARTICLE_HEADING_RE.finditer(text))
    if matches:
        return [
            ArticleSegment(
                normalize_article(match.group(1)),
                text[match.start() : matches[index + 1].start()]
                if index + 1 < len(matches)
                else text[match.start() :],
            )
            for index, match in enumerate(matches)
        ]
    articles: list[str] = []
    for value in re.findall(
        r"\d+(?:/[a-zA-Z])?",
        "" if context_article_numbers is None else str(context_article_numbers),
    ):
        article = normalize_article(value)
        if article and article not in articles:
            articles.append(article)
    return [ArticleSegment(articles[0], text)] if len(articles) == 1 else []


def _tokens(text: Any) -> list[str]:
    return [
        token
        for token in normalize_answer(text).split()
        if len(token) > 2 and token not in STOPWORDS
    ]


def _partial_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return fuzz.partial_ratio(left, right) / 100.0
    shorter, longer = sorted((left, right), key=len)
    if shorter in longer:
        return 1.0
    return difflib.SequenceMatcher(None, shorter, longer).ratio()


def score_answer_against_article(answer: Any, article_text: Any) -> tuple[float, str]:
    """Reproduce the audit's exact/recall/fuzzy/answer-sentence score."""
    normalized_answer = normalize_answer(answer)
    normalized_article = normalize_answer(article_text)
    if not normalized_answer or not normalized_article:
        return 0.0, "none"
    if normalized_answer in normalized_article:
        return 1.0, "exact"

    answer_tokens = _tokens(answer)
    article_tokens = set(_tokens(article_text))
    lexical = sum(token in article_tokens for token in answer_tokens) / max(
        1, len(answer_tokens)
    )
    fuzzy_score = _partial_ratio(normalized_answer, normalized_article)
    sentence_scores: list[tuple[int, float]] = []
    for sentence in re.split(r"(?<=[.!?])\s+", str(answer)):
        sentence_tokens = _tokens(sentence)
        if not sentence_tokens:
            continue
        sentence_lexical = sum(
            token in article_tokens for token in sentence_tokens
        ) / len(sentence_tokens)
        sentence_fuzzy = _partial_ratio(
            normalize_answer(sentence), normalized_article
        )
        sentence_scores.append(
            (len(sentence_tokens), (sentence_lexical + sentence_fuzzy) / 2.0)
        )
    sentence_score = sum(
        weight * score for weight, score in sentence_scores
    ) / max(1, sum(weight for weight, _ in sentence_scores))
    combined = 0.5 * lexical + 0.3 * fuzzy_score + 0.2 * sentence_score
    return combined, "lexical_fuzzy_sentence"


def attribute_answer_to_article(
    context: Any,
    answer: Any,
    anchor_article: Any,
    context_article_numbers: Any = "",
    normalize_article: Callable[[Any], str] = lambda value: str(value).strip().lower(),
) -> AnswerAttribution:
    segments = split_context_into_articles(
        context, context_article_numbers, normalize_article
    )
    if not segments or not normalize_answer(answer):
        return AnswerAttribution(
            AttributionStatus.MALFORMED, article_count=len(segments)
        )

    scored = [
        (segment, *score_answer_against_article(answer, segment.text))
        for segment in segments
    ]
    exact = [entry for entry in scored if entry[1] == 1.0]
    if len(exact) > 1:
        return AnswerAttribution(
            AttributionStatus.AMBIGUOUS,
            confidence=1.0,
            second_score=1.0,
            article_count=len(segments),
            method="exact",
        )

    scored.sort(key=lambda entry: (-entry[1], entry[0].article))
    best, best_score, method = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0
    margin = best_score - second_score
    if best_score < 0.48:
        return AnswerAttribution(
            AttributionStatus.ANSWER_NOT_SUPPORTED,
            primary_article=best.article,
            confidence=best_score,
            margin=margin,
            second_score=second_score,
            article_count=len(segments),
            method=method,
        )

    high_confidence = (
        bool(exact)
        or (best_score >= 0.72 and margin >= 0.10)
        or (len(segments) == 1 and best_score >= 0.58)
    )
    if not high_confidence:
        return AnswerAttribution(
            AttributionStatus.AMBIGUOUS,
            primary_article=best.article,
            confidence=best_score,
            margin=margin,
            second_score=second_score,
            article_count=len(segments),
            method=method,
        )

    status = (
        AttributionStatus.HIGH_CONFIDENCE_SAME
        if best.article == normalize_article(anchor_article)
        else AttributionStatus.HIGH_CONFIDENCE_MISMATCH
    )
    return AnswerAttribution(
        status,
        best.article,
        best_score,
        margin,
        second_score,
        len(segments),
        method,
    )


def ranking_metrics(
    ranks: list[int], denominator: int, prefix: str = ""
) -> dict[str, float]:
    if denominator <= 0:
        return {}
    return {
        f"{prefix}hit@1": sum(0 < rank <= 1 for rank in ranks) / denominator,
        f"{prefix}hit@3": sum(0 < rank <= 3 for rank in ranks) / denominator,
        f"{prefix}hit@5": sum(0 < rank <= 5 for rank in ranks) / denominator,
        f"{prefix}mrr": sum(1.0 / rank for rank in ranks if rank > 0) / denominator,
    }
