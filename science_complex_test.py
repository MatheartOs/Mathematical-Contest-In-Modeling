"""Run a multi-library scientific computing smoke test for MCM work."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import scipy.integrate
import scipy.linalg
import scipy.optimize
import seaborn as sns
import statsmodels.api as sm
import sympy as sp
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler


def run_linear_algebra() -> tuple[float, float]:
    rng = np.random.default_rng(20260507)
    matrix = rng.normal(size=(80, 80))
    positive_definite = matrix.T @ matrix + np.eye(80) * 0.25
    rhs = rng.normal(size=80)
    solution = scipy.linalg.solve(positive_definite, rhs, assume_a="pos")
    residual = np.linalg.norm(positive_definite @ solution - rhs)
    condition_number = np.linalg.cond(positive_definite)
    return residual, condition_number


def run_optimization() -> tuple[float, float, float]:
    def objective(values: np.ndarray) -> float:
        x_value, y_value = values
        return (x_value - 1.5) ** 2 + (y_value + 2.0) ** 2 + 0.1 * np.sin(5 * x_value)

    result = scipy.optimize.minimize(objective, x0=np.array([0.0, 0.0]), method="BFGS")
    if not result.success:
        raise RuntimeError(result.message)

    integral, error = scipy.integrate.quad(lambda x: np.exp(-x * x) * np.cos(3 * x), 0, 2)
    return result.fun, integral, error


def run_statistics_and_ml() -> tuple[float, float, float]:
    rng = np.random.default_rng(7)
    samples = 240
    x1 = rng.normal(size=samples)
    x2 = rng.uniform(-2, 2, size=samples)
    noise = rng.normal(scale=0.25, size=samples)
    target = 3.0 * x1 - 1.5 * x2 + 0.8 * x1 * x2 + noise

    frame = pd.DataFrame({"x1": x1, "x2": x2, "x1_x2": x1 * x2, "target": target})
    design = sm.add_constant(frame[["x1", "x2", "x1_x2"]])
    ols_model = sm.OLS(frame["target"], design).fit()

    features = frame[["x1", "x2", "x1_x2"]].to_numpy()
    scaled_features = StandardScaler().fit_transform(features)
    ridge = Ridge(alpha=0.1).fit(scaled_features, target)
    prediction = ridge.predict(scaled_features)
    pca = PCA(n_components=2).fit(scaled_features)

    return float(ols_model.rsquared), float(r2_score(target, prediction)), float(pca.explained_variance_ratio_.sum())


def run_symbolic_and_graph() -> tuple[sp.Expr, float]:
    x_value = sp.symbols("x")
    symbolic_integral = sp.integrate(sp.exp(-x_value) * sp.sin(x_value), (x_value, 0, sp.pi))

    graph = nx.Graph()
    graph.add_weighted_edges_from(
        [
            ("A", "B", 4.0),
            ("A", "C", 2.0),
            ("B", "C", 1.0),
            ("B", "D", 5.0),
            ("C", "D", 8.0),
            ("C", "E", 10.0),
            ("D", "E", 2.0),
            ("D", "F", 6.0),
            ("E", "F", 3.0),
        ]
    )
    shortest_path_length = nx.shortest_path_length(graph, "A", "F", weight="weight")
    return sp.simplify(symbolic_integral), float(shortest_path_length)


def save_plot() -> Path:
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    plot_path = output_dir / "science_complex_test.png"

    rng = np.random.default_rng(42)
    frame = pd.DataFrame(
        {
            "x": rng.normal(size=400),
            "y": rng.normal(size=400),
            "group": rng.choice(["model_a", "model_b", "model_c"], size=400),
        }
    )

    sns.set_theme(style="whitegrid")
    figure, axis = plt.subplots(figsize=(7, 4.5))
    sns.scatterplot(data=frame, x="x", y="y", hue="group", alpha=0.75, ax=axis)
    axis.set_title("Scientific stack plotting check")
    figure.tight_layout()
    figure.savefig(plot_path, dpi=150)
    plt.close(figure)

    return plot_path


def main() -> None:
    residual, condition_number = run_linear_algebra()
    optimum, integral, integration_error = run_optimization()
    ols_r2, ridge_r2, pca_ratio = run_statistics_and_ml()
    symbolic_integral, shortest_path = run_symbolic_and_graph()
    plot_path = save_plot()

    print("Advanced scientific computing test OK")
    print(f"Linear solve residual: {residual:.3e}")
    print(f"Matrix condition number: {condition_number:.3e}")
    print(f"Optimization objective minimum: {optimum:.8f}")
    print(f"Oscillatory Gaussian integral: {integral:.8f} +/- {integration_error:.1e}")
    print(f"Statsmodels OLS R^2: {ols_r2:.6f}")
    print(f"Scikit-learn Ridge R^2: {ridge_r2:.6f}")
    print(f"PCA explained variance ratio sum: {pca_ratio:.6f}")
    print(f"Sympy integral result: {symbolic_integral}")
    print(f"NetworkX shortest path A -> F: {shortest_path:.2f}")
    print(f"Plot saved to: {plot_path}")

    assert residual < 1e-10
    assert condition_number > 1.0
    assert optimum < 0.2
    assert integration_error < 1e-10
    assert ols_r2 > 0.98
    assert ridge_r2 > 0.98
    assert 0.5 < pca_ratio <= 1.0
    x_value = sp.symbols("x")
    expected_integral = sp.integrate(sp.exp(-x_value) * sp.sin(x_value), (x_value, 0, sp.pi))
    assert sp.simplify(symbolic_integral - expected_integral) == 0
    assert shortest_path == 13.0
    assert plot_path.exists() and plot_path.stat().st_size > 0


if __name__ == "__main__":
    main()
