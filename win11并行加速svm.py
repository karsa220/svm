import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from joblib import Parallel, delayed


# ------------------------------------------------------------
# Step 1: Load txt data
# ------------------------------------------------------------
features = np.loadtxt("./resnet101/AwA2-features.txt")
labels = np.loadtxt("./resnet101/AwA2-labels.txt").astype(int) - 1  # 0~49

num_classes = len(np.unique(labels))
print(f"Loaded features: {features.shape}, classes: {num_classes}")


# ------------------------------------------------------------
# Step 2: 60/40 split by class
# ------------------------------------------------------------
X_train, y_train, X_test, y_test = [], [], [], []

for cls in range(num_classes):
    idx = np.where(labels == cls)[0]

    train_idx, test_idx = train_test_split(
        idx, test_size=0.4, random_state=42, shuffle=True
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
# Standardize
# ------------------------------------------------------------
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


# ------------------------------------------------------------
# Parallel One-vs-Rest SVM
# ------------------------------------------------------------
def train_single_class(cls, kernel, C, hard_margin):
    y_binary = (y_train == cls).astype(int)

    if hard_margin:
        model = SVC(kernel=kernel, C=1e10)
    else:
        model = SVC(kernel=kernel, C=C)

    model.fit(X_train, y_binary)
    return model


def train_ovr_svm(kernel="linear", C=1.0, hard_margin=False, n_jobs=-1):
    # Train 50 classifiers in parallel
    classifiers = Parallel(n_jobs=n_jobs)(
        delayed(train_single_class)(cls, kernel, C, hard_margin)
        for cls in range(num_classes)
    )
    return classifiers


def predict_ovr(classifiers, X):
    # decision_function returns (n_samples,)
    scores = np.vstack([clf.decision_function(X) for clf in classifiers])
    return np.argmax(scores, axis=0)


# ------------------------------------------------------------
# Evaluation
# ------------------------------------------------------------
def evaluate(kernel, C=None, hard=False):
    if hard:
        C_val = 1.0
    else:
        C_val = C

    classifiers = train_ovr_svm(kernel=kernel, C=C_val, hard_margin=hard, n_jobs=-1)

    pred_train = predict_ovr(classifiers, X_train)
    pred_test = predict_ovr(classifiers, X_test)

    acc_train = accuracy_score(y_train, pred_train)
    acc_test = accuracy_score(y_test, pred_test)

    if hard:
        print(f"Hard-margin {kernel}: Train {acc_train:.4f}, Test {acc_test:.4f}")
    else:
        print(f"Soft-margin {kernel} (C={C}): Train {acc_train:.4f}, Test {acc_test:.4f}")


# ------------------------------------------------------------
# Required Experiments
# ------------------------------------------------------------
# 1. Hard-margin linear
evaluate(kernel="linear", hard=True)

# 2. Soft-margin linear
for C in [0.01, 0.1, 1, 10, 100]:
    evaluate(kernel="linear", C=C)

# 3. Hard-margin RBF
evaluate(kernel="rbf", hard=True)

# 4. Soft-margin RBF
for C in [0.01, 0.1, 1, 10, 100]:
    evaluate(kernel="rbf", C=C)
