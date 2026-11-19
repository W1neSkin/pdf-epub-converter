import { fitScanWords, liftTransparentWords } from './scanTextLayer';

function svgWith(words) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '612');
  svg.setAttribute('height', '792');
  svg.setAttribute('viewBox', '0 0 612 792');
  svg.style.width = '612px';
  svg.style.height = '792px';
  words.forEach((word) => {
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('fill', 'transparent');
    text.setAttribute('x', word.x);
    text.setAttribute('y', word.y);
    text.setAttribute('font-size', word.fontSize);
    if (word.textLength) {
      text.setAttribute('textLength', word.textLength);
    }
    text.textContent = word.text;
    svg.appendChild(text);
  });
  const root = document.createElement('div');
  root.appendChild(svg);
  document.body.appendChild(root);
  return root;
}

describe('scan text layer', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('clips a word to its ink box and scales the glyphs to that width', () => {
    const root = svgWith([
      { x: '251.28', y: '89.86', fontSize: '26.50', textLength: '113.04', text: 'INVOICE' },
    ]);
    liftTransparentWords(root.querySelector('svg'));

    const word = root.querySelector('.scan-word');
    expect(word.style.width).toBe('113.04px');
    expect(word.style.letterSpacing).toBe('');
    expect(word.style.overflow).toBe('hidden');
    expect(word.textContent).toBe('INVOICE');

    const glyphs = word.querySelector('.scan-word-text');
    Object.defineProperty(glyphs, 'scrollWidth', { configurable: true, value: 160 });
    fitScanWords(root);
    expect(glyphs.style.transform).toBe(`scaleX(${113.04 / 160})`);
  });

  test('a gap after a word does not keep its own hit box', () => {
    const root = svgWith([
      { x: '78', y: '220', fontSize: '10', textLength: '22', text: 'Item' },
      { x: '100', y: '220', fontSize: '10', text: ' ' },
    ]);
    liftTransparentWords(root.querySelector('svg'));

    const boxes = root.querySelectorAll('.scan-word');
    expect(boxes).toHaveLength(2);
    expect(boxes[1].style.width).toBe('0px');
    expect(boxes[1].style.pointerEvents).toBe('none');
    expect(boxes[1].textContent).toBe(' ');
  });
});
