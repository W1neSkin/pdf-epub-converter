//! Геометрия страницы. Единица — пункт PDF, он же пункт CSS: 1/72 дюйма.
//! Начало координат у PDF снизу слева. В структурах координаты остаются такими,
//! как в файле. Переворот в верхний левый угол делает уже запись в HTML.

/// Точка на странице.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Point {
    pub x: f32,
    pub y: f32,
}

/// Прямоугольник. `x` и `y` — левый нижний угол.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Rect {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}

impl Rect {
    /// Прямоугольник по левому нижнему и правому верхнему углу.
    pub fn from_minmax(x0: f32, y0: f32, x1: f32, y1: f32) -> Self {
        let (min_x, max_x) = if x0 <= x1 { (x0, x1) } else { (x1, x0) };
        let (min_y, max_y) = if y0 <= y1 { (y0, y1) } else { (y1, y0) };
        Self {
            x: min_x,
            y: min_y,
            width: max_x - min_x,
            height: max_y - min_y,
        }
    }

    pub fn union(self, other: Self) -> Self {
        if self.width == 0.0 && self.height == 0.0 {
            return other;
        }
        Self::from_minmax(
            self.x.min(other.x),
            self.y.min(other.y),
            (self.x + self.width).max(other.x + other.width),
            (self.y + self.height).max(other.y + other.height),
        )
    }

    pub fn contains(self, x: f32, y: f32) -> bool {
        x >= self.x && y >= self.y && x <= self.x + self.width && y <= self.y + self.height
    }
}

/// Цвет после приведения к RGBA. Компоненты от 0 до 1.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Color {
    pub r: f32,
    pub g: f32,
    pub b: f32,
    pub a: f32,
}
