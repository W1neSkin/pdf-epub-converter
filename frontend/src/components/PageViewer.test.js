import { calculatePageScale } from './PageViewer';


describe('calculatePageScale', () => {
  test('shrinks a fixed-layout page to fit the viewer width', () => {
    expect(calculatePageScale(900, 1240)).toBeCloseTo(0.726, 3);
  });

  test('does not enlarge pages that already fit', () => {
    expect(calculatePageScale(1240, 900)).toBe(1);
  });
});
