"""Кластеризация дневных маршрутов (этап предобработки).

Data-driven замена эвристике архетипов: маршруты группируются k-means по признакам,
число кластеров k подбирается по силуэту, каждому кластеру даётся авто-описание по
центроиду. Детерминировано (фиксированный seed). Чистая функция — легко тестировать.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

# признаки маршрута для кластеризации (имена совпадают с полями DayRoute)
FEATURES = ["concerts_count", "transition_minutes", "wait_minutes",
            "cost_kopecks", "diversity_score", "hall_changes"]

# (фраза при z>0, фраза при z<0) по каждому признаку
_PHRASES = {
    0: ("много концертов", "мало концертов"),
    1: ("много переходов", "мало переходов"),
    2: ("много ожидания", "мало ожидания"),
    3: ("дороже", "дешевле"),
    4: ("разнообразная программа", "узкая программа"),
    5: ("частые смены залов", "редкие смены залов"),
}
SEED = 42
_Z = 0.5  # порог «выраженности» признака для подписи


def _describe(i: int, X: np.ndarray, labels: List[int],
              gmean: np.ndarray, gstd: np.ndarray) -> Dict:
    idx = [j for j, lab in enumerate(labels) if lab == i]
    mean = X[idx].mean(axis=0)
    z = np.array([(mean[f] - gmean[f]) / gstd[f] if gstd[f] > 1e-9 else 0.0
                  for f in range(len(mean))])
    traits = []
    for f in sorted(range(len(mean)), key=lambda f: abs(z[f]), reverse=True):
        if abs(z[f]) < _Z or len(traits) == 2:
            break
        pos, neg = _PHRASES[f]
        traits.append(pos if z[f] > 0 else neg)
    title = ", ".join(traits) if traits else "сбалансированный маршрут"
    title = title[0].upper() + title[1:]
    desc = (f"≈{round(mean[0])} концертов · переходы {round(mean[1])} мин · "
            f"ожидание {round(mean[2])} мин · разнообразие {round(mean[4])}")
    return {"key": f"cluster-{i}", "title": title, "description": desc, "size": len(idx)}


def cluster_routes(rows: List[Dict], max_k: int = 8) -> Tuple[List[int], List[Dict]]:
    """rows: список словарей с ключами FEATURES. → (метки кластеров, описания кластеров)."""
    n = len(rows)
    if n == 0:
        return [], []
    X = np.array([[float(r[f]) for f in FEATURES] for r in rows], dtype=float)
    gmean, gstd = X.mean(axis=0), X.std(axis=0)

    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    Xs = StandardScaler().fit_transform(X)
    distinct = len({tuple(np.round(row, 6)) for row in Xs.tolist()})
    if n < 4 or distinct < 2:  # мало данных / нет вариативности → один кластер
        labels = [0] * n
        return labels, [_describe(0, X, labels, gmean, gstd)]

    best = None  # (silhouette, k, labels)
    for k in range(2, min(max_k, n - 1, distinct) + 1):  # k не больше числа уникальных точек
        lab = KMeans(n_clusters=k, random_state=SEED, n_init=10).fit_predict(Xs)
        if len(set(lab)) < 2:
            continue
        score = silhouette_score(Xs, lab)
        if best is None or score > best[0]:
            best = (score, k, lab)
    if best is None:
        labels = [0] * n
        return labels, [_describe(0, X, labels, gmean, gstd)]

    _, k, lab = best
    labels = [int(x) for x in lab]
    return labels, [_describe(i, X, labels, gmean, gstd) for i in range(k)]
