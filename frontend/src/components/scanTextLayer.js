// Firefox paints SVG text while it is selected, even when fill is transparent.
// Those glyphs are a stand-in font, so they sit off the scan. HTML text with a
// transparent selection color leaves only the highlight, and copying still
// returns the word.

export function liftTransparentWords(svg) {
  const words = svg.querySelectorAll('text[fill="transparent"]');
  if (!words.length || !svg.parentNode) {
    return;
  }

  const box = svg.viewBox && svg.viewBox.baseVal;
  const boxWidth = (box && box.width) || number(svg.getAttribute('width'), 1) || 1;
  const boxHeight = (box && box.height) || number(svg.getAttribute('height'), 1) || 1;
  const pixelWidth = number(svg.style.width, number(svg.getAttribute('width'), boxWidth));
  const pixelHeight = number(svg.style.height, number(svg.getAttribute('height'), boxHeight));
  const scaleX = pixelWidth / boxWidth;
  const scaleY = pixelHeight / boxHeight;

  const layer = svg.ownerDocument.createElement('div');
  layer.className = 'scan-text-layer';
  layer.style.position = 'relative';
  layer.style.width = `${pixelWidth}px`;
  layer.style.height = `${pixelHeight}px`;
  svg.parentNode.insertBefore(layer, svg);
  layer.appendChild(svg);
  svg.style.position = 'absolute';
  svg.style.left = '0';
  svg.style.top = '0';

  words.forEach((word) => {
    const text = word.textContent || '';
    const fontSize = number(word.getAttribute('font-size'), 12) * scaleY;
    const x = number(word.getAttribute('x'), 0) * scaleX;
    const baseline = number(word.getAttribute('y'), 0) * scaleY;
    const textLength = number(word.getAttribute('textLength'), 0) * scaleX;
    const span = svg.ownerDocument.createElement('span');
    span.className = 'scan-word';
    span.textContent = text;
    span.style.position = 'absolute';
    span.style.left = `${x}px`;
    span.style.top = `${baseline - fontSize * 0.8}px`;
    span.style.fontSize = `${fontSize}px`;
    span.style.fontFamily = word.getAttribute('font-family') || 'serif';
    span.style.lineHeight = '1';
    span.style.whiteSpace = 'pre';
    span.style.color = 'transparent';
    span.style.webkitTextFillColor = 'transparent';
    const letters = text.trim();
    if (textLength > 0 && letters.length > 1) {
      const extra = textLength - letters.length * fontSize * 0.5;
      if (extra > 0) {
        span.style.letterSpacing = `${extra / (letters.length - 1)}px`;
      }
    }
    layer.appendChild(span);
    word.remove();
  });
}

function number(value, fallback) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
