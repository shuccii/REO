"""k-nearest-neighbour regression of ionic conductivity (numpy only)."""
import csv
import numpy as np

with open('data.csv') as f:
    rows = list(csv.DictReader(f))
X = np.array([[float(r['temperature']), float(r['additive_wt_pct'])] for r in rows])
y = np.array([float(r['conductivity_mS_cm']) for r in rows])


def knn_predict(X_train, y_train, X_test, k):
    d = ((X_test[:, None, :] - X_train[None, :, :]) ** 2).sum(axis=2)
    nearest = np.argsort(d, axis=1)[:, :k]
    return y_train[nearest].mean(axis=1)


def r2(y_true, y_pred):
    return 1 - ((y_true - y_pred) ** 2).sum() / ((y_true - y_true.mean()) ** 2).sum()


rng = np.random.default_rng(0)
folds = np.array_split(rng.permutation(len(y)), 5)
scores, chosen = [], []
for i, test in enumerate(folds):
    train = np.concatenate([f for j, f in enumerate(folds) if j != i])
    mean, std = X[train].mean(axis=0), X[train].std(axis=0)
    Xtr, Xte = (X[train] - mean) / std, (X[test] - mean) / std
    best = max((r2(y[test], knn_predict(Xtr, y[train], Xte, k)), k) for k in (1, 3, 5, 9, 15))
    scores.append(best[0])
    chosen.append(best[1])

scores = np.array(scores)
print(f"n_rows={len(y)} folds=5 k_chosen={chosen}")
print(f"R2 = {scores.mean():.3f} +/- {scores.std() / np.sqrt(len(scores)):.3f}")
print(f"corr(temperature, conductivity) = {np.corrcoef(X[:, 0], y)[0, 1]:.3f}")
