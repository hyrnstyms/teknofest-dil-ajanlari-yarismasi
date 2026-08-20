from typing import Any, Dict, List

def calculate_accuracy(y_true: Any, y_pred: Any) -> float:
    return 1.0 if y_true == y_pred else 0.0

def calculate_precision_recall_f1(gold_items: List[Any], pred_items: List[Any]) -> Dict[str, float]:
    gold_set = set(gold_items)
    pred_set = set(pred_items)
    
    true_positives = len(gold_set.intersection(pred_set))
    
    precision = true_positives / len(pred_set) if pred_set else 0.0
    recall = true_positives / len(gold_set) if gold_set else 0.0
    
    f1 = 0.0
    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
        
    if not gold_set and not pred_set:
        precision, recall, f1 = 1.0, 1.0, 1.0
        
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def calculate_hit_at_k(gold_item: Any, pred_ranked_items: List[Any], k: int) -> float:
    return 1.0 if gold_item in pred_ranked_items[:k] else 0.0

def calculate_mrr(gold_item: Any, pred_ranked_items: List[Any]) -> float:
    for i, item in enumerate(pred_ranked_items):
        if item == gold_item:
            return 1.0 / (i + 1)
    return 0.0

def _naive_levenshtein(seq1, seq2):
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = [[0] * size_y for _ in range(size_x)]
    for x in range(size_x):
        matrix[x][0] = x
    for y in range(size_y):
        matrix[0][y] = y
    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x-1] == seq2[y-1]:
                matrix[x][y] = matrix[x-1][y-1]
            else:
                matrix[x][y] = min(
                    matrix[x-1][y] + 1,
                    matrix[x][y-1] + 1,
                    matrix[x-1][y-1] + 1
                )
    return matrix[size_x-1][size_y-1]

def calculate_cer_wer(gold_text: str, pred_text: str) -> Dict[str, float]:
    if not gold_text:
        return {"cer": 1.0, "wer": 1.0}
    
    char_distance = _naive_levenshtein(gold_text, pred_text)
    cer = min(char_distance / max(len(gold_text), 1), 1.0)
    
    gold_words = gold_text.split()
    pred_words = pred_text.split()
    if not gold_words:
        return {"cer": cer, "wer": 1.0}
        
    word_distance = _naive_levenshtein(gold_words, pred_words)
    wer = min(word_distance / max(len(gold_words), 1), 1.0)
    
    return {"cer": cer, "wer": wer}
