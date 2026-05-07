"""Small sanity checks for the contest modeling Python environment."""

from __future__ import annotations

import math
import cmath


def quadratic_roots(a: float, b: float, c: float) -> tuple[float, float]:
    """Return the two real roots of ax^2 + bx + c = 0."""
    discriminant = b * b - 4 * a * c
    if a == 0:
        raise ValueError("a must be non-zero for a quadratic equation")
    if discriminant < 0:
        raise ValueError("this simple test only handles real roots")

    sqrt_disc = math.sqrt(discriminant)
    return ((-b - sqrt_disc) / (2 * a), (-b + sqrt_disc) / (2 * a))


def trapezoid_integral(start: float, end: float, steps: int) -> float:
    """Approximate the integral of sin(x) from start to end."""
    if steps <= 0:
        raise ValueError("steps must be positive")

    width = (end - start) / steps
    total = 0.5 * (math.sin(start) + math.sin(end))
    for index in range(1, steps):
        total += math.sin(start + index * width)
    return total * width


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve Ax = b using Gaussian elimination with partial pivoting."""
    size = len(vector)
    augmented = [row[:] + [rhs] for row, rhs in zip(matrix, vector)]

    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot_row][column]) < 1e-12:
            raise ValueError("matrix is singular or nearly singular")

        augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        pivot = augmented[column][column]
        augmented[column] = [value / pivot for value in augmented[column]]

        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[column])
            ]

    return [row[-1] for row in augmented]


def matrix_vector_product(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(value * vector[index] for index, value in enumerate(row)) for row in matrix]


def residual_norm(matrix: list[list[float]], solution: list[float], vector: list[float]) -> float:
    residual = [
        predicted - actual
        for predicted, actual in zip(matrix_vector_product(matrix, solution), vector)
    ]
    return math.sqrt(sum(value * value for value in residual))


def dominant_eigenvalue(matrix: list[list[float]], iterations: int = 100) -> float:
    """Estimate the largest eigenvalue of a real matrix using power iteration."""
    size = len(matrix)
    vector = [1.0 / math.sqrt(size)] * size

    for _ in range(iterations):
        next_vector = matrix_vector_product(matrix, vector)
        norm = math.sqrt(sum(value * value for value in next_vector))
        vector = [value / norm for value in next_vector]

    multiplied = matrix_vector_product(matrix, vector)
    return sum(left * right for left, right in zip(vector, multiplied))


def simpson_integral(start: float, end: float, steps: int) -> float:
    """Approximate the integral of exp(-x^2) using Simpson's rule."""
    if steps <= 0 or steps % 2:
        raise ValueError("steps must be a positive even number")

    width = (end - start) / steps
    total = math.exp(-(start * start)) + math.exp(-(end * end))

    for index in range(1, steps):
        x_value = start + index * width
        weight = 4 if index % 2 else 2
        total += weight * math.exp(-(x_value * x_value))

    return total * width / 3


def complex_polynomial_value(z_value: complex) -> complex:
    """Evaluate z^5 - 3z^2 + 2 for a complex input."""
    return z_value**5 - 3 * z_value**2 + 2


def main() -> None:
    roots = quadratic_roots(1, -3, 2)
    integral = trapezoid_integral(0, math.pi, 10_000)
    matrix = [
        [10.0, -1.0, 2.0, 0.0],
        [-1.0, 11.0, -1.0, 3.0],
        [2.0, -1.0, 10.0, -1.0],
        [0.0, 3.0, -1.0, 8.0],
    ]
    vector = [6.0, 25.0, -11.0, 15.0]
    solution = solve_linear_system(matrix, vector)
    residual = residual_norm(matrix, solution, vector)
    eigenvalue = dominant_eigenvalue(matrix)
    gaussian_integral = simpson_integral(0, 1, 10_000)
    complex_result = complex_polynomial_value(1 + 2j)

    print(f"Python math environment OK")
    print(f"Roots of x^2 - 3x + 2: {roots}")
    print(f"Integral of sin(x) from 0 to pi: {integral:.8f}")
    print(f"Linear system solution: {[round(value, 8) for value in solution]}")
    print(f"Linear system residual norm: {residual:.2e}")
    print(f"Dominant eigenvalue estimate: {eigenvalue:.8f}")
    print(f"Integral of exp(-x^2) from 0 to 1: {gaussian_integral:.8f}")
    print(f"Complex polynomial at 1 + 2i: {complex_result:.8g}")
    print(f"Complex magnitude: {abs(complex_result):.8f}")

    assert roots == (1.0, 2.0)
    assert math.isclose(integral, 2.0, rel_tol=1e-7, abs_tol=1e-7)
    assert residual < 1e-10
    assert math.isclose(gaussian_integral, math.sqrt(math.pi) * math.erf(1) / 2, rel_tol=1e-12)
    assert cmath.isclose(complex_result, 52 - 50j)


if __name__ == "__main__":
    main()
