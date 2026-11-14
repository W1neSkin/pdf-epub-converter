//! Матрица преобразования PDF: [a b c d e f].
//! Точка переводится так: x' = a*x + c*y + e, y' = b*x + d*y + f.

#[derive(Clone, Copy, Debug)]
pub struct Matrix {
    pub a: f32,
    pub b: f32,
    pub c: f32,
    pub d: f32,
    pub e: f32,
    pub f: f32,
}

impl Matrix {
    pub fn identity() -> Self {
        Self { a: 1.0, b: 0.0, c: 0.0, d: 1.0, e: 0.0, f: 0.0 }
    }

    pub fn translate(x: f32, y: f32) -> Self {
        Self { a: 1.0, b: 0.0, c: 0.0, d: 1.0, e: x, f: y }
    }

    /// `first` применяется к точке раньше, чем `second`.
    /// Так PDF присоединяет матрицу команды `cm` к текущей.
    pub fn concat(first: Self, second: Self) -> Self {
        Self {
            a: first.a * second.a + first.b * second.c,
            b: first.a * second.b + first.b * second.d,
            c: first.c * second.a + first.d * second.c,
            d: first.c * second.b + first.d * second.d,
            e: first.e * second.a + first.f * second.c + second.e,
            f: first.e * second.b + first.f * second.d + second.f,
        }
    }

    pub fn transform(self, x: f32, y: f32) -> (f32, f32) {
        (self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f)
    }

    /// Во сколько раз матрица растягивает штрих по горизонтали.
    pub fn scale_x(self) -> f32 {
        (self.a * self.a + self.b * self.b).sqrt()
    }
}
