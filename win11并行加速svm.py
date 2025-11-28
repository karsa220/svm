import numpy as np
from sklearn.svm import SVC, LinearSVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from joblib import Parallel, delayed

# ------------------------------------------------------------
# Step 1: Load txt data
# ------------------------------------------------------------
features = np.loadtxt("./resnet101/AwA2-features.txt")
labels = np.loadtxt("./resnet101/AwA2-labels.txt").astype(int) - 1
num_classes = len(np.unique(labels))

print(f"Loaded features: {features.shape}, classes: {num_classes}")

# ------------------------------------------------------------
# Step 2: 60/40 split by class
# ------------------------------------------------------------
X_train, y_train, X_test, y_test = [], [], [], []

for cls in range(num_classes):
    idx = np.where(labels == cls)[0]

    train_idx, test_idx = train_test_split(
        idx, test_size=0.4, shuffle=True, random_state=42
    )
    X_train.append(features[train_idx])
    y_train.append(labels[train_idx])
    X_test.append(features[test_idx])
    y_test.append(labels[test_idx])

X_train = np.vstack(X_train)
y_train = np.hstack(y_train)
X_test = np.vstack(X_test)
y_test = np.hstack(y_test)

print("Train:", X_train.shape, "Test:", X_test.shape)

# Scale
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


# ------------------------------------------------------------
# Helper: Train one-vs-rest SVM classifier for one class
# ------------------------------------------------------------
def train_one_class(cls, kernel, C, hard):
    y_binary = (y_train == cls).astype(int)

    if kernel == "linear":
        # Use LIBLINEAR for speed
        if hard:
            model = LinearSVC(C=1e5, max_iter=20000)  # hard-margin (approx)
        else:
            model = LinearSVC(C=C, max_iter=20000)

    else:  # RBF kernel
        if hard:
            model = SVC(kernel="rbf", C=1e5)
        else:
            model = SVC(kernel="rbf", C=C)

    model.fit(X_train, y_binary)
    return model


# ------------------------------------------------------------
# Train OVR SVM
# ------------------------------------------------------------
def train_ovr(kernel="linear", C=1, hard=False):
    models = Parallel(n_jobs=-1)(
        delayed(train_one_class)(cls, kernel, C, hard)
        for cls in range(num_classes)
    )
    return models


# ------------------------------------------------------------
# Prediction
# ------------------------------------------------------------
def predict_ovr(models, X):
    scores = np.vstack([m.decision_function(X) for m in models])
    return np.argmax(scores, axis=0)


# ------------------------------------------------------------
# Evaluation wrapper
# ------------------------------------------------------------
def evaluate(kernel, C=None, hard=False):
    C_val = C if C is not None else 1

    models = train_ovr(kernel=kernel, C=C_val, hard=hard)

    pred_train = predict_ovr(models, X_train)
    pred_test = predict_ovr(models, X_test)

    acc_train = accuracy_score(y_train, pred_train)
    acc_test = accuracy_score(y_test, pred_test)

    if hard:
        print(f"[Hard-margin] {kernel}: Train={acc_train:.4f}, Test={acc_test:.4f}")
    else:
        print(f"[Soft-margin] {kernel}, C={C_val}: Train={acc_train:.4f}, Test={acc_test:.4f}")


# ------------------------------------------------------------
# Experiments required by assignment
# ------------------------------------------------------------

# 1. Hard-margin linear
evaluate(kernel="linear", hard=True)

# 2. Soft-margin linear, tune C
for C in [0.01, 0.1, 1, 10, 100]:
    evaluate(kernel="linear", C=C)

# 3. Hard-margin RBF
evaluate(kernel="rbf", hard=True)

# 4. Soft-margin RBF
for C in [0.01, 0.1, 1, 10, 100]:
    evaluate(kernel="rbf", C=C)
