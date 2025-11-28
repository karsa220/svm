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


# ------------------------------------------------------------
# Step 3: Standardization
# ------------------------------------------------------------
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


# ------------------------------------------------------------
# Helper: Train single binary classifier (for one class)
# ------------------------------------------------------------
def train_single_classifier(cls, kernel, C, hard_margin):
    y_binary = (y_train == cls).astype(int)

    if kernel == "linear":
        # LinearSVC is much faster than SVC(kernel="linear")
        if hard_margin:
            C_value = 1e5          # avoid C=1e10 instability
        else:
            C_value = C

        model = LinearSVC(C=C_value, max_iter=20000)
    else:
        # RBF uses SVC
        if hard_margin:
            C_value = 1e5
        else:
            C_value = C
        model = SVC(kernel="rbf", C=C_value)

    model.fit(X_train, y_binary)
    return model


def train_ovr_svm(kernel="linear", C=1.0, hard_margin=False):
    return Parallel(n_jobs=-1)(
        delayed(train_single_classifier)(cls, kernel, C, hard_margin)
        for cls in range(num_classes)
    )


# ------------------------------------------------------------
# OVR prediction
# ------------------------------------------------------------
def predict_ovr(classifiers, X):
    scores = np.vstack([clf.decision_function(X) for clf in classifiers])
    return np.argmax(scores, axis=0)


# ------------------------------------------------------------
# Evaluation
# ------------------------------------------------------------
def evaluate(kernel, C=None, hard=False):
    c_val = C if C is not None else 1.0

    models = train_ovr_svm(kernel=kernel, C=c_val, hard_margin=hard)
    pred_train = predict_ovr(models, X_train)
    pred_test = predict_ovr(models, X_test)

    acc_train = accuracy_score(y_train, pred_train)
    acc_test = accuracy_score(y_test, pred_test)

    if hard:
        desc = f"Hard-margin {kernel}"
    else:
        desc = f"Soft-margin {kernel} (C={C})"

    print(f"{desc}: Train {acc_train:.4f}, Test {acc_test:.4f}")


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
