import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from collections import defaultdict


# ------------------------------------------------------------
# Step 1: Load txt data
# ------------------------------------------------------------
# features.txt: each line is 2048-dim ResNet feature
features = np.loadtxt("./resnet101/AwA2-features.txt")

# labels.txt: each line is class index (1~50)
# convert to 0~49
labels = np.loadtxt("./resnet101/AwA2-labels.txt").astype(int) - 1

num_classes = len(np.unique(labels))
print(f"Loaded features: {features.shape}, classes: {num_classes}")


# ------------------------------------------------------------
# Step 2: 60/40 split by class
# ------------------------------------------------------------
X_train, y_train, X_test, y_test = [], [], [], []

for cls in range(num_classes):
    idx = np.where(labels == cls)[0]
    cls_feat = features[idx]

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

# Standardize
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


# ------------------------------------------------------------
# Helper: One-vs-Rest SVM training
# ------------------------------------------------------------
def train_ovr_svm(kernel="linear", C=1e5, hard_margin=False):
    classifiers = []

    for cls in range(num_classes):
        y_binary = (y_train == cls).astype(int)

        if hard_margin:
            # Hard-margin: effectively C → ∞
            model = SVC(kernel=kernel, C=1e10)
        else:
            model = SVC(kernel=kernel, C=C)

        model.fit(X_train, y_binary)
        classifiers.append(model)

    return classifiers


def predict_ovr(classifiers, X):
    # For each classifier, use decision_function
    scores = np.vstack([clf.decision_function(X) for clf in classifiers])
    pred = np.argmax(scores, axis=0)
    return pred


# ------------------------------------------------------------
# Step 3: Train & Evaluate
# ------------------------------------------------------------

def evaluate(kernel, C=None, hard=False):
    cls = train_ovr_svm(kernel=kernel, C=C if C else 1, hard_margin=hard)
    pred_train = predict_ovr(cls, X_train)
    pred_test = predict_ovr(cls, X_test)

    acc_train = accuracy_score(y_train, pred_train)
    acc_test = accuracy_score(y_test, pred_test)

    if hard:
        name = f"Hard-margin {kernel}"
    else:
        name = f"Soft-margin {kernel} (C={C})"

    print(f"{name}: Train {acc_train:.4f}, Test {acc_test:.4f}")


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
